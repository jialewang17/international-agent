"""P0.8-A — Minimal Human Review / Audit core tests.

Every test is deterministic: no LLM, no sleep, no network. Time assertions only
check tz-awareness of the produced timestamp.
"""
from __future__ import annotations

from datetime import timezone

import pytest

from api.human_review import (
    ELIGIBLE_EVALUATION_STATUSES,
    INELIGIBLE_EVALUATION_STATUSES,
    LOOP_STOP_REASON_REFERENCE,
    HumanReviewError,
    HumanReviewStore,
    OUTCOME_APPROVED,
    review_content_version,
)
from api.schemas import (
    HUMAN_REVIEW_DECISIONS,
    Approval,
    ContentVersion,
    EvaluationResult,
    HumanReviewDecision,
)
from api.versioning import ContentVersionStore


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def make_version(store: ContentVersionStore, *, task_id="task-1", content="hello",
                 evidence_pack_id="pack-1"):
    return store.create_initial_version(
        task_id, content, evidence_pack_id=evidence_pack_id, claim_ids=["c1"]
    )


def make_evaluation(version: ContentVersion, *, status="HUMAN_REVIEW_PENDING",
                    task_id=None, evaluation_id="eval-1", return_to_part1=False):
    return EvaluationResult(
        evaluation_id=evaluation_id,
        content_version_id=version.content_version_id,
        part="evaluation",
        status=status,
        task_id=version.task_id if task_id is None else task_id,
        return_to_part1=return_to_part1,
    )


def review(store, version, evaluation, decision="ACCEPT", reviewer="alice",
           **kwargs):
    review_store = kwargs.pop("review_store", None)
    return review_content_version(
        version.content_version_id,
        evaluation,
        store,
        decision,
        reviewer,
        store=review_store,
        **kwargs,
    )


# --------------------------------------------------------------------------- #
# 1-6 ACCEPT
# --------------------------------------------------------------------------- #
def test_accept_yields_approved():
    store = ContentVersionStore()
    version = make_version(store)
    outcome = review(store, version, make_evaluation(version), decision="ACCEPT")

    assert outcome.decision == "ACCEPT"
    assert outcome.status == OUTCOME_APPROVED


def test_accept_is_never_published():
    store = ContentVersionStore()
    version = make_version(store)
    outcome = review(store, version, make_evaluation(version), decision="ACCEPT")

    assert outcome.published is False
    assert outcome.record.published is False


def test_accept_audit_record_binds_task_version_evaluation():
    store = ContentVersionStore()
    version = make_version(store)
    evaluation = make_evaluation(version, evaluation_id="eval-xyz")
    outcome = review(store, version, evaluation, decision="ACCEPT", reviewer="alice")

    record = outcome.record
    assert record.task_id == version.task_id
    assert record.content_version_id == version.content_version_id
    assert record.evaluation_id == "eval-xyz"
    assert record.reviewer == "alice"
    assert record.decision == "ACCEPT"
    assert record.reviewed_at is not None
    assert record.reviewed_at.tzinfo is not None


def test_accept_binds_evidence_pack_id_from_content_version():
    store = ContentVersionStore()
    version = make_version(store, evidence_pack_id="pack-abc")
    outcome = review(store, version, make_evaluation(version), decision="ACCEPT")

    assert outcome.record.evidence_pack_id == "pack-abc"


def test_accept_does_not_modify_content_version():
    store = ContentVersionStore()
    version = make_version(store)
    before = version.model_dump()

    review(store, version, make_evaluation(version), decision="ACCEPT")

    after = store.get_version(version.content_version_id)
    assert after.model_dump() == before


def test_accept_does_not_create_a_new_content_version():
    store = ContentVersionStore()
    version = make_version(store)
    review(store, version, make_evaluation(version), decision="ACCEPT")

    assert len(store.get_history(version.task_id)) == 1


