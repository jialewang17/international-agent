"""v0.4 用户论据：无 LLM 冒烟 + 可选 3 条成稿抽检。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.user_materials import merge_evidence, normalize_user_materials  # noqa: E402
from tools.kb_local import check_theme_evidence_alignment, retrieve_statements  # noqa: E402


def test_normalize():
    raw = "第一段关于焊接工坊的介绍，足够长。\n\n第二段体验团安全培训说明，也足够长。\n---\n第三段夜间加班火花场景描述。"
    items = normalize_user_materials(raw, theme="张铁机车")
    assert len(items) >= 2, items
    assert all(i["source_type"] == "用户上传" for i in items)
    print("OK normalize", len(items))


def test_merge_and_gate():
    user = normalize_user_materials(
        "崇礼雪场夜滑体验，缆车仍有冬奥遗产标识，教练强调分层雪道安全。",
        theme="崇礼冬奥场馆大众滑雪",
    )
    local = retrieve_statements(["sports", "culture"], limit_per_cat=2, query="崇礼 冬奥")
    merged = merge_evidence(user, local)
    assert any(e["source_type"] == "用户上传" for e in merged)
    print("OK merge", {"total": len(merged), "user": sum(1 for e in merged if e["source_type"] == "用户上传")})

    bad = normalize_user_materials("曼联本场控球58%，右路传中效率提升。", theme="曼联战术分析")
    local2 = retrieve_statements(["sports"], limit_per_cat=1, query="曼联 战术")
    merged2 = merge_evidence(bad, local2)
    al = check_theme_evidence_alignment("曼联本轮战术分析与积分走势", merged2)
    assert not al.get("ok"), al
    print("OK gate blocks football", al.get("reason"))


def test_optional_llm(n: int = 3):
    from tools.story_post_gen import run_story_post_generation

    cases = [
        (
            "张铁机车海外社媒短帖——车间烟火气与匠人日常",
            "张铁机车是中国定制机车工坊，保留手工焊接；2024年接待欧美体验团并要求安全培训。",
        ),
        (
            "曼联本轮战术分析与积分走势",
            "曼联中场压迫加强；预期控球58%。",
        ),
        (
            "春节作为联合国教科文组织人类非物质文化遗产的当代生活意义",
            "",
        ),
    ]
    out_dir = ROOT / "eval" / "outputs_evidence_v04"
    out_dir.mkdir(parents=True, exist_ok=True)
    for i, (theme, mats) in enumerate(cases[:n], 1):
        r = run_story_post_generation(theme=theme, user_materials=mats or None, max_words=80)
        path = out_dir / f"smoke_E{i:02d}.json"
        path.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
        stats = r.get("evidence_stats")
        print(
            f"LLM E{i:02d}",
            "err=" + str(bool(r.get("error"))),
            "stats=",
            stats,
            "skills=",
            r.get("skills_applied"),
            "post_len=",
            len(r.get("post") or ""),
        )


if __name__ == "__main__":
    test_normalize()
    test_merge_and_gate()
    if "--llm" in sys.argv:
        test_optional_llm()
    print("smoke done")
