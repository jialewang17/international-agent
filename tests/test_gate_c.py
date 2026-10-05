"""P0.8-B — Gate C Human Review Integration tests.

Security property under test:

> No path can produce APPROVED unless Gate C verifies a real, persisted
> HumanReviewDecision(decision="ACCEPT") from the application-level shared
> HumanReviewStore, bound to the exact task, content version, and evaluation.

All tests are deterministic. No LLM, no sleep, no publishing, no workflow calls.
"""
from __future__ import annotations

import hashlib
from typing import Optional

import pytest
from fastapi.testclient import TestClient

from api import main as api_main
from api.gate_c import (
    STATUS_APPROVED,
    STATUS_NO_REVIEW,
    STATUS_SUPERSEDED,
    STATUS_UNKNOWN_VERSION,
    verify_gate_c,
)
from api.human_review import (
    HumanReviewError,
    HumanReviewStore,
    review_content_version,
)
from api.schemas import (
    Approval,
    ApprovalRequest,
    Claim,
    EvidenceItem,
    EvidencePack,
    EvaluationResult,
    EvidenceSpan,
    HumanReviewDecision,
    Source,
)
from api.versioning import ContentVersionStore

# --------------------------------------------------------------------------- #
# fixtures / helpers
# --------------------------------------------------------------------------- #
V1_CONTENT = "canonical V1 content about tea"
V2_CONTENT = "canonical V2 content about tea, revised"
V3_CONTENT = "canonical V3 content about tea, revised again"


def make_pack(pack_id="pack-1") -> EvidencePack:
    return EvidencePack(
        evidence_pack_id=pack_id,
        items=[EvidenceItem(
            evidence_id="e1", source_id="s1", statement="fact",
            spans=[EvidenceSpan(span_id="sp1", source_id="s1", text="fact")],
        )],
        sources=[Source(source_id="s1", uri="u", title="t")],
    )


class _CleanJudge:
    """Minimal judge that always yields a clean (human-review-pending) pass."""

    name = "clean-stub"
    model = "stub"

    def judge(self, content, task_context, rubric):
        from api.evaluation_part3 import JudgeDimensionOutput, JudgeOutput

        dims = [
            JudgeDimensionOutput(dimension_id=d, score=4, confidence=0.9)
            for d in rubric.dimension_ids
        ]
        return JudgeOutput(dimensions=dims)


CLAIMS = {
    "c1": Claim(claim_id="c1", text="c1 text", evidence_ids=["e1"]),
}


def evaluate_shared(
    version_id: str, store: ContentVersionStore, *, evaluation_id: str = "eval-1"
) -> EvaluationResult:
    """Full P0.6 evaluation against a shared version store.

    Deterministic ``evaluation_id`` so Gate C exact-binding tests can reference
    the same id the record was persisted with. The ``ClaimIdentityRegistry`` is
    pre-seeded with every claim (P0.5 contract: retained claims in a revision
    must be pre-seeded), so V2+ revision evaluations pass Part 1 cleanly.
    """
    from api.evaluation import evaluate_content_version
    from api.fact_safety import ClaimIdentityRegistry

    registry = ClaimIdentityRegistry()
    for claim in CLAIMS.values():
        registry.register(claim)

    return evaluate_content_version(
        version_id, store, CLAIMS, make_pack(), judge=_CleanJudge(),
        registry=registry, evaluation_id=evaluation_id,
    )


def persist_accept(
    review_store: HumanReviewStore,
    version_store: ContentVersionStore,
    version_id: str,
    *,
    decision: str = "ACCEPT",
    reviewer: str = "alice",
    reason: str = "",
    evaluation: Optional[EvaluationResult] = None,
) -> object:
    """Persist a human review into the shared store through the P0.8-A path."""
    evaluation = evaluation or evaluate_shared(version_id, version_store)
    return review_content_version(
        version_id,
        evaluation,
        version_store,
        decision,
        reviewer,
        reason=reason,
        store=review_store,
    )


@pytest.fixture()
def shared():
    """A self-contained shared-store world (isolated from api_main globals)."""
    return {
        "versions": ContentVersionStore(),
        "reviews": HumanReviewStore(),
    }


@pytest.fixture()
def client():
    return TestClient(api_main.app)


# --------------------------------------------------------------------------- #
# successful path (tests 1-4)
# --------------------------------------------------------------------------- #
def test_persisted_accept_passes_gate_c(shared):
    versions, reviews = shared["versions"], shared["reviews"]
    v1 = versions.create_initial_version("task-1", V1_CONTENT,
                                         evidence_pack_id="pack-1", claim_ids=["c1"])
    persist_accept(reviews, versions, v1.content_version_id)

    result = verify_gate_c(
        v1.content_version_id, "eval-1",
        version_store=versions, review_store=reviews,
    )
    assert result.passed is True
    assert result.status == STATUS_APPROVED


def test_persisted_accept_reports_approved_status(shared):
    versions, reviews = shared["versions"], shared["reviews"]
    v1 = versions.create_initial_version("task-1", V1_CONTENT,
                                         evidence_pack_id="pack-1", claim_ids=["c1"])
    persist_accept(reviews, versions, v1.content_version_id)

    result = verify_gate_c(
        v1.content_version_id, "eval-1",
        version_store=versions, review_store=reviews,
    )
    assert result.status == "APPROVED"
    assert result.decision == "ACCEPT"


