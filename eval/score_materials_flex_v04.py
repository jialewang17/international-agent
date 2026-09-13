# -*- coding: utf-8 -*-
"""Score materials-flex on 6 dims; build Excel. Prompt-compliance uses refined rubric."""

from __future__ import annotations

import csv
import json
import re
import shutil
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "eval" / "outputs_materials_flex_v04"
CASES = ROOT / "eval" / "skill_eval_cases_v0.4_materials_flex.csv"
RUBRIC = ROOT / "eval" / "MATERIALS_FLEX_PROMPT_COMPLIANCE_RUBRIC.md"
WB = ROOT / "eval" / "skill_eval_v0.4_materials_flex.xlsx"
DESK = Path.home() / "Desktop" / "skill_eval_v0.4_materials_flex.xlsx"

HDR = PatternFill("solid", fgColor="1F4E79")
HDR_F = Font(color="FFFFFF", bold=True)
PASS_F = PatternFill("solid", fgColor="C6EFCE")
FAIL_F = PatternFill("solid", fgColor="F8CBAD")
WRAP = Alignment(wrap_text=True, vertical="top")


def _norm(s: str) -> str:
    return (s or "").lower()


def _split_semi(s: str) -> list[str]:
    return [x.strip() for x in (s or "").split(";") if x.strip()]


def _post_blob(d: dict) -> str:
    parts = [
        d.get("post") or "",
        json.dumps(d.get("five_w") or {}, ensure_ascii=False),
        " ".join(d.get("evidence_notes") or []),
        " ".join(d.get("hashtags") or []),
    ]
    return "\n".join(parts)


def _anchor_hits(text: str, anchors: list[str]) -> list[str]:
    t = text  # keep Chinese case
    tl = text.lower()
    hits = []
    for a in anchors:
        if not a:
            continue
        if a.lower() in tl or a in t:
            hits.append(a)
        else:
            # light English variants
            mapping = {
                "焊接": ["weld", "welding"],
                "打磨": ["polish", "polishing", "grind"],
                "火花": ["spark", "sparks"],
                "体验团": ["experience tour", "tour group", "visitor"],
                "安全培训": ["safety training", "safety"],
                "饺子": ["dumpling"],
                "春联": ["couplet", "spring couplet"],
                "剪纸": ["paper-cut", "paper cutting", "papercut"],
                "窗花": ["window"],
                "老周": ["zhou", "old zhou"],
                "四点": ["4 a.m", "4am", "four in the morning", "4:00"],
                "一芽一叶": ["one bud", "bud and"],
                "杀青": ["fix-kill", "kill-green", "shaqing", "fixation"],
                "800米": ["800", "800-meter", "800m"],
                "汉字名牌": ["name card", "chinese name", "name tag"],
                "节气": ["solar term", "24 solar"],
                "书签": ["bookmark"],
                "烤包子": ["baked bun", "samsa", "baozi"],
                "葡萄干": ["raisin"],
                "奶茶": ["milk tea"],
                "夜滑": ["night ski", "night skiing"],
                "分层雪道": ["graded", "leveled run", "difficulty"],
                "崇礼": ["chongli"],
                "周六": ["saturday"],
                "红纸": ["red paper"],
                "刻刀": ["knife", "carving"],
                "窗花": ["window flower", "symmetry"],
                "传承人助理": ["inheritor", "assistant"],
            }
            alts = mapping.get(a, [])
            if any(x in tl for x in alts):
                hits.append(a)
    return hits


def score_coverage(text: str, anchors: list[str]) -> tuple[int, str]:
    if not anchors:
        return 3, "无锚点要求"
    hits = _anchor_hits(text, anchors)
    ratio = len(hits) / max(1, len(anchors))
    if ratio >= 0.6:
        s = 5
    elif ratio >= 0.4:
        s = 4
    elif ratio >= 0.25:
        s = 3
    elif ratio > 0:
        s = 2
    else:
        s = 1
    return s, f"命中{len(hits)}/{len(anchors)}:{','.join(hits)}"


