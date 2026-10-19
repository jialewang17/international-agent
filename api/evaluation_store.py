"""In-memory snapshots of canonical EvaluationResult records.

I2-B-004B. No approval authority, publication, or durable database.
"""

from threading import RLock
from typing import Optional

from api.schemas import EvaluationResult

__all__ = ["EvaluationStoreError", "EvaluationResultStore"]


class EvaluationStoreError(ValueError):
    """Invalid result identity or immutable evaluation collision."""


class EvaluationResultStore:
    """Store defensive EvaluationResult snapshots by evaluation_id."""

    def __init__(self) -> None:
        self._results: dict[str, EvaluationResult] = {}
        self._lock = RLock()

    @staticmethod
    def _check_id(evaluation_id: str) -> None:
        if (
            not isinstance(evaluation_id, str)
            or not evaluation_id.strip()
        ):
            raise EvaluationStoreError(
                "evaluation_id must be a non-empty str"
            )

    def put(self, result: EvaluationResult) -> EvaluationResult:
        if not isinstance(result, EvaluationResult):
            raise EvaluationStoreError(
                "result must be api.schemas.EvaluationResult"
            )

        self._check_id(result.evaluation_id)

        if (
            not isinstance(result.content_version_id, str)
            or not result.content_version_id.strip()
        ):
            raise EvaluationStoreError(
                "content_version_id must be a non-empty str"
            )

        if not result.task_id.strip():
            raise EvaluationStoreError(
                "task_id must be a non-empty str"
            )

        if result.part != "evaluation":
            raise EvaluationStoreError(
                "only whole-pipeline EvaluationResult is accepted"
            )

        if result.status in {"APPROVED", "PUBLISHED"}:
            raise EvaluationStoreError(
                "evaluation has no approval or publishing authority"
            )

        snapshot = result.model_copy(deep=True)

        with self._lock:
            existing = self._results.get(result.evaluation_id)

            if existing is not None:
                if existing != snapshot:
                    raise EvaluationStoreError(
                        f"evaluation_id collision: {result.evaluation_id}"
                    )
                return existing.model_copy(deep=True)

            self._results[result.evaluation_id] = snapshot
            return snapshot.model_copy(deep=True)

    def get(
        self,
        evaluation_id: str,
    ) -> Optional[EvaluationResult]:
        self._check_id(evaluation_id)

        with self._lock:
            existing = self._results.get(evaluation_id)
            if existing is None:
                return None
            return existing.model_copy(deep=True)

    def __len__(self) -> int:
        with self._lock:
            return len(self._results)