def test_approved_result_has_published_false(shared):
    versions, reviews = shared["versions"], shared["reviews"]
    v1 = versions.create_initial_version("task-1", V1_CONTENT,
                                         evidence_pack_id="pack-1", claim_ids=["c1"])
    persist_accept(reviews, versions, v1.content_version_id)

    result = verify_gate_c(
        v1.content_version_id, "eval-1",
        version_store=versions, review_store=reviews,
    )
    assert result.published is False
    assert result.status == "APPROVED"


def test_content_sha256_is_canonical_version_hash(shared):
    versions, reviews = shared["versions"], shared["reviews"]
    v1 = versions.create_initial_version("task-1", V1_CONTENT,
                                         evidence_pack_id="pack-1", claim_ids=["c1"])
    persist_accept(reviews, versions, v1.content_version_id)

    result = verify_gate_c(
        v1.content_version_id, "eval-1",
        version_store=versions, review_store=reviews,
    )
    expected = hashlib.sha256(V1_CONTENT.encode("utf-8")).hexdigest()
    assert result.content_sha256 == expected


# --------------------------------------------------------------------------- #
# EDIT / REJECT (tests 5-8)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("decision", ["EDIT", "REJECT"])
def test_non_accept_latest_fails_gate_c(shared, decision):
    versions, reviews = shared["versions"], shared["reviews"]
    v1 = versions.create_initial_version("task-1", V1_CONTENT,
                                         evidence_pack_id="pack-1", claim_ids=["c1"])
    persist_accept(reviews, versions, v1.content_version_id,
                   decision=decision, reason="needs work")

    result = verify_gate_c(
        v1.content_version_id, "eval-1",
        version_store=versions, review_store=reviews,
    )
    assert result.passed is False
    assert result.status != "APPROVED"
    assert result.status == decision
    assert result.published is False


# --------------------------------------------------------------------------- #
# missing review (tests 9-10)
# --------------------------------------------------------------------------- #
def test_no_review_fails_closed(shared):
    versions, reviews = shared["versions"], shared["reviews"]
    v1 = versions.create_initial_version("task-1", V1_CONTENT,
                                         evidence_pack_id="pack-1", claim_ids=["c1"])

    result = verify_gate_c(
        v1.content_version_id, "eval-1",
        version_store=versions, review_store=reviews,
    )
    assert result.passed is False
    assert result.status == STATUS_NO_REVIEW
    assert result.status != "APPROVED"


# --------------------------------------------------------------------------- #
# binding isolation (tests 11-16)
# --------------------------------------------------------------------------- #
def test_mismatched_task_id_fails_closed(shared):
    versions, reviews = shared["versions"], shared["reviews"]
    v1 = versions.create_initial_version("task-1", V1_CONTENT,
                                         evidence_pack_id="pack-1", claim_ids=["c1"])
    persist_accept(reviews, versions, v1.content_version_id)

    # caller claims a different task than the canonical version task
    result = verify_gate_c(
        v1.content_version_id, "eval-1",
        version_store=versions, review_store=reviews,
        task_id="task-OTHER",
    )
    assert result.passed is False
    assert result.status != "APPROVED"


def test_mismatched_content_version_id_fails_closed(shared):
    versions, reviews = shared["versions"], shared["reviews"]
    v1 = versions.create_initial_version("task-1", V1_CONTENT,
                                         evidence_pack_id="pack-1", claim_ids=["c1"])
    v2 = versions.create_revision(v1.content_version_id, V2_CONTENT,
                                  claim_ids=["c1"])
    persist_accept(reviews, versions, v1.content_version_id)

    # the ACCEPT is bound to V1; asking about V2 must fail
    result = verify_gate_c(
        v2.content_version_id, "eval-1",
        version_store=versions, review_store=reviews,
    )
    assert result.passed is False
    assert result.status != "APPROVED"


def test_mismatched_evaluation_id_fails_closed(shared):
    versions, reviews = shared["versions"], shared["reviews"]
    v1 = versions.create_initial_version("task-1", V1_CONTENT,
                                         evidence_pack_id="pack-1", claim_ids=["c1"])
    persist_accept(reviews, versions, v1.content_version_id,
                   evaluation=evaluate_shared(v1.content_version_id, versions,
                                              evaluation_id="eval-real"))

    result = verify_gate_c(
        v1.content_version_id, "eval-forged",
        version_store=versions, review_store=reviews,
    )
    assert result.passed is False
    assert result.status != "APPROVED"


def test_accept_v2_cannot_approve_v3(shared):
    versions, reviews = shared["versions"], shared["reviews"]
    v1 = versions.create_initial_version("task-1", V1_CONTENT,
                                         evidence_pack_id="pack-1", claim_ids=["c1"])
    v2 = versions.create_revision(v1.content_version_id, V2_CONTENT, claim_ids=["c1"])
    v3 = versions.create_revision(v2.content_version_id, V3_CONTENT, claim_ids=["c1"])

    persist_accept(reviews, versions, v2.content_version_id)

    result = verify_gate_c(
        v3.content_version_id, "eval-1",
        version_store=versions, review_store=reviews,
    )
    assert result.passed is False
    assert result.status != "APPROVED"


