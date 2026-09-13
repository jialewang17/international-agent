# -*- coding: utf-8 -*-
"""Run materials-flex cases: with materials; optional ablation without materials."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.story_post_gen import run_story_post_generation  # noqa: E402
from utils.skill_registry import clear_skill_registry_cache  # noqa: E402

CASES = ROOT / "eval" / "skill_eval_cases_v0.4_materials_flex.csv"
OUT = ROOT / "eval" / "outputs_materials_flex_v04"
OUT.mkdir(parents=True, exist_ok=True)


def _run_one(r: dict, *, with_materials: bool) -> dict:
    full = (r["用户输入Prompt（完整）"] or "").strip()
    angle = (r.get("解析theme") or "").strip()
    mats = (r.get("用户资料（粘贴）") or "").strip() if with_materials else ""
    # for ablation keep prompt but strip "必须使用资料" pressure slightly? keep same prompt for fair gain test
    result = run_story_post_generation(
        theme=angle or full,
        user_brief=full,
        user_materials=mats or None,
        country=r.get("country") or "America",
        platform=r.get("platform") or "instagram",
        identity=r.get("identity") or "online_influencer",
        tone=r.get("tone") or "optimistic",
        max_words=int(r.get("max_words") or 80),
        language=r.get("language") or "English",
        use_emoji=True,
    )
    return result


def main(ids: list[str] | None = None, ablation_only: bool = False):
    clear_skill_registry_cache()
    rows = list(csv.DictReader(CASES.open(encoding="utf-8-sig")))
    if ids:
        rows = [r for r in rows if r["测试ID"] in set(ids)]
    for r in rows:
        cid = r["测试ID"]
        do_ablation = (r.get("是否无资料对照") or "") == "是"
        modes = []
        if not ablation_only:
            modes.append(("with", True))
        if do_ablation:
            modes.append(("ablate", False))
        if not modes:
            modes = [("with", True)]
        for tag, with_m in modes:
            print(f"== {cid}/{tag} ==")
            try:
                result = _run_one(r, with_materials=with_m)
            except Exception as e:  # noqa: BLE001
                result = {"error": str(e), "post": "", "evidence_used": []}
            result["_meta"] = {
                "id": cid,
                "mode": tag,
                "with_materials": with_m,
                "prompt_style": r.get("提示词形态"),
                "full_prompt": r.get("用户输入Prompt（完整）"),
                "anchors": r.get("专有锚点（必须命中,分号分隔）"),
                "forbid": r.get("越界禁止（分号分隔）"),
                "prompt_slots": r.get("prompt_slots"),
                "narrative_directive": r.get("narrative_directive"),
                "hard_constraints": r.get("hard_constraints"),
                "material_use_directive": r.get("material_use_directive"),
                "expect": r.get("用户要求（本条预期）"),
                "focus": r.get("评分重点"),
                "expect_block": "expect_block" in (r.get("hard_constraints") or ""),
            }
            path = OUT / f"{cid}_{tag}.json"
            path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            print(
                " err=",
                bool(result.get("error")),
                " post_len=",
                len(result.get("post") or ""),
                " user_ev=",
                (result.get("evidence_stats") or {}).get("user"),
            )


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a.startswith("MF")]
    ablation_only = "--ablation-only" in sys.argv
    main(args or None, ablation_only=ablation_only)
