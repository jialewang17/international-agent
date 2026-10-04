from api.schemas import (
    Approval,
    Claim,
    ContentVersion,
    EvidenceItem,
    EvidencePack,
    EvidenceSpan,
    EvaluationResult,
    GateDecision,
    Source,
    TaskContext,
)


def test_evidence_claim_and_approval_links():
    source = Source(source_id="src-1", uri="https://example.test/source")
    span = EvidenceSpan(span_id="span-1", source_id=source.source_id, text="verified fact")
    item = EvidenceItem(
        evidence_id="ev-1",
        source_id=source.source_id,
        statement="verified fact",
        spans=[span],
    )
    pack = EvidencePack(evidence_pack_id="pack-1", sources=[source], items=[item])
    claim = Claim(claim_id="claim-1", text="verified fact", evidence_ids=[item.evidence_id])
    version = ContentVersion(
        content_version_id="version-1",
        content="draft",
        evidence_pack_id=pack.evidence_pack_id,
        claim_ids=[claim.claim_id],
    )
    approval = Approval(
        approval_id="approval-1",
        content_version_id=version.content_version_id,
        approved=True,
        approver="human",
    )
    assert item.source_id == source.source_id
    assert claim.evidence_ids == [item.evidence_id]
    assert approval.content_version_id == version.content_version_id


def test_remaining_p01_models_validate_minimal_payloads():
    assert TaskContext(task_id="task-1", topic="苏绣").task_id == "task-1"
    assert GateDecision(gate="B", decision="blocked").gate == "B"
    assert EvaluationResult(
        evaluation_id="eval-1",
        content_version_id="version-1",
        part="fact",
        status="pending",
    ).content_version_id == "version-1"


def test_claim_can_represent_unsupported_claim():
    assert Claim(claim_id="claim-1", text="unsupported").evidence_ids == []


def test_content_version_can_link_to_parent():
    version = ContentVersion(
        content_version_id="version-2",
        parent_version_id="version-1",
        content="revised",
    )
    assert version.parent_version_id == "version-1"