# --------------------------------------------------------------------------- #
# 7-10 EDIT
# --------------------------------------------------------------------------- #
def test_edit_is_recorded():
    store = ContentVersionStore()
    version = make_version(store)
    outcome = review(
        store, version, make_evaluation(version), decision="EDIT",
        reason="needs a clearer opening",
    )

    assert outcome.decision == "EDIT"
    assert outcome.record.reason == "needs a clearer opening"


def test_edit_requires_non_blank_reason():
    store = ContentVersionStore()
    version = make_version(store)
    with pytest.raises(HumanReviewError):
        review(store, version, make_evaluation(version), decision="EDIT", reason="   ")


def test_edit_never_yields_approved():
    store = ContentVersionStore()
    version = make_version(store)
    outcome = review(
        store, version, make_evaluation(version), decision="EDIT", reason="fix tone"
    )

    assert outcome.status != OUTCOME_APPROVED
    assert outcome.status == "EDIT"


def test_edit_creates_no_revision():
    store = ContentVersionStore()
    version = make_version(store)
    before = version.model_dump()

    review(store, version, make_evaluation(version), decision="EDIT", reason="fix tone")

    assert len(store.get_history(version.task_id)) == 1
    assert store.get_version(version.content_version_id).model_dump() == before


# --------------------------------------------------------------------------- #
# 11-14 REJECT
# --------------------------------------------------------------------------- #
def test_reject_is_recorded():
    store = ContentVersionStore()
    version = make_version(store)
    outcome = review(
        store, version, make_evaluation(version), decision="REJECT", reason="off-message"
    )

    assert outcome.decision == "REJECT"
    assert outcome.record.reason == "off-message"


def test_reject_requires_non_blank_reason():
    store = ContentVersionStore()
    version = make_version(store)
    with pytest.raises(HumanReviewError):
        review(store, version, make_evaluation(version), decision="REJECT", reason="")


def test_reject_never_yields_approved():
    store = ContentVersionStore()
    version = make_version(store)
    outcome = review(
        store, version, make_evaluation(version), decision="REJECT", reason="off-message"
    )

    assert outcome.status != OUTCOME_APPROVED
    assert outcome.status == "REJECT"


def test_reject_does_not_change_workflow():
    """The review core must not touch workflow state at all."""
    import api.human_review as hr

    assert not hasattr(hr, "workflow_state_machine")
    assert not hasattr(hr, "GateDecision")

    store = ContentVersionStore()
    version = make_version(store)
    review(store, version, make_evaluation(version), decision="REJECT", reason="no")


# --------------------------------------------------------------------------- #
# 15-17 ineligible statuses fail closed
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "status",
    ["REVISION_RECOMMENDED", "RETURN_TO_PART1", "INSUFFICIENT_CONTEXT"],
)
def test_ineligible_status_fails_closed(status):
    store = ContentVersionStore()
    version = make_version(store)
    with pytest.raises(HumanReviewError):
        review(store, version, make_evaluation(version, status=status), decision="ACCEPT")


def test_return_to_part1_flag_fails_closed():
    store = ContentVersionStore()
    version = make_version(store)
    evaluation = make_evaluation(
        version, status="HUMAN_REVIEW_PENDING", return_to_part1=True
    )
    with pytest.raises(HumanReviewError):
        review(store, version, evaluation, decision="ACCEPT")


def test_blocked_status_fails_closed():
    store = ContentVersionStore()
    version = make_version(store)
    with pytest.raises(HumanReviewError):
        review(store, version, make_evaluation(version, status="BLOCKED"), decision="ACCEPT")


# --------------------------------------------------------------------------- #
# 18-22 structural validation
# --------------------------------------------------------------------------- #
def test_evaluation_version_mismatch_fails_closed():
    store = ContentVersionStore()
    version = make_version(store)
    other = make_version(store, content="other")
    evaluation = make_evaluation(other)  # bound to a different version

    with pytest.raises(HumanReviewError):
        review_content_version(
            version.content_version_id, evaluation, store, "ACCEPT", "alice"
        )