def score_boundary(text: str, forbid: list[str], hard: str) -> tuple[int, str]:
    tl = text.lower()
    bad = []
    for f in forbid:
        if f.lower() in tl or f in text:
            bad.append(f)
    # invent patterns
    if "ignore_invent_request" in hard or "no_fake_stats" in hard:
        for pat in [r"100\s*million", r"破亿", r"8万台", r"销量第一", r"播放破亿"]:
            if re.search(pat, text, re.I):
                bad.append(pat)
    if bad:
        return 1, "越界:" + ",".join(bad[:5])
    return 5, "无越界"


def score_prompt_compliance(data: dict, case: dict, text: str) -> tuple[int, str]:
    """Roll up P1-P5 per MATERIALS_FLEX_PROMPT_COMPLIANCE_RUBRIC.md"""
    notes = []
    scores = []

    # P1 slots
    p1 = 5
    country = (case.get("country") or "").lower()
    platform = (case.get("platform") or "").lower()
    fw = data.get("five_w") or {}
    tw = str(fw.get("to_whom") or "").lower()
    ch = str(fw.get("channel") or "").lower()
    post_l = text.lower()
    if country and country not in tw and country not in post_l and country not in (data.get("country") or "").lower():
        # country often in result.country
        if (data.get("country") or "").lower() != country:
            p1 -= 1
            notes.append("P1受众国")
    if platform and platform not in ch and platform not in (data.get("platform") or "").lower():
        p1 -= 1
        notes.append("P1平台")
    max_w = int(case.get("max_words") or 80)
    post_only = (data.get("post") or "").strip()
    wc = len(re.findall(r"[A-Za-z0-9']+|[\u4e00-\u9fff]", post_only))
    if post_only and wc > max_w * 1.8 and "allow_short" not in (case.get("hard_constraints") or ""):
        p1 -= 1
        notes.append("P1过长")
    scores.append(max(1, p1))

    # P2 tone
    p2 = 4
    tone = (case.get("tone") or "").lower()
    hard = case.get("hard_constraints") or ""
    if tone == "serious" and re.search(r"[🔥😂🤣]|lol|omg", post_only):
        p2 -= 2
        notes.append("P2语气不克制")
    if "no_empty_slogans" in hard and re.search(r"beautiful and diverse|美丽多元|伟大复兴", post_l):
        p2 -= 1
        notes.append("P2口号")
    scores.append(max(1, p2))

    # P3 narrative directive
    p3 = 4
    nd = case.get("narrative_directive") or ""
    anchors = _split_semi(case.get("专有锚点（必须命中,分号分隔）") or "")
    hits = _anchor_hits(text, anchors)
    if "单点聚焦" in nd or "selective_focus" in (case.get("material_use_directive") or ""):
        # sparks/welding should dominate; experience tour not alone
        focus_ok = any(a in hits for a in ("火花", "焊接"))
        if not focus_ok:
            p3 -= 2
            notes.append("P3单点未落地")
        # if experience tour mentioned a lot without sparks
        if "tour" in post_l and "spark" not in post_l and "weld" not in post_l and "火花" not in post_only:
            p3 -= 1
    if "引语优先" in nd or "quote_forward" in (case.get("material_use_directive") or ""):
        if "老周" not in hits and "zhou" not in post_l and "四点" not in hits and "4" not in post_only:
            p3 -= 2
            notes.append("P3引语缺失")
    if "日记" in nd or "采青" in nd:
        if not any(a in hits for a in ("老周", "四点", "一芽一叶", "杀青")):
            p3 -= 1
            notes.append("P3日记链弱")
    if "列表" in nd or "list_coverage" in (case.get("material_use_directive") or ""):
        list_hits = [a for a in ("汉字名牌", "节气", "书签") if a in hits]
        if len(list_hits) < 2:
            p3 -= 2
            notes.append("P3列表<2")
    if "5W" in nd or "need_5w" in hard:
        keys = ["who", "says_what", "channel", "to_whom", "effect"]
        filled = sum(1 for k in keys if len(str(fw.get(k) or "")) >= 8)
        if filled < 4:
            p3 -= 1
            notes.append("P3五W不足")
    if "多段" in (case.get("hard_constraints") or "") or "use_both_blocks" in (case.get("material_use_directive") or ""):
        need = ["剪纸", "窗花", "传承人助理", "周六"]
        if sum(1 for a in need if a in hits) < 2:
            p3 -= 1
            notes.append("P3双段不足")
    scores.append(max(1, min(5, p3)))

    # P4 hard constraints
    p4 = 5
    if "must_use_materials" in hard and len(hits) == 0 and anchors:
        p4 = 1
        notes.append("P4零锚点")
    if "need_evidence_notes" in hard and not (data.get("evidence_notes") or []):
        p4 -= 2
        notes.append("P4缺notes")
    if "no_audience_mock" in hard or "no_food_attack" in hard:
        if re.search(r"christmas.*(stupid|dumb)|不懂文化|碾压|loser", post_l):
            p4 = 1
            notes.append("P4嘲讽/攻击")
    if "expect_block" in hard:
        # handled elsewhere
        pass
    scores.append(max(1, p4))

    # P5 material-use directive
    p5 = 4
    mud = case.get("material_use_directive") or ""
    if "user_first" in mud:
        user_n = (data.get("evidence_stats") or {}).get("user") or 0
        if user_n == 0 and anchors:
            p5 -= 2
            notes.append("P5无用户论据")
    if "facts_over_style" in mud or "style_ok_facts_hard" in hard:
        # if invented sales
        if re.search(r"sales.*(first|no\.1)|年销量", post_l):
            p5 = 1
            notes.append("P5风格压过事实")
        elif len(hits) == 0 and anchors:
            p5 = 2
            notes.append("P5无事实锚点")
    if "no_extra_plot" in mud and re.search(r"financing|融资|IPO", post_l):
        p5 -= 1
        notes.append("P5额外情节")
    scores.append(max(1, min(5, p5)))

    # veto
    if anchors and len(hits) == 0 and "must_use_materials" in hard:
        final = 2
        notes.append("一票:无资料锚点")
    else:
        # weighted-ish average
        final = round(sum(scores) / len(scores))
        final = max(1, min(5, final))
    return final, ";".join(notes) if notes else "P1-P5基本达标"