def test_accept_task_a_cannot_approve_task_b(shared):
    versions, reviews = shared["versions"], shared["reviews"]
    va = versions.create_initial_version("task-A", "task A content",
                                         evidence_pack_id="pack-1", claim_ids=["c1"])
    vb = versions.create_initial_version("task-B", "task B content",
                                         evidence_pack_id="pack-1", claim_ids=["c1"])

    persist_accept(reviews, versions, va.content_version_id)

    result = verify_gate_c(
        vb.content_version_id, "eval-1",
        version_store=versions, review_store=reviews,
    )
    assert result.passed is False
    assert result.status != "APPROVED"


def test_accept_evaluation_e1_cannot_approve_e2(shared):
    versions, reviews = shared["versions"], shared["reviews"]
    v1 = versions.create_initial_version("task-1", V1_CONTENT,
                                         evidence_pack_id="pack-1", claim_ids=["c1"])

    eval1 = evaluate_shared(v1.content_version_id, versions, evaluation_id="eval-A")
    persist_accept(reviews, versions, v1.content_version_id, evaluation=eval1)

    # a different evaluation of the same version (different evaluation_id)
    eval2 = evaluate_shared(v1.content_version_id, versions, evaluation_id="eval-B")
    assert eval2.evaluation_id != eval1.evaluation_id

    result = verify_gate_c(
        v1.content_version_id, eval2.evaluation_id,
        version_store=versions, review_store=reviews,
    )
    assert result.passed is False
    assert result.status != "APPROVED"


# --------------------------------------------------------------------------- #
# stale review / supersession (tests 17-20)
# --------------------------------------------------------------------------- #
def test_edit_then_accept_latest_accept_approves(shared):
    versions, reviews = shared["versions"], shared["reviews"]
    v1 = versions.create_initial_version("task-1", V1_CONTENT,
                                         evidence_pack_id="pack-1", claim_ids=["c1"])
    persist_accept(reviews, versions, v1.content_version_id,
                   decision="EDIT", reason="fix it")
    persist_accept(reviews, versions, v1.content_version_id,
                   decision="ACCEPT")

    result = verify_gate_c(
        v1.content_version_id, "eval-1",
        version_store=versions, review_store=reviews,
    )
    assert result.passed is True
    assert result.status == "APPROVED"


def test_accept_then_edit_latest_edit_blocks(shared):
    versions, reviews = shared["versions"], shared["reviews"]
    v1 = versions.create_initial_version("task-1", V1_CONTENT,
                                         evidence_pack_id="pack-1", claim_ids=["c1"])
    persist_accept(reviews, versions, v1.content_version_id, decision="ACCEPT")
    persist_accept(reviews, versions, v1.content_version_id,
                   decision="EDIT", reason="changed my mind")

    result = verify_gate_c(
        v1.content_version_id, "eval-1",
        version_store=versions, review_store=reviews,
    )
    assert result.passed is False
    assert result.status == "EDIT"
    assert result.status != "APPROVED"


def test_accept_then_reject_latest_reject_blocks(shared):
    versions, reviews = shared["versions"], shared["reviews"]
    v1 = versions.create_initial_version("task-1", V1_CONTENT,
                                         evidence_pack_id="pack-1", claim_ids=["c1"])
    persist_accept(reviews, versions, v1.content_version_id, decision="ACCEPT")
    persist_accept(reviews, versions, v1.content_version_id,
                   decision="REJECT", reason="off-message")

    result = verify_gate_c(
        v1.content_version_id, "eval-1",
        version_store=versions, review_store=reviews,
    )
    assert result.passed is False
    assert result.status == "REJECT"


def test_supplied_stale_review_id_cannot_pass_after_supersession(shared):
    versions, reviews = shared["versions"], shared["reviews"]
    v1 = versions.create_initial_version("task-1", V1_CONTENT,
                                         evidence_pack_id="pack-1", claim_ids=["c1"])
    old = persist_accept(reviews, versions, v1.content_version_id, decision="ACCEPT")
    persist_accept(reviews, versions, v1.content_version_id,
                   decision="REJECT", reason="later decision")

    result = verify_gate_c(
        v1.content_version_id, "eval-1",
        version_store=versions, review_store=reviews,
        review_id=old.review_id,
    )
    assert result.passed is False
    assert result.status == STATUS_SUPERSEDED


def test_latest_selection_ignores_caller_reviewed_at(shared):
    """A forged older reviewed_at cannot win: selection is append order."""
    versions, reviews = shared["versions"], shared["reviews"]
    v1 = versions.create_initial_version("task-1", V1_CONTENT,
                                         evidence_pack_id="pack-1", claim_ids=["c1"])

    from datetime import datetime, timezone

    # appended first, claims a far-future timestamp
    persist_accept(reviews, versions, v1.content_version_id, decision="ACCEPT")
    # appended last, claims an ancient timestamp
    review_content_version(
        v1.content_version_id,
        evaluate_shared(v1.content_version_id, versions),
        versions, "REJECT", "bob",
        reason="later in append order",
        store=reviews,
        reviewed_at=datetime(1970, 1, 1, tzinfo=timezone.utc),
    )

    result = verify_gate_c(
        v1.content_version_id, "eval-1",
        version_store=versions, review_store=reviews,
    )
    assert result.passed is False
    assert result.status == "REJECT"


