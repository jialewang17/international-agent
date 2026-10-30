"""I2-C-002: minimal Claim–Evidence binding loop.

Additive module only. It never mutates existing Part 1 / Part 3 code; the
gate is a wrapper around the unchanged ``evaluate_part1``.

Safety model (the reason this module exists):

* An LLM verdict about evidence support is a *claim about a claim*. It is
  never a verified fact. Every result therefore carries the constant
  ``fact_verification_status = "NOT_VERIFIED"`` and ``verified = False``.
* Fail closed: an unknown Evidence ID, an unmapped factual claim, a stale
  content digest, or an identity mismatch can never produce PASS.
* Conflicts are *retained*: a CONTRADICTED binding keeps the conflicting
  evidence IDs and forces REVIEW. Nothing in this module ever picks the
  "favourable" source.
* Revisions invalidate bindings: bindings are keyed to
  ``(content_version_id, content_sha256)``; a new content digest can never
  reuse them.
"""

from __future__ import annotations

from typing import Iterable, List, Mapping, Optional
from threading import RLock

from pydantic import BaseModel, Field

from api.evaluation import evaluate_content_version
from api.evaluation_part1 import evaluate_part1
from api.evidence_adapter import canonical_digest
from api.schemas import (
    Claim,
    ContentVersion,
    EvidencePack,
    EvaluationResult,
)
from api.versioning import ContentVersionStore
from hashlib import sha256

__all__ = [
    "EvidenceBindingError",
    "EvidenceBinding",
    "EvidenceBindingStore",
    "derive_binding_id",
    "validate_evidence_bindings",
    "BindingGateResult",
    "stale_binding_ids",
    "evaluate_with_binding_gate",
    "PART_BINDING",
    "STATUS_PASS",
    "STATUS_REVIEW",
    "STATUS_BLOCK",
    "SUPPORT_DIRECT",
    "SUPPORT_INFERRED",
    "SUPPORT_CONTRADICTED",
    "SUPPORT_UNSUPPORTED",
    "SUPPORT_TYPES",
    "FACT_VERIFICATION_STATUS",
]


class EvidenceBindingError(ValueError):
    """Invalid binding payload or store request."""


PART_BINDING = "part1_evidence_binding"

#: Gate outcomes. REVIEW is deliberately *not* PASS: inferred, contradicted or
#: unsupported claims route to human review instead of Part 3.
STATUS_PASS = "PASS"
STATUS_REVIEW = "REVIEW"
STATUS_BLOCK = "BLOCK"

#: Support typology required by the task.
SUPPORT_DIRECT = "DIRECT_SUPPORT"
SUPPORT_INFERRED = "INDIRECT_INFERENCE"
SUPPORT_CONTRADICTED = "CONTRADICTED"
SUPPORT_UNSUPPORTED = "UNSUPPORTED"

SUPPORT_TYPES = frozenset(
    {SUPPORT_DIRECT, SUPPORT_INFERRED, SUPPORT_CONTRADICTED, SUPPORT_UNSUPPORTED}
)

#: Support types that must reference at least one real Evidence ID.
_SUPPORT_TYPES_REQUIRING_EVIDENCE = frozenset(
    {SUPPORT_DIRECT, SUPPORT_INFERRED, SUPPORT_CONTRADICTED}
)

#: Ceiling constant: an LLM (or human) support verdict is never a verified fact.
FACT_VERIFICATION_STATUS = "NOT_VERIFIED"

JUDGED_BY_LLM = "llm"
JUDGED_BY_HUMAN = "human"
JUDGED_BY_RULE = "rule"
_JUDGED_BY = frozenset({JUDGED_BY_LLM, JUDGED_BY_HUMAN, JUDGED_BY_RULE})


def _content_digest(content: str) -> str:
    if not isinstance(content, str):
        raise EvidenceBindingError("content must be str")
    return sha256(content.encode("utf-8")).hexdigest()


def derive_binding_id(
    content_version_id: str,
    claim_id: str,
    content_sha256: str,
) -> str:
    """Deterministic binding identity: one claim, one document state."""
    return "bnd_" + canonical_digest(
        content_version_id, claim_id, content_sha256
    )