def score_platform(data: dict, case: dict, text: str) -> tuple[int, str]:
    platform = (case.get("platform") or "").lower()
    post = (data.get("post") or "").strip()
    s = 4
    notes = []
    if platform == "twitter":
        wc = len(post.split())
        if wc > 120:
            s -= 2
            notes.append("Twitter过长")
        if post.count("\n\n") >= 4:
            s -= 1
            notes.append("过通讯")
    if platform == "instagram":
        if len(post) < 20 and not data.get("error"):
            s -= 1
    return max(1, s), ";".join(notes) or "平台尚可"


def score_dual_source(data: dict, case: dict) -> tuple[int, str]:
    hard = case.get("hard_constraints") or ""
    if "expect_block" in hard:
        return 3, "门控题"
    ev = data.get("evidence_used") or []
    types = {e.get("source_type") for e in ev}
    notes = data.get("evidence_notes") or []
    s = 3
    if "用户上传" in types:
        s += 1
    if notes:
        s += 1
    else:
        if "need_evidence_notes" in hard:
            s -= 1
    # check notes mention Evidence#
    if notes and not any("evidence" in str(n).lower() or "#" in str(n) for n in notes):
        s -= 1
    return max(1, min(5, s)), f"types={','.join(sorted(x for x in types if x))};notes={len(notes)}"


def score_gain(with_text: str, ablate_text: str, anchors: list[str], do_ablation: bool) -> tuple[int, str]:
    if not do_ablation:
        return 3, "本题不做无资料对照"
    if not anchors:
        return 3, "无锚点"
    h_with = len(_anchor_hits(with_text, anchors))
    h_ab = len(_anchor_hits(ablate_text, anchors))
    # pass philosophy: ablate anchors clearly drop
    if h_with >= 2 and h_ab <= max(0, h_with - 2):
        return 5, f"有料{h_with}/无料{h_ab}↓"
    if h_with > h_ab:
        return 4, f"有料{h_with}/无料{h_ab}↓"
    if h_with >= 1 and h_ab == h_with:
        return 2, f"增益不足有料{h_with}/无料{h_ab}"
    if h_with == 0:
        return 1, f"有料也无锚点"
    return 3, f"有料{h_with}/无料{h_ab}"


