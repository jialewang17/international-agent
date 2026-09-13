"""联测：用户资料 + 5W/受众/权威质量。"""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.story_post_gen import run_story_post_generation  # noqa: E402

CASES = ROOT / "eval" / "skill_eval_cases_v0.4_joint.csv"
OUT = ROOT / "eval" / "outputs_joint_v04"
OUT.mkdir(parents=True, exist_ok=True)


def main(ids: list[str] | None = None):
    rows = list(csv.DictReader(CASES.open(encoding="utf-8-sig")))
    if ids:
        rows = [r for r in rows if r["测试ID"] in set(ids)]
    for r in rows:
        cid = r["测试ID"]
        full = (r["用户输入Prompt（完整）"] or "").strip()
        angle = (r.get("解析theme") or "").strip()
        mats = (r.get("用户资料（粘贴）") or "").strip()
        print(f"== {cid} ==")
        try:
            result = run_story_post_generation(
                theme=angle or full,
                user_brief=full,
                user_materials=mats or None,
                country=r.get("country") or "America",
                platform=r.get("platform") or "instagram",
                identity=r.get("identity") or "online_influencer",
                tone=r.get("tone") or "optimistic",
                max_words=int(r.get("max_words") or 80),
            )
        except Exception as e:
            result = {"error": str(e), "post": "", "five_w": {}, "evidence_used": []}
        result["_meta"] = {
            "id": cid,
            "prompt_style": r.get("提示词形态"),
            "full_prompt": full,
            "expect": r.get("用户要求（本条预期）"),
            "focus": r.get("评分重点"),
            "has_materials": bool(mats),
            "expect_block": cid in {"J11", "J12"},
        }
        (OUT / f"{cid}.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(
            " err=",
            bool(result.get("error")),
            " stats=",
            result.get("evidence_stats"),
            " post_len=",
            len(result.get("post") or ""),
        )


if __name__ == "__main__":
    arg_ids = [a for a in sys.argv[1:] if a.startswith("J")]
    main(arg_ids or None)