# --------------------------------------------------------------------------- #
# binding model
# --------------------------------------------------------------------------- #
class EvidenceBinding(BaseModel):
    """One judge verdict binding one Claim to Evidence IDs.

    ``evidence_ids`` is a list, so many-to-many arises naturally: one claim may
    cite several evidence items, and several claims may cite the same item.
    ``excerpts`` (optional) must align 1:1 with ``evidence_ids`` and each entry
    must be an exact substring of the corresponding evidence statement.
    """

    binding_id: str
    content_version_id: str
    content_sha256: str
    evidence_pack_id: str
    claim_id: str
    evidence_ids: List[str] = Field(default_factory=list)
    excerpts: List[str] = Field(default_factory=list)
    support_type: str
    uncertainty_note: str = ""
    judged_by: str = JUDGED_BY_RULE


# --------------------------------------------------------------------------- #
# store
# --------------------------------------------------------------------------- #
class EvidenceBindingStore:
    """Deep-copy, fail-closed in-memory bindings keyed (version, claim).

    Old versions keep their bindings (audit trail); a new version simply has
    none until fresh bindings are stored, so stale reuse is structurally
    impossible on top of the digest check inside the gate.
    """

    def __init__(self) -> None:
        self._bindings: dict[tuple[str, str], EvidenceBinding] = {}
        self._lock = RLock()

    @staticmethod
    def _check_key_parts(content_version_id: str, claim_id: str) -> None:
        if not isinstance(content_version_id, str) or not content_version_id.strip():
            raise EvidenceBindingError(
                "content_version_id must be a non-empty str"
            )
        if not isinstance(claim_id, str) or not claim_id.strip():
            raise EvidenceBindingError("claim_id must be a non-empty str")

    @classmethod
    def _check_binding(cls, binding: EvidenceBinding) -> None:
        if not isinstance(binding, EvidenceBinding):
            raise EvidenceBindingError("binding must be EvidenceBinding")
        cls._check_key_parts(binding.content_version_id, binding.claim_id)
        if not binding.binding_id.strip():
            raise EvidenceBindingError("binding_id must be non-empty")
        if not binding.content_sha256.strip():
            raise EvidenceBindingError("content_sha256 must be non-empty")
        if not isinstance(binding.evidence_pack_id, str) or not binding.evidence_pack_id.strip():
            raise EvidenceBindingError("evidence_pack_id must be non-empty")
        if binding.support_type not in SUPPORT_TYPES:
            raise EvidenceBindingError(
                f"unknown support_type: {binding.support_type!r}"
            )
        if binding.judged_by not in _JUDGED_BY:
            raise EvidenceBindingError(f"unknown judged_by: {binding.judged_by!r}")
        if any(not isinstance(e, str) or not e.strip() for e in binding.evidence_ids):
            raise EvidenceBindingError("evidence_ids must be non-empty strings")
        if len(set(binding.evidence_ids)) != len(binding.evidence_ids):
            raise EvidenceBindingError("duplicate evidence_ids in binding")

    @staticmethod
    def _collision(key: tuple[str, str]) -> EvidenceBindingError:
        return EvidenceBindingError(
            f"binding collision: content_version_id={key[0]}, claim_id={key[1]}"
        )

    def put(self, binding: EvidenceBinding) -> EvidenceBinding:
        return self.put_many([binding])[0]

    def put_many(
        self, bindings: Iterable[EvidenceBinding]
    ) -> list[EvidenceBinding]:
        if bindings is None or isinstance(bindings, (str, bytes)):
            raise EvidenceBindingError("bindings must be an iterable")

        try:
            requested = list(bindings)
        except TypeError as exc:
            raise EvidenceBindingError(
                "bindings must be an iterable of EvidenceBinding"
            ) from exc

        staged: dict[tuple[str, str], EvidenceBinding] = {}
        ordered_keys: list[tuple[str, str]] = []

        for binding in requested:
            self._check_binding(binding)
            key = (binding.content_version_id, binding.claim_id)
            snapshot = binding.model_copy(deep=True)

            previous = staged.get(key)
            if previous is not None and previous != snapshot:
                raise self._collision(key)
            if previous is None:
                staged[key] = snapshot
            ordered_keys.append(key)

        with self._lock:
            for key, snapshot in staged.items():
                stored = self._bindings.get(key)
                if stored is not None and stored != snapshot:
                    raise self._collision(key)
            for key, snapshot in staged.items():
                self._bindings.setdefault(key, snapshot)

            return [self._bindings[k].model_copy(deep=True) for k in ordered_keys]

    def get(self, content_version_id: str, claim_id: str) -> Optional[EvidenceBinding]:
        self._check_key_parts(content_version_id, claim_id)
        with self._lock:
            stored = self._bindings.get((content_version_id, claim_id))
            return stored.model_copy(deep=True) if stored is not None else None

    def for_version(self, content_version_id: str) -> list[EvidenceBinding]:
        if not isinstance(content_version_id, str) or not content_version_id.strip():
            raise EvidenceBindingError("content_version_id must be non-empty")
        with self._lock:
            keys = sorted(k for k in self._bindings if k[0] == content_version_id)
            return [self._bindings[k].model_copy(deep=True) for k in keys]

    def drop_version(self, content_version_id: str) -> int:
        """Remove every binding of one version; returns the removed count."""
        if not isinstance(content_version_id, str) or not content_version_id.strip():
            raise EvidenceBindingError("content_version_id must be non-empty")
        with self._lock:
            keys = [k for k in self._bindings if k[0] == content_version_id]
            for key in keys:
                del self._bindings[key]
            return len(keys)

    def __len__(self) -> int:
        with self._lock:
            return len(self._bindings)