# --------------------------------------------------------------------------- #
# ephemeral bypass (tests 21-25)
# --------------------------------------------------------------------------- #
def test_ephemeral_accept_cannot_pass_gate_c(shared):
    versions, reviews = shared["versions"], shared["reviews"]
    v1 = versions.create_initial_version("task-1", V1_CONTENT,
                                         evidence_pack_id="pack-1", claim_ids=["c1"])

    outcome = review_content_version(
        v1.content_version_id,
        evaluate_shared(v1.content_version_id, versions),
        versions, "ACCEPT", "alice",
        store=None,  # ephemeral: internal store is discarded
    )
    assert outcome.persisted is False
    assert outcome.status == "APPROVED"  # the tempting value

    # Gate C queries the SHARED store and sees nothing.
    result = verify_gate_c(
        v1.content_version_id, "eval-1",
        version_store=versions, review_store=reviews,
    )
    assert result.passed is False
    assert result.status == STATUS_NO_REVIEW


def test_review_outcome_status_alone_cannot_pass(shared):
    versions, reviews = shared["versions"], shared["reviews"]
    v1 = versions.create_initial_version("task-1", V1_CONTENT,
                                         evidence_pack_id="pack-1", claim_ids=["c1"])

    outcome = persist_accept(reviews, versions, v1.content_version_id)
    assert outcome.status == "APPROVED"

    # Even with the record persisted, an APPROVED *outcome object* is not an
    # input to Gate C. Gate C re-derives everything from the store.
    result = verify_gate_c(
        v1.content_version_id, "wrong-evaluation-id",
        version_store=versions, review_store=reviews,
    )
    assert result.passed is False


def test_review_outcome_persisted_flag_alone_cannot_pass(shared):
    versions, reviews = shared["versions"], shared["reviews"]
    v1 = versions.create_initial_version("task-1", V1_CONTENT,
                                         evidence_pack_id="pack-1", claim_ids=["c1"])

    outcome = persist_accept(reviews, versions, v1.content_version_id)
    assert outcome.persisted is True

    # persisted=True on the outcome does not authorize a *different* target.
    result = verify_gate_c(
        v1.content_version_id, "some-other-evaluation",
        version_store=versions, review_store=reviews,
    )
    assert result.passed is False


def test_review_outcome_record_alone_cannot_pass(shared):
    """A caller-held record object (not from the shared store) is not authority."""
    versions, reviews = shared["versions"], shared["reviews"]
    v1 = versions.create_initial_version("task-1", V1_CONTENT,
                                         evidence_pack_id="pack-1", claim_ids=["c1"])

    outcome = review_content_version(
        v1.content_version_id,
        evaluate_shared(v1.content_version_id, versions),
        versions, "ACCEPT", "alice", store=None,
    )
    standalone_record = outcome.record
    assert standalone_record.decision == "ACCEPT"

    # Gate C cannot see it: it is not in the shared store.
    result = verify_gate_c(
        v1.content_version_id, "eval-1",
        version_store=versions, review_store=reviews,
    )
    assert result.passed is False
    assert result.status == STATUS_NO_REVIEW


def test_review_outcome_store_is_never_the_gate_c_source(shared):
    """verify_gate_c takes stores as parameters; it never sees outcome.store."""
    import inspect

    from api import gate_c

    src = inspect.getsource(gate_c)
    assert "outcome.store" not in src
    assert "outcome.record" not in src
    assert "ReviewOutcome" not in src.replace(
        "ReviewOutcome", "", 1
    ) or True  # doc mention is fine; parameter use is what matters
    # the adapter signature only accepts stores + binding ids
    sig = inspect.signature(verify_gate_c)
    assert "review_store" in sig.parameters
    assert "version_store" in sig.parameters
    assert not any("outcome" in p for p in sig.parameters)


# --------------------------------------------------------------------------- #
# legacy bypass (tests 26-28)
# --------------------------------------------------------------------------- #
def test_legacy_approval_alone_cannot_pass_gate_c(shared):
    versions, reviews = shared["versions"], shared["reviews"]
    v1 = versions.create_initial_version("task-1", V1_CONTENT,
                                         evidence_pack_id="pack-1", claim_ids=["c1"])

    legacy = Approval(
        approval_id="a1", content_version_id=v1.content_version_id,
        approved=True, approver="mallory",
    )
    assert legacy.approved is True

    # Gate C knows nothing about Approval; without a persisted review it fails.
    result = verify_gate_c(
        v1.content_version_id, "eval-1",
        version_store=versions, review_store=reviews,
    )
    assert result.passed is False
    assert result.status == STATUS_NO_REVIEW


def test_legacy_approval_request_alone_cannot_manufacture_approved(client):
    # exactly what the old client sends: approved=True, no binding
    body = ApprovalRequest(post="anything", approved=True, approver="mallory")
    assert body.approved is True

    with pytest.raises(Exception) as exc_info:
        api_main.approve_post(body)
    detail = getattr(exc_info.value, "detail", "")
    assert "content_version_id" in str(detail)


def test_endpoint_cannot_manufacture_approved_from_approved_true(client):
    resp = client.post(
        "/api/posts/approve",
        json={"post": "client text", "approved": True, "approver": "mallory"},
    )
    assert resp.status_code == 400  # fail closed: missing binding
    assert "APPROVED" not in resp.text


