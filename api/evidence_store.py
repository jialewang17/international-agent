"""Application-level in-memory store for canonical EvidencePack snapshots (I1)."""
from __future__ import annotations

from typing import Dict, List

from api.schemas import EvidencePack


class EvidenceStoreError(ValueError):
    pass


class EvidencePackStore:
    """Persist immutable-by-convention canonical evidence snapshots by deterministic id."""

    def __init__(self):
        self._packs: Dict[str, EvidencePack] = {}

    def put(self, pack: EvidencePack) -> EvidencePack:
        existing = self._packs.get(pack.evidence_pack_id)
        if existing is not None:
            if existing.model_dump(mode="json") != pack.model_dump(mode="json"):
                raise EvidenceStoreError(
                    f"evidence_pack_id collision: {pack.evidence_pack_id}"
                )
            return existing.model_copy(deep=True)
        self._packs[pack.evidence_pack_id] = pack.model_copy(deep=True)
        return pack.model_copy(deep=True)

    def get(self, evidence_pack_id: str) -> EvidencePack:
        try:
            return self._packs[evidence_pack_id].model_copy(deep=True)
        except KeyError as exc:
            raise EvidenceStoreError(
                f"evidence pack not found: {evidence_pack_id}"
            ) from exc

    def all_packs(self) -> List[EvidencePack]:
        return [pack.model_copy(deep=True) for pack in self._packs.values()]

    def __len__(self) -> int:
        return len(self._packs)
