"""P0.8-B — Gate C verification adapter.

One security property:

> There is no path to ``APPROVED`` unless Gate C verifies a real, persisted
> ``HumanReviewDecision(decision="ACCEPT")`` from the application-level shared
> ``HumanReviewStore``, bound to the exact task, content version, and
> evaluation being approved.

This module is an adapter over the frozen P0.8-A primitives. It does **not**:

* trust ``approved=True`` from any request or legacy schema;
* trust ``ReviewOutcome.status`` / ``persisted`` / ``record`` / ``store``;
* trust client-provided decision, task, content, or post text;
* modify ``ContentVersion`` (the canonical content is only *read* to hash it);
* publish anything (``published`` is always ``False``);
* touch ``api/workflow.py`` or the revision loop.

Authorization inputs are exactly two injected stores — the shared
``HumanReviewStore`` and the ``ContentVersionStore`` that holds the canonical
content — plus the binding identifiers of the approval target.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Optional

from api.human_review import HumanReviewStore, OUTCOME_APPROVED
from api.schemas import HumanReviewDecision
from api.versioning import ContentVersionStore, VersioningError

#: Gate C outcome statuses. ``APPROVED`` is reachable only through the exact
#: exact-binding persisted-ACCEPT path; every other status is a fail-closed
#: outcome and is never an approval.
STATUS_APPROVED = OUTCOME_APPROVED
STATUS_NO_REVIEW = "NO_REVIEW"
STATUS_UNKNOWN_VERSION = "UNKNOWN_VERSION"
STATUS_SUPERSEDED = "SUPERSEDED"
STATUS_BINDING_MISMATCH = "BINDING_MISMATCH"
STATUS_NOT_PUBLISHED_SAFE = "REVIEW_NOT_PUBLISHABLE"  # corrupt record guard


def canonical_content_sha256(content: str) -> str:
    """SHA-256 of canonical content, UTF-8 encoded, hex digest."""
    return hashlib.sha256((content or "").encode("utf-8")).hexdigest()


@dataclass
class GateCResult:
    """Deterministic Gate C verification outcome.

    ``passed=True`` **and only then** ``status == "APPROVED"``. ``published`` is
    always ``False``: Gate C approves; it never publishes.
    """

    passed: bool
    status: str
    published: bool = False
    task_id: str = ""
    content_version_id: str = ""
    evaluation_id: str = ""
    review_id: str = ""
    decision: str = ""
    content_sha256: str = ""
    reviewed_at: object = None
    reviewer: str = ""
    reason: str = ""


def _failed(
    status: str,
    task_id: str = "",
    content_version_id: str = "",
    evaluation_id: str = "",
    review_id: str = "",
    decision: str = "",
    reason: str = "",
) -> GateCResult:
    return GateCResult(
        passed=False,
        status=status,
        published=False,
        task_id=task_id,
        content_version_id=content_version_id,
        evaluation_id=evaluation_id,
        review_id=review_id,
        decision=decision,
        reason=reason,
    )


def verify_gate_c(
    content_version_id: str,
    evaluation_id: str,
    *,
    version_store: ContentVersionStore,
    review_store: HumanReviewStore,
    task_id: str = "",
    review_id: str = "",
) -> GateCResult:
    """Verify Gate C for one approval target. Fails closed on everything else.

    Parameters
    ----------
    content_version_id, evaluation_id:
        The exact binding of the approval target. Both are required.
    version_store:
        The canonical ``ContentVersionStore``. Supplies the canonical task id
        and the canonical content that gets hashed. Caller text is ignored.
    review_store:
        The **application-level shared** ``HumanReviewStore``. This is the only
        trusted source of review facts.
    task_id:
        Optional caller claim. Never used *instead of* the canonical version
        task; a non-empty claim that conflicts with it fails closed.
    review_id:
        Optional caller claim used only to *locate* a record. It is still
        subject to exact-binding and supersession checks; it cannot make a
        non-authoritative record pass.

    Returns
    -------
    GateCResult
        ``passed=True`` with ``status="APPROVED"`` only when the authoritative
        persisted review for the exact binding is an ``ACCEPT``. Every other
        case returns ``passed=False`` with an explanatory status.
    """
    # --- canonical target: version must exist ----------------------------- #
    try:
        version = version_store.get_version(content_version_id)
    except VersioningError as exc:
        return _failed(
            STATUS_UNKNOWN_VERSION,
            content_version_id=content_version_id,
            evaluation_id=evaluation_id,
            reason=f"content version not found: {exc}",
        )

    canonical_task = version.task_id

    # A caller-supplied task is at most a claim; a conflict fails closed.
    if task_id and task_id != canonical_task:
        return _failed(
            STATUS_BINDING_MISMATCH,
            task_id=task_id,
            content_version_id=content_version_id,
            evaluation_id=evaluation_id,
            reason=(
                "supplied task_id conflicts with canonical version task: "
                f"{task_id!r} != {canonical_task!r}"
            ),
        )

    def _binding_matches(record: HumanReviewDecision) -> bool:
        return (
            record.task_id == canonical_task
            and record.content_version_id == content_version_id
            and record.evaluation_id == evaluation_id
        )

    # --- authoritative review: latest persisted event for the exact binding #
    if review_id:
        try:
            claimed = review_store.get(review_id)
        except Exception as exc:  # unknown review id -> fail closed
            return _failed(
                STATUS_NO_REVIEW,
                task_id=canonical_task,
                content_version_id=content_version_id,
                evaluation_id=evaluation_id,
                reason=f"review_id not found in shared store: {exc}",
            )
        if not _binding_matches(claimed):
            return _failed(
                STATUS_BINDING_MISMATCH,
                task_id=canonical_task,
                content_version_id=content_version_id,
                evaluation_id=evaluation_id,
                reason="supplied review_id is not bound to the exact approval target",
            )
        latest = review_store.latest_review_for(
            canonical_task, content_version_id, evaluation_id
        )
        if latest is not None and latest.review_id != claimed.review_id:
            return _failed(
                STATUS_SUPERSEDED,
                task_id=canonical_task,
                content_version_id=content_version_id,
                evaluation_id=evaluation_id,
                review_id=latest.review_id,
                decision=latest.decision,
                reason="supplied review has been superseded by a later review",
            )
        record: Optional[HumanReviewDecision] = claimed
    else:
        record = review_store.latest_review_for(
            canonical_task, content_version_id, evaluation_id
        )

    if record is None:
        return _failed(
            STATUS_NO_REVIEW,
            task_id=canonical_task,
            content_version_id=content_version_id,
            evaluation_id=evaluation_id,
            reason="no persisted human review for the exact binding",
        )

    # --- defensive invariant: a review record is never publishable --------- #
    if record.published is not False:
        return _failed(
            STATUS_NOT_PUBLISHED_SAFE,
            task_id=canonical_task,
            content_version_id=content_version_id,
            evaluation_id=evaluation_id,
            review_id=record.review_id,
            decision=record.decision,
            reason="persisted review record claims published=True; refusing",
        )

    # --- decision ---------------------------------------------------------- #
    if record.decision != "ACCEPT":
        return GateCResult(
            passed=False,
            status=record.decision,  # EDIT / REJECT: the latest human word wins
            published=False,
            task_id=canonical_task,
            content_version_id=content_version_id,
            evaluation_id=evaluation_id,
            review_id=record.review_id,
            decision=record.decision,
            reason=f"latest human review is {record.decision}, not ACCEPT",
        )

    # --- passed: bind the result to canonical content ---------------------- #
    return GateCResult(
        passed=True,
        status=STATUS_APPROVED,
        published=False,
        task_id=canonical_task,
        content_version_id=content_version_id,
        evaluation_id=evaluation_id,
        review_id=record.review_id,
        decision=record.decision,
        content_sha256=canonical_content_sha256(version.content),
        reviewed_at=record.reviewed_at,
        reviewer=record.reviewer,
        reason="latest persisted ACCEPT for the exact binding",
    )