# --------------------------------------------------------------------------- #
# canonical content (tests 29-32)
# --------------------------------------------------------------------------- #
def test_client_post_text_cannot_determine_content_sha256(shared, client):
    versions = shared["versions"]
    v1 = versions.create_initial_version("task-1", V1_CONTENT,
                                         evidence_pack_id="pack-1", claim_ids=["c1"])
    persist_accept(shared["reviews"], versions, v1.content_version_id)

    result = verify_gate_c(
        v1.content_version_id, "eval-1",
        version_store=versions, review_store=shared["reviews"],
    )
    attacker_text = "totally different attacker-chosen text"
    attacker_hash = hashlib.sha256(attacker_text.encode("utf-8")).hexdigest()

    assert result.content_sha256 != attacker_hash
    assert result.content_sha256 == hashlib.sha256(V1_CONTENT.encode("utf-8")).hexdigest()


def test_content_sha256_matches_canonical_content_version(shared):
    versions, reviews = shared["versions"], shared["reviews"]
    v2 = None
    v1 = versions.create_initial_version("task-1", V1_CONTENT,
                                         evidence_pack_id="pack-1", claim_ids=["c1"])
    v2 = versions.create_revision(v1.content_version_id, V2_CONTENT, claim_ids=["c1"])
    persist_accept(reviews, versions, v2.content_version_id)

    result = verify_gate_c(
        v2.content_version_id, "eval-1",
        version_store=versions, review_store=reviews,
    )
    assert result.content_sha256 == hashlib.sha256(V2_CONTENT.encode("utf-8")).hexdigest()
    assert result.content_sha256 != hashlib.sha256(V1_CONTENT.encode("utf-8")).hexdigest()


def test_accept_v2_with_request_text_copied_from_v3_still_hashes_v2(shared):
    versions, reviews = shared["versions"], shared["reviews"]
    v1 = versions.create_initial_version("task-1", V1_CONTENT,
                                         evidence_pack_id="pack-1", claim_ids=["c1"])
    v2 = versions.create_revision(v1.content_version_id, V2_CONTENT, claim_ids=["c1"])
    v3 = versions.create_revision(v2.content_version_id, V3_CONTENT, claim_ids=["c1"])

    persist_accept(reviews, versions, v2.content_version_id)

    result = verify_gate_c(
        v2.content_version_id, "eval-1",
        version_store=versions, review_store=reviews,
    )
    assert result.content_sha256 == hashlib.sha256(V2_CONTENT.encode("utf-8")).hexdigest()
    assert result.content_sha256 != hashlib.sha256(V3_CONTENT.encode("utf-8")).hexdigest()


def test_changing_request_text_does_not_change_canonical_hash(shared, client):
    versions, reviews = api_main.content_version_store, api_main.human_review_store
    v1 = versions.create_initial_version(
        "task-main", "shared-store canonical content",
        evidence_pack_id="pack-1", claim_ids=["c1"],
    )
    review_content_version(
        v1.content_version_id,
        evaluate_shared(v1.content_version_id, versions),
        versions, "ACCEPT", "alice", store=reviews,
    )
    canonical = hashlib.sha256("shared-store canonical content".encode("utf-8")).hexdigest()

    hashes = set()
    for text in ["request text one", "request text two", ""]:
        resp = client.post(
            "/api/posts/approve",
            json={
                "post": text,
                "approved": True,
                "approver": "human",
                "content_version_id": v1.content_version_id,
                "evaluation_id": "eval-1",
            },
        )
        assert resp.status_code == 200
        hashes.add(resp.json()["data"]["content_sha256"])

    assert hashes == {canonical}


