"""P0.6 — Evaluation Integration tests.

Covers the rubric loader, Part 1 fact/evidence aggregation (initial + revision),
the Part 3 judge interface, status safety, and the P0.6/P0.7 boundary.

The stub judge defined here exists **only** for testing. Production code has no
default scorer on purpose (see ``api/evaluation_part3.py``).
"""
import shutil
import tempfile
from pathlib import Path

import pytest

from api.evaluation import evaluate_content_version
from api.evaluation_part1 import STATUS_BLOCKED, STATUS_PASS, evaluate_part1
from api.evaluation_part3 import (
    FORBIDDEN_STATUSES,
    JudgeDimensionOutput,
    JudgeOutput,
    Part3Error,
    STATUS_COMPLETED,
    STATUS_HUMAN_REVIEW_PENDING,
    STATUS_INSUFFICIENT_CONTEXT,
    STATUS_RETURN_TO_PART1,
    STATUS_REVISION_RECOMMENDED,
    evaluate_part3,
)
from api.rubric_loader import (
    CANONICAL_DIMENSION_IDS,
    CANONICAL_DIMENSION_NAMES,
    SUPPORTED_RUBRIC_VERSION,
    RubricError,
    load_rubric,
)
from api.schemas import Claim, EvaluationResult, EvidenceItem, EvidencePack, EvidenceSpan, Source
from api.versioning import ContentVersionStore


# --------------------------------------------------------------------------- #
# fixtures / helpers
# --------------------------------------------------------------------------- #
RUBRIC_PATH = Path(__file__).resolve().parent.parent / "eval" / "CHINASTORY_CONTENT_QUALITY_RUBRIC_v2.1.md"


def make_pack(pack_id: str = "pack") -> EvidencePack:
    return EvidencePack(
        evidence_pack_id=pack_id,
        sources=[Source(source_id="s1")],
        items=[
            EvidenceItem(
                evidence_id="e1", source_id="s1", statement="fact",
                spans=[EvidenceSpan(span_id="sp", source_id="s1", text="fact")],
            )
        ],
    )


def full_dimensions(**overrides) -> list:
    """A complete, valid D1-D6 judge output."""
    out = []
    for dimension_id in CANONICAL_DIMENSION_IDS:
        payload = dict(dimension_id=dimension_id, score=4, confidence=0.8, rationale="ok")
        payload.update(overrides.pop(dimension_id, {}))
        out.append(JudgeDimensionOutput(**payload))
    assert not overrides, f"unused overrides: {overrides}"
    return out


class StubJudge:
    """Test-only judge. Never present in production code paths."""

    def __init__(
        self,
        dimensions=None,
        priority_issues=None,
        revision_suggestions=None,
        return_to_part1=False,
    ):
        self._dimensions = dimensions
        self._priority_issues = priority_issues or []
        self._revision_suggestions = revision_suggestions or []
        self._return_to_part1 = return_to_part1
        self.name = "stub-judge"
        self.model = "stub"

    def judge(self, content, task_context, rubric):
        dimensions = self._dimensions if self._dimensions is not None else full_dimensions()
        return JudgeOutput(
            dimensions=dimensions,
            priority_issues=self._priority_issues,
            revision_suggestions=self._revision_suggestions,
            return_to_part1=self._return_to_part1,
        )



def _trace(result, claim_id):
    """Convenience accessor for a Part 1 per-claim verdict."""
    for trace in result.claim_traces:
        if trace.claim_id == claim_id:
            return trace.status
    raise AssertionError(f"no claim trace for {claim_id}")


def build_initial(claim_ids, *, pack_id="pack", task_id="t", content="draft"):
    store = ContentVersionStore()
    version = store.create_initial_version(
        task_id, content, evidence_pack_id=pack_id, claim_ids=list(claim_ids)
    )
    return store, version


# --------------------------------------------------------------------------- #
# TEST 1-3 — rubric loader
# --------------------------------------------------------------------------- #
def test_rubric_loads_with_exact_canonical_dimensions():
    rubric = load_rubric()
    assert rubric.rubric_version == SUPPORTED_RUBRIC_VERSION
    assert rubric.dimension_ids == list(CANONICAL_DIMENSION_IDS)
    assert [d.name for d in rubric.dimensions] == list(CANONICAL_DIMENSION_NAMES)
    assert [d.code for d in rubric.dimensions] == ["D1", "D2", "D3", "D4", "D5", "D6"]
    assert len(rubric.dimensions) == 6
    # stable across repeated loads (deterministic ordering)
    assert load_rubric().dimension_ids == rubric.dimension_ids


