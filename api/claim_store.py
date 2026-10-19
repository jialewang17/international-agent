"""In-memory pack-scoped snapshots for candidate Claims (I2-B-002).

Identity is (evidence_pack_id, claim_id). Neither this store nor its API
verifies that evidence IDs exist or semantically support a claim.
"""

from collections.abc import Iterable
from threading import RLock
from typing import Optional

from api.schemas import Claim

__all__ = ["ClaimStoreError", "ClaimStore"]


class ClaimStoreError(ValueError):
    """Invalid store request, missing batch member, or immutable ID collision."""


class ClaimStore:
    """Deep-copy, fail-closed, in-memory Claim snapshots grouped by EvidencePack."""

    def __init__(self) -> None:
        self._claims: dict[tuple[str, str], Claim] = {}
        self._lock = RLock()

    @staticmethod
    def _check_pack_id(evidence_pack_id: str) -> None:
        if not isinstance(evidence_pack_id, str) or not evidence_pack_id.strip():
            raise ClaimStoreError("evidence_pack_id must be a non-empty str")

    @staticmethod
    def _check_claim_id(claim_id: str) -> None:
        if not isinstance(claim_id, str) or not claim_id.strip():
            raise ClaimStoreError("claim_id must be a non-empty str")

    @classmethod
    def _check_claim(cls, claim: Claim) -> None:
        if not isinstance(claim, Claim):
            raise ClaimStoreError("claim must be api.schemas.Claim")
        cls._check_claim_id(claim.claim_id)
        if not isinstance(claim.text, str) or not claim.text.strip():
            raise ClaimStoreError("claim.text must be a non-empty str")
        if not isinstance(claim.evidence_ids, list) or any(
            not isinstance(ref, str) or not ref.strip()
            for ref in claim.evidence_ids
        ):
            raise ClaimStoreError(
                "claim.evidence_ids must be a list of non-empty strings"
            )

    @staticmethod
    def _collision(key: tuple[str, str]) -> ClaimStoreError:
        return ClaimStoreError(
            f"claim collision: evidence_pack_id={key[0]}, claim_id={key[1]}"
        )

    def put(self, evidence_pack_id: str, claim: Claim) -> Claim:
        """Insert an immutable snapshot; equal repeats are idempotent."""
        return self.put_many(evidence_pack_id, [claim])[0]

    def put_many(
        self,
        evidence_pack_id: str,
        claims: Iterable[Claim],
    ) -> list[Claim]:
        """Atomically validate and add a batch, retaining exact input order."""
        self._check_pack_id(evidence_pack_id)

        if claims is None or isinstance(claims, (str, bytes)):
            raise ClaimStoreError("claims must be an iterable of Claim")

        try:
            requested = list(claims)
        except TypeError as exc:
            raise ClaimStoreError(
                "claims must be an iterable of Claim"
            ) from exc

        staged: dict[tuple[str, str], Claim] = {}
        ordered_keys: list[tuple[str, str]] = []

        for claim in requested:
            self._check_claim(claim)
            key = (evidence_pack_id, claim.claim_id)
            snapshot = claim.model_copy(deep=True)

            previous = staged.get(key)
            if previous is not None and previous != snapshot:
                raise self._collision(key)

            if previous is None:
                staged[key] = snapshot

            ordered_keys.append(key)

        with self._lock:
            for key, snapshot in staged.items():
                stored = self._claims.get(key)
                if stored is not None and stored != snapshot:
                    raise self._collision(key)

            for key, snapshot in staged.items():
                if key not in self._claims:
                    self._claims[key] = snapshot

            return [
                self._claims[key].model_copy(deep=True)
                for key in ordered_keys
            ]

    def get(
        self,
        evidence_pack_id: str,
        claim_id: str,
    ) -> Optional[Claim]:
        """Return a defensive copy or None when the identity is absent."""
        self._check_pack_id(evidence_pack_id)
        self._check_claim_id(claim_id)

        with self._lock:
            stored = self._claims.get((evidence_pack_id, claim_id))
            return stored.model_copy(deep=True) if stored is not None else None

    def get_many(
        self,
        evidence_pack_id: str,
        claim_ids: Iterable[str],
    ) -> list[Claim]:
        """Read a complete batch; fail if any requested Claim is missing."""
        self._check_pack_id(evidence_pack_id)

        if claim_ids is None or isinstance(claim_ids, (str, bytes)):
            raise ClaimStoreError(
                "claim_ids must be an iterable of strings"
            )

        try:
            requested = list(claim_ids)
        except TypeError as exc:
            raise ClaimStoreError(
                "claim_ids must be an iterable of strings"
            ) from exc

        for claim_id in requested:
            self._check_claim_id(claim_id)

        with self._lock:
            for claim_id in requested:
                if (evidence_pack_id, claim_id) not in self._claims:
                    raise ClaimStoreError(
                        f"missing claim: evidence_pack_id={evidence_pack_id}, "
                        f"claim_id={claim_id}"
                    )

            return [
                self._claims[
                    (evidence_pack_id, claim_id)
                ].model_copy(deep=True)
                for claim_id in requested
            ]

    def all(self, evidence_pack_id: str) -> list[Claim]:
        """List pack-local snapshots, sorted by claim ID."""
        self._check_pack_id(evidence_pack_id)

        with self._lock:
            keys = sorted(
                key for key in self._claims
                if key[0] == evidence_pack_id
            )
            return [
                self._claims[key].model_copy(deep=True)
                for key in keys
            ]

    def __len__(self) -> int:
        """Number of distinct (pack ID, claim ID) identities."""
        with self._lock:
            return len(self._claims)