# --------------------------------------------------------------------------- #
# gate
# --------------------------------------------------------------------------- #
class BindingGateResult(BaseModel):
    """Outcome of :func:`validate_evidence_bindings`."""

    status: str
    content_version_id: str
    content_sha256: str
    evidence_pack_id: str
    blocking_issues: List[str] = Field(default_factory=list)
    review_issues: List[str] = Field(default_factory=list)
    unmapped_claim_ids: List[str] = Field(default_factory=list)
    unknown_evidence_ids: List[str] = Field(default_factory=list)
    inferred_claim_ids: List[str] = Field(default_factory=list)
    conflicted_claim_ids: List[str] = Field(default_factory=list)
    unsupported_claim_ids: List[str] = Field(default_factory=list)
    binding_count: int = 0
    #: Constant ceiling: a support verdict is never a verified fact.
    fact_verification_status: str = FACT_VERIFICATION_STATUS
    verified: bool = False

    def as_evaluation_result(
        self, evaluation_id: str, task_id: str = ""
    ) -> EvaluationResult:
        status = {STATUS_PASS: "PASS", STATUS_REVIEW: "REVIEW", STATUS_BLOCK: "BLOCKED"}[
            self.status
        ]
        return EvaluationResult(
            evaluation_id=evaluation_id,
            content_version_id=self.content_version_id,
            part=PART_BINDING,
            status=status,
            issues=list(self.blocking_issues) + list(self.review_issues),
            task_id=task_id,
            return_to_part1=self.status == STATUS_BLOCK,
            human_review="PENDING" if self.status == STATUS_REVIEW else "",
        )


