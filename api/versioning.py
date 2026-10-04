"""集中管理 ContentVersion 的最小内存版本链。"""
from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import uuid4

from api.schemas import ContentVersion


class VersioningError(ValueError):
    pass


class ContentVersionStore:
    def __init__(self):
        self._versions: Dict[str, ContentVersion] = {}

    def create_initial_version(
        self, task_id: str, content: str, *, evidence_pack_id: Optional[str] = None,
        claim_ids: Optional[List[str]] = None,
    ) -> ContentVersion:
        version = ContentVersion(
            content_version_id=str(uuid4()), task_id=task_id, content=content,
            evidence_pack_id=evidence_pack_id, claim_ids=list(claim_ids or []),
            parent_version_id=None, created_at=datetime.now(timezone.utc),
        )
        self._versions[version.content_version_id] = version
        return version

    def create_revision(
        self, parent_version_id: str, content: str, *, task_id: Optional[str] = None,
        evidence_pack_id: Optional[str] = None, claim_ids: Optional[List[str]] = None,
    ) -> ContentVersion:
        parent = self.get_version(parent_version_id)
        if task_id is not None and task_id != parent.task_id:
            raise VersioningError("revision task_id does not match parent task_id")
        version = ContentVersion(
            content_version_id=str(uuid4()), task_id=parent.task_id, content=content,
            parent_version_id=parent.content_version_id,
            # None means inherit; P0.4 intentionally has no explicit clear sentinel.
            evidence_pack_id=parent.evidence_pack_id if evidence_pack_id is None else evidence_pack_id,
            claim_ids=list(parent.claim_ids if claim_ids is None else claim_ids),
            created_at=datetime.now(timezone.utc),
        )
        self._versions[version.content_version_id] = version
        return version

    def get_version(self, content_version_id: str) -> ContentVersion:
        try:
            return self._versions[content_version_id]
        except KeyError as exc:
            raise VersioningError(f"version not found: {content_version_id}") from exc

    def get_history(self, task_id: str) -> List[ContentVersion]:
        """Return all versions for a task in chronological creation order."""
        return sorted(
            (v for v in self._versions.values() if v.task_id == task_id),
            key=lambda v: v.created_at or datetime.min.replace(tzinfo=timezone.utc),
        )

    def get_lineage(self, content_version_id: str) -> List[ContentVersion]:
        """Return the actual root-to-target parent chain, including branches safely."""
        chain: List[ContentVersion] = []
        current_id: Optional[str] = content_version_id
        seen = set()
        while current_id is not None:
            if current_id in seen:
                raise VersioningError(f"cycle in version lineage: {current_id}")
            seen.add(current_id)
            current = self.get_version(current_id)
            chain.append(current)
            current_id = current.parent_version_id
        chain.reverse()
        return chain
