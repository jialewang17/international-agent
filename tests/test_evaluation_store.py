"""I2-B-004B: independent EvaluationResultStore tests."""

import pytest

from api.evaluation_store import (
    EvaluationResultStore,
    EvaluationStoreError,
)
from api.schemas import EvaluationResult


def make_result(
    evaluation_id="eval_1",
    status="RETURN_TO_PART1",
):
    return EvaluationResult(
        evaluation_id=evaluation_id,
        content_version_id="cv_1",
        task_id="task_1",
        part="evaluation",
        status=status,
        issues=["synthetic issue"],
        human_review="PENDING",
    )


def test_store_snapshot_and_idempotency():
    store = EvaluationResultStore()
    original = make_result()

    returned = store.put(original)
    assert returned == original
    assert returned is not original

    original.issues.append("input mutated")
    returned.issues.append("return mutated")

    persisted = store.get("eval_1")
    assert persisted.issues == ["synthetic issue"]

    persisted.issues.append("read mutated")
    assert store.get("eval_1").issues == [
        "synthetic issue"
    ]

    assert store.put(make_result()) == make_result()
    assert len(store) == 1


def test_store_collision_is_fail_closed():
    store = EvaluationResultStore()
    store.put(make_result())

    with pytest.raises(
        EvaluationStoreError,
        match="evaluation_id collision",
    ):
        store.put(
            make_result(
                status="INSUFFICIENT_CONTEXT",
            )
        )

    assert store.get("eval_1").status == "RETURN_TO_PART1"


def test_missing_and_invalid_identity():
    store = EvaluationResultStore()

    assert store.get("missing") is None

    with pytest.raises(EvaluationStoreError):
        store.get(" ")

    with pytest.raises(EvaluationStoreError):
        store.put("not a result")

    invalid = make_result(evaluation_id=" ")
    with pytest.raises(EvaluationStoreError):
        store.put(invalid)

    assert len(store) == 0


def test_no_evaluation_can_claim_approval_or_publication():
    store = EvaluationResultStore()

    for status in ("APPROVED", "PUBLISHED"):
        with pytest.raises(EvaluationStoreError):
            store.put(
                make_result(
                    evaluation_id=f"eval_{status}",
                    status=status,
                )
            )

    assert len(store) == 0