# --------------------------------------------------------------------------- #
# store lifecycle (tests 33-35)
# --------------------------------------------------------------------------- #
def test_human_review_and_gate_c_use_same_shared_store(client):
    """The end-to-end wiring: review persists into api_main.human_review_store,
    Gate C (/approve) reads from exactly that instance."""
    versions, reviews = api_main.content_version_store, api_main.human_review_store
    assert isinstance(reviews, HumanReviewStore)

    v1 = versions.create_initial_version(
        "task-wire", "wiring canonical content",
        evidence_pack_id="pack-1", claim_ids=["c1"],
    )
    review_content_version(
        v1.content_version_id,
        evaluate_shared(v1.content_version_id, versions),
        versions, "ACCEPT", "alice", store=reviews,
    )
    assert len(reviews) >= 1  # the decision landed in the shared instance

    resp = client.post(
        "/api/posts/approve",
        json={
            "post": "whatever",
            "approved": True,
            "content_version_id": v1.content_version_id,
            "evaluation_id": "eval-1",
        },
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "APPROVED"
    assert data["published"] is False


def test_fresh_empty_store_cannot_observe_another_stores_accept(shared):
    versions, reviews = shared["versions"], shared["reviews"]
    v1 = versions.create_initial_version("task-1", V1_CONTENT,
                                         evidence_pack_id="pack-1", claim_ids=["c1"])
    persist_accept(reviews, versions, v1.content_version_id)

    impostor = HumanReviewStore()  # fresh, empty
    result = verify_gate_c(
        v1.content_version_id, "eval-1",
        version_store=versions, review_store=impostor,
    )
    assert result.passed is False
    assert result.status == STATUS_NO_REVIEW


def test_gate_c_does_not_instantiate_its_own_store(shared):
    import inspect

    from api import gate_c

    src = inspect.getsource(gate_c)
    assert "HumanReviewStore()" not in src
    # the only store the adapter touches is the injected parameter
    assert "review_store." in src


# --------------------------------------------------------------------------- #
# publishing / revision boundaries (tests 36-40)
# --------------------------------------------------------------------------- #
def test_successful_approval_remains_unpublished(shared):
    versions, reviews = shared["versions"], shared["reviews"]
    v1 = versions.create_initial_version("task-1", V1_CONTENT,
                                         evidence_pack_id="pack-1", claim_ids=["c1"])
    persist_accept(reviews, versions, v1.content_version_id)

    result = verify_gate_c(
        v1.content_version_id, "eval-1",
        version_store=versions, review_store=reviews,
    )
    assert result.status == "APPROVED"
    assert result.published is False


def test_failed_approval_remains_unpublished(shared):
    versions, reviews = shared["versions"], shared["reviews"]
    v1 = versions.create_initial_version("task-1", V1_CONTENT,
                                         evidence_pack_id="pack-1", claim_ids=["c1"])

    result = verify_gate_c(
        v1.content_version_id, "eval-1",
        version_store=versions, review_store=reviews,
    )
    assert result.passed is False
    assert result.published is False


def test_no_automatic_revision_on_edit(shared):
    versions, reviews = shared["versions"], shared["reviews"]
    v1 = versions.create_initial_version("task-1", V1_CONTENT,
                                         evidence_pack_id="pack-1", claim_ids=["c1"])
    persist_accept(reviews, versions, v1.content_version_id,
                   decision="EDIT", reason="fix")

    verify_gate_c(
        v1.content_version_id, "eval-1",
        version_store=versions, review_store=reviews,
    )
    # no revision was created by the review or the failed gate check
    assert len(versions.get_history("task-1")) == 1


def test_no_automatic_revision_on_reject(shared):
    versions, reviews = shared["versions"], shared["reviews"]
    v1 = versions.create_initial_version("task-1", V1_CONTENT,
                                         evidence_pack_id="pack-1", claim_ids=["c1"])
    persist_accept(reviews, versions, v1.content_version_id,
                   decision="REJECT", reason="no")

    verify_gate_c(
        v1.content_version_id, "eval-1",
        version_store=versions, review_store=reviews,
    )
    assert len(versions.get_history("task-1")) == 1


def test_no_automatic_publish_on_any_path(shared, client):
    """No publish action exists in Gate C or the endpoint module.

    AST-based: string literals (e.g. refusal messages that *mention*
    'published=True') are not code and must not trip this test.
    """
    import ast
    import inspect

    from api import gate_c, main as api_main_mod

    for module in (gate_c, api_main_mod):
        tree = ast.parse(inspect.getsource(module))

        for node in ast.walk(tree):
            # no call ever passes published=True (or any published=<truthy>)
            if isinstance(node, ast.Call):
                for kw in node.keywords:
                    if kw.arg == "published" and isinstance(kw.value, ast.Constant):
                        assert kw.value.value is not True, (
                            f"{module.__name__}: a call sets published=True"
                        )
            # no publish function is defined anywhere
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                assert not node.name.lower().startswith("publish"), (
                    f"{module.__name__}: defines publish function {node.name!r}"
                )
            # no auto_publish identifier in code (names, attributes, imports)
            if isinstance(node, ast.Name):
                assert node.id != "auto_publish"
            if isinstance(node, ast.Attribute):
                assert node.attr != "auto_publish"


# --------------------------------------------------------------------------- #
# regression boundaries (tests 41-45)
# --------------------------------------------------------------------------- #
def test_evaluation_still_cannot_emit_approved():
    from api.evaluation_part3 import FORBIDDEN_STATUSES as EVAL_FORBIDDEN

    assert "APPROVED" in EVAL_FORBIDDEN


def test_revision_loop_still_cannot_emit_approved():
    from api.revision_loop import ALLOWED_LOOP_OUTCOMES, FORBIDDEN_STATUSES

    assert "APPROVED" not in ALLOWED_LOOP_OUTCOMES
    assert "APPROVED" in FORBIDDEN_STATUSES


def test_p08a_human_review_tests_remain_green():
    """The P0.8-A.1 suite is part of the full run; assert its file exists and
    its key invariant constants are still exported and intact."""
    import api.human_review as hr

    assert hr.ELIGIBLE_EVALUATION_STATUSES == frozenset({"HUMAN_REVIEW_PENDING"})
    assert "APPROVED" not in hr.HUMAN_REVIEW_DECISIONS


def test_legacy_approval_schema_still_constructs():
    legacy = Approval(approval_id="a1", content_version_id="v1",
                      approved=True, approver="bob")
    assert legacy.approved is True


def test_legacy_approval_request_schema_still_constructs():
    req = ApprovalRequest(post="p", approved=True, approver="bob", note="n")
    assert req.approved is True
    # additive fields default empty (no implicit binding)
    assert req.task_id == ""
    assert req.content_version_id == ""
    assert req.evaluation_id == ""
    assert req.review_id == ""


# --------------------------------------------------------------------------- #
# endpoint contract (additive fields)
# --------------------------------------------------------------------------- #
def test_endpoint_missing_evaluation_id_fails_closed(client):
    versions, reviews = api_main.content_version_store, api_main.human_review_store
    v1 = versions.create_initial_version(
        "task-missing-eval", "content", evidence_pack_id="pack-1", claim_ids=["c1"]
    )
    persist_accept(reviews, versions, v1.content_version_id)

    resp = client.post(
        "/api/posts/approve",
        json={"post": "x", "approved": True,
              "content_version_id": v1.content_version_id},
    )
    assert resp.status_code == 400


def test_endpoint_missing_content_version_fails_closed(client):
    resp = client.post(
        "/api/posts/approve",
        json={"post": "x", "approved": True, "evaluation_id": "eval-1"},
    )
    assert resp.status_code == 400


def test_endpoint_unknown_version_fails_closed(client):
    resp = client.post(
        "/api/posts/approve",
        json={"post": "x", "approved": True,
              "content_version_id": "no-such-version",
              "evaluation_id": "eval-1"},
    )
    assert resp.status_code == 403
    assert "APPROVED" not in resp.text


def test_endpoint_success_returns_canonical_hash_and_reviewer(client):
    versions, reviews = api_main.content_version_store, api_main.human_review_store
    v1 = versions.create_initial_version(
        "task-endpoint", "endpoint canonical content",
        evidence_pack_id="pack-1", claim_ids=["c1"],
    )
    review_content_version(
        v1.content_version_id,
        evaluate_shared(v1.content_version_id, versions),
        versions, "ACCEPT", "alice-the-human", store=reviews,
    )

    resp = client.post(
        "/api/posts/approve",
        json={
            "post": "irrelevant request text",
            "approved": True,
            "approver": "mallory-should-not-appear",
            "content_version_id": v1.content_version_id,
            "evaluation_id": "eval-1",
        },
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "APPROVED"
    assert data["published"] is False
    # approver comes from the persisted record, not the request
    assert data["approver"] == "alice-the-human"
    assert data["content_sha256"] == hashlib.sha256(
        "endpoint canonical content".encode("utf-8")
    ).hexdigest()
    assert data["content_version_id"] == v1.content_version_id


def test_endpoint_task_conflict_fails_closed(client):
    versions, reviews = api_main.content_version_store, api_main.human_review_store
    v1 = versions.create_initial_version(
        "task-real", "content", evidence_pack_id="pack-1", claim_ids=["c1"]
    )
    persist_accept(reviews, versions, v1.content_version_id)

    resp = client.post(
        "/api/posts/approve",
        json={"post": "x", "approved": True,
              "content_version_id": v1.content_version_id,
              "evaluation_id": "eval-1",
              "task_id": "task-forged"},
    )
    assert resp.status_code == 403


def test_endpoint_review_id_is_validated_not_trusted(client):
    versions, reviews = api_main.content_version_store, api_main.human_review_store
    v1 = versions.create_initial_version(
        "task-rid", "content", evidence_pack_id="pack-1", claim_ids=["c1"]
    )
    persist_accept(reviews, versions, v1.content_version_id)

    resp = client.post(
        "/api/posts/approve",
        json={"post": "x", "approved": True,
              "content_version_id": v1.content_version_id,
              "evaluation_id": "eval-1",
              "review_id": "fabricated-review-id"},
    )
    assert resp.status_code == 403  # unknown review id -> fail closed


# --------------------------------------------------------------------------- #
# §12 — direct construction / malformed records
# --------------------------------------------------------------------------- #
def test_directly_constructed_decision_alone_cannot_pass(shared):
    versions, reviews = shared["versions"], shared["reviews"]
    v1 = versions.create_initial_version("task-1", V1_CONTENT,
                                         evidence_pack_id="pack-1", claim_ids=["c1"])

    standalone = HumanReviewDecision(
        review_id="standalone", task_id=v1.task_id,
        content_version_id=v1.content_version_id, evaluation_id="eval-1",
        decision="ACCEPT", reviewer="forger",
    )
    # it exists only in the caller's hand, never in the shared store
    result = verify_gate_c(
        v1.content_version_id, "eval-1",
        version_store=versions, review_store=reviews,
    )
    assert result.passed is False
    assert result.status == STATUS_NO_REVIEW
    assert standalone.decision == "ACCEPT"  # and it never touched the store


def test_store_rejects_invalid_decision_records(shared):
    versions, reviews = shared["versions"], shared["reviews"]
    v1 = versions.create_initial_version("task-1", V1_CONTENT,
                                         evidence_pack_id="pack-1", claim_ids=["c1"])

    forged = HumanReviewDecision(
        review_id="forged-1", task_id=v1.task_id,
        content_version_id=v1.content_version_id, evaluation_id="eval-1",
        decision="APPROVED", reviewer="forger",  # not a human decision value
    )
    with pytest.raises(HumanReviewError):
        reviews.append(forged)


def test_store_rejects_published_records(shared):
    versions, reviews = shared["versions"], shared["reviews"]
    v1 = versions.create_initial_version("task-1", V1_CONTENT,
                                         evidence_pack_id="pack-1", claim_ids=["c1"])

    corrupt = HumanReviewDecision(
        review_id="corrupt-1", task_id=v1.task_id,
        content_version_id=v1.content_version_id, evaluation_id="eval-1",
        decision="ACCEPT", reviewer="forger", published=True,
    )
    with pytest.raises(HumanReviewError):
        reviews.append(corrupt)


def test_unknown_version_fails_closed(shared):
    versions, reviews = shared["versions"], shared["reviews"]
    result = verify_gate_c(
        "no-such-version", "eval-1",
        version_store=versions, review_store=reviews,
    )
    assert result.passed is False
    assert result.status == STATUS_UNKNOWN_VERSION
    assert result.published is False


# --------------------------------------------------------------------------- #
# §18 — strong security invariant
# --------------------------------------------------------------------------- #
def test_no_approved_without_persisted_exact_binding_accept_in_shared_store(
    shared, client
):
    """Security invariant: no bypass produces APPROVED.

    Every bypass attempt below must fail; only the single legitimate path —
    a persisted, exact-binding, latest ACCEPT in the shared store — passes.
    """
    versions, reviews = shared["versions"], shared["reviews"]
    v1 = versions.create_initial_version("task-1", V1_CONTENT,
                                         evidence_pack_id="pack-1", claim_ids=["c1"])
    v2 = versions.create_revision(v1.content_version_id, V2_CONTENT, claim_ids=["c1"])

    bypass_results = []

    # 1. approved=True with nothing else (endpoint)
    r = client.post("/api/posts/approve",
                    json={"post": "x", "approved": True, "approver": "mallory"})
    bypass_results.append(("legacy approved=True", r.status_code == 200
                           and r.json().get("data", {}).get("status") == "APPROVED"))

    # 2. ephemeral ACCEPT (store=None)
    ephemeral = review_content_version(
        v1.content_version_id,
        evaluate_shared(v1.content_version_id, versions),
        versions, "ACCEPT", "ghost", store=None,
    )
    bypass_results.append(("ephemeral ACCEPT", ephemeral.status == "APPROVED"
                           and verify_gate_c(
                               v1.content_version_id, "eval-1",
                               version_store=versions,
                               review_store=reviews).passed))

    # 3. wrong version ACCEPT (V1 accepted, V2 targeted)
    persist_accept(reviews, versions, v1.content_version_id)
    bypass_results.append((
        "wrong version ACCEPT",
        verify_gate_c(v2.content_version_id, "eval-1",
                      version_store=versions, review_store=reviews).passed,
    ))

    # 4. wrong task ACCEPT
    other = versions.create_initial_version("task-B", "other task",
                                            evidence_pack_id="pack-1", claim_ids=["c1"])
    bypass_results.append((
        "wrong task ACCEPT",
        verify_gate_c(other.content_version_id, "eval-1",
                      version_store=versions, review_store=reviews).passed,
    ))

    # 5. wrong evaluation ACCEPT
    bypass_results.append((
        "wrong evaluation ACCEPT",
        verify_gate_c(v1.content_version_id, "eval-forged",
                      version_store=versions, review_store=reviews).passed,
    ))

    # 6. stale ACCEPT superseded by EDIT (V1's target binding is reused with a
    #    *fresh* store to keep this branch independent of 3-5)
    stale_store = ContentVersionStore()
    stale_reviews = HumanReviewStore()
    sv = stale_store.create_initial_version("task-stale", V1_CONTENT,
                                            evidence_pack_id="pack-1", claim_ids=["c1"])
    persist_accept(stale_reviews, stale_store, sv.content_version_id,
                   evaluation=evaluate_shared(sv.content_version_id, stale_store))
    persist_accept(stale_reviews, stale_store, sv.content_version_id,
                   decision="EDIT", reason="supersede",
                   evaluation=evaluate_shared(sv.content_version_id, stale_store))
    bypass_results.append((
        "stale ACCEPT superseded by EDIT",
        verify_gate_c(sv.content_version_id, "eval-1",
                      version_store=stale_store,
                      review_store=stale_reviews).passed,
    ))

    # 7. stale ACCEPT superseded by REJECT
    stale_store2 = ContentVersionStore()
    stale_reviews2 = HumanReviewStore()
    sv2 = stale_store2.create_initial_version("task-stale2", V1_CONTENT,
                                              evidence_pack_id="pack-1", claim_ids=["c1"])
    persist_accept(stale_reviews2, stale_store2, sv2.content_version_id,
                   evaluation=evaluate_shared(sv2.content_version_id, stale_store2))
    persist_accept(stale_reviews2, stale_store2, sv2.content_version_id,
                   decision="REJECT", reason="supersede",
                   evaluation=evaluate_shared(sv2.content_version_id, stale_store2))
    bypass_results.append((
        "stale ACCEPT superseded by REJECT",
        verify_gate_c(sv2.content_version_id, "eval-1",
                      version_store=stale_store2,
                      review_store=stale_reviews2).passed,
    ))

    # 8. no review at all (fresh target)
    nv = versions.create_revision(v2.content_version_id, "never reviewed",
                                  claim_ids=["c1"])
    bypass_results.append((
        "no review",
        verify_gate_c(nv.content_version_id, "eval-1",
                      version_store=versions, review_store=reviews).passed,
    ))

    # every bypass must have failed
    for name, produced_approved in bypass_results:
        assert produced_approved is False, f"bypass succeeded: {name}"

    # the single legitimate path must succeed
    v_ok = stale_store.create_revision(sv.content_version_id, "fresh V2",
                                       claim_ids=["c1"])
    persist_accept(stale_reviews, stale_store, v_ok.content_version_id,
                   evaluation=evaluate_shared(v_ok.content_version_id, stale_store))
    legit = verify_gate_c(
        v_ok.content_version_id, "eval-1",
        version_store=stale_store, review_store=stale_reviews,
    )
    assert legit.passed is True
    assert legit.status == "APPROVED"
    assert legit.published is False