def test_explicit_task_id_conflict_fails_closed():
    store = ContentVersionStore()
    version = make_version(store, task_id="task-1")
    evaluation = make_evaluation(version, task_id="task-OTHER")

    with pytest.raises(HumanReviewError):
        review(store, version, evaluation, decision="ACCEPT")


def test_empty_task_id_on_evaluation_is_tolerated():
    """The compatibility field may be empty; only an explicit conflict fails."""
    store = ContentVersionStore()
    version = make_version(store)
    evaluation = make_evaluation(version, task_id="")

    outcome = review(store, version, evaluation, decision="ACCEPT")
    assert outcome.record.task_id == version.task_id


def test_unknown_content_version_fails_closed():
    store = ContentVersionStore()
    version = make_version(store)
    evaluation = make_evaluation(version)

    with pytest.raises(HumanReviewError):
        review_content_version("no-such-version", evaluation, store, "ACCEPT", "alice")


def test_invalid_decision_fails_closed():
    store = ContentVersionStore()
    version = make_version(store)
    for bad in ["APPROVED", "PASS", "accept_", "", "  ", "MAYBE"]:
        with pytest.raises(HumanReviewError):
            review(store, version, make_evaluation(version), decision=bad)


def test_blank_reviewer_fails_closed():
    store = ContentVersionStore()
    version = make_version(store)
    for bad in ["", "   ", None]:
        with pytest.raises(HumanReviewError):
            review(store, version, make_evaluation(version), decision="ACCEPT", reviewer=bad)


# --------------------------------------------------------------------------- #
# 23-24 warnings / real audience
# --------------------------------------------------------------------------- #
def test_unresolved_warnings_are_audited_verbatim():
    store = ContentVersionStore()
    version = make_version(store)
    warnings = ["unverified pop figure", "tone drift in closing"]

    outcome = review(
        store, version, make_evaluation(version), decision="ACCEPT",
        unresolved_warnings=warnings,
    )

    assert list(outcome.record.unresolved_warnings) == warnings
    assert outcome.warnings == warnings


def test_absent_warnings_default_to_empty_and_are_not_fabricated():
    store = ContentVersionStore()
    version = make_version(store)
    outcome = review(store, version, make_evaluation(version), decision="ACCEPT")

    assert tuple(outcome.record.unresolved_warnings) == ()


def test_not_evaluated_real_audience_does_not_block_accept():
    store = ContentVersionStore()
    version = make_version(store)
    evaluation = make_evaluation(version)
    assert evaluation.real_audience_evaluation == "NOT_EVALUATED"

    outcome = review(store, version, evaluation, decision="ACCEPT")
    assert outcome.status == OUTCOME_APPROVED


# --------------------------------------------------------------------------- #
# 25-27 store semantics
# --------------------------------------------------------------------------- #
def test_duplicate_review_id_cannot_overwrite():
    store = ContentVersionStore()
    version = make_version(store)
    review_store = HumanReviewStore()

    review(store, version, make_evaluation(version), decision="ACCEPT",
           review_store=review_store, review_id="fixed-id")

    with pytest.raises(HumanReviewError):
        review(store, version, make_evaluation(version), decision="REJECT",
               reason="changed my mind", review_store=review_store, review_id="fixed-id")


def test_history_is_append_only():
    store = ContentVersionStore()
    version = make_version(store)
    review_store = HumanReviewStore()
    evaluation = make_evaluation(version)

    first = review(store, version, evaluation, decision="EDIT", reason="a",
                   review_store=review_store)
    second = review(store, version, evaluation, decision="ACCEPT",
                    review_store=review_store)

    history = review_store.history_for(version.content_version_id)
    assert [r.review_id for r in history] == [first.review_id, second.review_id]
    # the first record is untouched
    assert review_store.get(first.review_id).decision == "EDIT"


