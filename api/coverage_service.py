"""I2-C-001B-P1: canonical, read-only Coverage inspection service.

No cache. No Store mutation. No factual-safety or approval verdict.

A successful inspection establishes a source-text mapping snapshot
only. It does not establish atomic completeness, semantic evidence
support or evaluation approval.
"""

from __future__ import annotations

from hashlib import sha256

from api.claim_store import ClaimStore
from api.evidence_store import EvidencePackStore
from api.source_text_index import (
    SourceTextIndex,
    build_source_text_index,
)
from api.versioning import ContentVersionStore


class CoverageIntegrityError(ValueError):
    """The canonical Coverage inputs or snapshot are inconsistent."""


def inspect_canonical_coverage(
    *,
    content_version_id: str,
    version_store: ContentVersionStore,
    claim_store: ClaimStore,
    evidence_pack_store: EvidencePackStore,
    task_id: str = "",
    expected_content_sha256: str = "",
) -> SourceTextIndex:
    """Build Coverage from canonical stores, never client-supplied Claims.

    The before/after version comparison detects observed mutations
    during inspection. It is not a cross-Store transaction and does
    not guarantee atomicity against all concurrent modifications.
    """

    if (
        not isinstance(content_version_id, str)
        or not content_version_id.strip()
    ):
        raise CoverageIntegrityError(
            "content_version_id must be nonblank"
        )

    # ContentVersionStore currently returns a live mutable reference.
    # Never pass that live object directly into the index builder.
    version = version_store.get_version(
        content_version_id
    ).model_copy(deep=True)

    if version.content_version_id != content_version_id:
        raise CoverageIntegrityError(
            "canonical content_version_id mismatch"
        )

    if (
        not isinstance(version.task_id, str)
        or not version.task_id.strip()
    ):
        raise CoverageIntegrityError(
            "canonical version missing task_id"
        )

    if (
        task_id.strip()
        and task_id.strip() != version.task_id
    ):
        raise CoverageIntegrityError(
            "task_id does not match canonical version"
        )

    pack_id = version.evidence_pack_id

    if (
        not isinstance(pack_id, str)
        or not pack_id.strip()
    ):
        raise CoverageIntegrityError(
            "canonical version missing evidence_pack_id"
        )

    if not isinstance(version.content, str):
        raise CoverageIntegrityError(
            "canonical version content is not str"
        )

    canonical_digest = sha256(
        version.content.encode("utf-8")
    ).hexdigest()

    # The client may supply an EXPECTED digest as a stale-data guard.
    # The client cannot define the canonical digest.
    if (
        expected_content_sha256
        and expected_content_sha256 != canonical_digest
    ):
        raise CoverageIntegrityError(
            "content digest mismatch: canonical version changed"
        )

    # The pack must really exist. Its ID alone is not enough.
    pack = evidence_pack_store.get(pack_id)

    if pack.evidence_pack_id != pack_id:
        raise CoverageIntegrityError(
            "canonical EvidencePack identity mismatch"
        )

    # Resolve exactly the Claims belonging to this version's pack.
    # No global claim lookup and no client-provided Claim objects.
    claims = claim_store.get_many(
        pack_id,
        version.claim_ids,
    )

    # The approved SourceTextIndex validates canonical Claim identity,
    # sentence boundaries, offsets and duplicate occurrences.
    try:
        index = build_source_text_index(
            version,
            claims,
        )
    except (ValueError, TypeError, RuntimeError) as exc:
        raise CoverageIntegrityError(
            f"invalid canonical Coverage inputs: {exc}"
        ) from exc

    if (
        index.content_version_id != version.content_version_id
        or index.evidence_pack_id != pack_id
        or index.content_sha256 != canonical_digest
    ):
        raise CoverageIntegrityError(
            "Coverage index does not match canonical snapshot"
        )

    # Best-effort mutation detection. This is NOT a transaction.
    latest = version_store.get_version(
        content_version_id
    ).model_copy(deep=True)

    if latest != version:
        raise CoverageIntegrityError(
            "content version changed during Coverage inspection"
        )

    return index