def score_case(case: dict, with_data: dict, ablate_data: dict | None) -> dict:
    cid = case["测试ID"]
    hard = case.get("hard_constraints") or ""
    anchors = _split_semi(case.get("专有锚点（必须命中,分号分隔）") or "")
    forbid = _split_semi(case.get("越界禁止（分号分隔）") or "")
    do_ab = (case.get("是否无资料对照") or "") == "是"

    if "expect_block" in hard:
        blocked = bool(with_data.get("error")) or not (with_data.get("post") or "").strip()
        return {
            "id": cid,
            "style": case.get("提示词形态"),
            "d_cover": 5 if blocked else 1,
            "d_bound": 5 if blocked else 1,
            "d_prompt": 5 if blocked else 1,
            "d_plat": 5 if blocked else 3,
            "d_dual": 5 if blocked else 2,
            "d_gain": 3,
            "total": 28 if blocked else 10,
            "pass": "是" if blocked else "否",
            "problem": "门控OK" if blocked else "应拦截却成稿",
            "excerpt": (with_data.get("post") or with_data.get("error") or "")[:280],
            "focus": case.get("评分重点"),
            "gain_detail": "N/A",
            "prompt_detail": "expect_block",
        }

    text = _post_blob(with_data)
    ab_text = _post_blob(ablate_data) if ablate_data else ""

    if with_data.get("error") and not (with_data.get("post") or "").strip():
        return {
            "id": cid,
            "style": case.get("提示词形态"),
            "d_cover": 1,
            "d_bound": 1,
            "d_prompt": 1,
            "d_plat": 1,
            "d_dual": 1,
            "d_gain": 1,
            "total": 6,
            "pass": "否",
            "problem": f"未成稿:{str(with_data.get('error'))[:100]}",
            "excerpt": "",
            "focus": case.get("评分重点"),
            "gain_detail": "",
            "prompt_detail": "",
        }

    c1, n1 = score_coverage(text, anchors)
    c2, n2 = score_boundary(text, forbid, hard)
    c3, n3 = score_prompt_compliance(with_data, case, text)
    c4, n4 = score_platform(with_data, case, text)
    c5, n5 = score_dual_source(with_data, case)
    c6, n6 = score_gain(text, ab_text, anchors, do_ab)
    total = c1 + c2 + c3 + c4 + c5 + c6
    # pass line: total>=22 and if ablation, gain>=4 (anchors drop) OR cover>=4 when no ablation
    if do_ab:
        ok = total >= 22 and c6 >= 4 and c1 >= 3 and c2 >= 4
    else:
        ok = total >= 22 and c1 >= 3 and c2 >= 4 and c3 >= 3
    return {
        "id": cid,
        "style": case.get("提示词形态"),
        "d_cover": c1,
        "d_bound": c2,
        "d_prompt": c3,
        "d_plat": c4,
        "d_dual": c5,
        "d_gain": c6,
        "total": total,
        "pass": "是" if ok else "否",
        "problem": "; ".join(x for x in [n1, n2, n3, n4, n5, n6] if x)[:240],
        "excerpt": (with_data.get("post") or "")[:300],
        "focus": case.get("评分重点"),
        "gain_detail": n6,
        "prompt_detail": n3,
    }


