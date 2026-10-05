"""P0.8-A — Minimal Human Review / Audit core.

Scope: record one human decision (ACCEPT / EDIT / REJECT) against one
*evaluation of one content version*, and keep an append-only audit trail of it.

This module deliberately does **no** side effects beyond appending an audit
record:

* it never modifies or creates a ``ContentVersion``;
* it never calls the revision loop;
* it never touches ``workflow_state_machine`` / Gate B / Gate C;
* it never publishes anything (``published`` is always ``False``).

The human review ceiling is whatever P0.6 already established. Only an
evaluation that reached ``HUMAN_REVIEW_PENDING`` (or was explicitly ready for
human review) is eligible. ``REVISION_RECOMMENDED``, ``RETURN_TO_PART1`` and
``INSUFFICIENT_CONTEXT`` are **not** reviewable — and P0.7's failure stop
outcomes must never be reinterpreted as an approving state.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import uuid4

from api.schemas import (
    HUMAN_REVIEW_DECISIONS,
    EvaluationResult,
    HumanReviewDecision,
)
from api.versioning import ContentVersionStore, VersioningError

# --------------------------------------------------------------------------- #
# outcome vocabulary
# --------------------------------------------------------------------------- #
#: The Gate-C-equivalent outcome. It is an *outcome of ACCEPT*, never a decision
#: value and never something an evaluation may produce.
OUTCOME_APPROVED = "APPROVED"

#: P0.6 evaluation statuses that are eligible to enter human review.
#:
#: ``HUMAN_REVIEW_PENDING`` is the *only* true human-review ceiling. P0.6
#: establishes this explicitly in ``evaluation_part3._resolve_status``: a clean
#: pass returns ``HUMAN_REVIEW_PENDING`` with the comment "A clean pass still
#: needs a human; the skill has no approval authority."
#:
#: ``COMPLETED`` is deliberately excluded. The frozen contracts never connect it
#: to human review: SKILL_SPEC §13 lists it as a status the skill may *emit*
#: (alongside ``SCORING``/``CREATED``), and the pipeline spec's review status
#: vocabulary is ``REVISE | READY_FOR_HUMAN_REVIEW``. "Non-blocking terminal
#: state" is not the same as "authorised input to human approval", and this
#: module fails closed rather than inferring eligibility.
ELIGIBLE_EVALUATION_STATUSES = frozenset({"HUMAN_REVIEW_PENDING"})

#: Statuses that must fail closed if someone tries to review them.
INELIGIBLE_EVALUATION_STATUSES = frozenset(
    {
        "REVISION_RECOMMENDED",
        "RETURN_TO_PART1",
        "INSUFFICIENT_CONTEXT",
        "BLOCKED",
        # Not a human-review ceiling: see ELIGIBLE_EVALUATION_STATUSES above.
        "COMPLETED",
        "CREATED",
        "PRECHECK",
        "SCORING",
    }
)

#: Reference vocabulary only — NOT an enforced check.
#:
#: These three strings are P0.7 ``RevisionLoopState.stop_reason`` values
#: (``api/revision_loop.py``). They are stored on the loop state dataclass and
#: are *never* written into ``EvaluationResult.status``. ``review_content_version``
#: takes an ``EvaluationResult``, so it cannot observe them under the current
#: frozen contracts; there is no field to read them from.
#:
#: Kept as documentation of the vocabulary that must stay out of human review,
#: so a future P0.8-B adapter that does surface loop outcomes can enforce it.
#: Do not claim this is enforced today.
#:
#: Real enforcement for the observable surface already exists via
#: ``INELIGIBLE_EVALUATION_STATUSES`` (which covers every status an
#: ``EvaluationResult`` can actually carry out of P0.6).
LOOP_STOP_REASON_REFERENCE = frozenset(
    {"FACT_LOCK_FAILED", "MAX_ITERATIONS_REACHED", "EXECUTOR_FAILED"}
)


class HumanReviewError(ValueError):
    """Raised when a human review request is not reviewable or not well formed."""


# --------------------------------------------------------------------------- #
# store
# --------------------------------------------------------------------------- #
class HumanReviewStore:
    """In-memory, append-only audit store for human review records.

    "Append-only" is enforced in three ways:

    1. an existing ``review_id`` can never be overwritten;
    2. no public method mutates a stored record;
    3. stored records are returned as :meth:`~pydantic.BaseModel.model_copy`
       snapshots, and ``HumanReviewDecision`` itself is a frozen model, so a
       caller cannot rewrite audit facts through ``get()`` / ``history_for()`` /
       ``all_records()``, nor through the reference it handed to :meth:`append`.
    """

    def __init__(self):
        self._records: Dict[str, HumanReviewDecision] = {}

    def append(self, record: HumanReviewDecision) -> HumanReviewDecision:
        """Store a *defensive copy* of ``record`` and return that stored copy.

        Copying on write matters: if the caller keeps its own reference and the
        stored object were the same instance, ``record.decision = ...`` would
        silently rewrite stored history. ``model_copy`` prevents that.

        Smallest local validation (P0.8-B): a record whose ``decision`` is not a
        human decision value, or whose ``published`` is not ``False``, can never
        be a legitimate audit fact, so it is rejected here rather than being
        allowed to sit in the shared store for Gate C to trip over.
        """
        if not record.review_id:
            raise HumanReviewError("review_id is required")
        if str(record.decision) not in HUMAN_REVIEW_DECISIONS:
            raise HumanReviewError(
                f"invalid review decision: {record.decision!r}; "
                f"expected one of {sorted(HUMAN_REVIEW_DECISIONS)}"
            )
        if record.published is not False:
            raise HumanReviewError("a review record can never be created published")
        if record.review_id in self._records:
            raise HumanReviewError(f"review_id already exists: {record.review_id}")
        stored = record.model_copy(deep=True)
        self._records[record.review_id] = stored
        return stored

    def get(self, review_id: str) -> HumanReviewDecision:
        try:
            stored = self._records[review_id]
        except KeyError as exc:
            raise HumanReviewError(f"review not found: {review_id}") from exc
        # Hand out an independent frozen snapshot, never the stored instance.
        return stored.model_copy(deep=True)

    def history_for(self, content_version_id: str) -> List[HumanReviewDecision]:
        """All reviews for a version, in deterministic (append) order."""
        return [
            record.model_copy(deep=True)
            for record in self._records.values()
            if record.content_version_id == content_version_id
        ]

    def history_for_task(self, task_id: str) -> List[HumanReviewDecision]:
        return [
            record.model_copy(deep=True)
            for record in self._records.values()
            if record.task_id == task_id
        ]

    def all_records(self) -> List[HumanReviewDecision]:
        return [record.model_copy(deep=True) for record in self._records.values()]

    def latest_review_for(
        self,
        task_id: str,
        content_version_id: str,
        evaluation_id: str,
    ) -> Optional[HumanReviewDecision]:
        """The authoritative review for one exact binding.

        "Latest" means the last record **appended** to this store for the exact
        ``(task_id, content_version_id, evaluation_id)`` triple. Selection is by
        deterministic append order (Python dict insertion order), *never* by the
        caller-controlled ``reviewed_at`` timestamp. This is what makes a later
        EDIT/REJECT supersede an earlier ACCEPT for the same binding.
        """
        latest: Optional[HumanReviewDecision] = None
        for record in self._records.values():  # append order
            if (
                record.task_id == task_id
                and record.content_version_id == content_version_id
                and record.evaluation_id == evaluation_id
            ):
                latest = record
        if latest is None:
            return None
        return latest.model_copy(deep=True)

    def __len__(self) -> int:
        return len(self._records)


# --------------------------------------------------------------------------- #
# review outcome
# --------------------------------------------------------------------------- #
@dataclass
class ReviewOutcome:
    """What a completed review yields.

    ``status`` is ``APPROVED`` only for ACCEPT. Everything else returns the
    recorded decision itself, so a caller can never mistake EDIT/REJECT for an
    approval by looking at ``status``.

    **``status == "APPROVED"`` is NOT Gate C approval and must never be used as
    an approval credential.** It is a derived, in-process convenience. Future
    P0.8-B Gate C must independently load the persisted ``HumanReviewDecision``
    from the shared store and verify it is bound to the exact
    ``task_id`` / ``content_version_id`` / ``evaluation_id`` before passing.

    ``persisted`` records whether the decision was written to a caller-supplied
    shared store (``True``) or only to an ephemeral internal one (``False``).
    Only ``persisted=True`` outcomes can correspond to a retrievable audit fact.
    """

    review_id: str
    decision: str
    status: str
    published: bool = False
    record: Optional[HumanReviewDecision] = None
    warnings: List[str] = field(default_factory=list)
    persisted: bool = False
    store: Optional[HumanReviewStore] = None


# --------------------------------------------------------------------------- #
# core
# --------------------------------------------------------------------------- #
def review_content_version(
    content_version_id: str,
    evaluation: EvaluationResult,
    version_store: ContentVersionStore,
    decision: str,
    reviewer: str,
    *,
    reason: str = "",
    unresolved_warnings: Optional[List[str]] = None,
    evidence_pack_id: Optional[str] = None,
    store: Optional[HumanReviewStore] = None,
    review_id: str = "",
    reviewed_at: Optional[datetime] = None,
) -> ReviewOutcome:
    """Record a human review decision. Fails closed on anything ambiguous.

    Persistence semantics
    ---------------------
    * ``store`` provided: the ``HumanReviewDecision`` is appended to that shared
      store. This is the **only** form that can later become authoritative input
      to Gate C, because Gate C must re-read the persisted record.
    * ``store=None`` (supported for P0.8-A backward compatibility): a private,
      **ephemeral** store is created and discarded. The returned
      :class:`ReviewOutcome` is then an *unpersisted* outcome — no shared store
      can later retrieve the record. It must never be treated as an approval
      fact by a future Gate C.

    ``ReviewOutcome.status == "APPROVED"`` is a compatibility outcome, **not** an
    approval credential. See :class:`ReviewOutcome`.
    """
    # --- A. content version must exist ------------------------------------ #
    try:
        version = version_store.get_version(content_version_id)
    except VersioningError as exc:
        raise HumanReviewError(f"content version not found: {exc}") from exc

    if evaluation is None:
        raise HumanReviewError("an evaluation is required to review a version")

    # --- B. the evaluation must be about *this* version ------------------- #
    if evaluation.content_version_id != content_version_id:
        raise HumanReviewError(
            "evaluation/content_version_id mismatch: "
            f"evaluation={evaluation.content_version_id!r} requested={content_version_id!r}"
        )

    # --- C. task must not contradict (empty compatibility field is allowed) #
    if evaluation.task_id and evaluation.task_id != version.task_id:
        raise HumanReviewError(
            "evaluation task_id conflicts with version task_id: "
            f"evaluation={evaluation.task_id!r} version={version.task_id!r}"
        )

    # --- D. eligibility --------------------------------------------------- #
    _require_eligible(evaluation)

    # --- E. decision ------------------------------------------------------ #
    normalized = str(decision or "").strip().upper()
    if normalized not in HUMAN_REVIEW_DECISIONS:
        raise HumanReviewError(
            f"invalid decision: {decision!r}; expected one of {sorted(HUMAN_REVIEW_DECISIONS)}"
        )

    # --- F. reviewer ------------------------------------------------------ #
    reviewer_clean = str(reviewer or "").strip()
    if not reviewer_clean:
        raise HumanReviewError("reviewer is required")

    # EDIT / REJECT must carry a reason; ACCEPT may omit it.
    reason_clean = str(reason or "").strip()
    if normalized in {"EDIT", "REJECT"} and not reason_clean:
        raise HumanReviewError(f"reason is required for {normalized}")

    # --- evidence binding -------------------------------------------------- #
    bound_evidence = _resolve_evidence_pack_id(version.evidence_pack_id, evidence_pack_id)

    # --- warnings (tuple: immutable, see HumanReviewDecision) -------------- #
    warnings = tuple(str(w) for w in (unresolved_warnings or []))

    record = HumanReviewDecision(
        review_id=review_id or str(uuid4()),
        task_id=version.task_id,
        content_version_id=content_version_id,
        evaluation_id=evaluation.evaluation_id,
        decision=normalized,
        reviewer=reviewer_clean,
        reason=reason_clean,
        reviewed_at=reviewed_at or datetime.now(timezone.utc),
        unresolved_warnings=warnings,
        evidence_pack_id=bound_evidence,
        # --- G. never published, in any branch ---
        published=False,
    )

    persisted = store is not None
    target_store = store if persisted else HumanReviewStore()
    stored = target_store.append(record)

    status = OUTCOME_APPROVED if normalized == "ACCEPT" else normalized
    return ReviewOutcome(
        review_id=stored.review_id,
        decision=stored.decision,
        status=status,
        published=False,
        record=stored,
        warnings=list(stored.unresolved_warnings),
        persisted=persisted,
        store=target_store,
    )


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _require_eligible(evaluation: EvaluationResult) -> None:
    status = str(evaluation.status or "").strip().upper()

    if status in INELIGIBLE_EVALUATION_STATUSES:
        raise HumanReviewError(
            f"evaluation status {status!r} is not eligible for human review"
        )

    # A Part 3 -> Part 1 routing suspicion is never reviewable.
    if getattr(evaluation, "return_to_part1", False):
        raise HumanReviewError(
            "evaluation returned to Part 1; fact/evidence path must resolve first"
        )

    if status not in ELIGIBLE_EVALUATION_STATUSES:
        raise HumanReviewError(
            f"evaluation status {status!r} has not reached the human review ceiling"
        )


def _resolve_evidence_pack_id(
    version_evidence_pack_id: Optional[str],
    explicit_evidence_pack_id: Optional[str],
) -> Optional[str]:
    """Bind the evidence pack, preferring the reviewed ContentVersion.

    A conflicting explicit value fails closed rather than guessing.
    """
    if explicit_evidence_pack_id is None or explicit_evidence_pack_id == "":
        return version_evidence_pack_id
    if version_evidence_pack_id is None:
        return explicit_evidence_pack_id
    if explicit_evidence_pack_id != version_evidence_pack_id:
        raise HumanReviewError(
            "evidence_pack_id conflict: "
            f"version={version_evidence_pack_id!r} provided={explicit_evidence_pack_id!r}"
        )
    return version_evidence_pack_id
