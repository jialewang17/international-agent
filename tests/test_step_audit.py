"""步骤契约与质量门（C00–C06 / E00–E05）回归测试。

两类断言：
1. **契约自身**：13 个步骤编号齐全、每步的方法依据锚点在仓库里真实存在、
   终态判定与顺序自洽校验不会放水；
2. **真实接线**：生成链路与评测链路跑出来的 ``step_audit`` 必须与运行事实一致
   （成功 = 全 OK / 失败 = 停在该停的那一步 / 未跑 = NOT_RUN）。

全部测试不调用真实大模型：生成侧替换 ``_llm_text``，评测侧注入 StubJudge。
"""

from __future__ import annotations

import json
import pathlib

import pytest

from api.evaluation_part3 import (
    JudgeDimensionOutput,
    JudgeOutput,
    deterministic_checks,
    evaluate_part3,
    evaluate_part3_with_audit,
)
from api.rubric_loader import CANONICAL_DIMENSION_IDS
from tools import story_post_gen
from utils import skill_registry
from utils.skill_registry import (
    SkillInfo,
    SkillRegistry,
    SkillRegistryConfig,
)
from utils.step_audit import (
    EVALUATION_STEPS,
    GENERATION_STEPS,
    PIPELINE_EVALUATION,
    PIPELINE_GENERATION,
    STATUS_BLOCKED,
    STATUS_FAILED,
    STATUS_NOT_RUN,
    STATUS_OK,
    STEP_SPECS,
    StepAudit,
    StepAuditError,
    VERDICT_BLOCKED,
    VERTICT_COMPLETE,
    VERDICT_FAILED,
    VERDICT_INCOMPLETE,
    check_audit,
    digest,
    evidence_problems,
    summarize,
)

ROOT = pathlib.Path(__file__).resolve().parents[1]
SKILLS_YAML = ROOT / "config" / "skills.yaml"


