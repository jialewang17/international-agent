"""Deterministic, fail-closed fact safety checks for direct revisions."""
from dataclasses import dataclass, field
import hashlib
import re
from typing import Dict, List, Mapping, Optional

from api.binding import BindingError, resolve_claim_trace
from api.schemas import Claim, ContentVersion, EvidencePack
from api.versioning import ContentVersionStore, VersioningError


class FactSafetyError(ValueError):
    pass


class ClaimIdentityViolation(FactSafetyError):
    pass


def _fingerprint(text: str) -> str:
    normalized = re.sub(r"\s+", " ", (text or "").strip())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


class ClaimIdentityRegistry:
    def __init__(self):
        self._snapshots: Dict[str, str] = {}

    def register(self, claim: Claim) -> None:
        current = _fingerprint(claim.text)
        existing = self._snapshots.get(claim.claim_id)
        if existing is not None and existing != current:
            raise ClaimIdentityViolation(f"claim identity changed: {claim.claim_id}")
        self._snapshots.setdefault(claim.claim_id, current)

    def check(self, claim: Claim) -> None:
        if claim.claim_id not in self._snapshots:
            raise ClaimIdentityViolation(f"claim not registered: {claim.claim_id}")
        if self._snapshots[claim.claim_id] != _fingerprint(claim.text):
            raise ClaimIdentityViolation(f"claim identity changed: {claim.claim_id}")

    def commit(self, claims: Mapping[str, Claim]) -> None:
        """Atomically register a whole batch of claims.

        Either every claim in the batch is registered, or none is. A partially
        applied batch would leak state from a revision that later turns out to
        be unsafe, so the batch is validated before anything is written.
        """
        pending: Dict[str, str] = {}
        for claim in claims.values():
            current = _fingerprint(claim.text)
            for known, fingerprint in ((self._snapshots, "registry"), (pending, "batch")):
                existing = known.get(claim.claim_id)
                if existing is not None and existing != current:
                    raise ClaimIdentityViolation(
                        f"claim identity changed: {claim.claim_id} ({fingerprint})"
                    )
            pending.setdefault(claim.claim_id, current)
        self._snapshots.update(pending)


@dataclass
class FactSafetyResult:
    status: str
    parent_version_id: str
    child_version_id: str
    retained_claim_ids: List[str]
    removed_claim_ids: List[str]
    added_claim_ids: List[str]
    identity_violations: List[str] = field(default_factory=list)
    evidence_recheck_results: Dict[str, str] = field(default_factory=dict)
    drift_detected: bool = False
    lock_reasons: List[str] = field(default_factory=list)


def _unique_ids(ids: List[str], label: str) -> List[str]:
    seen = set()
    result = []
    for claim_id in ids:
        if claim_id in seen:
            raise FactSafetyError(f"duplicate {label} claim_id: {claim_id}")
        seen.add(claim_id)
        result.append(claim_id)
    return result


def analyze_revision(
    child_version_id: str,
    version_store: ContentVersionStore,
    claims: Mapping[str, Claim],
    evidence_pack: Optional[EvidencePack],
    registry: ClaimIdentityRegistry,
) -> FactSafetyResult:
    try:
        child = version_store.get_version(child_version_id)
        if child.parent_version_id is None:
            raise FactSafetyError("initial version is not a revision")
        parent = version_store.get_version(child.parent_version_id)
    except VersioningError as exc:
        raise FactSafetyError(str(exc)) from exc
    if parent.task_id != child.task_id:
        raise FactSafetyError("parent and child task_id differ")
    parent_ids = _unique_ids(parent.claim_ids, "parent")
    child_ids = _unique_ids(child.claim_ids, "child")
    parent_set, child_set = set(parent_ids), set(child_ids)
    retained = [x for x in child_ids if x in parent_set]
    removed = [x for x in parent_ids if x not in child_set]
    added = [x for x in child_ids if x not in parent_set]
    violations, rechecks, reasons = [], {}, []

    for claim_id in retained:
        claim = claims.get(claim_id)
        if claim is None:
            violations.append(f"missing claim: {claim_id}")
            continue
        try:
            registry.check(claim)
        except ClaimIdentityViolation as exc:
            violations.append(f"{claim_id}: {exc}")

    pending: Dict[str, Claim] = {}
    for claim_id in added:
        claim = claims.get(claim_id)
        if claim is None:
            rechecks[claim_id] = "missing_claim"
            reasons.append(f"missing claim: {claim_id}")
            continue
        if evidence_pack is None or child.evidence_pack_id != evidence_pack.evidence_pack_id:
            rechecks[claim_id] = "missing_evidence_pack"
            reasons.append(f"evidence pack unavailable: {claim_id}")
            continue
        try:
            trace = resolve_claim_trace(claim, evidence_pack)
            rechecks[claim_id] = trace["status"]
            if trace["status"] != "traceable":
                reasons.append(f"unbound claim: {claim_id}")
            else:
                pending[claim_id] = claim
        except BindingError as exc:
            rechecks[claim_id] = "binding_error"
            reasons.append(f"{claim_id}: {exc}")

    for violation in violations:
        reasons.append(violation)
    drift = bool(reasons)
    if not drift:
        registry.commit(pending)
    return FactSafetyResult(
        status="locked" if drift else "safe",
        parent_version_id=parent.content_version_id,
        child_version_id=child.content_version_id,
        retained_claim_ids=retained,
        removed_claim_ids=removed,
        added_claim_ids=added,
        identity_violations=violations,
        evidence_recheck_results=rechecks,
        drift_detected=drift,
        lock_reasons=reasons,
    )
