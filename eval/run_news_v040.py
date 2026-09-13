# -*- coding: utf-8 -*-
"""Run news-wire skill eval cases (v0.4 news)."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.story_post_gen import run_story_post_generation  # noqa: E402
from utils.skill_registry import clear_skill_registry_cache  # noqa: E402

CASES = ROOT / "eval" / "skill_eval_cases_v0.4_news.csv"
OUT = ROOT / "eval" / "outputs_news_v040"
OUT.mkdir(parents=True, exist_ok=True)

GATE_IDS = {"N11"}


def main(ids: list[str] | None = None):
    clear_skill_registry_cache()
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
                platform="facebook",
                identity=r.get("identity") or "political_commentator",
                tone=r.get("tone") or "optimistic",
                max_words=int(r.get("max_words") or 650),
                language=r.get("language") or "English",
                use_emoji=False,
            )
        except Exception as e:  # noqa: BLE001
            result = {"error": str(e), "post": "", "article": "", "genre": "?", "evidence_used": []}
        result["_meta"] = {
            "id": cid,
            "prompt_style": r.get("提示词形态"),
            "full_prompt": full,
            "expect": r.get("用户要求（本条预期）"),
            "focus": r.get("评分重点"),
            "has_materials": bool(mats),
            "expect_block": cid in GATE_IDS,
            "round": "r1",
        }
        (OUT / f"{cid}.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        art = result.get("article") or result.get("post") or ""
        print(
            " genre=",
            result.get("genre"),
            " err=",
            bool(result.get("error")),
            " len=",
            len(art),
            " skills=",
            result.get("skills_applied"),
        )


if __name__ == "__main__":
    arg_ids = [a for a in sys.argv[1:] if a.startswith("N")]
    main(arg_ids or None)