def test_history_order_is_deterministic():
    store = ContentVersionStore()
    version = make_version(store)
    review_store = HumanReviewStore()
    evaluation = make_evaluation(version)

    ids = []
    for i in range(5):
        out = review(store, version, evaluation, decision="ACCEPT",
                     review_store=review_store)
        ids.append(out.review_id)

    assert [r.review_id for r in review_store.history_for(version.content_version_id)] == ids
    assert [r.review_id for r in review_store.history_for(version.content_version_id)] == ids


def test_get_unknown_review_fails_closed():
    with pytest.raises(HumanReviewError):
        HumanReviewStore().get("nope")


# --------------------------------------------------------------------------- #
# 28-30 module boundaries
# --------------------------------------------------------------------------- #
def test_human_review_does_not_import_revision_loop():
    """No *import* of the revision loop — a docstring mention is not coupling."""
    import ast
    import inspect

    import api.human_review as hr

    tree = ast.parse(inspect.getsource(hr))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)

    assert not any("revision_loop" in m for m in imported), imported
    assert not hasattr(hr, "RevisionLoopRunner")
    assert not hasattr(hr, "compile_revision_instructions")


def test_human_review_does_not_import_workflow():
    import inspect

    import api.human_review as hr

    src = inspect.getsource(hr)
    assert "from api.workflow" not in src
    assert "import workflow" not in src
    assert not hasattr(hr, "workflow_state_machine")
    assert not hasattr(hr, "WorkflowStateMachine")


def test_no_path_produces_published_true():
    import inspect
    import api.human_review as hr

    src = inspect.getsource(hr)
    assert "published=True" not in src
    assert "published = True" not in src

    store = ContentVersionStore()
    version = make_version(store)
    for decision, kwargs in [
        ("ACCEPT", {}),
        ("EDIT", {"reason": "x"}),
        ("REJECT", {"reason": "y"}),
    ]:
        outcome = review(store, version, make_evaluation(version),
                         decision=decision, **kwargs)
        assert outcome.published is False
        assert outcome.record.published is False


# --------------------------------------------------------------------------- #
# regressions
# --------------------------------------------------------------------------- #
def test_evaluation_still_cannot_produce_approved():
    from api.evaluation_part3 import FORBIDDEN_STATUSES

    assert "APPROVED" in FORBIDDEN_STATUSES


def test_revision_loop_outcomes_still_exclude_approved():
    from api.revision_loop import ALLOWED_LOOP_OUTCOMES, FORBIDDEN_STATUSES

    assert "APPROVED" not in ALLOWED_LOOP_OUTCOMES
    assert "APPROVED" in FORBIDDEN_STATUSES


def test_legacy_approval_schema_still_constructs():
    legacy = Approval(
        approval_id="a1", content_version_id="v1", approved=True, approver="bob"
    )
    assert legacy.approved is True


def test_human_review_decision_set_excludes_approved():
    assert "APPROVED" not in HUMAN_REVIEW_DECISIONS
    assert HUMAN_REVIEW_DECISIONS == frozenset({"ACCEPT", "EDIT", "REJECT"})


def test_eligible_statuses_are_the_real_human_review_ceiling():
    """Eligibility is exactly the P0.6 human-review ceiling.

    Grounded in ``api/evaluation_part3._resolve_status``, which returns
    ``HUMAN_REVIEW_PENDING`` for a clean pass with the comment "A clean pass
    still needs a human; the skill has no approval authority."
    """
    assert ELIGIBLE_EVALUATION_STATUSES == frozenset({"HUMAN_REVIEW_PENDING"})


def test_completed_is_not_review_eligible():
    """COMPLETED is a skill status, not a human-review ceiling.

    SKILL_SPEC §13 lists COMPLETED among statuses the skill may emit; the
    pipeline spec's review vocabulary is ``REVISE | READY_FOR_HUMAN_REVIEW``.
    Nothing in the frozen contracts authorises COMPLETED as review input, so
    this module fails closed.
    """
    assert "COMPLETED" not in ELIGIBLE_EVALUATION_STATUSES
    assert "COMPLETED" in INELIGIBLE_EVALUATION_STATUSES

    store = ContentVersionStore()
    version = make_version(store)
    with pytest.raises(HumanReviewError):
        review(store, version, make_evaluation(version, status="COMPLETED"),
               decision="ACCEPT")