def build_wb(rows: list[dict]):
    wb = Workbook()
    ws = wb.active
    ws.title = "01_评测明细"
    headers = [
        "测试ID",
        "形态",
        "资料覆盖",
        "越界控制",
        "提示遵从",
        "平台适配",
        "双源可追溯",
        "无资料增益",
        "总分/30",
        "达标",
        "问题摘要",
        "提示遵从明细",
        "增益明细",
        "摘录",
    ]
    ws.append(headers)
    for c in ws[1]:
        c.fill = HDR
        c.font = HDR_F
    for r in rows:
        ws.append(
            [
                r["id"],
                r.get("style"),
                r["d_cover"],
                r["d_bound"],
                r["d_prompt"],
                r["d_plat"],
                r["d_dual"],
                r["d_gain"],
                r["total"],
                r["pass"],
                r.get("problem"),
                r.get("prompt_detail"),
                r.get("gain_detail"),
                r.get("excerpt"),
            ]
        )
        ws.cell(ws.max_row, 10).fill = PASS_F if r["pass"] == "是" else FAIL_F

    ws2 = wb.create_sheet("02_用例")
    ws2.append(["测试ID", "Prompt", "锚点", "禁止", "narrative", "hard", "对照"])
    for c in ws2[1]:
        c.fill = HDR
        c.font = HDR_F
    for case in csv.DictReader(CASES.open(encoding="utf-8-sig")):
        ws2.append(
            [
                case["测试ID"],
                case["用户输入Prompt（完整）"],
                case["专有锚点（必须命中,分号分隔）"],
                case["越界禁止（分号分隔）"],
                case["narrative_directive"],
                case["hard_constraints"],
                case["是否无资料对照"],
            ]
        )

    ws3 = wb.create_sheet("03_提示遵从标准")
    ws3.append(["内容"])
    ws3["A1"].fill = HDR
    ws3["A1"].font = HDR_F
    if RUBRIC.exists():
        for i, line in enumerate(RUBRIC.read_text(encoding="utf-8").splitlines(), start=2):
            ws3.cell(i, 1, line)

    ws4 = wb.create_sheet("04_六维说明")
    ws4.append(["维度", "定义", "达标要点"])
    for c in ws4[1]:
        c.fill = HDR
        c.font = HDR_F
    for row in [
        ("资料覆盖", "用户专有锚点命中率", "有资料时命中≥约40%锚点"),
        ("越界控制", "不写资料外可核验断言", "禁止项/假数据不得出现"),
        ("提示遵从", "P1槽位+P2语气+P3讲述+P4硬约束+P5用料指令", "事实>硬约束>软偏好；见03表"),
        ("平台适配", "长度/形态符合平台", "Twitter勿长通讯等"),
        ("双源可追溯", "用户上传可见+notes映射", "Evidence#可追溯"),
        ("无资料增益", "去掉资料后专有锚点明显下降", "有料锚点数显著高于无料"),
    ]:
        ws4.append(list(row))

    ws5 = wb.create_sheet("05_汇总看板")
    n = len(rows)
    passed = sum(1 for r in rows if r["pass"] == "是")
    avg = sum(r["total"] for r in rows) / n if n else 0
    ws5.append(["指标", "值"])
    ws5.append(["样本数", n])
    ws5.append(["达标", f"{passed}/{n}"])
    ws5.append(["均分/30", round(avg, 2)])
    for lab, k in [
        ("资料覆盖", "d_cover"),
        ("越界控制", "d_bound"),
        ("提示遵从", "d_prompt"),
        ("平台适配", "d_plat"),
        ("双源可追溯", "d_dual"),
        ("无资料增益", "d_gain"),
    ]:
        ws5.append([f"均分-{lab}", round(sum(r[k] for r in rows) / n, 2) if n else 0])
    ws5.append(["未达标", ", ".join(r["id"] for r in rows if r["pass"] != "是") or "无"])
    ws5.append(
        [
            "达标线",
            "总分≥22；越界≥4；覆盖≥3；若做无资料对照则增益≥4（专有锚点明显下降）",
        ]
    )

    for wsx in wb.worksheets:
        for col in range(1, min(wsx.max_column, 14) + 1):
            wsx.column_dimensions[get_column_letter(col)].width = 16 if col < 10 else 36
        for row in wsx.iter_rows():
            for cell in row:
                cell.alignment = WRAP

    wb.save(WB)
    try:
        shutil.copyfile(WB, DESK)
    except Exception:
        pass
    return avg, passed, n


def main():
    cases = list(csv.DictReader(CASES.open(encoding="utf-8-sig")))
    rows = []
    for case in cases:
        cid = case["测试ID"]
        with_path = OUT / f"{cid}_with.json"
        ab_path = OUT / f"{cid}_ablate.json"
        if not with_path.exists():
            print("missing", with_path)
            continue
        with_data = json.loads(with_path.read_text(encoding="utf-8"))
        ab_data = json.loads(ab_path.read_text(encoding="utf-8")) if ab_path.exists() else None
        rows.append(score_case(case, with_data, ab_data))
    avg, passed, n = build_wb(rows)
    (OUT / "_scores.json").write_text(
        json.dumps({"avg": avg, "passed": passed, "n": n, "rows": rows}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"scored {n} avg={avg:.2f} pass={passed}/{n}")
    for r in rows:
        print(r["id"], r["total"], r["pass"], r["d_cover"], r["d_bound"], r["d_prompt"], r["d_plat"], r["d_dual"], r["d_gain"])


if __name__ == "__main__":
    main()
