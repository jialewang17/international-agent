"""Run v0.3.2 output-quality cases (diverse long/short prompts). Focus: 5W / audience / authority — not gate."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.story_post_gen import run_story_post_generation  # noqa: E402

CASES = ROOT / "eval" / "skill_eval_cases_v0.3.2_quality.csv"
OUT = ROOT / "eval" / "outputs_quality_v032"
OUT.mkdir(parents=True, exist_ok=True)


def main(ids: list[str] | None = None):
    rows = list(csv.DictReader(CASES.open(encoding="utf-8-sig")))
    if ids:
        want = set(ids)
        rows = [r for r in rows if r["测试ID"] in want]
    for r in rows:
        cid = r["测试ID"]
        # 关键：把「完整用户提示词」作为 theme，模拟真实问法；结构化字段作参数
        full_prompt = (r["用户输入Prompt（完整）"] or "").strip()
        angle = (r.get("解析theme") or "").strip()
        # 检索用故事角度；成稿吃完整问法（长短/口语/英文等）
        kwargs = {
            "theme": angle or full_prompt,
            "user_brief": full_prompt,
            "country": r.get("country") or "America",
            "platform": r.get("platform") or "instagram",
            "identity": r.get("identity") or "online_influencer",
            "tone": r.get("tone") or "optimistic",
            "max_words": int(r.get("max_words") or 80),
            "language": "English",
            "use_emoji": True,
        }
        print(f"== {cid} {r.get('提示词形态')} ==")
        try:
            result = run_story_post_generation(**kwargs)
        except Exception as e:
            result = {"error": str(e), "post": "", "five_w": {}, "evidence_used": []}
        result["_meta"] = {
            "id": cid,
            "prompt_style": r.get("提示词形态"),
            "full_prompt": full_prompt,
            "expect": r.get("用户要求（本条预期）"),
            "focus": r.get("评分重点"),
            "parsed_theme": r.get("解析theme"),
            "pair": r.get("稳定配对") or "",
        }
        path = OUT / f"{cid}.json"
        path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(
            "  err=",
            bool(result.get("error")),
            " post_len=",
            len(result.get("post") or ""),
            " 5w_keys=",
            list((result.get("five_w") or {}).keys()),
        )


if __name__ == "__main__":
    arg_ids = [a for a in sys.argv[1:] if a.startswith("Q")]
    main(arg_ids or None)