@pytest.mark.parametrize("status", ["CREATED", "PRECHECK", "SCORING"])
def test_non_terminal_skill_statuses_are_not_review_eligible(status):
    store = ContentVersionStore()
    version = make_version(store)
    with pytest.raises(HumanReviewError):
        review(store, version, make_evaluation(version, status=status),
               decision="ACCEPT")


def test_loop_stop_reasons_are_reference_only_not_enforced_here():
    """P0.7 stop reasons live on RevisionLoopState, not on EvaluationResult.

    ``review_content_version`` accepts an ``EvaluationResult`` and therefore
    cannot observe them. The constant is vocabulary documentation, not a check.
    """
    assert LOOP_STOP_REASON_REFERENCE == frozenset(
        {"FACT_LOCK_FAILED", "MAX_ITERATIONS_REACHED", "EXECUTOR_FAILED"}
    )
    # They are not EvaluationResult statuses, so they are not in either set.
    for reason in LOOP_STOP_REASON_REFERENCE:
        assert reason not in ELIGIBLE_EVALUATION_STATUSES


def test_loop_stop_reasons_are_not_evaluation_result_statuses():
    """Proves the non-enforcement claim against the real P0.7 contract."""
    from api.revision_loop import RevisionLoopState
    from api.schemas import EvaluationResult

    # The reasons are stored on the loop state, not on EvaluationResult.
    assert "stop_reason" in RevisionLoopState.__dataclass_fields__
    assert "stop_reason" not in EvaluationResult.model_fields
    assert "final_status" not in EvaluationResult.model_fields


# --------------------------------------------------------------------------- #
# HARDENING A — audit immutability (real security property)
# --------------------------------------------------------------------------- #
def _append_edit(store, version, review_store, review_id="r-imm"):
    evaluation = make_evaluation(version)
    review(store, version, evaluation, decision="EDIT", reason="original reason",
           review_store=review_store, review_id=review_id)
    return evaluation


def test_get_does_not_expose_a_mutable_reference():
    """Threat: record = store.get(id); record.decision = "ACCEPT"."""
    store = ContentVersionStore()
    version = make_version(store)
    review_store = HumanReviewStore()
    _append_edit(store, version, review_store)

    leaked = review_store.get("r-imm")
    with pytest.raises(Exception):
        leaked.decision = "ACCEPT"

    # stored audit fact is unchanged
    assert review_store.get("r-imm").decision == "EDIT"


def test_history_for_does_not_expose_mutable_references():
    """Threat: history[0].decision = "ACCEPT"."""
    store = ContentVersionStore()
    version = make_version(store)
    review_store = HumanReviewStore()
    _append_edit(store, version, review_store)

    history = review_store.history_for(version.content_version_id)
    with pytest.raises(Exception):
        history[0].decision = "ACCEPT"

    assert review_store.get("r-imm").decision == "EDIT"
    assert review_store.history_for(version.content_version_id)[0].decision == "EDIT"


def test_all_records_does_not_expose_mutable_references():
    store = ContentVersionStore()
    version = make_version(store)
    review_store = HumanReviewStore()
    _append_edit(store, version, review_store)

    records = review_store.all_records()
    with pytest.raises(Exception):
        records[0].decision = "ACCEPT"

    assert review_store.get("r-imm").decision == "EDIT"


def test_caller_reference_cannot_rewrite_stored_history():
    """Threat: the object passed to append() is still held by the caller."""
    store = ContentVersionStore()
    version = make_version(store)
    review_store = HumanReviewStore()
    _append_edit(store, version, review_store)

    # A *new* caller-owned record appended, then mutated by its holder.
    holder = HumanReviewDecision(
        review_id="r-holder", task_id=version.task_id,
        content_version_id=version.content_version_id,
        evaluation_id="eval-1", decision="EDIT", reviewer="alice",
        reason="r",
    )
    review_store.append(holder)
    with pytest.raises(Exception):
        holder.decision = "ACCEPT"

    assert review_store.get("r-holder").decision == "EDIT"


