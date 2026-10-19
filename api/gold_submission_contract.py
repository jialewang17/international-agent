"""I2-C-001B-P2B-R2: independent annotation submission & adjudication contract.

Four identities are kept strictly separate and must never be conflated:

1. **Fact occurrence** (``focc_``, defined by ``api.atomic_gold_contract``):
   where a fact occurrence sits in the source text. Its identity is
   deliberately *annotator-agnostic*, so two annotators describing the same
   occurrence share one ``fact_occurrence_id``.
2. **Annotation submission** (``sub_``, this module): one annotator's single
   submission event. Two annotators submitting the same occurrence must be
   two distinct submissions.
3. **Annotation batch** (``bat_``, this module): one annotator's completed
   round of annotation over one specific content version. Independent
   annotation is a *batch* property, never a two-record property.
4. **Gold adjudication decision** (``adj_``, this module): one third-party
   decision about one fact group, referencing the batches and submissions it
   relied on.

This module is a structural contract only. It does not:

* compute Claim Recall or any numeric score;
* decide that a document's facts are exhaustively enumerated;
* authenticate annotator / adjudicator identity;
* align facts automatically or merge anything by textual similarity;
* bind evidence or touch any Store, API, Evaluation or Gate C.

``identity_verified`` is therefore always ``False`` and any attempt to set it
to ``True`` is rejected at construction time. A structurally valid
adjudication is *not* a complete gold set: the aggregate status stays
``COMPLETENESS_NOT_VERIFIED`` and recall stays ``NOT_EVALUATED``.

R2 hardening closed five provenance holes without changing the four-layer
architecture: a CONFIRMED decision may only use INDEPENDENT_ANNOTATED
members; a batch that already submitted a fact cannot be labelled silent; one
observation cannot be confirmed into two gold groups; batch ids must be unique
and match their submissions' round; and identity components may not contain
the NUL separator that would make the encoding ambiguous.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Sequence

from api.atomic_gold_contract import (
    POLARITIES,
    AtomicFactAnnotation,
    validate_atomic_annotations,
)
from api.source_text_index import SourceTextIndex

__all__ = [
    "ADJUDICATION_ID_PREFIX",
    "BATCH_ID_PREFIX",
    "COMPLETENESS_NOT_VERIFIED",
    "DECISION_STATUSES",
    "NOT_EVALUATED",
    "STRUCTURE_INVALID",
    "STRUCTURE_VALID",
    "SUBMISSION_ID_PREFIX",
    "SUBMISSION_REVIEW_STATUSES",
    "AdjudicationValidationResult",
    "AnnotationBatch",
    "AnnotationSubmission",
    "GoldAdjudicationDecision",
    "GoldSubmissionError",
    "SubmissionValidationResult",
    "derive_adjudication_id",
    "derive_batch_id",
    "derive_submission_id",
    "validate_adjudications",
    "validate_annotation_batches",
    "validate_annotation_submissions",
]

# --------------------------------------------------------------------------- #
# closed vocabularies and fixed constants
# --------------------------------------------------------------------------- #
NOT_EVALUATED = "NOT_EVALUATED"
STRUCTURE_VALID = "STRUCTURE_VALID"
STRUCTURE_INVALID = "STRUCTURE_INVALID"

#: Aggregate status of every result in this module. No object here may claim
#: that a document's atomic facts are exhaustively enumerated.
COMPLETENESS_NOT_VERIFIED = "COMPLETENESS_NOT_VERIFIED"

#: An independent submission may not carry the third-party ADJUDICATED state.
#: Self-declared adjudication would collapse layers 2 and 4.
SUBMISSION_REVIEW_STATUSES = frozenset(
    {"DRAFT", "INDEPENDENT_ANNOTATED", "REJECTED"}
)

#: Decision vocabulary. Deliberately excludes PASS / APPROVED / SUPPORTED.
DECISION_STATUSES = frozenset(
    {"CONFIRMED", "REJECTED", "NEEDS_MORE_REVIEW"}
)

SUBMISSION_ID_PREFIX = "sub_"
BATCH_ID_PREFIX = "bat_"
ADJUDICATION_ID_PREFIX = "adj_"

_SEPARATOR = "\x00"


class GoldSubmissionError(ValueError):
    """A structural violation of the submission / adjudication contract."""


# --------------------------------------------------------------------------- #
# small helpers
# --------------------------------------------------------------------------- #
def _require_nonblank(label: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GoldSubmissionError(f"{label} must be a nonblank str")
    return value


def _require_str(label: str, value: object) -> str:
    if not isinstance(value, str):
        raise GoldSubmissionError(f"{label} must be a str")
    return value


def _require_identity_part(label: str, value: object) -> str:
    """Validate one component that participates in an identity derivation.

    Identity payloads are joined with a NUL separator. If a component itself
    contains NUL, two different field tuples can serialise to the same byte
    string and therefore to the same identity. That is not a SHA-256
    collision, it is an ambiguous encoding, and it is rejected here.
    """
    text = _require_nonblank(label, value)
    if _SEPARATOR in text:
        raise GoldSubmissionError(
            f"{label} must not contain the NUL separator; identity encoding "
            "would become ambiguous"
        )
    return text


def _id_tuple(label: str, value: object) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)):
        raise GoldSubmissionError(
            f"{label} must be a sequence of ids, not a single string"
        )
    try:
        items = tuple(value)  # type: ignore[arg-type]
    except TypeError as exc:
        raise GoldSubmissionError(
            f"{label} must be a sequence of ids"
        ) from exc

    for item in items:
        if not isinstance(item, str) or not item.strip():
            raise GoldSubmissionError(
                f"{label} entries must be nonblank strings"
            )
    return items


def _derived(prefix: str, parts: Sequence[str]) -> str:
    payload = _SEPARATOR.join(parts)
    return prefix + sha256(payload.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- #
# identity derivations
# --------------------------------------------------------------------------- #
def derive_submission_id(
    annotator_id: str,
    batch_id: str,
    round_id: str,
    submission_nonce: str,
) -> str:
    """Derive one submission *event* identity.

    The identity binds the annotator, the batch, the round and an explicit
    per-event nonce. Consequences by construction:

    * two annotators describing the identical occurrence get different
      submission ids;
    * one annotator re-submitting after a revision can keep a distinct
      submission id by using a new nonce;
    * the source span is *not* part of the key, so the same annotator can
      submit two facts inside one span without identity collision.
    """
    for label, value in (
        ("annotator_id", annotator_id),
        ("batch_id", batch_id),
        ("round_id", round_id),
        ("submission_nonce", submission_nonce),
    ):
        _require_identity_part(label, value)

    return _derived(
        SUBMISSION_ID_PREFIX,
        [annotator_id, batch_id, round_id, submission_nonce],
    )


def derive_batch_id(
    benchmark_id: str,
    content_version_id: str,
    content_sha256: str,
    evidence_pack_id: str,
    annotator_id: str,
    round_id: str,
    batch_nonce: str,
) -> str:
    """Derive one annotation batch identity.

    The batch binds the canonical document (benchmark, version, digest,
    pack), the annotator, the round and a batch nonce. Two annotators on the
    same document therefore always produce different batch ids, and one
    annotator's repeated rounds cannot silently reuse a batch identity.
    """
    for label, value in (
        ("benchmark_id", benchmark_id),
        ("content_version_id", content_version_id),
        ("content_sha256", content_sha256),
        ("evidence_pack_id", evidence_pack_id),
        ("annotator_id", annotator_id),
        ("round_id", round_id),
        ("batch_nonce", batch_nonce),
    ):
        _require_identity_part(label, value)

    return _derived(
        BATCH_ID_PREFIX,
        [
            benchmark_id,
            content_version_id,
            content_sha256,
            evidence_pack_id,
            annotator_id,
            round_id,
            batch_nonce,
        ],
    )


def derive_adjudication_id(
    benchmark_id: str,
    content_version_id: str,
    content_sha256: str,
    evidence_pack_id: str,
    canonical_fact_group_id: str,
) -> str:
    """Derive one adjudication *scope* identity.

    The scope is one canonical fact group inside one exact document state.
    The adjudicator is deliberately not part of the key: a second adjudicator
    producing a different decision over the same scope is a conflict that
    must be surfaced, never a silently accepted second truth.
    """
    for label, value in (
        ("benchmark_id", benchmark_id),
        ("content_version_id", content_version_id),
        ("content_sha256", content_sha256),
        ("evidence_pack_id", evidence_pack_id),
        ("canonical_fact_group_id", canonical_fact_group_id),
    ):
        _require_identity_part(label, value)

    return _derived(
        ADJUDICATION_ID_PREFIX,
        [
            benchmark_id,
            content_version_id,
            content_sha256,
            evidence_pack_id,
            canonical_fact_group_id,
        ],
    )


# --------------------------------------------------------------------------- #
# layer 2: one submission event
# --------------------------------------------------------------------------- #
@dataclass(frozen=True, slots=True)
class AnnotationSubmission:
    """One annotator's single submission event.

    Construction enforces identity and consistency only. It never proves
    that ``annotator_id`` refers to a real, distinct human.
    """

    batch_id: str
    round_id: str
    annotator_id: str
    annotation: AtomicFactAnnotation
    submission_nonce: str
    submission_id: str = ""
    submitted_at: str = ""

    def __post_init__(self) -> None:
        for label in ("batch_id", "round_id", "annotator_id"):
            _require_identity_part(label, getattr(self, label))

        _require_identity_part("submission_nonce", self.submission_nonce)

        if not isinstance(self.annotation, AtomicFactAnnotation):
            raise GoldSubmissionError(
                "annotation must be an AtomicFactAnnotation"
            )

        # The P2A-R1 occurrence identity uses the same NUL join. A NUL inside
        # any of its own components would let two different occurrences
        # collapse into one id before this layer ever sees them, so such a
        # record is refused instead of being carried forward.
        for label, value in (
            ("annotation.benchmark_id", self.annotation.benchmark_id),
            (
                "annotation.content_version_id",
                self.annotation.content_version_id,
            ),
            ("annotation.content_sha256", self.annotation.content_sha256),
            ("annotation.evidence_pack_id", self.annotation.evidence_pack_id),
            ("annotation.fact_group_id", self.annotation.fact_group_id),
            (
                "annotation.fact_occurrence_id",
                self.annotation.fact_occurrence_id,
            ),
        ):
            if _SEPARATOR in value:
                raise GoldSubmissionError(
                    f"{label} contains the NUL separator; identity encoding "
                    "would become ambiguous"
                )

        if self.annotation.annotator_id != self.annotator_id:
            raise GoldSubmissionError(
                "submission annotator_id does not match annotation annotator_id"
            )

        if (
            self.annotation.review_status
            not in SUBMISSION_REVIEW_STATUSES
        ):
            raise GoldSubmissionError(
                "an independent submission cannot carry the "
                f"adjudicator-only state {self.annotation.review_status!r}"
            )

        derived = derive_submission_id(
            self.annotator_id,
            self.batch_id,
            self.round_id,
            self.submission_nonce,
        )

        if not self.submission_id:
            object.__setattr__(self, "submission_id", derived)
        elif self.submission_id != derived:
            raise GoldSubmissionError(
                "submission_id does not match its derivation; "
                "submission identity cannot be forged"
            )

    @property
    def fact_occurrence_id(self) -> str:
        return self.annotation.fact_occurrence_id


# --------------------------------------------------------------------------- #
# layer 3: one annotator's completed round over one document state
# --------------------------------------------------------------------------- #
@dataclass(frozen=True, slots=True)
class AnnotationBatch:
    """One annotator's independent annotation round over one exact version.

    A batch may legitimately contain zero facts: an annotator can conclude
    that a document contains no checkable atomic fact under the current
    protocol. ``declared_complete`` is only the annotator's own statement;
    it never establishes exhaustiveness.
    """

    benchmark_id: str
    content_version_id: str
    content_sha256: str
    evidence_pack_id: str
    annotator_id: str
    round_id: str
    batch_nonce: str
    submission_ids: tuple[str, ...] = ()
    declared_complete: bool = False
    batch_id: str = ""

    def __post_init__(self) -> None:
        for label in (
            "benchmark_id",
            "content_version_id",
            "content_sha256",
            "evidence_pack_id",
            "annotator_id",
            "round_id",
            "batch_nonce",
        ):
            _require_identity_part(label, getattr(self, label))

        ids = _id_tuple("submission_ids", self.submission_ids)
        if len(set(ids)) != len(ids):
            raise GoldSubmissionError(
                "a batch cannot reference the same submission_id twice"
            )
        object.__setattr__(self, "submission_ids", ids)

        if not isinstance(self.declared_complete, bool):
            raise GoldSubmissionError("declared_complete must be a bool")

        derived = derive_batch_id(
            self.benchmark_id,
            self.content_version_id,
            self.content_sha256,
            self.evidence_pack_id,
            self.annotator_id,
            self.round_id,
            self.batch_nonce,
        )

        if not self.batch_id:
            object.__setattr__(self, "batch_id", derived)
        elif self.batch_id != derived:
            raise GoldSubmissionError(
                "batch_id does not match its derivation; "
                "batch identity cannot be forged"
            )


# --------------------------------------------------------------------------- #
# layer 4: one third-party decision about one fact group
# --------------------------------------------------------------------------- #
@dataclass(frozen=True, slots=True)
class GoldAdjudicationDecision:
    """One adjudicator's decision over one canonical fact group.

    This is a *per-fact-group* decision, never a statement that a whole
    document's gold set is complete. Original annotator values are preserved
    in their ``AnnotationSubmission`` objects; the decision only records the
    adjudicator's explicit resolved values and rationale.
    """

    benchmark_id: str
    content_version_id: str
    content_sha256: str
    evidence_pack_id: str
    canonical_fact_group_id: str
    resolved_proposition: str
    source_batch_ids: tuple[str, ...]
    member_submission_ids: tuple[str, ...]
    adjudicator_id: str
    rationale: str
    resolved_subject_ref: str = ""
    resolved_polarity: str = ""
    omission_batch_ids: tuple[str, ...] = ()
    decision_status: str = "NEEDS_MORE_REVIEW"
    adjudicated_at: str = ""
    adjudication_id: str = ""
    identity_verified: bool = False

    def __post_init__(self) -> None:
        for label in (
            "benchmark_id",
            "content_version_id",
            "content_sha256",
            "evidence_pack_id",
            "canonical_fact_group_id",
        ):
            _require_identity_part(label, getattr(self, label))

        for label in (
            "resolved_proposition",
            "adjudicator_id",
            "rationale",
        ):
            _require_nonblank(label, getattr(self, label))

        _require_str("resolved_subject_ref", self.resolved_subject_ref)

        if self.resolved_polarity and (
            self.resolved_polarity not in POLARITIES
        ):
            raise GoldSubmissionError(
                f"invalid resolved_polarity: {self.resolved_polarity!r}"
            )

        if self.decision_status not in DECISION_STATUSES:
            raise GoldSubmissionError(
                f"invalid decision_status: {self.decision_status!r}"
            )

        batch_ids = _id_tuple("source_batch_ids", self.source_batch_ids)
        if len(set(batch_ids)) != len(batch_ids):
            raise GoldSubmissionError(
                "source_batch_ids must not contain duplicates"
            )
        object.__setattr__(self, "source_batch_ids", batch_ids)

        member_ids = _id_tuple(
            "member_submission_ids", self.member_submission_ids
        )
        if len(set(member_ids)) != len(member_ids):
            raise GoldSubmissionError(
                "member_submission_ids must not contain duplicates"
            )
        object.__setattr__(self, "member_submission_ids", member_ids)

        omission_ids = _id_tuple(
            "omission_batch_ids", self.omission_batch_ids
        )
        if len(set(omission_ids)) != len(omission_ids):
            raise GoldSubmissionError(
                "omission_batch_ids must not contain duplicates"
            )
        object.__setattr__(self, "omission_batch_ids", omission_ids)

        if self.identity_verified is not False:
            raise GoldSubmissionError(
                "identity_verified is always False: this contract does not "
                "authenticate annotator or adjudicator identity"
            )

        derived = derive_adjudication_id(
            self.benchmark_id,
            self.content_version_id,
            self.content_sha256,
            self.evidence_pack_id,
            self.canonical_fact_group_id,
        )

        if not self.adjudication_id:
            object.__setattr__(self, "adjudication_id", derived)
        elif self.adjudication_id != derived:
            raise GoldSubmissionError(
                "adjudication_id does not match its derivation; "
                "adjudication scope identity cannot be forged"
            )


# --------------------------------------------------------------------------- #
# validation results
# --------------------------------------------------------------------------- #
@dataclass(frozen=True, slots=True)
class SubmissionValidationResult:
    """Immutable structural outcome for submissions and batches.

    ``status == STRUCTURE_VALID`` means the batch/submission graph satisfies
    this contract. It never means exhaustiveness, independence or identity
    authentication.
    """

    status: str
    errors: tuple[str, ...]
    benchmark_id: str
    content_version_id: str
    content_sha256: str
    evidence_pack_id: str
    submission_count: int
    batch_count: int
    annotator_count: int
    batch_ids: tuple[str, ...]
    #: Occurrence ids referenced by submissions from more than one annotator.
    #: Informational only: this is agreement, not independent verification.
    shared_occurrence_ids: tuple[str, ...]
    zero_fact_batch_ids: tuple[str, ...]
    declared_complete_batch_ids: tuple[str, ...]
    completeness_status: str
    claim_recall_status: str
    evidence_support_status: str
    annotator_identity_verified: bool


@dataclass(frozen=True, slots=True)
class AdjudicationValidationResult:
    """Immutable structural outcome for adjudication decisions."""

    status: str
    errors: tuple[str, ...]
    benchmark_id: str
    content_version_id: str
    content_sha256: str
    evidence_pack_id: str
    decision_count: int
    #: Raw tally of decisions that *declare* CONFIRMED. This is a structural
    #: count, not a verified gold count: it carries no authority at all unless
    #: ``status == STRUCTURE_VALID``.
    confirmed_decision_count: int
    unresolved_decision_count: int
    adjudicated_fact_group_ids: tuple[str, ...]
    #: Decisions that explicitly record the batch which did not submit the
    #: fact (one-sided omission provenance).
    omission_traced_decision_ids: tuple[str, ...]
    gold_completeness_status: str
    claim_recall_status: str
    evidence_support_status: str
    identity_verified: bool


# --------------------------------------------------------------------------- #
# input coercion
# --------------------------------------------------------------------------- #
def _as_index(index: object, source_text: object) -> str:
    if not isinstance(index, SourceTextIndex):
        raise TypeError("index must be a SourceTextIndex")
    if not isinstance(source_text, str):
        raise TypeError("source_text must be str")
    return source_text


def _as_submissions(submissions: object) -> list[AnnotationSubmission]:
    if submissions is None or isinstance(submissions, (str, bytes)):
        raise TypeError(
            "submissions must be a sequence of AnnotationSubmission"
        )
    try:
        items = list(submissions)  # type: ignore[arg-type]
    except TypeError as exc:
        raise TypeError(
            "submissions must be a sequence of AnnotationSubmission"
        ) from exc

    for item in items:
        if not isinstance(item, AnnotationSubmission):
            raise TypeError(
                "submissions must be AnnotationSubmission instances"
            )
    return items


def _as_batches(batches: object) -> list[AnnotationBatch]:
    if batches is None or isinstance(batches, (str, bytes)):
        raise TypeError("batches must be a sequence of AnnotationBatch")
    try:
        items = list(batches)  # type: ignore[arg-type]
    except TypeError as exc:
        raise TypeError(
            "batches must be a sequence of AnnotationBatch"
        ) from exc

    for item in items:
        if not isinstance(item, AnnotationBatch):
            raise TypeError(
                "batches must be AnnotationBatch instances"
            )
    return items


def _as_decisions(
    decisions: object,
) -> list[GoldAdjudicationDecision]:
    if decisions is None or isinstance(decisions, (str, bytes)):
        raise TypeError(
            "decisions must be a sequence of GoldAdjudicationDecision"
        )
    try:
        items = list(decisions)  # type: ignore[arg-type]
    except TypeError as exc:
        raise TypeError(
            "decisions must be a sequence of GoldAdjudicationDecision"
        ) from exc

    for item in items:
        if not isinstance(item, GoldAdjudicationDecision):
            raise TypeError(
                "decisions must be GoldAdjudicationDecision instances"
            )
    return items


# --------------------------------------------------------------------------- #
# validation: layer 2 only
# --------------------------------------------------------------------------- #
def validate_annotation_submissions(
    index: SourceTextIndex,
    source_text: str,
    submissions: Sequence[AnnotationSubmission],
) -> SubmissionValidationResult:
    """Validate submission events alone.

    Each submission's ``AnnotationFactAnnotation`` is checked through the
    unchanged P2A-R1 validator **individually**. A flat list of two
    annotators' records must never be passed to that validator: it treats a
    shared ``fact_occurrence_id`` as a duplicate. Cross-annotator sharing is
    legitimate and is checked here instead.
    """
    _as_index(index, source_text)
    items = _as_submissions(submissions)

    # R3-01: document integrity is a precondition of the whole provenance
    # chain, not a side effect of holding at least one submission. The
    # per-submission loop below never runs for an empty submission list, so
    # the canonical baseline checks are executed once, unconditionally, and
    # their errors propagate to the batch and adjudication layers unchanged.
    baseline = validate_atomic_annotations(index, source_text, [])
    errors: list[str] = list(baseline.errors)
    benchmark_id = ""

    by_id: dict[str, AnnotationSubmission] = {}

    for submission in items:
        # Layered use of the existing contract: one submission at a time.
        result = validate_atomic_annotations(
            index, source_text, [submission.annotation]
        )
        if result.status != STRUCTURE_VALID:
            errors.extend(
                f"{submission.submission_id}: {error}"
                for error in result.errors
            )

        if not benchmark_id:
            benchmark_id = submission.annotation.benchmark_id
        elif submission.annotation.benchmark_id != benchmark_id:
            errors.append(
                "benchmark_id mismatch across submissions: "
                f"{submission.annotation.benchmark_id!r} vs {benchmark_id!r}"
            )

        previous = by_id.get(submission.submission_id)
        if previous is None:
            by_id[submission.submission_id] = submission
            continue

        errors.append(
            f"duplicate submission_id: {submission.submission_id}"
        )

        if previous.annotation != submission.annotation:
            errors.append(
                "conflicting payload under the same submission event "
                f"identity: {submission.submission_id}"
            )

    # Cross-annotator sharing of one occurrence is legitimate, not an error.
    occurrence_annotators: dict[str, set[str]] = {}
    for submission in items:
        occurrence_annotators.setdefault(
            submission.fact_occurrence_id, set()
        ).add(submission.annotator_id)

    shared = tuple(
        sorted(
            occurrence_id
            for occurrence_id, annotators in occurrence_annotators.items()
            if len(annotators) > 1
        )
    )

    return SubmissionValidationResult(
        status=STRUCTURE_VALID if not errors else STRUCTURE_INVALID,
        errors=tuple(errors),
        benchmark_id=benchmark_id,
        content_version_id=index.content_version_id,
        content_sha256=index.content_sha256,
        evidence_pack_id=index.evidence_pack_id,
        submission_count=len(items),
        batch_count=0,
        annotator_count=len(
            {submission.annotator_id for submission in items}
        ),
        batch_ids=(),
        shared_occurrence_ids=shared,
        zero_fact_batch_ids=(),
        declared_complete_batch_ids=(),
        completeness_status=COMPLETENESS_NOT_VERIFIED,
        claim_recall_status=NOT_EVALUATED,
        evidence_support_status=NOT_EVALUATED,
        annotator_identity_verified=False,
    )


# --------------------------------------------------------------------------- #
# validation: layer 2 + 3
# --------------------------------------------------------------------------- #
def validate_annotation_batches(
    index: SourceTextIndex,
    source_text: str,
    batches: Sequence[AnnotationBatch],
    submissions: Sequence[AnnotationSubmission],
) -> SubmissionValidationResult:
    """Validate batches together with their member submissions."""
    base = validate_annotation_submissions(index, source_text, submissions)
    batch_items = _as_batches(batches)
    submission_items = _as_submissions(submissions)

    errors = list(base.errors)

    submission_by_id = {
        submission.submission_id: submission
        for submission in submission_items
    }
    batch_ids = {batch.batch_id for batch in batch_items}

    benchmark_id = base.benchmark_id
    zero_fact_ids: list[str] = []
    declared_complete_ids: list[str] = []
    referenced: set[str] = set()

    # R2-04: one batch identity may appear at most once. A repeated id is an
    # identity collision even when both payloads are byte-identical, because
    # two submission lists would then silently collapse into one record.
    seen_batch_payloads: dict[str, AnnotationBatch] = {}

    for batch in batch_items:
        previous_payload = seen_batch_payloads.get(batch.batch_id)
        if previous_payload is None:
            seen_batch_payloads[batch.batch_id] = batch
        else:
            errors.append(f"duplicate batch_id: {batch.batch_id}")
            if previous_payload != batch:
                errors.append(
                    "conflicting batch payload under the same batch "
                    f"identity: {batch.batch_id}"
                )

    for batch in batch_items:
        if batch.content_version_id != index.content_version_id:
            errors.append(
                f"batch {batch.batch_id}: content_version_id "
                f"{batch.content_version_id!r} does not match index "
                f"{index.content_version_id!r}"
            )

        if batch.content_sha256 != index.content_sha256:
            errors.append(
                f"batch {batch.batch_id}: content_sha256 does not match index"
            )

        if batch.evidence_pack_id != index.evidence_pack_id:
            errors.append(
                f"batch {batch.batch_id}: evidence_pack_id "
                f"{batch.evidence_pack_id!r} does not match index "
                f"{index.evidence_pack_id!r}"
            )

        if not benchmark_id:
            benchmark_id = batch.benchmark_id
        elif batch.benchmark_id != benchmark_id:
            errors.append(
                f"batch {batch.batch_id}: benchmark_id "
                f"{batch.benchmark_id!r} does not match batch set "
                f"{benchmark_id!r}"
            )

        if not batch.submission_ids:
            zero_fact_ids.append(batch.batch_id)

        if batch.declared_complete:
            declared_complete_ids.append(batch.batch_id)

        seen_occurrences: dict[str, str] = {}

        for submission_id in batch.submission_ids:
            referenced.add(submission_id)
            submission = submission_by_id.get(submission_id)

            if submission is None:
                errors.append(
                    f"batch {batch.batch_id}: unknown member submission "
                    f"{submission_id}"
                )
                continue

            if submission.batch_id != batch.batch_id:
                errors.append(
                    f"submission {submission_id}: batch_id "
                    f"{submission.batch_id!r} does not match containing "
                    f"batch {batch.batch_id!r}"
                )

            if submission.annotator_id != batch.annotator_id:
                errors.append(
                    f"batch {batch.batch_id}: submission {submission_id} "
                    "belongs to a different annotator"
                )

            # R2-04: a submission belongs to exactly one round of one batch.
            if submission.round_id != batch.round_id:
                errors.append(
                    f"submission {submission_id}: round_id "
                    f"{submission.round_id!r} does not match batch "
                    f"{batch.batch_id!r} round_id {batch.round_id!r}"
                )

            # Re-submitting one occurrence inside the same batch is a data
            # error; an explicit re-submission needs a new round or batch.
            occurrence_id = submission.fact_occurrence_id
            if occurrence_id in seen_occurrences:
                errors.append(
                    f"batch {batch.batch_id}: duplicate fact_occurrence_id "
                    f"{occurrence_id}; a re-submission requires an explicit "
                    "new round or batch"
                )
            else:
                seen_occurrences[occurrence_id] = submission_id

    for submission in submission_items:
        if submission.batch_id not in batch_ids:
            errors.append(
                f"submission {submission.submission_id}: references unknown "
                f"batch {submission.batch_id}"
            )
        elif submission.submission_id not in referenced:
            errors.append(
                f"batch {submission.batch_id}: does not list its member "
                f"submission {submission.submission_id}"
            )

    return SubmissionValidationResult(
        status=STRUCTURE_VALID if not errors else STRUCTURE_INVALID,
        errors=tuple(errors),
        benchmark_id=benchmark_id,
        content_version_id=index.content_version_id,
        content_sha256=index.content_sha256,
        evidence_pack_id=index.evidence_pack_id,
        submission_count=len(submission_items),
        batch_count=len(batch_items),
        annotator_count=len(
            {submission.annotator_id for submission in submission_items}
            | {batch.annotator_id for batch in batch_items}
        ),
        batch_ids=tuple(sorted(batch_ids)),
        shared_occurrence_ids=base.shared_occurrence_ids,
        zero_fact_batch_ids=tuple(sorted(zero_fact_ids)),
        declared_complete_batch_ids=tuple(sorted(declared_complete_ids)),
        completeness_status=COMPLETENESS_NOT_VERIFIED,
        claim_recall_status=NOT_EVALUATED,
        evidence_support_status=NOT_EVALUATED,
        annotator_identity_verified=False,
    )


# --------------------------------------------------------------------------- #
# validation: layer 4 (+ referenced layers 2 and 3)
# --------------------------------------------------------------------------- #
def validate_adjudications(
    index: SourceTextIndex,
    source_text: str,
    batches: Sequence[AnnotationBatch],
    submissions: Sequence[AnnotationSubmission],
    decisions: Sequence[GoldAdjudicationDecision],
) -> AdjudicationValidationResult:
    """Validate adjudication decisions against their full provenance chain.

    Structural zero-tolerance rules enforced here:

    * at least two *distinct* annotators must have produced batches for the
      same document state (two batches by one person are one person);
    * every referenced batch and submission must exist and be bound to the
      same benchmark / version / digest / pack;
    * the adjudicator must differ from every involved annotator;
    * unresolved subject or polarity conflicts must be explicitly resolved;
    * a batch that reviewed the document but did not submit the fact must be
      recorded in ``omission_batch_ids``, and that batch must not itself hold
      a submission for the same fact occurrence;
    * a CONFIRMED decision may only rely on INDEPENDENT_ANNOTATED members;
    * one observation may be confirmed into at most one gold group;
    * two facts sharing one span are never merged implicitly.
    """
    _as_index(index, source_text)
    batch_items = _as_batches(batches)
    submission_items = _as_submissions(submissions)
    decision_items = _as_decisions(decisions)

    errors: list[str] = []

    # Reuse batch validation first: a decision can only be as sound as its
    # provenance graph.
    batch_result = validate_annotation_batches(
        index, source_text, batch_items, submission_items
    )
    errors.extend(batch_result.errors)

    batch_by_id = {batch.batch_id: batch for batch in batch_items}
    submission_by_id = {
        submission.submission_id: submission
        for submission in submission_items
    }

    benchmark_id = batch_result.benchmark_id

    confirmed_ids: list[str] = []
    unresolved_ids: list[str] = []
    fact_group_ids: list[str] = []
    omission_traced: list[str] = []
    seen_adjudication_ids: dict[str, GoldAdjudicationDecision] = {}

    # R2-03: one raw observation may back at most one confirmed gold group.
    confirmed_submission_groups: dict[str, str] = {}
    confirmed_occurrence_groups: dict[str, str] = {}

    # R2-02: provenance of everything each source batch actually submitted.
    submissions_by_batch: dict[str, list[AnnotationSubmission]] = {}
    for submission in submission_items:
        submissions_by_batch.setdefault(submission.batch_id, []).append(
            submission
        )

    for decision in decision_items:
        # --- document binding -------------------------------------------- #
        if decision.content_version_id != index.content_version_id:
            errors.append(
                f"decision {decision.adjudication_id}: content_version_id "
                f"{decision.content_version_id!r} does not match index "
                f"{index.content_version_id!r}"
            )

        if decision.content_sha256 != index.content_sha256:
            errors.append(
                f"decision {decision.adjudication_id}: content_sha256 does "
                "not match index; a stale decision cannot be reused"
            )

        if decision.evidence_pack_id != index.evidence_pack_id:
            errors.append(
                f"decision {decision.adjudication_id}: evidence_pack_id "
                f"{decision.evidence_pack_id!r} does not match index "
                f"{index.evidence_pack_id!r}"
            )

        if not benchmark_id:
            benchmark_id = decision.benchmark_id
        elif decision.benchmark_id != benchmark_id:
            errors.append(
                f"decision {decision.adjudication_id}: benchmark_id "
                f"{decision.benchmark_id!r} does not match batch set "
                f"{benchmark_id!r}"
            )

        previous_decision = seen_adjudication_ids.get(
            decision.adjudication_id
        )
        if previous_decision is None:
            seen_adjudication_ids[decision.adjudication_id] = decision
        else:
            errors.append(
                "duplicate adjudication scope: "
                f"{decision.adjudication_id}"
            )
            if previous_decision != decision:
                errors.append(
                    "conflicting adjudication payload under one scope: "
                    f"{decision.adjudication_id}"
                )

        # --- batch provenance -------------------------------------------- #
        source_batches: list[AnnotationBatch] = []

        if len(decision.source_batch_ids) < 2:
            errors.append(
                f"decision {decision.adjudication_id}: requires at least "
                "two source batches from independent annotators"
            )

        for batch_id in decision.source_batch_ids:
            batch = batch_by_id.get(batch_id)
            if batch is None:
                errors.append(
                    f"decision {decision.adjudication_id}: unknown source "
                    f"batch {batch_id}"
                )
                continue
            source_batches.append(batch)

        source_annotators = {batch.annotator_id for batch in source_batches}
        if len(source_annotators) < 2:
            errors.append(
                f"decision {decision.adjudication_id}: requires batches "
                "from at least two distinct annotators; repeated batches by "
                "one annotator do not establish independence"
            )

        if decision.adjudicator_id in source_annotators:
            errors.append(
                f"decision {decision.adjudication_id}: adjudicator must "
                "differ from every annotator involved"
            )

        # --- submission provenance --------------------------------------- #
        member_submissions: list[AnnotationSubmission] = []

        if not decision.member_submission_ids:
            errors.append(
                f"decision {decision.adjudication_id}: requires at least "
                "one member submission"
            )

        for submission_id in decision.member_submission_ids:
            submission = submission_by_id.get(submission_id)
            if submission is None:
                errors.append(
                    f"decision {decision.adjudication_id}: unknown member "
                    f"submission {submission_id}"
                )
                continue

            member_submissions.append(submission)

            if submission.batch_id not in decision.source_batch_ids:
                errors.append(
                    f"decision {decision.adjudication_id}: member submission "
                    f"{submission_id} does not belong to any source batch"
                )

            if decision.adjudicator_id == submission.annotator_id:
                errors.append(
                    f"decision {decision.adjudication_id}: adjudicator must "
                    "differ from every annotator involved"
                )

            # R2-01: a CONFIRMED decision may only rest on submissions that
            # actually reached independent annotation. DRAFT work may be kept
            # for NEEDS_MORE_REVIEW, but it must never confirm a fact.
            if (
                decision.decision_status == "CONFIRMED"
                and submission.annotation.review_status
                != "INDEPENDENT_ANNOTATED"
            ):
                errors.append(
                    f"decision {decision.adjudication_id}: member submission "
                    f"{submission_id} has review_status "
                    f"{submission.annotation.review_status!r}; a CONFIRMED "
                    "decision may only rely on INDEPENDENT_ANNOTATED "
                    "submissions"
                )

            # Each member must still satisfy the canonical source contract.
            member_result = validate_atomic_annotations(
                index, source_text, [submission.annotation]
            )
            if member_result.status != STRUCTURE_VALID:
                errors.extend(
                    f"decision {decision.adjudication_id}: member "
                    f"{submission_id}: {error}"
                    for error in member_result.errors
                )

        member_annotations = [
            submission.annotation for submission in member_submissions
        ]

        # --- conflict detection: subjects and polarity -------------------- #
        subjects = {
            annotation.subject_ref
            for annotation in member_annotations
            if annotation.subject_ref
        }

        if subjects and not decision.resolved_subject_ref.strip():
            errors.append(
                f"decision {decision.adjudication_id}: explicit "
                "resolved_subject_ref required; annotator subjects must not "
                "be merged implicitly"
            )

        polarities = {annotation.polarity for annotation in member_annotations}

        if len(polarities) > 1 and not decision.resolved_polarity:
            errors.append(
                f"decision {decision.adjudication_id}: unresolved polarity "
                f"conflict {sorted(polarities)}; an explicit "
                "resolved_polarity is required"
            )

        # --- one-sided omission provenance -------------------------------- #
        contributing_batches = {
            submission.batch_id for submission in member_submissions
        }
        silent_batches = [
            batch.batch_id
            for batch in source_batches
            if batch.batch_id not in contributing_batches
        ]

        member_occurrences: dict[str, str] = {}
        for submission in member_submissions:
            member_occurrences.setdefault(
                submission.fact_occurrence_id, submission.submission_id
            )

        for batch_id in silent_batches:
            if batch_id not in decision.omission_batch_ids:
                errors.append(
                    f"decision {decision.adjudication_id}: batch {batch_id} "
                    "did not submit this fact but is not recorded in "
                    "omission_batch_ids"
                )

        for batch_id in decision.omission_batch_ids:
            if batch_id not in decision.source_batch_ids:
                errors.append(
                    f"decision {decision.adjudication_id}: omission batch "
                    f"{batch_id} is not one of the source batches"
                )
                continue

            if batch_id in contributing_batches:
                errors.append(
                    f"decision {decision.adjudication_id}: batch {batch_id} "
                    "contributed a member submission but is recorded as an "
                    "omission batch"
                )
                continue

            omission_batch = batch_by_id.get(batch_id)

            # R2-02: an omission claim is a statement about what a *finished*
            # review did not find. An unfinished batch cannot support it.
            # ``declared_complete`` remains only the annotator's own word.
            if (
                omission_batch is not None
                and not omission_batch.declared_complete
            ):
                errors.append(
                    f"decision {decision.adjudication_id}: omission batch "
                    f"{batch_id} is not declared_complete; an unfinished "
                    "review cannot support a 'did not submit this fact' claim"
                )

            # R2-02: a batch cannot be called silent while it in fact holds a
            # submission for the very same occurrence. Only exact occurrence
            # identity is used here - never span overlap, similarity or any
            # semantic merge.
            for stray in submissions_by_batch.get(batch_id, ()):
                if stray.fact_occurrence_id in member_occurrences:
                    errors.append(
                        f"decision {decision.adjudication_id}: batch "
                        f"{batch_id} is recorded in omission_batch_ids but "
                        f"submission {stray.submission_id} already submits "
                        "the same fact occurrence "
                        f"{stray.fact_occurrence_id} "
                        f"(member {member_occurrences[stray.fact_occurrence_id]})"
                    )

        if decision.omission_batch_ids:
            omission_traced.append(decision.adjudication_id)

        # --- status accounting ------------------------------------------- #
        if decision.decision_status == "CONFIRMED":
            confirmed_ids.append(decision.adjudication_id)

            # R2-03: one observation may back exactly one gold group. Two
            # *different* facts sharing one span stay legal because their
            # occurrence ids differ; re-confirming the same occurrence under a
            # second canonical group is not.
            for submission in member_submissions:
                previous_group = confirmed_submission_groups.get(
                    submission.submission_id
                )
                if previous_group is None:
                    confirmed_submission_groups[
                        submission.submission_id
                    ] = decision.canonical_fact_group_id
                elif previous_group != decision.canonical_fact_group_id:
                    errors.append(
                        f"decision {decision.adjudication_id}: member "
                        f"submission {submission.submission_id} already "
                        f"supports confirmed gold group {previous_group!r} "
                        "and cannot also confirm "
                        f"{decision.canonical_fact_group_id!r}"
                    )

                previous_occurrence = confirmed_occurrence_groups.get(
                    submission.fact_occurrence_id
                )
                if previous_occurrence is None:
                    confirmed_occurrence_groups[
                        submission.fact_occurrence_id
                    ] = decision.canonical_fact_group_id
                elif previous_occurrence != decision.canonical_fact_group_id:
                    errors.append(
                        f"decision {decision.adjudication_id}: fact "
                        f"occurrence {submission.fact_occurrence_id} is "
                        "already confirmed under gold group "
                        f"{previous_occurrence!r} and cannot be confirmed "
                        f"again under {decision.canonical_fact_group_id!r}"
                    )

        elif decision.decision_status == "NEEDS_MORE_REVIEW":
            unresolved_ids.append(decision.adjudication_id)

        fact_group_ids.append(decision.canonical_fact_group_id)

    return AdjudicationValidationResult(
        status=STRUCTURE_VALID if not errors else STRUCTURE_INVALID,
        errors=tuple(errors),
        benchmark_id=benchmark_id,
        content_version_id=index.content_version_id,
        content_sha256=index.content_sha256,
        evidence_pack_id=index.evidence_pack_id,
        decision_count=len(decision_items),
        confirmed_decision_count=len(confirmed_ids),
        unresolved_decision_count=len(unresolved_ids),
        adjudicated_fact_group_ids=tuple(sorted(set(fact_group_ids))),
        omission_traced_decision_ids=tuple(sorted(omission_traced)),
        gold_completeness_status=COMPLETENESS_NOT_VERIFIED,
        claim_recall_status=NOT_EVALUATED,
        evidence_support_status=NOT_EVALUATED,
        identity_verified=False,
    )
