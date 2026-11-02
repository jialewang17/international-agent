"""P0 六体裁接入验收脚本：打印路由/加载/注入/失败路径结果，并导出脱敏 Prompt 样例。

用法（不调用真实大模型）：
    ./venv/Scripts/python.exe scripts/p0_acceptance_check.py

产出：
    docs/chinastory_v6.1/P0_prompt_samples/prompt_post_sample.txt
    docs/chinastory_v6.1/P0_prompt_samples/prompt_news_sample.txt
    docs/chinastory_v6.1/P0_prompt_samples/acceptance_report.txt
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools import story_post_gen  # noqa: E402
from tools.genre_router import resolve_selection  # noqa: E402
from utils.genre_contracts import GENRE_CONTRACTS, GENRES, consistency_report  # noqa: E402

import yaml  # noqa: E402

EVIDENCE = [
    {
        "category": "culture",
        "statement": "苏绣于2006年列入国家级非物质文化遗产名录",
        "source": "https://www.ihchina.cn/suxiu",
        "source_type": "本地库",
        "retrieval": "kb",
    },
    {
        "category": "culture",
        "statement": "镇湖绣品街聚集数千名绣娘，双面绣需数月完成",
        "source": "https://www.suzhou.gov.cn/zhenhu",
        "source_type": "本地库",
        "retrieval": "kb",
    },
]

STUB_OUTPUT = {
    "post": {
        "5w": {"who": "culture explainer", "says_what": "living heritage", "channel": "Instagram",
               "to_whom": "craft readers", "effect": "curiosity"},
        "post": "[stub] Suzhou embroidery, one thread two faces.",
        "hashtags": ["#SuzhouEmbroidery"],
        "title_or_hook": "",
        "ops_tips": [],
        "evidence_notes": ["Evidence#1 -> ICH listing"],
    },
    "news": {
        "wire_plan": {"editorial_mode": "institutional_release", "angle": "ICH listing"},
        "headline": "[stub] Suzhou embroidery marks two decades on ICH list",
        "dek": "",
        "dateline": "",
        "article": "[stub] Suzhou embroidery entered the national ICH list in 2006.",
        "quotes_used": [],
        "ops_tips": [],
        "evidence_notes": ["Evidence#1 -> ICH listing"],
    },
}
for _g in ("feature", "indepth", "script", "faq"):
    STUB_OUTPUT[_g] = {
        "genre": _g,
        "title": f"[stub] {_g} title",
        "body": f"[stub] {_g} body grounded in Evidence#1.",
        "ops_tips": [],
        "missing_fields": [],
        "evidence_notes": ["Evidence#1 -> ICH listing"],
    }

PROMPT_FILES = {}


def _install_stubs() -> None:
    story_post_gen.retrieve_statements = lambda *a, **k: EVIDENCE
    story_post_gen.check_theme_evidence_alignment = lambda *a, **k: {"ok": True, "reason": "stub"}

    def fake_llm(prompt: str) -> str:
        PROMPT_FILES[len(PROMPT_FILES)] = prompt
        return json.dumps(STUB_OUTPUT["_current"], ensure_ascii=False)

    story_post_gen._llm_text = fake_llm


def _run(genre: str, **kwargs):
    STUB_OUTPUT["_current"] = STUB_OUTPUT[genre]
    return story_post_gen.run_story_post_generation(theme="苏绣", genre=genre, **kwargs)


def main() -> int:
    lines: list[str] = []

    def say(text: str = "") -> None:
        print(text)
        lines.append(text)

    say("=" * 78)
    say("P0 六体裁接入验收（不调用真实大模型）")
    say("=" * 78)

    cfg = yaml.safe_load((ROOT / "config" / "skills.yaml").read_text(encoding="utf-8"))
    problems = consistency_report(cfg)
    say("")
    say("[1] 映射一致性（genre ↔ skill_id ↔ 方法卡 ↔ format）")
    say(f"    skills.yaml 与契约差异项：{len(problems)}")
    for genre in GENRES:
        c = GENRE_CONTRACTS[genre]
        exists = (ROOT / c.method_path).is_file()
        say(
            f"    {genre:8s} -> {c.skill_id:24s} {c.method_path.split('/')[-1]:12s}"
            f" default={c.default_format:16s} supported={','.join(c.supported_formats):14s}"
            f" file={'OK' if exists else 'MISSING'}"
        )

    _install_stubs()
    say("")
    say("[2] 六体裁真实链路（路由 / 加载 / 注入 / 输出）")
    say(f"    {'genre':9s}{'format':17s}{'路由来源':14s}{'加载':6s}{'注入字符':8s}{'状态':8s}{'正文':6s}字段")
    for genre in GENRES:
        result = _run(genre)
        diag = result.get("skill_load", {})
        prompt = PROMPT_FILES[max(PROMPT_FILES)] if PROMPT_FILES else ""
        card_injected = f"### TeamSkill::{GENRE_CONTRACTS[genre].skill_id}" in prompt
        other_injected = [
            g for g in GENRES
            if g != genre and f"### TeamSkill::{GENRE_CONTRACTS[g].skill_id}" in prompt
        ]
        field_note = {
            "post": f"hashtags={len(result.get('hashtags') or [])}",
            "news": f"headline={'Y' if result.get('headline') else 'N'}",
        }.get(genre, "article=%s" % ("Y" if result.get("article") else "N"))
        say(
            f"    {genre:9s}{str(result.get('format')):17s}"
            f"{str(diag.get('routing_source')):14s}"
            f"{str(diag.get('load_status')):6s}"
            f"{diag.get('skill_chars', 0):<8d}{result.get('generation_status'):8s}"
            f"{'Y' if result.get('post') else 'N':6s}{field_note}"
        )
        say(
            f"              loaded_method={diag.get('loaded_method_id')} "
            f"files={diag.get('loaded_files')} 仅注入本体裁卡={card_injected and not other_injected}"
        )

    say("")
    say("[3] 失败路径（必须显式失败，不得伪装成功）")
    cases = [
        ("非法体裁 genre=story", dict(genre="story")),
        ("体裁/格式冲突 news+social_post", dict(genre="news", format="social_post")),
        ("未实现格式 post+thread", dict(genre="post", format="thread")),
    ]
    for label, kwargs in cases:
        STUB_OUTPUT["_current"] = STUB_OUTPUT["post"]
        before = len(PROMPT_FILES)
        result = story_post_gen.run_story_post_generation(theme="苏绣", **kwargs)
        say(
            f"    {label:34s} -> status={result.get('generation_status'):24s} "
            f"post={'非空' if result.get('post') else '空'} "
            f"调用模型={'是' if len(PROMPT_FILES) > before else '否'}"
        )

    say("")
    say("[4] 显式选择优先于关键词")
    for theme, genre in [("写一篇苏绣的深度报道", "post"), ("写一条 instagram 帖文介绍苏绣", "indepth")]:
        sel = resolve_selection(genre=genre, text=theme)
        say(f"    theme={theme!r} + genre={genre} -> {sel.genre} (source={sel.source})")

    out_dir = ROOT / "docs" / "chinastory_v6.1" / "P0_prompt_samples"
    out_dir.mkdir(parents=True, exist_ok=True)

    PROMPT_FILES.clear()
    _run("post")
    (out_dir / "prompt_post_sample.txt").write_text(
        PROMPT_FILES[max(PROMPT_FILES)], encoding="utf-8"
    )
    PROMPT_FILES.clear()
    _run("news")
    (out_dir / "prompt_news_sample.txt").write_text(
        PROMPT_FILES[max(PROMPT_FILES)], encoding="utf-8"
    )

    say("")
    say(f"[5] 已导出脱敏 Prompt 组装样例：{out_dir.relative_to(ROOT)}")
    for name in ("prompt_post_sample.txt", "prompt_news_sample.txt"):
        path = out_dir / name
        say(f"    {name}: {len(path.read_text(encoding='utf-8'))} 字符")

    (out_dir / "acceptance_report.txt").write_text("\n".join(lines), encoding="utf-8")
    print()
    print(f"验收记录已写入：{(out_dir / 'acceptance_report.txt').relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