def test_nested_warnings_cannot_be_mutated_in_place():
    """frozen=True alone does not protect nested containers; tuple does."""
    store = ContentVersionStore()
    version = make_version(store)
    review_store = HumanReviewStore()
    review(store, version, make_evaluation(version), decision="ACCEPT",
           unresolved_warnings=["w1"], review_store=review_store,
           review_id="r-warn")

    record = review_store.get("r-warn")
    with pytest.raises(Exception):
        record.unresolved_warnings.append("injected")

    assert list(review_store.get("r-warn").unresolved_warnings) == ["w1"]


def test_frozen_records_cannot_be_reassigned_via_model_copy_bypass():
    """The only way to change a record is to build a new one, not to mutate."""
    store = ContentVersionStore()
    version = make_version(store)
    review_store = HumanReviewStore()
    _append_edit(store, version, review_store)

    original = review_store.get("r-imm")
    changed = original.model_copy(update={"decision": "ACCEPT"})
    # the copy is a *new* object; the stored record is untouched
    assert changed.decision == "ACCEPT"
    assert review_store.get("r-imm").decision == "EDIT"


def test_audit_critical_fields_are_all_immutable():
    store = ContentVersionStore()
    version = make_version(store)
    review_store = HumanReviewStore()
    _append_edit(store, version, review_store)

    record = review_store.get("r-imm")
    for field_name, bad_value in [
        ("decision", "ACCEPT"),
        ("task_id", "other-task"),
        ("content_version_id", "other-version"),
        ("evaluation_id", "other-eval"),
        ("reviewer", "mallory"),
        ("reviewed_at", None),
        ("evidence_pack_id", "other-pack"),
        ("published", True),
    ]:
        with pytest.raises(Exception):
            setattr(record, field_name, bad_value)

    stored = review_store.get("r-imm")
    assert stored.decision == "EDIT"
    assert stored.reviewer == "alice"
    assert stored.published is False


# --------------------------------------------------------------------------- #
# HARDENING B — persisted vs ephemeral review
# --------------------------------------------------------------------------- #
def test_explicit_shared_store_review_is_persisted():
    store = ContentVersionStore()
    version = make_version(store)
    review_store = HumanReviewStore()

    outcome = review(store, version, make_evaluation(version), decision="ACCEPT",
                     review_store=review_store)

    assert outcome.persisted is True
    assert len(review_store) == 1
    assert review_store.get(outcome.review_id).decision == "ACCEPT"


def test_no_store_review_is_ephemeral_and_unretrievable():
    store = ContentVersionStore()
    version = make_version(store)

    outcome = review(store, version, make_evaluation(version), decision="ACCEPT")

    # outcome exists, but no shared store can later retrieve it
    assert outcome.persisted is False
    assert outcome.status == OUTCOME_APPROVED
    shared = HumanReviewStore()
    with pytest.raises(HumanReviewError):
        shared.get(outcome.review_id)


def test_store_none_remains_supported_for_compatibility():
    store = ContentVersionStore()
    version = make_version(store)
    outcome = review_content_version(
        version.content_version_id, make_evaluation(version), store,
        "ACCEPT", "alice",
    )
    assert outcome.persisted is False
    assert outcome.published is False


def test_review_outcome_exposes_no_approval_credential_api():
    """No public helper turns ReviewOutcome.status into Gate C truth."""
    import inspect

    import api.human_review as hr

    src = inspect.getsource(hr)
    for banned in ["def approve", "def pass_gate", "def finalize", "publish("]:
        assert banned not in src


def test_status_approved_is_not_a_decision_value():
    """APPROVED stays an outcome, never an input."""
    store = ContentVersionStore()
    version = make_version(store)
    with pytest.raises(HumanReviewError):
        review(store, version, make_evaluation(version), decision="APPROVED")