def test_missing_rubric_file_fails_closed():
    with pytest.raises(RubricError, match="not found"):
        load_rubric(str(RUBRIC_PATH.parent / "does_not_exist.md"))


def test_rubric_missing_dimension_fails_closed():
    text = RUBRIC_PATH.read_text(encoding="utf-8")
    broken = text.replace("# 10. D5｜Genre & Platform Fit", "# 10. D5 renamed away")
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "broken.md"
        path.write_text(broken, encoding="utf-8")
        with pytest.raises(RubricError, match="missing dimensions"):
            load_rubric(str(path))


def test_rubric_duplicate_dimension_fails_closed():
    text = RUBRIC_PATH.read_text(encoding="utf-8")
    broken = text.replace("# 11. D6｜Naturalness & Non-sloganeering", "# 11. D4｜Narrative Engagement Potential")
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "dup.md"
        path.write_text(broken, encoding="utf-8")
        with pytest.raises(RubricError, match="duplicate dimension"):
            load_rubric(str(path))


def test_rubric_wrong_version_fails_closed():
    text = RUBRIC_PATH.read_text(encoding="utf-8").replace(
        "# ChinaStory Content Quality Rubric v2.1", "# ChinaStory Content Quality Rubric v9.9"
    )
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "v99.md"
        path.write_text(text, encoding="utf-8")
        with pytest.raises(RubricError, match="unsupported rubric version"):
            load_rubric(str(path))


# --------------------------------------------------------------------------- #
# TEST 4-6 — Part 1 on an initial version
# --------------------------------------------------------------------------- #
def test_initial_version_all_claims_traceable_passes():
    store, version = build_initial(["c1"])
    claims = {"c1": Claim(claim_id="c1", text="fact", evidence_ids=["e1"])}

    result = evaluate_part1(version.content_version_id, store, claims, make_pack())

    assert result.status == STATUS_PASS
    assert _trace(result, "c1") == "traceable"
    assert result.issues == []


def test_initial_version_unbound_claim_blocks():
    store, version = build_initial(["c1"])
    claims = {"c1": Claim(claim_id="c1", text="unsupported")}

    result = evaluate_part1(version.content_version_id, store, claims, make_pack())

    assert result.status == STATUS_BLOCKED
    assert _trace(result, "c1") == "unbound"
    assert any("unbound claim" in i for i in result.issues)


def test_initial_version_dangling_evidence_blocks():
    store, version = build_initial(["c1"])
    claims = {"c1": Claim(claim_id="c1", text="fact", evidence_ids=["nope"])}

    result = evaluate_part1(version.content_version_id, store, claims, make_pack())

    assert result.status == STATUS_BLOCKED
    assert _trace(result, "c1") == "binding_error"


def test_initial_version_missing_pack_blocks():
    store, version = build_initial(["c1"])
    claims = {"c1": Claim(claim_id="c1", text="fact", evidence_ids=["e1"])}

    result = evaluate_part1(version.content_version_id, store, claims, None)

    assert result.status == STATUS_BLOCKED
    assert any("missing evidence pack" in i for i in result.issues)


def test_initial_version_missing_claim_blocks():
    store, version = build_initial(["c1"])

    result = evaluate_part1(version.content_version_id, store, {}, make_pack())

    assert result.status == STATUS_BLOCKED
    assert _trace(result, "c1") == "missing_claim"


def test_unknown_content_version_blocks():
    store, version = build_initial(["c1"])

    result = evaluate_part1("no-such-version", store, {}, make_pack())

    assert result.status == STATUS_BLOCKED
    assert any("not found" in i for i in result.issues)