# ---------------------------------------------------------------------------
# 测试替身
# ---------------------------------------------------------------------------
def _evidence_rows():
    return [
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


POST_PAYLOAD = {
    "genre": "post",
    "title_or_hook": "一根线的两面",
    "five_w": {"who": "苏州绣娘", "what": "双面绣", "when": "今天", "where": "镇湖", "why": "非遗传承"},
    "post": "Suzhou embroidery is a story told twice on one thread.",
    "hashtags": ["#SuzhouEmbroidery"],
    "ops_tips": [],
    "evidence_notes": ["Evidence#1 -> ICH listing"],
}


class PromptSpy:
    def __init__(self, payload=POST_PAYLOAD):
        self.payload = payload
        self.prompts: list[str] = []

    def __call__(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if isinstance(self.payload, str):
            return self.payload
        return json.dumps(self.payload, ensure_ascii=False)


def _skill_info(skill_id: str, rel: str, content: str):
    return SkillInfo(
        skill_id=skill_id,
        title=skill_id,
        file_path=ROOT / rel,
        enabled=True,
        priority=90,
        keywords=[],
        content=content,
        summary=skill_id,
        truncated=False,
        source="configured",
        error=None,
        raw_chars=len(content),
    )


def _use_registry(monkeypatch, *, always_on=()):
    """构造只含所需卡片的假注册表；always_on 由调用方显式指定。"""
    infos = [
        _skill_info("china_story_post", "skills/china-story-generation/references/genres/post.md", "POST 方法卡"),
        _skill_info("intl_comm", "skills/intl-comm.md", "立场与证据硬约束"),
        _skill_info("evidence_user_materials", "skills/evidence-user-materials.md", "用户资料与本地库双源"),
    ]
    config = SkillRegistryConfig(
        enabled=True,
        auto_activate=True,
        discover_files=False,
        max_chars_per_skill=16000,
        max_active_skills=3,
        max_total_chars=24000,
        always_on=list(always_on),
        disabled=[],
    )
    registry = SkillRegistry(
        config_path=SKILLS_YAML,
        config=config,
        skills={i.skill_id: i for i in infos},
        load_errors=[],
    )
    monkeypatch.setattr(skill_registry, "get_skill_registry", lambda force_reload=False: registry)
    return registry


@pytest.fixture
def stub_gates(monkeypatch):
    monkeypatch.setattr(story_post_gen, "retrieve_statements", lambda *a, **k: _evidence_rows())
    monkeypatch.setattr(
        story_post_gen, "check_theme_evidence_alignment", lambda *a, **k: {"ok": True, "reason": "stub"}
    )


# ---------------------------------------------------------------------------
# 1. 契约自身
# ---------------------------------------------------------------------------
def test_thirteen_steps_with_contract_and_evidence():
    assert [s.step_id for s in GENERATION_STEPS] == [f"C0{i}" for i in range(7)]
    assert [s.step_id for s in EVALUATION_STEPS] == [f"E0{i}" for i in range(6)]
    assert len(STEP_SPECS) == 13
    for spec in STEP_SPECS.values():
        assert spec.contract.strip(), f"{spec.step_id} 缺少一句话契约"
        assert spec.evidence, f"{spec.step_id} 缺少方法依据"
        assert spec.required, f"{spec.step_id} 应为必做步骤"


def test_every_evidence_anchor_exists_in_repo():
    """每一步的依据都必须能在仓库里指到具体位置（防止"依据"写在空气里）。"""
    problems = evidence_problems(ROOT)
    assert problems == [], "步骤依据锚点失真：\n" + "\n".join(problems)


def test_step_contracts_documents_exist_and_cover_all_steps():
    gen = (ROOT / "skills/china-story-generation/references/step-contracts.md").read_text(encoding="utf-8")
    ev = (ROOT / "skills/china-story-evaluation/references/step-contracts.md").read_text(encoding="utf-8")
    for i in range(7):
        assert f"### C0{i}" in gen
    for i in range(6):
        assert f"### E0{i}" in ev


def test_audit_rejects_unknown_step_and_duplicate():
    audit = StepAudit(PIPELINE_GENERATION)
    with pytest.raises(StepAuditError):
        audit.ok("E01")  # 跨管线
    audit.ok("C00", note="x")
    with pytest.raises(StepAuditError):
        audit.ok("C00")  # 重复记录不得覆盖首次结果
    with pytest.raises(StepAuditError):
        audit.ok("C01", note="x") or audit.record("C01", "WHATEVER")


def test_verdict_semantics():
    audit = StepAudit(PIPELINE_GENERATION)
    for sid in [s.step_id for s in GENERATION_STEPS]:
        audit.ok(sid)
    assert audit.finish()["verdict"] == VERTICT_COMPLETE

    blocked = StepAudit(PIPELINE_GENERATION)
    blocked.ok("C00")
    blocked.blocked("C01", "evidence_empty")
    out = blocked.finish()
    assert out["verdict"] == VERDICT_BLOCKED
    assert out["first_blocked"] == "C01"
    assert out["not_run"] == ["C02", "C03", "C04", "C05", "C06"]

    failed = StepAudit(PIPELINE_GENERATION)
    failed.failed("C00", "invalid_genre")
    assert failed.finish()["verdict"] == VERDICT_FAILED

    skipped = StepAudit(PIPELINE_GENERATION)
    skipped.ok("C00")
    skipped.skip("C01", "not needed")
    assert skipped.finish()["verdict"] == VERDICT_INCOMPLETE


def test_check_audit_detects_not_run_claimed_complete_and_bad_order():
    audit = StepAudit(PIPELINE_GENERATION)
    audit.ok("C00")
    good = audit.finish()
    assert check_audit(good) == []

    tampered = json.loads(json.dumps(good))
    tampered["verdict"] = VERTICT_COMPLETE
    problems = check_audit(tampered)
    assert any("NOT_RUN" in p for p in problems)

    reordered = json.loads(json.dumps(good))
    reordered["steps"] = list(reversed(reordered["steps"]))
    assert any("顺序" in p for p in check_audit(reordered))
    assert check_audit({"pipeline": "nope"}), "未知管线必须报错"


def test_check_audit_rejects_failed_step_with_later_ok_claimed_complete():
    audit = StepAudit(PIPELINE_GENERATION)
    audit.ok("C00")
    audit.failed("C01", "canonical_evidence_invalid")
    audit.ok("C02")
    tampered = audit.finish()
    tampered["verdict"] = VERTICT_COMPLETE
    problems = check_audit(tampered)
    assert any("后续步骤仍标记成功" in p for p in problems)


def test_committed_trace_samples_stay_consistent():
    """样例是提交进仓库的证据：一旦代码行为变了，样例必须重新生成，不能悄悄过期。"""
    sample_dir = ROOT / "docs" / "chinastory_v6.1" / "step_trace_samples"
    files = sorted(sample_dir.glob("*.json"))
    assert len(files) >= 4, "追溯样例缺失，请运行 scripts/make_step_trace_samples.py"
    for path in files:
        data = json.loads(path.read_text(encoding="utf-8"))
        audit = data.get("step_audit", data)
        assert check_audit(audit) == [], f"{path.name} 审计不自洽：{check_audit(audit)}"
        assert data.get("_note"), f"{path.name} 缺少说明，容易被误读成真实模型效果"


def test_digest_is_stable_and_short():
    assert digest("abc") == digest("abc")
    assert digest("abc") != digest("abd")
    assert len(digest({"a": 1})) == len("sha256:") + 16


# ---------------------------------------------------------------------------
# 2. 生成链路真实接线
# ---------------------------------------------------------------------------
def test_generation_success_records_all_seven_steps(stub_gates, monkeypatch):
    _use_registry(monkeypatch, always_on=["intl_comm", "evidence_user_materials"])
    monkeypatch.setattr(story_post_gen, "_llm_text", PromptSpy())

    result = story_post_gen.run_story_post_generation(theme="苏绣", genre="post")
    audit = result["step_audit"]

    assert result["generation_status"] == "OK"
    assert audit["pipeline"] == PIPELINE_GENERATION
    assert audit["verdict"] == VERTICT_COMPLETE
    assert [s["step_id"] for s in audit["steps"]] == [f"C0{i}" for i in range(7)]
    assert all(s["status"] == STATUS_OK for s in audit["steps"])
    assert audit["not_run"] == []

    by_id = {s["step_id"]: s for s in audit["steps"]}
    assert by_id["C00"]["detail"]["resolved_genre"] == "post"
    assert by_id["C01"]["detail"]["gate_b"] == "ready_to_generate"
    assert by_id["C02"]["detail"]["loaded_method_id"] == "china_story_post"
    assert by_id["C02"]["detail"]["always_on_loaded"] == ["intl_comm", "evidence_user_materials"]
    assert by_id["C03"]["detail"]["prompt_chars"] > 0
    assert by_id["C04"]["detail"]["output_chars"] > 0
    assert by_id["C05"]["detail"]["output_contract"] == "post5w"
    assert by_id["C06"]["detail"]["human_review"] == "PENDING"
    assert by_id["C06"]["detail"]["publishable"] is False
    # 自检六问不允许把"机器判定不了"的项写成 PASS
    assert by_id["C06"]["detail"]["self_check"]["no_fabricated_quote_or_link"].startswith(
        "PENDING_HUMAN"
    )
    assert check_audit(audit) == []


def test_generation_invalid_genre_stops_at_c00(stub_gates, monkeypatch):
    spy = PromptSpy()
    monkeypatch.setattr(story_post_gen, "_llm_text", spy)

    result = story_post_gen.run_story_post_generation(theme="苏绣", genre="story")
    audit = result["step_audit"]
    assert result["generation_status"] == "INVALID_GENRE"
    assert audit["verdict"] == VERDICT_FAILED
    assert audit["first_failed"] == "C00"
    assert audit["not_run"] == ["C01", "C02", "C03", "C04", "C05", "C06"]
    assert spy.prompts == []


def test_generation_empty_evidence_stops_at_c01(stub_gates, monkeypatch):
    _use_registry(monkeypatch, always_on=[])
    monkeypatch.setattr(story_post_gen, "retrieve_statements", lambda *a, **k: [])

    result = story_post_gen.run_story_post_generation(theme="苏绣", genre="post")
    audit = result["step_audit"]
    assert audit["verdict"] == VERDICT_BLOCKED
    assert audit["first_blocked"] == "C01"
    assert audit["not_run"] == ["C02", "C03", "C04", "C05", "C06"]


def test_generation_output_invalid_stops_at_c05(stub_gates, monkeypatch):
    _use_registry(monkeypatch, always_on=[])
    monkeypatch.setattr(story_post_gen, "_llm_text", PromptSpy("这不是 JSON"))

    result = story_post_gen.run_story_post_generation(theme="苏绣", genre="post")
    audit = result["step_audit"]
    assert result["generation_status"] == "OUTPUT_INVALID"
    assert audit["first_failed"] == "C05"
    assert [s["status"] for s in audit["steps"]][:5] == [STATUS_OK] * 5
    assert audit["not_run"] == ["C06"]


def test_generation_missing_always_on_fails_at_c02(stub_gates, monkeypatch):
    """配置了 always_on 但卡片不可用 → C02 失败，绝不"少一张卡继续写"。"""
    _use_registry(monkeypatch, always_on=["intl_comm"])
    registry = skill_registry.get_skill_registry()
    registry.skills["intl_comm"].enabled = False
    monkeypatch.setattr(story_post_gen, "_llm_text", PromptSpy())

    result = story_post_gen.run_story_post_generation(theme="苏绣", genre="post")
    audit = result["step_audit"]
    assert result["generation_status"] == "SKILL_ALWAYS_ON_UNAVAILABLE"
    assert audit["first_failed"] == "C02"
    assert result["skill_load"]["always_on_problems"][0]["reason"] == "disabled"


# ---------------------------------------------------------------------------
# 3. 评测链路真实接线
# ---------------------------------------------------------------------------
class StubJudge:
    name = "stub-judge"
    model = "stub-model-v1"
    prompt_version = "p3-prompt-1"

    def __init__(self, spans=None, **overrides):
        self.spans = spans or []
        self.overrides = overrides

    def judge(self, content, task_context, rubric):
        dims = []
        for dim in CANONICAL_DIMENSION_IDS:
            dims.append(
                JudgeDimensionOutput(
                    dimension_id=dim,
                    score=self.overrides.get(dim, 4),
                    confidence=0.5,
                    rationale="stub",
                    evidence_spans=[dict(s) for s in self.spans],
                    problems=[],
                    revision_suggestion="",
                )
            )
        return JudgeOutput(dimensions=dims)


def test_evaluation_success_audit_is_complete():
    content = "苏绣是一门在丝绸两面同时成像的手艺。"
    result, audit = evaluate_part3_with_audit(
        "v1", content, {"genre": "post"}, StubJudge(), part1_status="PASS"
    )
    assert audit["pipeline"] == PIPELINE_EVALUATION
    assert audit["verdict"] == VERTICT_COMPLETE
    assert [s["step_id"] for s in audit["steps"]] == [f"E0{i}" for i in range(6)]
    assert all(s["status"] == STATUS_OK for s in audit["steps"])
    assert check_audit(audit) == []
    by_id = {s["step_id"]: s for s in audit["steps"]}
    assert by_id["E05"]["detail"]["checks"]["six_dimensions_unique"] is True
    assert by_id["E05"]["detail"]["content_sha256"] == deterministic_checks(result, content)["content_sha256"]
    # 契约不变：overall_score 仍为 null、human_review 仍为 PENDING
    assert result.overall_score is None
    assert result.human_review == "PENDING"


def test_evaluation_entrypoint_signature_unchanged():
    """evaluate_part3 仍只返回 EvaluationResult（不破坏既有契约）。"""
    result = evaluate_part3("v1", "some content", {}, StubJudge())
    assert result.dimensions
    assert not isinstance(result, tuple)


def test_evaluation_without_judge_is_blocked_at_e02():
    result, audit = evaluate_part3_with_audit("v1", "content", {}, None)
    assert result.status == "INSUFFICIENT_CONTEXT"
    assert audit["verdict"] == VERDICT_BLOCKED
    assert audit["first_blocked"] == "E02"
    assert audit["not_run"] == ["E03", "E04", "E05"]


def test_evaluation_empty_content_is_blocked_at_e00():
    result, audit = evaluate_part3_with_audit("v1", "   ", {}, StubJudge())
    assert result.status == "INSUFFICIENT_CONTEXT"
    assert audit["first_blocked"] == "E00"


def test_evaluation_span_mismatch_is_not_silently_accepted():
    content = "苏绣是一门在丝绸两面同时成像的手艺。"
    bad_span = {"span_id": "s1", "source_id": "src", "text": "原文里没有这句", "start": 0, "end": 8}
    result, audit = evaluate_part3_with_audit("v1", content, {}, StubJudge(spans=[bad_span]))
    by_id = {s["step_id"]: s for s in audit["steps"]}
    assert by_id["E03"]["status"] == STATUS_FAILED
    assert audit["verdict"] == VERDICT_FAILED
    assert any("偏移" in i for i in result.issues), "偏移不一致必须变成可修改项"
    assert result.status == "REVISION_RECOMMENDED"


def test_evaluation_span_match_passes_when_offsets_are_exact():
    content = "苏绣是一门在丝绸两面同时成像的手艺。"
    span = {"span_id": "s1", "source_id": "src", "text": "两面同时成像", "start": 8, "end": 14}
    assert content[8:14] == "两面同时成像"
    _result, audit = evaluate_part3_with_audit("v1", content, {}, StubJudge(spans=[span]))
    by_id = {s["step_id"]: s for s in audit["steps"]}
    assert by_id["E03"]["status"] == STATUS_OK
    assert by_id["E03"]["detail"]["spans_checked"] == 6
    assert audit["verdict"] == VERTICT_COMPLETE


def test_summarize_is_one_line():
    audit = StepAudit(PIPELINE_GENERATION)
    audit.ok("C00")
    line = summarize(audit.finish())
    assert "\n" not in line and "C00" in line
