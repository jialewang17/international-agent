"""Minimal, fail-closed Rubric loader for the ChinaStory Evaluation Skill.

The rubric Markdown file stays the single source of truth for dimension
definitions. This module only *reads and validates* it — it never duplicates
rubric prose into Python. Only the canonical identifier list is kept here, so a
silent rename or reordering in the document is caught instead of silently
propagated.

There is intentionally no heavyweight Markdown dependency: dimensions are read
from the ``# <n>. D<k>｜<Name>`` section headings emitted by the v2.1 rubric.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

#: Rubric version this loader is allowed to serve.
SUPPORTED_RUBRIC_VERSION = "CHINASTORY_CONTENT_QUALITY_RUBRIC_v2.1"

#: Canonical D1–D6 identifiers, in canonical order (rubric §6–§11).
CANONICAL_DIMENSION_IDS: Tuple[str, ...] = (
    "cross_cultural_comprehensibility",
    "cultural_expression_quality",
    "audience_fit",
    "narrative_engagement_potential",
    "genre_platform_fit",
    "naturalness_non_sloganeering",
)

#: Canonical display names, used to detect renames/typos in the document.
CANONICAL_DIMENSION_NAMES: Tuple[str, ...] = (
    "Cross-cultural Comprehensibility",
    "Cultural Expression Quality",
    "Audience Fit",
    "Narrative Engagement Potential",
    "Genre & Platform Fit",
    "Naturalness & Non-sloganeering",
)

#: Rubric §5: 1–5 BARS.
MIN_SCORE, MAX_SCORE = 1, 5

DEFAULT_RUBRIC_PATH = (
    Path(__file__).resolve().parent.parent
    / "eval"
    / "CHINASTORY_CONTENT_QUALITY_RUBRIC_v2.1.md"
)


class RubricError(ValueError):
    """Raised when the rubric cannot be trusted. Always fail closed."""


@dataclass(frozen=True)
class RubricDimension:
    dimension_id: str
    name: str
    order: int
    code: str  # "D1".."D6"


@dataclass(frozen=True)
class Rubric:
    rubric_version: str
    dimensions: List[RubricDimension]
    source_path: str = ""

    @property
    def dimension_ids(self) -> List[str]:
        return [d.dimension_id for d in self.dimensions]

    def dimension(self, dimension_id: str) -> Optional[RubricDimension]:
        for item in self.dimensions:
            if item.dimension_id == dimension_id:
                return item
        return None


_VERSION_RE = re.compile(r"^#\s*ChinaStory Content Quality Rubric\s+(v[\d.]+)\s*$", re.M)
_HEADING_RE = re.compile(r"^#\s*\d+\.\s*(D[1-9])\s*[｜|]\s*(.+?)\s*$", re.M)


def _normalize_name(raw: str) -> str:
    """Fold the separator/whitespace noise the rubric uses around names."""
    text = raw.replace("\u3000", " ").strip()
    text = re.sub(r"\s*/\s*", " & ", text)
    text = re.sub(r"\s+", " ", text)
    # Rubric writes "Naturalness / Non-sloganeering" in prose, "&" in heading.
    return text


def load_rubric(path: Optional[str] = None) -> Rubric:
    """Load and validate the ChinaStory rubric. Fail closed on any doubt."""
    rubric_path = Path(path) if path else DEFAULT_RUBRIC_PATH

    if not rubric_path.is_file():
        raise RubricError(f"rubric file not found: {rubric_path}")

    try:
        text = rubric_path.read_text(encoding="utf-8")
    except OSError as exc:  # unreadable / permission / encoding
        raise RubricError(f"rubric file unreadable: {rubric_path}: {exc}") from exc

    version_match = _VERSION_RE.search(text)
    if not version_match:
        raise RubricError("rubric version header not found")
    version = f"CHINASTORY_CONTENT_QUALITY_RUBRIC_{version_match.group(1)}"
    if version != SUPPORTED_RUBRIC_VERSION:
        raise RubricError(
            f"unsupported rubric version: {version} (expected {SUPPORTED_RUBRIC_VERSION})"
        )

    dimensions = _parse_dimensions(text)
    _validate_dimensions(dimensions)
    return Rubric(rubric_version=version, dimensions=dimensions, source_path=str(rubric_path))


def _parse_dimensions(text: str) -> List[RubricDimension]:
    found: List[RubricDimension] = []
    for code, raw_name in _HEADING_RE.findall(text):
        name = _normalize_name(raw_name)
        if not code.startswith("D") or not code[1:].isdigit():
            raise RubricError(f"malformed dimension code: {code}")
        index = int(code[1:])
        if not 1 <= index <= len(CANONICAL_DIMENSION_IDS):
            raise RubricError(f"unexpected dimension outside D1-D6: {code}")
        found.append(
            RubricDimension(
                dimension_id=CANONICAL_DIMENSION_IDS[index - 1],
                name=name,
                order=index,
                code=code,
            )
        )
    if not found:
        raise RubricError("no dimension headings found in rubric")
    return found


def _validate_dimensions(dimensions: Sequence[RubricDimension]) -> None:
    codes = [d.code for d in dimensions]

    duplicates = sorted({c for c in codes if codes.count(c) > 1})
    if duplicates:
        raise RubricError(f"duplicate dimension headings: {', '.join(duplicates)}")

    expected = [f"D{i}" for i in range(1, len(CANONICAL_DIMENSION_IDS) + 1)]
    missing = [c for c in expected if c not in codes]
    if missing:
        raise RubricError(f"missing dimensions: {', '.join(missing)}")

    if codes != expected:
        raise RubricError(f"dimension order not canonical: {codes}")

    for item in dimensions:
        canonical_name = CANONICAL_DIMENSION_NAMES[item.order - 1]
        if item.name != canonical_name:
            raise RubricError(
                f"{item.code} name mismatch: {item.name!r} (expected {canonical_name!r})"
            )