# --------------------------------------------------------------------------- #
# TEST 7-8 — Part 1 on a revision delegates to P0.5
# --------------------------------------------------------------------------- #
def test_revision_safe_delegates_to_fact_safety():
    from api.fact_safety import ClaimIdentityRegistry

    store, parent = build_initial(["c1"])
    child = store.create_revision(parent.content_version_id, "revised", claim_ids=["c1"])
    claims = {"c1": Claim(claim_id="c1", text="fact", evidence_ids=["e1"])}
    # c1 is a retained claim, so its identity snapshot must already exist.
    registry = ClaimIdentityRegistry()
    registry.register(claims["c1"])

    result = evaluate_part1(
        child.content_version_id, store, claims, make_pack(), registry
    )

    assert result.status == STATUS_PASS
    assert result.return_to_part1 is False
    # P0.5 only reports evidence rechecks for added claims, so a pure retained
    # revision has no per-claim recheck entry.
    assert result.claim_traces == []


def test_revision_locked_is_never_reported_safe():
    from api.fact_safety import ClaimIdentityRegistry

    store, parent = build_initial(["c1"])
    child = store.create_revision(parent.content_version_id, "revised", claim_ids=["c1", "c2"])
    claims = {
        "c1": Claim(claim_id="c1", text="fact", evidence_ids=["e1"]),
        "c2": Claim(claim_id="c2", text="new"),  # unbound added claim
    }
    registry = ClaimIdentityRegistry()

    result = evaluate_part1(
        child.content_version_id, store, claims, make_pack(), registry
    )

    assert result.status == STATUS_BLOCKED
    assert result.return_to_part1 is True
    assert any("c2" in i for i in result.issues)


# --------------------------------------------------------------------------- #
# TEST 9 — Part 3 with an injected stub judge
# --------------------------------------------------------------------------- #
def test_part3_stub_judge_produces_structured_result():
    result = evaluate_part3("v1", "some english content", {"genre": "post"}, StubJudge())

    assert result.part == "part3_chinastory_quality"
    assert len(result.dimensions) == 6
    assert [d.dimension_id for d in result.dimensions] == list(CANONICAL_DIMENSION_IDS)
    assert all(d.score == 4 for d in result.dimensions)
    assert result.overall_score is None
    assert result.rubric_version == SUPPORTED_RUBRIC_VERSION
    assert result.audit is not None and result.audit.rubric_version == SUPPORTED_RUBRIC_VERSION


# --------------------------------------------------------------------------- #
# TEST 10-14 — malformed judge output fails closed
# --------------------------------------------------------------------------- #
def test_judge_missing_dimension_fails_closed():
    dims = [d for d in full_dimensions() if d.dimension_id != "narrative_engagement_potential"]
    with pytest.raises(Part3Error, match="missing dimensions"):
        evaluate_part3("v1", "content", {}, StubJudge(dims))


def test_judge_duplicate_dimension_fails_closed():
    dims = full_dimensions()
    dims.append(JudgeDimensionOutput(dimension_id="audience_fit", score=3, confidence=0.5))
    with pytest.raises(Part3Error, match="duplicate dimension"):
        evaluate_part3("v1", "content", {}, StubJudge(dims))


def test_judge_unknown_dimension_fails_closed():
    dims = full_dimensions()
    dims.append(JudgeDimensionOutput(dimension_id="d7_invented", score=3, confidence=0.5))
    with pytest.raises(Part3Error, match="unknown dimension"):
        evaluate_part3("v1", "content", {}, StubJudge(dims))


def test_judge_score_out_of_range_fails_closed():
    dims = full_dimensions()
    dims[0] = JudgeDimensionOutput(dimension_id=dims[0].dimension_id, score=9, confidence=0.8)
    with pytest.raises(Part3Error, match="outside allowed range"):
        evaluate_part3("v1", "content", {}, StubJudge(dims))


def test_judge_bad_confidence_fails_closed():
    dims = full_dimensions()
    dims[0] = JudgeDimensionOutput(dimension_id=dims[0].dimension_id, score=3, confidence=1.7)
    with pytest.raises(Part3Error, match="confidence"):
        evaluate_part3("v1", "content", {}, StubJudge(dims))


def test_judge_non_numeric_score_fails_closed():
    dims = full_dimensions()
    dims[0] = JudgeDimensionOutput(dimension_id=dims[0].dimension_id, score="great", confidence=0.8)
    with pytest.raises(Part3Error, match="score must be an integer"):
        evaluate_part3("v1", "content", {}, StubJudge(dims))


