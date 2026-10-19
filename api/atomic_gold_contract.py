"""I2-C-001B-P2A-R1: offline atomic fact annotation contract.

This module defines a *structural* contract for human atomic-fact gold
annotations. It validates data shape and identity only.

It never proves that:
* annotations were produced by real, independent human annotators;
* an annotation set enumerates every atomic fact (atomic completeness);
* a fact is covered by a sentence Claim candidate (lexical overlap is
  recorded informationally, never promoted to enumeration evidence);
* evidence supports a fact;
* any Claim Recall value is real.

Without independently adjudicated human gold, the recall posture of the
system remains ``NOT_EVALUATED``. This module provides no scoring at all.

Three capabilities stay strictly separated and must never be substituted
for one another:

1. Sentence Candidate Coverage -- whether a sentence-level Claim candidate
   covers the text region of a fact (recorded informationally only).
2. Atomic Fact Enumeration -- whether independent atomic facts were
   enumerated one by one (human work; not verifiable here).
3. Evidence Support -- whether evidence actually supports a fact
   (never computed here).
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Optional, Sequence

from api.source_text_index import SourceTextIndex

__all__ = [
    "ATOMIC_ENUMERATION_NOT_VERIFIED",
    "FACT_KINDS",
    "LANGUAGES",
    "NOT_EVALUATED",
    "POLARITIES",
    "REVIEW_STATUSES",
    "STRUCTURE_INVALID",
    "STRUCTURE_VALID",
    "AtomicAnnotationError",
    "AtomicAnnotationValidationResult",
    "AtomicFactAnnotation",
    "derive_fact_occurrence_id",
    "validate_atomic_annotations",
]

# --------------------------------------------------------------------------- #
# closed vocabularies
# --------------------------------------------------------------------------- #
NOT_EVALUATED = "NOT_EVALUATED"
STRUCTURE_VALID = "STRUCTURE_VALID"
STRUCTURE_INVALID = "STRUCTURE_INVALID"

#: Overlapping a sentence Claim candidate is recorded, never treated as proof
#: that atomic facts were independently enumerated.
ATOMIC_ENUMERATION_NOT_VERIFIED = "ATOMIC_ENUMERATION_NOT_VERIFIED"

REVIEW_STATUSES = frozenset(
    {"DRAFT", "INDEPENDENT_ANNOTATED", "ADJUDICATED", "REJECTED"}
)
POLARITIES = frozenset({"POSITIVE", "NEGATIVE"})
LANGUAGES = frozenset({"zh", "en", "mixed"})
FACT_KINDS = frozenset(
    {
        "NUMERIC",
        "DATE",
        "NEGATION",
        "COMPARISON",
        "SUPERLATIVE",
        "CAUSAL",
        "ATTRIBUTION",
        "IDENTITY_RELATION",
        "MODALITY",
        "OTHER",
    }
)

OCCURRENCE_ID_PREFIX = "focc_"
_SEPARATOR = "\x00"


class AtomicAnnotationError(ValueError):
    """A structural violation of the atomic annotation contract."""


def _require_nonblank(label: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AtomicAnnotationError(f"{label} must be a nonblank str")
    return value


def _require_int(label: str, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise AtomicAnnotationError(f"{label} must be an int")
    return value


# --------------------------------------------------------------------------- #
# stable occurrence identity
# --------------------------------------------------------------------------- #
def derive_fact_occurrence_id(
    benchmark_id: str,
    content_version_id: str,
    content_sha256: str,
    evidence_pack_id: str,
    fact_group_id: str,
    start: int,
    end: int,
) -> str:
    """Deterministically derive the occurrence identity.

    The identity binds benchmark, version, content fingerprint, evidence
    pack, fact group and the exact span. Consequences (by construction):

    * two different fact groups with the *same* source span get different
      occurrence IDs;
    * repeated occurrences of one fact group keep one record per position;
    * the same sentence text in a different version/digest/pack never
      shares an occurrence identity.
    """
    for label, value in (
        ("benchmark_id", benchmark_id),
        ("content_version_id", content_version_id),
        ("content_sha256", content_sha256),
        ("evidence_pack_id", evidence_pack_id),
        ("fact_group_id", fact_group_id),
    ):
        _require_nonblank(label, value)

    _require_int("start", start)
    _require_int("end", end)

    payload = _SEPARATOR.join(
        [
            benchmark_id,
            content_version_id,
            content_sha256,
            evidence_pack_id,
            fact_group_id,
            str(start),
            str(end),
        ]
    )
    return OCCURRENCE_ID_PREFIX + sha256(
        payload.encode("utf-8")
    ).hexdigest()


# --------------------------------------------------------------------------- #
# annotation model
# --------------------------------------------------------------------------- #
@dataclass(frozen=True, slots=True)
class AtomicFactAnnotation:
    """One immutable, human-supplied atomic fact occurrence record.

    Construction enforces structural rules only. It does not authenticate
    ``annotator_id`` / ``adjudicator_id`` and does not verify that the
    annotation was produced by a real independent human.
    """

    benchmark_id: str
    content_version_id: str
    content_sha256: str
    evidence_pack_id: str
    fact_group_id: str
    start: int
    end: int
    source_quote: str
    proposition: str
    fact_occurrence_id: str = ""
    subject_ref: str = ""
    polarity: str = "POSITIVE"
    fact_kind: str = "OTHER"
    language: str = "zh"
    requires_context: bool = False
    context_start: Optional[int] = None
    context_end: Optional[int] = None
    review_status: str = "DRAFT"
    annotator_id: str = ""
    adjudicator_id: str = ""
    note: str = ""

    def __post_init__(self) -> None:
        for label in (
            "benchmark_id",
            "content_version_id",
            "content_sha256",
            "evidence_pack_id",
            "fact_group_id",
        ):
            _require_nonblank(label, getattr(self, label))

        _require_int("start", self.start)
        _require_int("end", self.end)

        if self.start < 0 or self.end <= self.start:
            raise AtomicAnnotationError(
                "span must satisfy 0 <= start < end"
            )

        if not isinstance(self.source_quote, str) or not self.source_quote:
            raise AtomicAnnotationError(
                "source_quote must be a nonempty str"
            )

        _require_nonblank("proposition", self.proposition)

        if self.polarity not in POLARITIES:
            raise AtomicAnnotationError(
                f"invalid polarity: {self.polarity!r}"
            )

        if self.fact_kind not in FACT_KINDS:
            raise AtomicAnnotationError(
                f"invalid fact_kind: {self.fact_kind!r}"
            )

        if self.language not in LANGUAGES:
            raise AtomicAnnotationError(
                f"invalid language: {self.language!r}"
            )

        if self.review_status not in REVIEW_STATUSES:
            raise AtomicAnnotationError(
                f"invalid review_status: {self.review_status!r}"
            )

        _require_nonblank("annotator_id", self.annotator_id)

        if self.review_status == "ADJUDICATED":
            _require_nonblank("adjudicator_id", self.adjudicator_id)

        if self.requires_context:
            _require_int("context_start", self.context_start)
            _require_int("context_end", self.context_end)

            if self.context_start < 0 or self.context_end <= self.context_start:
                raise AtomicAnnotationError(
                    "context span must satisfy 0 <= context_start < context_end"
                )
        else:
            if (
                self.context_start is not None
                or self.context_end is not None
            ):
                raise AtomicAnnotationError(
                    "context offsets require requires_context=True"
                )

        derived = derive_fact_occurrence_id(
            self.benchmark_id,
            self.content_version_id,
            self.content_sha256,
            self.evidence_pack_id,
            self.fact_group_id,
            self.start,
            self.end,
        )

        if not self.fact_occurrence_id:
            object.__setattr__(self, "fact_occurrence_id", derived)
        elif self.fact_occurrence_id != derived:
            raise AtomicAnnotationError(
                "fact_occurrence_id does not match its derivation; "
                "occurrence identity cannot be forged"
            )


# --------------------------------------------------------------------------- #
# validation result
# --------------------------------------------------------------------------- #
@dataclass(frozen=True, slots=True)
class AtomicAnnotationValidationResult:
    """Immutable structural validation outcome.

    ``status == STRUCTURE_VALID`` means the annotation set satisfies the
    contract's structural rules. It does NOT mean the annotations are
    truthful, complete, human-verified, or evidence-supported.
    """

    status: str
    errors: tuple[str, ...]
    benchmark_id: str
    content_version_id: str
    content_sha256: str
    evidence_pack_id: str
    annotation_count: int
    fact_group_count: int
    fact_occurrence_count: int
    adjudicated_group_count: int
    rejected_annotation_count: int
    #: Informational only: annotations whose span overlaps a sentence-level
    #: Claim occurrence. This is NOT atomic enumeration and NOT evidence
    #: support; it must never be promoted to either.
    sentence_candidate_covered_occurrence_ids: tuple[str, ...]
    atomic_enumeration_status: str
    claim_recall_status: str
    evidence_support_status: str
    #: Always False in this module: no identity authentication exists.
    annotator_identity_verified: bool


# --------------------------------------------------------------------------- #
# structural validation
# --------------------------------------------------------------------------- #
def validate_atomic_annotations(
    index: SourceTextIndex,
    source_text: str,
    annotations: Sequence[AtomicFactAnnotation],
) -> AtomicAnnotationValidationResult:
    """Validate an annotation batch against a canonical index and source.

    Deterministic, pure, offline. No model calls, no Store writes, no
    scoring, no similarity merging of any kind.
    """
    if not isinstance(index, SourceTextIndex):
        raise TypeError("index must be a SourceTextIndex")

    if not isinstance(source_text, str):
        raise TypeError("source_text must be str")

    if annotations is None or isinstance(annotations, (str, bytes)):
        raise TypeError(
            "annotations must be a sequence of AtomicFactAnnotation"
        )

    try:
        items = list(annotations)
    except TypeError as exc:
        raise TypeError(
            "annotations must be a sequence of AtomicFactAnnotation"
        ) from exc

    for annotation in items:
        if not isinstance(annotation, AtomicFactAnnotation):
            raise TypeError(
                "annotations must be AtomicFactAnnotation instances"
            )

    errors: list[str] = []

    # --- source integrity ------------------------------------------------- #
    digest = sha256(source_text.encode("utf-8")).hexdigest()

    if digest != index.content_sha256:
        errors.append(
            "source sha256 mismatch: "
            f"source={digest} index={index.content_sha256}"
        )

    if index.source_length != len(source_text):
        errors.append(
            "index source_length does not match source text: "
            f"index={index.source_length} source={len(source_text)}"
        )

    rebuilt = "".join(segment.text for segment in index.segments)

    if rebuilt != source_text:
        errors.append(
            "index segments do not reconstruct source text losslessly"
        )

    # --- per-annotation checks -------------------------------------------- #
    benchmark = ""
    seen_occurrence_ids: set[str] = set()

    for annotation in items:
        if not benchmark:
            benchmark = annotation.benchmark_id
        elif annotation.benchmark_id != benchmark:
            errors.append(
                "benchmark_id mismatch: "
                f"{annotation.fact_occurrence_id} declares "
                f"{annotation.benchmark_id!r}, batch is {benchmark!r}"
            )

        if annotation.content_version_id != index.content_version_id:
            errors.append(
                f"{annotation.fact_occurrence_id}: content_version_id "
                f"{annotation.content_version_id!r} does not match index "
                f"{index.content_version_id!r}"
            )

        if annotation.content_sha256 != index.content_sha256:
            errors.append(
                f"{annotation.fact_occurrence_id}: content_sha256 does not "
                "match index"
            )

        if annotation.evidence_pack_id != index.evidence_pack_id:
            errors.append(
                f"{annotation.fact_occurrence_id}: evidence_pack_id "
                f"{annotation.evidence_pack_id!r} does not match index "
                f"{index.evidence_pack_id!r}"
            )

        if not (
            0 <= annotation.start < annotation.end <= len(source_text)
        ):
            errors.append(
                f"{annotation.fact_occurrence_id}: span out of bounds or "
                f"empty ({annotation.start}, {annotation.end})"
            )
        elif (
            source_text[annotation.start : annotation.end]
            != annotation.source_quote
        ):
            errors.append(
                f"{annotation.fact_occurrence_id}: source_quote does not "
                "equal source_text[start:end]"
            )

        if annotation.requires_context and not (
            0
            <= annotation.context_start
            < annotation.context_end
            <= len(source_text)
        ):
            errors.append(
                f"{annotation.fact_occurrence_id}: context span out of "
                f"bounds ({annotation.context_start}, {annotation.context_end})"
            )

        if annotation.fact_occurrence_id in seen_occurrence_ids:
            errors.append(
                f"duplicate fact_occurrence_id: "
                f"{annotation.fact_occurrence_id}"
            )

        seen_occurrence_ids.add(annotation.fact_occurrence_id)

    # --- fact-group consistency (no silent merging) ----------------------- #
    groups: dict[str, list[AtomicFactAnnotation]] = {}

    for annotation in items:
        groups.setdefault(annotation.fact_group_id, []).append(annotation)

    for group_id, members in groups.items():
        subjects = {
            member.subject_ref for member in members if member.subject_ref
        }

        if len(subjects) > 1:
            errors.append(
                f"fact_group {group_id}: conflicting subject_ref "
                f"{sorted(subjects)}; manual adjudication required"
            )

        polarities = {member.polarity for member in members}

        if len(polarities) > 1:
            errors.append(
                f"fact_group {group_id}: conflicting polarity "
                f"{sorted(polarities)}; manual adjudication required"
            )

        spans = [(member.start, member.end) for member in members]

        if len(set(spans)) != len(spans):
            errors.append(
                f"fact_group {group_id}: duplicate occurrence span inside "
                "one fact group"
            )

    # --- informational sentence-candidate overlap ------------------------- #
    covered = tuple(
        annotation.fact_occurrence_id
        for annotation in items
        if any(
            occurrence.start < annotation.end
            and annotation.start < occurrence.end
            for occurrence in index.occurrences
        )
    )

    adjudicated_groups = sum(
        1
        for members in groups.values()
        if any(
            member.review_status == "ADJUDICATED"
            for member in members
        )
    )

    rejected_count = sum(
        1
        for annotation in items
        if annotation.review_status == "REJECTED"
    )

    return AtomicAnnotationValidationResult(
        status=STRUCTURE_VALID if not errors else STRUCTURE_INVALID,
        errors=tuple(errors),
        benchmark_id=benchmark,
        content_version_id=index.content_version_id,
        content_sha256=index.content_sha256,
        evidence_pack_id=index.evidence_pack_id,
        annotation_count=len(items),
        fact_group_count=len(groups),
        fact_occurrence_count=len(seen_occurrence_ids),
        adjudicated_group_count=adjudicated_groups,
        rejected_annotation_count=rejected_count,
        sentence_candidate_covered_occurrence_ids=covered,
        atomic_enumeration_status=ATOMIC_ENUMERATION_NOT_VERIFIED,
        claim_recall_status=NOT_EVALUATED,
        evidence_support_status=NOT_EVALUATED,
        annotator_identity_verified=False,
    )