def validate_evidence_bindings(
    content: str,
    version: ContentVersion,
    pack: Optional[EvidencePack],
    claims: Mapping[str, Claim],
    bindings: Iterable[EvidenceBinding],
) -> BindingGateResult:
    """Validate the full binding graph for one document state.

    Deterministic, pure, offline. Collects all issues (never fail-fast) so one
    run reports every problem at once.
    """
    if not isinstance(version, ContentVersion):
        raise EvidenceBindingError("version must be ContentVersion")
    digest = _content_digest(content)
    if content != version.content:
        raise EvidenceBindingError(
            "content does not match version.content; refusing to validate"
        )

    blocking: List[str] = []
    review: List[str] = []
    unmapped: List[str] = []
    unknown_ids: List[str] = []
    inferred: List[str] = []
    conflicted: List[str] = []
    unsupported: List[str] = []

    if pack is None:
        blocking.append("missing evidence pack")
        pack_items: dict[str, str] = {}
    else:
        if version.evidence_pack_id != pack.evidence_pack_id:
            blocking.append(
                "evidence pack mismatch: "
                f"version={version.evidence_pack_id!r} "
                f"provided={pack.evidence_pack_id!r}"
            )
        pack_items = {item.evidence_id: item.statement for item in pack.items}

    if bindings is None or isinstance(bindings, (str, bytes)):
        raise EvidenceBindingError("bindings must be an iterable of EvidenceBinding")
    try:
        binding_items = list(bindings)
    except TypeError as exc:
        raise EvidenceBindingError(
            "bindings must be an iterable of EvidenceBinding"
        ) from exc

    by_claim: dict[str, list[EvidenceBinding]] = {}
    for binding in binding_items:
        if not isinstance(binding, EvidenceBinding):
            raise EvidenceBindingError("bindings must be EvidenceBinding instances")
        by_claim.setdefault(binding.claim_id, []).append(binding)

    for claim_id in version.claim_ids:
        claim = claims.get(claim_id)
        if claim is None:
            blocking.append(f"missing claim: {claim_id}")
            continue

        found = by_claim.get(claim_id, [])
        if not found:
            unmapped.append(claim_id)
            blocking.append(f"unmapped factual claim: {claim_id}")
            continue
        if len(found) > 1:
            blocking.append(
                f"duplicate binding for claim: {claim_id} "
                f"({len(found)} bindings)"
            )
            continue

        binding = found[0]

        # --- identity binding -------------------------------------------- #
        if binding.content_version_id != version.content_version_id:
            blocking.append(
                f"binding {binding.binding_id}: content_version_id mismatch"
            )
        if binding.evidence_pack_id != version.evidence_pack_id:
            blocking.append(f"binding {binding.binding_id}: evidence_pack_id mismatch")
        if binding.content_sha256 != digest:
            blocking.append(
                f"binding {binding.binding_id}: stale binding (content_sha256 "
                "does not match current content)"
            )

        # --- support typology --------------------------------------------- #
        if binding.support_type not in SUPPORT_TYPES:
            blocking.append(
                f"binding {binding.binding_id}: unknown support_type "
                f"{binding.support_type!r}"
            )
            continue

        # --- evidence existence -------------------------------------------- #
        ids = list(dict.fromkeys(binding.evidence_ids))
        if not ids:
            if binding.support_type in _SUPPORT_TYPES_REQUIRING_EVIDENCE:
                blocking.append(
                    f"binding {binding.binding_id}: support_type "
                    f"{binding.support_type} requires at least one evidence id"
                )
        else:
            missing = [e for e in ids if e not in pack_items]
            if missing:
                unknown_ids.extend(missing)
                blocking.append(
                    f"binding {binding.binding_id}: unknown evidence id(s): "
                    f"{', '.join(missing)}"
                )

        # --- excerpts must be real quotes of the referenced evidence ------- #
        if binding.excerpts:
            if len(binding.excerpts) != len(binding.evidence_ids):
                blocking.append(
                    f"binding {binding.binding_id}: excerpts must align 1:1 "
                    "with evidence_ids"
                )
            else:
                for evidence_id, excerpt in zip(ids, binding.excerpts):
                    statement = pack_items.get(evidence_id)
                    if statement is not None and excerpt not in statement:
                        blocking.append(
                            f"binding {binding.binding_id}: excerpt for "
                            f"{evidence_id} is not a substring of the evidence "
                            "statement"
                        )

        # --- review routing (conflicts are kept, never auto-resolved) ------ #
        if binding.support_type == SUPPORT_INFERRED:
            inferred.append(claim_id)
            review.append(
                f"claim {claim_id}: indirect inference, not direct support"
            )
        elif binding.support_type == SUPPORT_CONTRADICTED:
            conflicted.append(claim_id)
            review.append(
                f"claim {claim_id}: evidence conflict retained "
                f"(evidence_ids={ids}); no source was auto-selected"
            )
        elif binding.support_type == SUPPORT_UNSUPPORTED:
            unsupported.append(claim_id)
            review.append(
                f"claim {claim_id}: insufficient evidence support; request "
                "more material, weaken the wording, or route to human review"
            )

    # Bindings that point at claims absent from the version are orphans.
    version_claims = set(version.claim_ids)
    for claim_id in sorted(by_claim):
        if claim_id not in version_claims:
            blocking.append(
                f"binding references unknown claim: {claim_id} "
                "(not part of this content version)"
            )

    status = STATUS_BLOCK if blocking else (
        STATUS_REVIEW if review else STATUS_PASS
    )

    return BindingGateResult(
        status=status,
        content_version_id=version.content_version_id,
        content_sha256=digest,
        evidence_pack_id=version.evidence_pack_id or "",
        blocking_issues=blocking,
        review_issues=review,
        unmapped_claim_ids=unmapped,
        unknown_evidence_ids=sorted(set(unknown_ids)),
        inferred_claim_ids=inferred,
        conflicted_claim_ids=conflicted,
        unsupported_claim_ids=unsupported,
        binding_count=len(binding_items),
    )