def test_judge_empty_output_fails_closed():
    with pytest.raises(Part3Error, match="no dimensions"):
        evaluate_part3("v1", "content", {}, StubJudge([]))


def test_judge_exception_fails_closed():
    class ExplodingJudge:
        name = "boom"
        model = "boom"

        def judge(self, content, task_context, rubric):
            raise RuntimeError("network down")

    with pytest.raises(Part3Error, match="judge failed"):
        evaluate_part3("v1", "content", {}, ExplodingJudge())


# --------------------------------------------------------------------------- #
# TEST 15 — no production scorer
# --------------------------------------------------------------------------- #
def test_production_path_without_judge_does_not_fabricate_scores():
    result = evaluate_part3("v1", "content", {}, None)

    assert result.status == STATUS_INSUFFICIENT_CONTEXT
    assert result.dimensions == []
    assert result.scores == {}
    assert result.overall_score is None
    assert any("refusing to fabricate" in i for i in result.issues)


def test_production_module_has_no_default_judge():
    import api.evaluation_part3 as module

    # The only judge type allowed to ship is the Protocol *interface*.
    assert getattr(module.ChinaStoryJudge, "_is_protocol", False) is True

    # Any other exported Judge class must not be a runnable implementation.
    implementations = [
        name
        for name in dir(module)
        if name.endswith("Judge") and name != "ChinaStoryJudge"
    ]
    assert implementations == [], f"concrete judge shipped in production: {implementations}"


# --------------------------------------------------------------------------- #
# TEST 16-17 — status safety
# --------------------------------------------------------------------------- #
def test_part3_structured_return_to_part1_signal():
    """FIX 1: routing is driven by the structured flag."""
    result = evaluate_part3(
        "v1", "content", {}, StubJudge(return_to_part1=True)
    )

    assert result.status == STATUS_RETURN_TO_PART1
    assert result.return_to_part1 is True


def test_keyword_in_rationale_does_not_trigger_return_to_part1():
    """FIX 1: the old natural-language heuristic is gone.

    The same wording that used to trigger routing must now be inert when the
    structured flag is False.
    """
    dims = full_dimensions()
    dims[0] = JudgeDimensionOutput(
        dimension_id=dims[0].dimension_id,
        score=3,
        confidence=0.7,
        rationale="suspected factual error, unsupported factual statement, evidence inconsistency",
    )
    issues = [{"problem": "suspected factual error in paragraph 2"}]

    result = evaluate_part3(
        "v1", "content", {}, StubJudge(dims, priority_issues=issues, return_to_part1=False)
    )

    assert result.return_to_part1 is False
    assert result.status != STATUS_RETURN_TO_PART1
    assert result.status == STATUS_REVISION_RECOMMENDED


@pytest.mark.parametrize("target", ["D7", "fake", "unknown_dimension"])
def test_priority_issue_unknown_dimension_fails_closed(target):
    """FIX 2: issue dimension_id must be canonical D1-D6 (or a system target)."""
    issues = [{"problem": "real problem", "dimension_id": target}]
    with pytest.raises(Part3Error, match="unknown dimension target"):
        evaluate_part3("v1", "content", {}, StubJudge(priority_issues=issues))


@pytest.mark.parametrize("bad_issue", [{}, {"problem": ""}, {"problem": "   "}])
def test_empty_priority_issue_fails_closed(bad_issue):
    """FIX 3: an issue must carry actual problem content."""
    with pytest.raises(Part3Error, match="no problem content"):
        evaluate_part3("v1", "content", {}, StubJudge(priority_issues=[bad_issue]))


def test_priority_issue_system_target_is_allowed():
    issues = [{"problem": "needs factual recheck", "dimension_id": "system"}]
    result = evaluate_part3("v1", "content", {}, StubJudge(priority_issues=issues))
    assert result.priority_issues[0].dimension_id == "system"


@pytest.mark.parametrize("target", ["D7_fake", "nope"])
def test_revision_suggestion_unknown_target_fails_closed(target):
    """FIX 3: suggestion target_dimension must be canonical when provided."""
    suggestions = [{"target_dimension": target, "instruction": "do something"}]
    with pytest.raises(Part3Error, match="unknown dimension target"):
        evaluate_part3("v1", "content", {}, StubJudge(revision_suggestions=suggestions))


