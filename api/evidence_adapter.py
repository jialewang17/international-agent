"""B/C 边界 Evidence Adapter（I0-B2）。

职责单一：把既有 retrieval / merged evidence rows（legacy dict）
无损映射为 canonical :class:`api.schemas.EvidencePack`。

    retrieve_statements / merge_evidence
            ↓  legacy evidence rows
    build_evidence_pack()
            ↓  canonical EvidencePack
    manual Claim  →  api.binding.resolve_claim_trace()

本 Adapter **只**负责：
- 必要字符串 normalize（strip）
- provenance-preserving mapping（原始 source 一字不改地进 ``Source.uri``）
- deterministic IDs（sha256，无 random UUID）
- deduplication（``(source, statement)`` 为键）
- fail closed（无有效 evidence 时 raise）
- canonical schema construction

本 Adapter **不**负责：Claim extraction、LLM、事实判断、evidence ranking、
retrieval、KG、Graph RAG、Gate B、generation、evaluation、revision、Gate C。

设计约束（与仓库约定一致）：
- 不新增 / 不修改任何 schema；``status`` 沿用 canonical 既有默认语义；
- legacy retrieval 没有 start/end offset，故 ``spans`` 一律为 ``[]``，
  **不伪造 EvidenceSpan**；
- ``source`` 若为 HTTP(S) URL，原样保留；若为内部 locator（如
  ``user_paste:<title>``），同样原样保留，**不伪装成 URL**。
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from api.schemas import EvidenceItem, EvidencePack, Source

__all__ = [
    "EvidenceAdapterError",
    "SOURCE_TYPE_USER_UPLOAD",
    "SOURCE_TYPE_LOCAL_KB",
    "canonical_digest",
    "source_id_for",
    "evidence_id_for",
    "evidence_pack_id_for",
    "build_evidence_pack",
]

#: Stable ID prefixes (readable + collision-resistant).
_SRC_PREFIX = "src_"
_EV_PREFIX = "ev_"
_PACK_PREFIX = "ep_"

#: Digest length in hex chars. 24 hex = 96 bits: ample for a fixture-scale pack,
#: and short enough to stay readable in traces.
_DIGEST_LEN = 24

#: ``row["source_type"]`` values emitted by ``tools/user_materials.py``. These
#: are the *existing* Core semantics; the adapter maps them verbatim and never
#: invents a new vocabulary. Anything unknown maps to "" (never guessed).
SOURCE_TYPE_USER_UPLOAD = "用户上传"
SOURCE_TYPE_LOCAL_KB = "本地库"

_KNOWN_SOURCE_TYPES = frozenset({SOURCE_TYPE_USER_UPLOAD, SOURCE_TYPE_LOCAL_KB})


class EvidenceAdapterError(ValueError):
    """Raised when legacy rows cannot yield at least one canonical evidence item."""


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------


def _normalize_text(value: Any) -> str:
    """Minimal normalization: stringify + strip outer whitespace.

    Deliberately does NOT rewrite the factual text: no translation, no summary,
    no internal whitespace collapsing, no LLM pass. ``None`` becomes ``""``.
    """
    if value is None:
        return ""
    if not isinstance(value, str):
        value = str(value)
    return value.strip()


# ---------------------------------------------------------------------------
# Deterministic IDs
# ---------------------------------------------------------------------------


def canonical_digest(*parts: str, length: int = _DIGEST_LEN) -> str:
    """``sha256`` over length-prefixed parts → stable hex prefix.

    Length-prefixing each part makes the digest unambiguous: ``("ab", "c")``
    and ``("a", "bc")`` can never collide.
    """
    hasher = hashlib.sha256()
    for part in parts:
        chunk = part.encode("utf-8")
        hasher.update(str(len(chunk)).encode("ascii"))
        hasher.update(b":")
        hasher.update(chunk)
        hasher.update(b"|")
    return hasher.hexdigest()[:length]


def source_id_for(source_locator: str) -> str:
    """Deterministic ``Source.source_id`` from the normalized source locator."""
    return _SRC_PREFIX + canonical_digest(_normalize_text(source_locator))


def evidence_id_for(source_id: str, statement: str) -> str:
    """Deterministic ``EvidenceItem.evidence_id`` from source identity + statement.

    Derived from ``source_id`` (itself a function of the locator) plus the
    normalized statement — never from a retrieval rank or list index.
    """
    return _EV_PREFIX + canonical_digest(source_id, _normalize_text(statement))


def evidence_pack_id_for(identities: Iterable[Tuple[str, str]]) -> str:
    """Deterministic ``EvidencePack.evidence_pack_id`` from canonical identities.

    ``identities`` is the set of ``(source_id, evidence_id)`` pairs. Callers
    pass them in any order; this function sorts them, so reordering the input
    rows yields the *same* pack id for the *same* evidence set.
    """
    ordered = sorted(set(identities))
    parts: List[str] = []
    for source_id, evidence_id in ordered:
        parts.append(source_id)
        parts.append(evidence_id)
    return _PACK_PREFIX + canonical_digest(*parts)


# ---------------------------------------------------------------------------
# Mapping helpers
# ---------------------------------------------------------------------------


def _extract_row(raw: Any, index: int) -> Tuple[str, str, str]:
    """Pull ``(statement, source, category)`` out of one legacy row.

    Returns normalized values; an empty ``statement`` or ``source`` marks the
    row invalid (the caller decides what to do about it).
    """
    if not isinstance(raw, Mapping):
        raise EvidenceAdapterError(
            f"row #{index} is not a mapping (got {type(raw).__name__})"
        )
    statement = _normalize_text(raw.get("statement"))
    source = _normalize_text(raw.get("source"))
    category = _normalize_text(raw.get("category"))
    return statement, source, category


def _source_type_for(raw: Mapping[str, Any]) -> str:
    """Preserve an existing Core ``source_type``; never invent one."""
    value = _normalize_text(raw.get("source_type"))
    return value if value in _KNOWN_SOURCE_TYPES else ""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_evidence_pack(rows: Sequence[Mapping[str, Any]], **_: Any) -> EvidencePack:
    """Map legacy evidence rows → canonical :class:`EvidencePack`.

    Parameters
    ----------
    rows:
        Legacy rows, typically from :func:`tools.kb_local.retrieve_statements`
        and/or :func:`tools.user_materials.merge_evidence`. Accepted shape::

            {"category": "...", "statement": "...", "source": "...", "retrieval": "..."}
            {"category": "...", "statement": "...", "source": "...", "retrieval": "...",
             "source_type": "本地库"}

        The optional ``source_type`` is only carried over when it is one of the
        existing Core values (``本地库`` / ``用户上传``).

    Returns
    -------
    EvidencePack
        With ``status`` left at the canonical default (``"ready"``). No new
        status vocabulary is introduced.

    Raises
    ------
    EvidenceAdapterError
        If ``rows`` is not a sequence, a row is not a mapping, or no valid
        evidence remains after validation. Never returns an empty "ready" pack.
    """
    if rows is None or isinstance(rows, (str, bytes, Mapping)):
        raise EvidenceAdapterError(
            "rows must be a sequence of evidence-row mappings"
        )

    items: List[EvidenceItem] = []
    sources: Dict[str, Source] = {}
    seen_keys = set()
    identities: set = set()
    invalid = 0

    for index, raw in enumerate(rows):
        statement, source_locator, category = _extract_row(raw, index)

        # --- fail closed per row: invalid rows never become canonical evidence
        if not statement or not source_locator:
            invalid += 1
            continue

        source_id = source_id_for(source_locator)
        evidence_id = evidence_id_for(source_id, statement)

        # --- dedup key = (normalized source, normalized statement).
        # Same statement + different source stays two separate items, because
        # those are two independent provenance chains.
        dedup_key = (source_locator, statement)
        if dedup_key in seen_keys:
            continue
        seen_keys.add(dedup_key)

        if source_id not in sources:
            sources[source_id] = Source(
                source_id=source_id,
                # Provenance preserved verbatim: real URL stays a real URL,
                # an internal locator like "user_paste:<title>" is not dressed
                # up as an HTTP URL.
                uri=source_locator,
                title="",
                source_type=_source_type_for(raw),
            )

        items.append(
            EvidenceItem(
                evidence_id=evidence_id,
                source_id=source_id,
                statement=statement,
                spans=[],  # no offsets in legacy retrieval -> never fabricate
                category=category,
            )
        )
        identities.add((source_id, evidence_id))

    if not items:
        raise EvidenceAdapterError(
            f"no valid evidence in {len(rows)} row(s) "
            f"({invalid} invalid: missing/blank statement or source)"
        )

    return EvidencePack(
        evidence_pack_id=evidence_pack_id_for(identities),
        items=items,
        sources=[sources[sid] for sid in sorted(sources)],
        # status intentionally left at the canonical default ("ready").
    )