def stale_binding_ids(
    version: ContentVersion,
    claims: Mapping[str, Claim],
    bindings: Iterable[EvidenceBinding],
) -> List[str]:
    """Bindings that a revision must not reuse.

    A binding is stale when its content digest differs from the version's
    content, its claim no longer exists, or the claim text changed (a new text
    yields a new claim_id, but the check makes the rule explicit).
    """
    digest = _content_digest(version.content)
    stale: List[str] = []
    for binding in bindings:
        if not isinstance(binding, EvidenceBinding):
            raise EvidenceBindingError("bindings must be EvidenceBinding instances")
        if binding.content_sha256 != digest:
            stale.append(binding.binding_id)
            continue
        claim = claims.get(binding.claim_id)
        if claim is None or claim.claim_id not in version.claim_ids:
            stale.append(binding.binding_id)
    return sorted(set(stale))


# --------------------------------------------------------------------------- #
# orchestrator: Part 1 -> binding gate -> Part 3
# --------------------------------------------------------------------------- #
def evaluate_with_binding_gate(
    content_version_id: str,
    version_store: ContentVersionStore,
    claims: Mapping[str, Claim],
    evidence_pack: Optional[EvidencePack],
    bindings: Iterable[EvidenceBinding],
    *,
    judge=None,
    rubric=None,
    task_context: Optional[dict] = None,
    evaluation_id: str = "",
) -> tuple[Optional[EvaluationResult], Optional[BindingGateResult], EvaluationResult]:
    """Run the unchanged Part 1, then the binding gate, then (only on PASS) Part 3.

    Returns ``(part1_result, gate_result, final_result)``. When Part 1 already
    blocks, ``gate_result`` is ``None`` and the binding graph is not consulted:
    the existing Part 1 conditions remain authoritative.
    """
    part1 = evaluate_part1(
        content_version_id,
        version_store,
        claims,
        evidence_pack,
        evaluation_id=f"{evaluation_id}-p1" if evaluation_id else "",
    )

    if part1.status != "PASS":
        return part1, None, part1

    version = version_store.get_version(content_version_id)
    gate = validate_evidence_bindings(
        version.content, version, evidence_pack, claims, bindings
    )

    if gate.status != STATUS_PASS:
        final = gate.as_evaluation_result(
            evaluation_id=f"{evaluation_id}-bnd" if evaluation_id else "",
            task_id=part1.task_id,
        )
        return part1, gate, final

    final = evaluate_content_version(
        content_version_id,
        version_store,
        claims,
        evidence_pack,
        judge=judge,
        rubric=rubric,
        task_context=task_context,
        evaluation_id=evaluation_id,
    )
    return part1, gate, final