@pytest.mark.parametrize("instruction", ["", "   "])
def test_empty_revision_instruction_fails_closed(instruction):
    """FIX 3: a suggestion must carry an executable instruction."""
    suggestions = [{"target_dimension": "audience_fit", "instruction": instruction}]
    with pytest.raises(Part3Error, match="no instruction"):
        evaluate_part3("v1", "content", {}, StubJudge(revision_suggestions=suggestions))


def test_part3_never_outputs_approved():
    assert "APPROVED" not in {
        STATUS_COMPLETED, STATUS_REVISION_RECOMMENDED, STATUS_RETURN_TO_PART1,
        STATUS_HUMAN_REVIEW_PENDING, STATUS_INSUFFICIENT_CONTEXT,
    }
    assert "APPROVED" in FORBIDDEN_STATUSES

    clean = evaluate_part3("v1", "content", {}, StubJudge())
    dirty = evaluate_part3("v1", "content", {}, StubJudge(
        priority_issues=[{"problem": "audience fit issue"}]
    ))
    for result in (clean, dirty):
        assert result.status not in FORBIDDEN_STATUSES


def test_clean_evaluation_goes_to_human_review_not_approval():
    result = evaluate_part3("v1", "content", {}, StubJudge())
    assert result.status == STATUS_HUMAN_REVIEW_PENDING
    assert result.human_review == "PENDING"


def test_issues_produce_revision_recommended():
    result = evaluate_part3("v1", "content", {}, StubJudge(
        priority_issues=[{"problem": "cross-cultural barrier", "dimension_id": "audience_fit"}]
    ))
    assert result.status == STATUS_REVISION_RECOMMENDED


# --------------------------------------------------------------------------- #
# TEST 18 — EvaluationResult carries the full P0.6 payload
# --------------------------------------------------------------------------- #
def test_evaluation_result_retains_p06_fields():
    store, version = build_initial(["c1"], content="english body")
    claims = {"c1": Claim(claim_id="c1", text="fact", evidence_ids=["e1"])}

    result = evaluate_content_version(
        version.content_version_id, store, claims, make_pack(), judge=StubJudge()
    )
    assert _trace(result, "c1") == "traceable"

    assert result.rubric_version == SUPPORTED_RUBRIC_VERSION
    assert result.content_version_id == version.content_version_id
    assert len(result.dimensions) == 6
    assert result.audit is not None
    assert result.audit.rubric_version == SUPPORTED_RUBRIC_VERSION
    assert result.audit.evaluator == "stub-judge"
    assert result.overall_score is None


# --------------------------------------------------------------------------- #
# TEST 19 — backward compatibility with the P0.1 schema
# --------------------------------------------------------------------------- #
def test_legacy_evaluation_result_construction_still_works():
    legacy = EvaluationResult(
        evaluation_id="eval-1",
        content_version_id="version-1",
        part="fact",
        status="pending",
    )
    assert legacy.content_version_id == "version-1"
    assert legacy.issues == []
    assert legacy.scores == {}
    # additive fields default safely
    assert legacy.dimensions == []
    assert legacy.overall_score is None
    assert legacy.audit is None


# --------------------------------------------------------------------------- #
# TEST 20 — integration never creates a new ContentVersion (P0.7 boundary)
# --------------------------------------------------------------------------- #
def test_evaluation_integration_creates_no_new_version():
    store, version = build_initial(["c1"], content="body")
    claims = {"c1": Claim(claim_id="c1", text="fact", evidence_ids=["e1"])}

    before = store.get_history(version.task_id)
    evaluate_content_version(version.content_version_id, store, claims, make_pack(),
                             judge=StubJudge())
    after = store.get_history(version.task_id)

    assert len(before) == len(after) == 1
    assert [v.content_version_id for v in before] == [v.content_version_id for v in after]


def test_blocked_part1_skips_part3_and_does_not_create_version():
    store, version = build_initial(["c1"], content="body")
    claims = {"c1": Claim(claim_id="c1", text="unsupported")}

    result = evaluate_content_version(
        version.content_version_id, store, claims, make_pack(), judge=StubJudge()
    )

    assert result.status == STATUS_RETURN_TO_PART1
    assert result.dimensions == []
    assert len(store.get_history(version.task_id)) == 1
