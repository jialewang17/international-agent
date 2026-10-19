"""I2-B-004A: zero-Claim Part 1 evaluation must fail closed.

Offline tests. No LLM, external network, or production API mutation.
"""

from api.evaluation import evaluate_content_version
from api.evaluation_part1 import (
    STATUS_BLOCKED,
    STATUS_PASS,
    evaluate_part1,
)
from api.evaluation_part3 import STATUS_RETURN_TO_PART1
from api.schemas import Claim, EvidenceItem, EvidencePack, Source
from api.versioning import ContentVersionStore


def make_pack():
    return EvidencePack(
        evidence_pack_id="ep_zero_guard",
        sources=[
            Source(
                source_id="src_guard",
                title="Synthetic test source",
            )
        ],
        items=[
            EvidenceItem(
                evidence_id="ev_guard",
                source_id="src_guard",
                statement="Synthetic evidence text.",
                spans=[],
            )
        ],
    )


def empty_initial():
    versions = ContentVersionStore()
    version = versions.create_initial_version(
        "task-zero-claim",
        "An unreviewed factual sentence.",
        evidence_pack_id="ep_zero_guard",
        claim_ids=[],
    )
    return versions, version


def test_01_zero_claim_initial_is_blocked():
    versions, version = empty_initial()

    result = evaluate_part1(
        version.content_version_id,
        versions,
        {},
        make_pack(),
        evaluation_id="eval-zero-p1",
    )

    assert result.status == STATUS_BLOCKED
    assert result.return_to_part1 is True
    assert result.claim_traces == []
    assert result.task_id == "task-zero-claim"
    assert result.evaluation_id == "eval-zero-p1"
    assert any(
        "no claims extracted" in reason
        for reason in result.issues
    )
    assert result.audit is not None
    assert result.audit.part1_status == STATUS_BLOCKED


def test_02_unused_claim_mapping_cannot_hide_zero_claims():
    versions, version = empty_initial()

    unrelated_claim = Claim(
        claim_id="clm_unrelated",
        text="Another synthetic claim.",
        evidence_ids=["ev_guard"],
    )

    result = evaluate_part1(
        version.content_version_id,
        versions,
        {"clm_unrelated": unrelated_claim},
        make_pack(),
    )

    assert result.status == STATUS_BLOCKED
    assert result.claim_traces == []
    assert any(
        "no claims extracted" in reason
        for reason in result.issues
    )


def test_03_zero_claim_without_pack_is_still_blocked():
    versions, version = empty_initial()

    result = evaluate_part1(
        version.content_version_id,
        versions,
        {},
        None,
    )

    assert result.status == STATUS_BLOCKED
    assert result.return_to_part1 is True
    assert any(
        "no claims extracted" in reason
        for reason in result.issues
    )


def test_04_zero_claim_revision_is_blocked():
    versions = ContentVersionStore()

    parent = versions.create_initial_version(
        "task-zero-revision",
        "Original text.",
        evidence_pack_id="ep_zero_guard",
        claim_ids=["clm_parent"],
    )

    revision = versions.create_revision(
        parent.content_version_id,
        "Revised text.",
        claim_ids=[],
    )

    result = evaluate_part1(
        revision.content_version_id,
        versions,
        {},
        make_pack(),
    )

    assert result.status == STATUS_BLOCKED
    assert result.return_to_part1 is True
    assert result.claim_traces == []
    assert any(
        "no claims extracted" in reason
        for reason in result.issues
    )


def test_05_orchestrator_skips_part3_for_zero_claims():
    versions, version = empty_initial()

    class MustNotRunJudge:
        def judge(self, *_args, **_kwargs):
            raise AssertionError(
                "Part 3 judge must not run for zero claims"
            )

    result = evaluate_content_version(
        version.content_version_id,
        versions,
        {},
        make_pack(),
        judge=MustNotRunJudge(),
    )

    assert result.status == STATUS_RETURN_TO_PART1
    assert result.return_to_part1 is True
    assert result.dimensions == []
    assert result.overall_score is None
    assert result.human_review == "PENDING"
    assert any(
        "no claims extracted" in reason
        for reason in result.issues
    )

    assert len(versions.get_history("task-zero-claim")) == 1


def test_06_nonempty_traceable_claim_keeps_existing_part1_behavior():
    versions = ContentVersionStore()

    version = versions.create_initial_version(
        "task-nonempty-control",
        "Synthetic test sentence.",
        evidence_pack_id="ep_zero_guard",
        claim_ids=["clm_control"],
    )

    claim = Claim(
        claim_id="clm_control",
        text="Synthetic test sentence.",
        evidence_ids=["ev_guard"],
    )

    result = evaluate_part1(
        version.content_version_id,
        versions,
        {"clm_control": claim},
        make_pack(),
    )

    assert result.status == STATUS_PASS
    assert result.return_to_part1 is False
    assert len(result.claim_traces) == 1
    assert result.claim_traces[0].status == "traceable"
