"""I2-C-001A-R2: strict, pack-scoped Claim occurrence mapping.

Occurrence/lexical identity is NOT contextual identity, atomic completeness,
semantic evidence support, Evaluation PASS or approval. No Store mutation.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import re
from typing import Optional, Sequence

from api.claim_extraction import (
    _MD_BULLET_RE,
    _MD_HEADING_RE,
    _MD_NUMBERED_RE,
    _clean_markdown_prefix,
    _is_separator,
    _is_skippable_text,
    _iter_blocks,
    _normalize_text,
    _split_sentences,
)
from api.fact_safety import _fingerprint
from api.schemas import Claim, ContentVersion


CLAIM_MAPPED = "CLAIM_MAPPED"
NON_FACTUAL_WITH_REASON = "NON_FACTUAL_WITH_REASON"
UNCERTAIN_REVIEW_REQUIRED = "UNCERTAIN_REVIEW_REQUIRED"
NOT_EVALUATED = "NOT_EVALUATED"
CONTEXT_EQUIVALENCE_NOT_EVALUATED = "CONTEXT_EQUIVALENCE_NOT_EVALUATED"

_RULE = re.compile(r"(?:[-*_=]\s*){3,}")

_COMPOUND = re.compile(
    r"[，,；;]|\b(?:and|but|while|whereas|because|although)\b"
    r"|并且|以及|同时|不仅|而且|分别",
    re.I,
)
_NUMERIC = re.compile(r"(?<!\d)\d+(?:\.\d+)?%?(?!\d)")
_CAUSAL = re.compile(
    r"\b(?:because|therefore|caused|led\s+to)\b|因为|因此|导致|使得",
    re.I,
)
_CONTEXT = re.compile(
    r"\b(?:it|its|he|she|they|their|here|there|today|currently|this\s+company)\b"
    r"|它|他|她|其|该公司|该项目|当地|今年|目前|上述",
    re.I,
)


@dataclass(frozen=True, slots=True)
class ClaimOccurrence:
    evidence_pack_id: str
    claim_id: str
    start: int
    end: int
    source_text: str
    alignment: str
    context_status: str = CONTEXT_EQUIVALENCE_NOT_EVALUATED


@dataclass(frozen=True, slots=True)
class SourceSegment:
    segment_id: str
    start: int
    end: int
    text: str
    status: str
    reason: str
    claim_ids: tuple[str, ...]
    atomic_risks: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SourceTextIndex:
    content_version_id: str
    task_id: str
    evidence_pack_id: str
    parent_version_id: Optional[str]
    content_sha256: str
    source_length: int
    offset_unit: str
    unique_claim_ids: tuple[str, ...]
    segments: tuple[SourceSegment, ...]
    occurrences: tuple[ClaimOccurrence, ...]
    unlocated_claim_ids: tuple[str, ...]
    claim_recall_status: str = NOT_EVALUATED
    semantic_support_status: str = NOT_EVALUATED


@dataclass(frozen=True, slots=True)
class HumanGoldAtomicFact:
    fact_id: str
    content_version_id: str
    content_sha256: str
    start: int
    end: int
    proposition: str
    reviewed_matching_claim_id: Optional[str] = None


@dataclass(frozen=True, slots=True)
class GoldRecallReport:
    status: str
    benchmark_id: str
    annotator_id: str
    gold_count: int
    matched_count: int
    recall: Optional[float]
    missing_fact_ids: tuple[str, ...]


def _raw_lines(source: str):
    """CR/LF/CRLF lines with exact original offsets."""
    for match in re.finditer(
        r"[^\r\n]*(?:\r\n|\r|\n|$)",
        source,
    ):
        line = match.group()
        if not line:
            continue

        length = (
            2 if line.endswith("\r\n")
            else (1 if line.endswith(("\n", "\r")) else 0)
        )

        yield (
            match.start(),
            line,
            line[:-length] if length else line,
        )


def _source_blocks(source: str):
    """Mirror existing extractor blocks while retaining source offsets.

    Any drift between this reconstruction and _iter_blocks raises.
    That prevents an incorrect occurrence from being silently accepted.
    """
    blocks: list[tuple[str, list[tuple[int, int]]]] = []
    paragraph: list[
        tuple[str, list[tuple[int, int]]]
    ] = []

    def flush():
        if not paragraph:
            return

        chars: list[str] = []
        ranges: list[tuple[int, int]] = []

        for text, char_ranges in paragraph:
            if chars:
                chars.append(" ")
                ranges.append(
                    (ranges[-1][1], char_ranges[0][0])
                )
            chars.extend(text)
            ranges.extend(char_ranges)

        blocks.append(("".join(chars), ranges))
        paragraph.clear()

    for line_start, _, body in _raw_lines(source):
        stripped = body.strip()

        if (
            not stripped
            or _is_separator(stripped)
            or _is_skippable_text(stripped)
        ):
            flush()
            continue

        left_trim = len(body) - len(body.lstrip())
        abs_start = line_start + left_trim

        positions = [
            (abs_start + i, abs_start + i + 1)
            for i in range(len(stripped))
        ]

        is_markdown = (
            _MD_HEADING_RE.match(stripped)
            or _MD_BULLET_RE.match(stripped)
            or _MD_NUMBERED_RE.match(stripped)
        )

        if is_markdown:
            flush()
            cleaned = _clean_markdown_prefix(stripped)

            if cleaned:
                if not stripped.endswith(cleaned):
                    raise RuntimeError(
                        "unmappable Markdown prefix"
                    )

                offset = len(stripped) - len(cleaned)
                blocks.append(
                    (cleaned, positions[offset:])
                )
            continue

        paragraph.append((stripped, positions))

    flush()

    if [
        text for text, _ in blocks
    ] != _iter_blocks(source):
        raise RuntimeError(
            "extractor block correspondence changed: fail closed"
        )

    return blocks


def _risk_flags(body: str) -> tuple[str, ...]:
    """Conservative signals, not atomic fact recognition."""
    flags: list[str] = []

    if _COMPOUND.search(body):
        flags.append("COMPOUND_CLAUSE_POSSIBLE")

    if len(_NUMERIC.findall(body)) >= 2:
        flags.append("MULTIPLE_NUMERIC_FACTS_POSSIBLE")

    if _CAUSAL.search(body):
        flags.append("CAUSAL_ASSERTION_REVIEW")

    if _CONTEXT.search(body):
        flags.append("CONTEXT_DEPENDENCY_POSSIBLE")

    return tuple(flags)


def _source_marker_mask(source: str) -> set[int]:
    """Recognized Markdown prefix chars, not factual prose."""
    structural: set[int] = set()

    for line_start, _, body in _raw_lines(source):
        line = body.strip()

        if not line:
            continue

        if not (
            _MD_HEADING_RE.match(line)
            or _MD_BULLET_RE.match(line)
            or _MD_NUMBERED_RE.match(line)
        ):
            continue

        cleaned = _clean_markdown_prefix(line)

        if not cleaned or not line.endswith(cleaned):
            continue

        left = len(body) - len(body.lstrip())
        prefix_len = len(line) - len(cleaned)

        structural.update(
            range(
                line_start + left,
                line_start + left + prefix_len,
            )
        )

    return structural


def build_source_text_index(
    version: ContentVersion,
    claims: Sequence[Claim],
) -> SourceTextIndex:
    """Map exact sentence identities to original occurrences.

    This function never verifies semantic support or factual truth.
    """
    if not isinstance(version, ContentVersion):
        raise TypeError("version must be ContentVersion")

    if not isinstance(version.content, str):
        raise TypeError("version.content must be str")

    for label in (
        "content_version_id",
        "task_id",
        "evidence_pack_id",
    ):
        val = getattr(version, label)

        if not isinstance(val, str) or not val.strip():
            raise ValueError(
                f"{label} must be nonblank str"
            )

    if not isinstance(claims, (list, tuple)):
        raise TypeError(
            "claims must be list/tuple of Claim snapshots"
        )

    if (
        not isinstance(version.claim_ids, list)
        or any(
            not isinstance(cid, str) or not cid.strip()
            for cid in version.claim_ids
        )
        or len(set(version.claim_ids)) != len(version.claim_ids)
    ):
        raise ValueError(
            "invalid/duplicate IDs in ContentVersion.claim_ids"
        )

    by_id: dict[str, Claim] = {}

    for claim in claims:
        if (
            not isinstance(claim, Claim)
            or not isinstance(claim.text, str)
            or not claim.text.strip()
        ):
            raise ValueError(
                "claims must be nonblank Claim snapshots"
            )

        if (
            not isinstance(claim.claim_id, str)
            or not claim.claim_id.strip()
        ):
            raise ValueError("blank claim ID")

        previous = by_id.get(claim.claim_id)

        if previous is not None and previous != claim:
            raise ValueError(
                "claim ID collision: differing snapshot payload"
            )

        # Claim.text must be the exact canonical extractor text.
        # No additional case-folding, translation or punctuation changes.
        if claim.text != _normalize_text(claim.text):
            raise ValueError(
                "Claim.text is not canonical extractor text"
            )

        if claim.claim_id != "clm_" + _fingerprint(claim.text):
            raise ValueError(
                "claim ID fingerprint does not match Claim.text"
            )

        by_id[claim.claim_id] = claim

    if set(by_id) != set(version.claim_ids):
        raise ValueError(
            "claim snapshot IDs must equal ContentVersion.claim_ids"
        )

    source = version.content
    digest = sha256(source.encode("utf-8")).hexdigest()

    occurrences: list[ClaimOccurrence] = []

    # Reuse the approved extractor's real block/sentence boundaries.
    # Never perform a global substring search for a Claim.
    for block, positions in _source_blocks(source):
        cursor = 0

        for chunk in _split_sentences(block):
            left = cursor
            right = left + len(chunk)
            cursor = right

            sentence = _normalize_text(chunk)

            if _is_skippable_text(sentence):
                continue

            claim_id = "clm_" + _fingerprint(sentence)
            stored = by_id.get(claim_id)

            if stored is None or stored.text != sentence:
                continue

            begin = (
                left + len(chunk) - len(chunk.lstrip())
            )
            finish = (
                right - (len(chunk) - len(chunk.rstrip()))
            )

            if begin >= finish:
                continue

            start = positions[begin][0]
            end = positions[finish - 1][1]
            raw_span = source[start:end]

            if _normalize_text(raw_span) != sentence:
                raise RuntimeError(
                    "offset does not map to exact Claim.text"
                )

            occurrences.append(
                ClaimOccurrence(
                    version.evidence_pack_id,
                    claim_id,
                    start,
                    end,
                    raw_span,
                    (
                        "SOURCE_EXACT"
                        if raw_span == sentence
                        else "WHITESPACE_NORMALIZED_SOURCE"
                    ),
                )
            )

        if cursor != len(block):
            raise RuntimeError(
                "sentence partition is not lossless"
            )

    occurrences.sort(
        key=lambda occurrence: (
            occurrence.start,
            occurrence.end,
            occurrence.claim_id,
        )
    )

    covered = bytearray(len(source))

    for occ in occurrences:
        covered[occ.start:occ.end] = (
            b"\x01" * (occ.end - occ.start)
        )

    structural = _source_marker_mask(source)
    located = {o.claim_id for o in occurrences}

    segments: list[SourceSegment] = []
    cursor = 0

    for ordinal, (
        start,
        full_line,
        body,
    ) in enumerate(_raw_lines(source)):
        end = start + len(full_line)

        if start != cursor:
            raise RuntimeError(
                "non-contiguous source segmentation"
            )

        cursor = end
        clean = body.strip()

        related = [
            o for o in occurrences
            if o.start < end and start < o.end
        ]

        related_ids = tuple(
            dict.fromkeys(
                o.claim_id for o in related
            )
        )

        risks = _risk_flags(clean) if clean else ()

        if not clean:
            status = NON_FACTUAL_WITH_REASON
            reason = "whitespace_only"

        elif _RULE.fullmatch(clean):
            status = NON_FACTUAL_WITH_REASON
            reason = "markdown_separator"

        else:
            unaligned = any(
                not source[i].isspace()
                and not covered[i]
                and i not in structural
                for i in range(start, end)
            )

            if related and not unaligned and not risks:
                status = CLAIM_MAPPED
                reason = "lexical_position_only"
            else:
                status = UNCERTAIN_REVIEW_REQUIRED
                reason = (
                    "atomic_or_context_review_required"
                    if risks
                    else "unmapped_or_partial_text"
                )

        segment_id = "seg_" + sha256(
            (
                f"{version.content_version_id}\x00"
                f"{digest}\x00"
                f"{ordinal}\x00"
                f"{start}\x00{end}"
            ).encode("utf-8")
        ).hexdigest()

        segments.append(
            SourceSegment(
                segment_id,
                start,
                end,
                full_line,
                status,
                reason,
                related_ids,
                risks,
            )
        )

    if (
        cursor != len(source)
        or "".join(
            seg.text for seg in segments
        ) != source
    ):
        raise RuntimeError(
            "source text lost or reordered"
        )

    return SourceTextIndex(
        content_version_id=version.content_version_id,
        task_id=version.task_id,
        evidence_pack_id=version.evidence_pack_id,
        parent_version_id=version.parent_version_id,
        content_sha256=digest,
        source_length=len(source),
        offset_unit="python_unicode_codepoints",
        unique_claim_ids=tuple(version.claim_ids),
        segments=tuple(segments),
        occurrences=tuple(occurrences),
        unlocated_claim_ids=tuple(
            cid for cid in version.claim_ids
            if cid not in located
        ),
    )


def evaluate_human_gold_recall(
    index: SourceTextIndex,
    gold_facts: Optional[
        Sequence[HumanGoldAtomicFact]
    ] = None,
    *,
    benchmark_id: str = "",
    annotator_id: str = "",
) -> GoldRecallReport:
    """Score supplied independently adjudicated atomic annotations only.

    Neither annotator_id nor the input objects prove human review,
    annotation quality, or semantic equivalence.
    """
    if not isinstance(index, SourceTextIndex):
        raise TypeError(
            "index must be SourceTextIndex"
        )

    if not gold_facts:
        return GoldRecallReport(
            NOT_EVALUATED,
            benchmark_id,
            annotator_id,
            0,
            0,
            None,
            (),
        )

    if not benchmark_id.strip() or not annotator_id.strip():
        raise ValueError(
            "human benchmark needs benchmark_id and annotator_id"
        )

    gold_ids: set[str] = set()
    propositions: set[str] = set()
    matched_claim_ids: set[str] = set()

    misses: list[str] = []
    hits = 0

    for fact in gold_facts:
        if not isinstance(fact, HumanGoldAtomicFact):
            raise TypeError(
                "gold facts must be HumanGoldAtomicFact"
            )

        if (
            fact.content_version_id != index.content_version_id
            or fact.content_sha256 != index.content_sha256
        ):
            raise ValueError(
                "human gold version/fingerprint mismatch"
            )

        if (
            not isinstance(fact.fact_id, str)
            or not fact.fact_id.strip()
            or fact.fact_id in gold_ids
        ):
            raise ValueError(
                "invalid/duplicate gold fact ID"
            )

        if (
            not isinstance(fact.proposition, str)
            or not fact.proposition.strip()
        ):
            raise ValueError(
                "empty gold atomic proposition"
            )

        if not (
            isinstance(fact.start, int)
            and isinstance(fact.end, int)
            and 0 <= fact.start < fact.end <= index.source_length
        ):
            raise ValueError(
                "invalid gold source offsets"
            )

        # Identical text is NOT proof of semantic identity.
        # Do not silently merge duplicate literal gold propositions.
        # Require human benchmark correction instead.
        if fact.proposition in propositions:
            raise ValueError(
                "ambiguous duplicate gold proposition: "
                "manual dedup review required"
            )

        gold_ids.add(fact.fact_id)
        propositions.add(fact.proposition)

        cid = fact.reviewed_matching_claim_id

        if cid is None:
            misses.append(fact.fact_id)
            continue

        if cid not in index.unique_claim_ids:
            raise ValueError(
                "gold references unknown claim ID"
            )

        if cid in matched_claim_ids:
            raise ValueError(
                "one sentence Claim cannot credit "
                "multiple atomic facts"
            )

        if not any(
            o.claim_id == cid
            and o.start < fact.end
            and fact.start < o.end
            for o in index.occurrences
        ):
            raise ValueError(
                "gold match not located at annotated span"
            )

        matched_claim_ids.add(cid)
        hits += 1

    return GoldRecallReport(
        "SUPPLIED_GOLD_SCORED_NOT_VERIFIED",
        benchmark_id,
        annotator_id,
        len(gold_facts),
        hits,
        hits / len(gold_facts),
        tuple(misses),
    )
