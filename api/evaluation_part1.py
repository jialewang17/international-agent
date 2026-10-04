"""Part 1 — Fact / Evidence evaluation.

This module is an **adapter only**. It measures nothing new about claims and
evidence: it calls the P0.3 binding primitives and the P0.5 fact-safety engine
and reshapes their verdicts into an :class:`~api.schemas.EvaluationResult`.

Deliberately *not* implemented here (would be a second, competing algorithm):
  * claim diff (retained / removed / added)  -> ``fact_safety.analyze_revision``
  * claim identity checking                  -> ``ClaimIdentityRegistry``
  * evidence recheck / Fact Lock             -> ``analyze_revision``
  * claim -> evidence -> source resolution   -> ``binding.resolve_claim_trace``
"""
from __future__ import annotations

from typing import List, Mapping, Optional

from api.binding import BindingError, resolve_claim_trace
from api.fact_safety import FactSafetyError, analyze_revision, ClaimIdentityRegistry
from api.schemas import (
    Claim,
    ContentVersion,
    EvaluationAuditMetadata,
    EvaluationClaimTrace,
    EvaluationResult,
    EvidencePack,
)
from api.versioning import ContentVersionStore, VersioningError

PART1 = "part1_fact_evidence"

STATUS_PASS = "PASS"
STATUS_BLOCKED = "BLOCKED"

TRACE_TRACEABLE = "traceable"
TRACE_UNBOUND = "unbound"
TRACE_BINDING_ERROR = "binding_error"
TRACE_MISSING_CLAIM = "missing_claim"
TRACE_MISSING_EVIDENCE_PACK = "missing_evidence_pack"


def evaluate_part1(
    content_version_id: str,
    version_store: ContentVersionStore,
    claims: Mapping[str, Claim],
    evidence_pack: Optional[EvidencePack],
    registry: Optional[ClaimIdentityRegistry] = None,
    *,
    evaluation_id: str = "",
    task_id: str = "",
) -> EvaluationResult:
    """Evaluate the fact/evidence posture of one ContentVersion.

    Initial versions are checked claim-by-claim through the binding primitives;
    revisions delegate to the P0.5 revision analyzer. Both paths fail closed.
    """
    if registry is None:
        registry = ClaimIdentityRegistry()

    try:
        version = version_store.get_version(content_version_id)
    except VersioningError as exc:
        return _blocked(
            content_version_id, evaluation_id, task_id,
            reason=f"content version not found: {exc}",
            claim_scores={},
        )

    if version.parent_version_id is None:
        traces, reasons = _evaluate_initial_version(version, claims, evidence_pack)
    else:
        return _evaluate_revision(
            version, version_store, claims, evidence_pack, registry,
            evaluation_id=evaluation_id, task_id=task_id,
        )

    status = STATUS_BLOCKED if reasons else STATUS_PASS
    return EvaluationResult(
        evaluation_id=evaluation_id,
        content_version_id=version.content_version_id,
        part=PART1,
        status=status,
        issues=reasons,
        claim_traces=traces,
        task_id=task_id or version.task_id,
        audit=EvaluationAuditMetadata(
            evaluator="part1_fact_evidence_aggregator",
            evaluator_type="deterministic_aggregation",
            part1_status=status,
        ),
    )


# --------------------------------------------------------------------------- #
# initial version: direct claim -> evidence -> source trace per claim
# --------------------------------------------------------------------------- #
def _evaluate_initial_version(
    version: ContentVersion,
    claims: Mapping[str, Claim],
    evidence_pack: Optional[EvidencePack],
) -> tuple[List[EvaluationClaimTrace], List[str]]:
    traces: List[EvaluationClaimTrace] = []
    reasons: List[str] = []

    if evidence_pack is None:
        return traces, ["missing evidence pack"]
    if version.evidence_pack_id != evidence_pack.evidence_pack_id:
        return traces, [
            "evidence pack mismatch: "
            f"version={version.evidence_pack_id!r} provided={evidence_pack.evidence_pack_id!r}"
        ]

    for claim_id in version.claim_ids:
        claim = claims.get(claim_id)
        if claim is None:
            traces.append(EvaluationClaimTrace(claim_id=claim_id, status=TRACE_MISSING_CLAIM))
            reasons.append(f"missing claim: {claim_id}")
            continue
        try:
            trace = resolve_claim_trace(claim, evidence_pack)
        except BindingError as exc:
            traces.append(
                EvaluationClaimTrace(
                    claim_id=claim_id, status=TRACE_BINDING_ERROR, detail=str(exc)
                )
            )
            reasons.append(f"{claim_id}: {exc}")
            continue
        traces.append(EvaluationClaimTrace(claim_id=claim_id, status=trace["status"]))
        if trace["status"] != TRACE_TRACEABLE:
            reasons.append(f"unbound claim: {claim_id}")

    return traces, reasons


# --------------------------------------------------------------------------- #
# revision: delegate entirely to the P0.5 fact-safety engine
# --------------------------------------------------------------------------- #
def _evaluate_revision(
    version: ContentVersion,
    version_store: ContentVersionStore,
    claims: Mapping[str, Claim],
    evidence_pack: Optional[EvidencePack],
    registry: ClaimIdentityRegistry,
    *,
    evaluation_id: str,
    task_id: str,
) -> EvaluationResult:
    try:
        safety = analyze_revision(
            version.content_version_id, version_store, claims, evidence_pack, registry
        )
    except FactSafetyError as exc:
        return _blocked(
            version.content_version_id, evaluation_id, task_id or version.task_id,
            reason=f"fact safety error: {exc}", claim_scores={},
        )

    reasons = list(safety.lock_reasons)
    status = STATUS_PASS if safety.status == "safe" else STATUS_BLOCKED
    traces = [
        EvaluationClaimTrace(claim_id=claim_id, status=verdict)
        for claim_id, verdict in safety.evidence_recheck_results.items()
    ]
    return EvaluationResult(
        evaluation_id=evaluation_id,
        content_version_id=version.content_version_id,
        part=PART1,
        status=status,
        issues=reasons,
        claim_traces=traces,
        task_id=task_id or version.task_id,
        return_to_part1=status == STATUS_BLOCKED,
        audit=EvaluationAuditMetadata(
            evaluator="part1_fact_evidence_aggregator",
            evaluator_type="deterministic_aggregation",
            part1_status=status,
        ),
    )


def _blocked(
    content_version_id: str,
    evaluation_id: str,
    task_id: str,
    *,
    reason: str,
    claim_scores: dict,
) -> EvaluationResult:
    return EvaluationResult(
        evaluation_id=evaluation_id,
        content_version_id=content_version_id,
        part=PART1,
        status=STATUS_BLOCKED,
        issues=[reason],
        task_id=task_id,
        return_to_part1=True,
        audit=EvaluationAuditMetadata(
            evaluator="part1_fact_evidence_aggregator",
            evaluator_type="deterministic_aggregation",
            part1_status=STATUS_BLOCKED,
        ),
    )
