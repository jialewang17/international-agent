#!/usr/bin/env python3
"""生成「脱敏追溯样例」：把真实运行结果里的 step_audit 落成可复核的 JSON。

为什么要有这个脚本
------------------
任务书要求"追溯样例"。样例如果手写，就等于自己证明自己。所以这里**调用真实代码**：

* 生成侧：``run_story_post_generation``，模型调用用固定替身（不联网、不花钱），
  产出一条成功样例 + 一条在 C05 被拦下的失败样例；
* 评测侧：``evaluate_part3_with_audit``，裁判用 StubJudge（不调用真模型），
  产出一条成功样例 + 一条偏移不一致被拦下的失败样例。

产物写到 ``docs/chinastory_v6.1/step_trace_samples/``，并在同目录 README 里说明
「哪些字段是真实的、哪些是替身给的」，避免把样例当成真实模型效果。

用法::

    python scripts/make_step_trace_samples.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

OUT_DIR = PROJECT_ROOT / "docs" / "chinastory_v6.1" / "step_trace_samples"

POST_PAYLOAD = {
    "genre": "post",
    "title_or_hook": "一根线的两面",
    "five_w": {
        "who": "苏州镇湖的绣娘",
        "what": "双面绣",
        "when": "2026年秋",
        "where": "江苏苏州镇湖绣品街",
        "why": "国家级非物质文化遗产的活态传承",
    },
    "post": (
        "In Zhenhu, one thread carries two faces. Suzhou embroidery was listed as "
        "national intangible cultural heritage in 2006; today the workshops still "
        "train new embroiderers."
    ),
    "hashtags": ["#SuzhouEmbroidery", "#IntangibleHeritage"],
    "ops_tips": [],
    "evidence_notes": ["Evidence#1 -> ICH listing", "Evidence#2 -> Zhenhu street"],
}


def _stub_llm(prompt: str) -> str:
    return json.dumps(POST_PAYLOAD, ensure_ascii=False)


def _write(name: str, payload: dict) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / name
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def build_generation_samples() -> list[Path]:
    from tools import story_post_gen

    rows = [
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
    story_post_gen.retrieve_statements = lambda *a, **k: rows
    story_post_gen.check_theme_evidence_alignment = lambda *a, **k: {"ok": True, "reason": "stub"}
    story_post_gen._llm_text = _stub_llm

    ok_result = story_post_gen.run_story_post_generation(theme="苏绣", genre="post")
    outputs = [
        _write(
            "generation_ok.json",
            {
                "_note": "成功路径：C00–C06 全部 OK。模型输出为固定替身，非真实 LLM 效果。",
                "generation_status": ok_result.get("generation_status"),
                "skill_load": ok_result.get("skill_load"),
                "step_audit": ok_result.get("step_audit"),
            },
        )
    ]

    story_post_gen._llm_text = lambda prompt: "抱歉，我无法按 JSON 输出。"
    bad_result = story_post_gen.run_story_post_generation(theme="苏绣", genre="post")
    outputs.append(
        _write(
            "generation_blocked_c05.json",
            {
                "_note": "失败路径：模型输出不是 JSON，C05 拒绝返回，C06 标 NOT_RUN。",
                "generation_status": bad_result.get("generation_status"),
                "error": bad_result.get("error"),
                "step_audit": bad_result.get("step_audit"),
            },
        )
    )
    return outputs


def build_evaluation_samples() -> list[Path]:
    from api.evaluation_part3 import (
        JudgeDimensionOutput,
        JudgeOutput,
        evaluate_part3_with_audit,
    )
    from api.rubric_loader import CANONICAL_DIMENSION_IDS

    content = "苏绣是一门在丝绸两面同时成像的手艺，镇湖的绣娘仍在带徒。"
    good_span = {
        "span_id": "span-1",
        "source_id": "src-1",
        "text": "两面同时成像",
        "start": content.index("两面同时成像"),
        "end": content.index("两面同时成像") + len("两面同时成像"),
    }

    class _Judge:
        name = "stub-judge"
        model = "stub-model-v1"
        prompt_version = "p3-prompt-1"

        def __init__(self, spans):
            self.spans = spans

        def judge(self, text, task_context, rubric):
            return JudgeOutput(
                dimensions=[
                    JudgeDimensionOutput(
                        dimension_id=dim,
                        score=4,
                        confidence=0.5,  # 替身占位值：旧 Schema 要求 float，未做人工校准前不代表可信度
                        rationale="stub rationale",
                        evidence_spans=[dict(s) for s in self.spans],
                    )
                    for dim in CANONICAL_DIMENSION_IDS
                ]
            )

    ok_result, ok_audit = evaluate_part3_with_audit(
        "ver-2026-11-02-01", content, {"genre": "post", "audience": "US general"}, _Judge([good_span]),
        part1_status="PASS",
    )
    outputs = [
        _write(
            "evaluation_ok.json",
            {
                "_note": "成功路径：E00–E05 全部 OK；分数与 confidence 由 StubJudge 给，是结构样例，不是真实评分，也不构成校准结论。",
                "evaluation_status": ok_result.status,
                "overall_score": ok_result.overall_score,
                "human_review": ok_result.human_review,
                "dimensions": [
                    {"dimension_id": d.dimension_id, "score": d.score, "confidence": d.confidence}
                    for d in ok_result.dimensions
                ],
                "step_audit": ok_audit,
            },
        )
    ]

    bad_span = {
        "span_id": "span-1",
        "source_id": "src-1",
        "text": "原文里并不存在的说法",
        "start": 0,
        "end": 10,
    }
    bad_result, bad_audit = evaluate_part3_with_audit(
        "ver-2026-11-02-02", content, {"genre": "post"}, _Judge([bad_span]), part1_status="PASS"
    )
    outputs.append(
        _write(
            "evaluation_blocked_e03.json",
            {
                "_note": "失败路径：evidence_spans 偏移与原文不一致，E03 失败并转成可修改项。",
                "evaluation_status": bad_result.status,
                "issues": bad_result.issues,
                "step_audit": bad_audit,
            },
        )
    )
    return outputs


def main() -> int:
    written = build_generation_samples() + build_evaluation_samples()
    for path in written:
        print(f"写入 {path.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
