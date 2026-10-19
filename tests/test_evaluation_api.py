"""I2-B-004B: explicit Evaluation API integration tests (offline)."""

from fastapi.testclient import TestClient

from api import main as api_main
from api.claim_store import ClaimStore
from api.evaluation_store import EvaluationResultStore
from api.evidence_store import EvidencePackStore
from api.schemas import Claim, EvidenceItem, EvidencePack, Source
from api.versioning import ContentVersionStore


PACK_ID = "ep_eval_fixture"
CLAIM_ID = "clm_eval_fixture"
TASK_ID = "task-eval-004b"


def make_pack():
    return EvidencePack(
        evidence_pack_id=PACK_ID,
        items=[
            EvidenceItem(
                evidence_id="ev_eval_fixture",
                source_id="src_eval_fixture",
                statement="Synthetic evidence statement.",
                spans=[],
            )
        ],
        sources=[
            Source(
                source_id="src_eval_fixture",
                uri="https://example.org/synthetic",
                title="Synthetic source",
                source_type="test",
            )
        ],
    )


def setup_api(
    monkeypatch,
    *,
    zero_claims=False,
    bound=False,
    include_pack=True,
    include_claim=True,
):
    versions = ContentVersionStore()
    packs = EvidencePackStore()
    claims = ClaimStore()
    evaluations = EvaluationResultStore()

    version = versions.create_initial_version(
        TASK_ID,
        "Synthetic content for evaluation.",
        evidence_pack_id=PACK_ID,
        claim_ids=[] if zero_claims else [CLAIM_ID],
    )

    if include_pack:
        packs.put(make_pack())

    if not zero_claims and include_claim:
        claims.put(
            PACK_ID,
            Claim(
                claim_id=CLAIM_ID,
                text=version.content,
                evidence_ids=(
                    ["ev_eval_fixture"]
                    if bound
                    else []
                ),
            ),
        )

    monkeypatch.setattr(
        api_main, "content_version_store", versions
    )
    monkeypatch.setattr(
        api_main, "evidence_pack_store", packs
    )
    monkeypatch.setattr(
        api_main, "claim_store", claims
    )
    monkeypatch.setattr(
        api_main,
        "evaluation_result_store",
        evaluations,
    )

    return (
        TestClient(api_main.app),
        versions,
        packs,
        claims,
        evaluations,
        version,
    )


def run(client, version):
    return client.post(
        "/api/evaluations/run",
        json={
            "content_version_id": version.content_version_id,
            "task_id": TASK_ID,
        },
    )


def test_01_unbound_claim_returns_to_part1(monkeypatch):
    client, versions, packs, claims, evaluations, version = (
        setup_api(monkeypatch)
    )

    response = run(client, version)

    assert response.status_code == 200
    body = response.json()

    assert body["ok"] is True
    data = body["data"]

    assert data["status"] == "RETURN_TO_PART1"
    assert data["return_to_part1"] is True
    assert data["human_review"] == "PENDING"
    assert data["dimensions"] == []
    assert data["overall_score"] is None

    assert any(
        "unbound claim" in issue
        for issue in data["issues"]
    )

    assert len(data["claim_traces"]) == 1
    assert data["claim_traces"][0]["status"] == "unbound"

    assert len(evaluations) == 1

    fetched = client.get(
        f"/api/evaluations/{data['evaluation_id']}"
    )
    assert fetched.status_code == 200
    assert fetched.json()["data"] == data

    assert len(versions.get_history(TASK_ID)) == 1
    assert len(packs) == 1
    assert len(claims) == 1


def test_02_zero_claims_are_blocked(monkeypatch):
    client, _, _, _, evaluations, version = setup_api(
        monkeypatch,
        zero_claims=True,
    )

    response = run(client, version)

    assert response.status_code == 200
    data = response.json()["data"]

    assert data["status"] == "RETURN_TO_PART1"
    assert data["return_to_part1"] is True
    assert data["claim_traces"] == []
    assert data["dimensions"] == []
    assert data["overall_score"] is None

    assert any(
        "no claims extracted" in issue
        for issue in data["issues"]
    )

    assert len(evaluations) == 1


def test_03_traceable_is_not_a_fabricated_quality_pass(
    monkeypatch,
):
    client, _, _, _, evaluations, version = setup_api(
        monkeypatch,
        bound=True,
    )

    response = run(client, version)

    assert response.status_code == 200
    data = response.json()["data"]

    # Part 1 only establishes reference traceability.
    # Part 3 has no real Judge, so it cannot make up D1-D6 scores.
    assert data["status"] == "INSUFFICIENT_CONTEXT"
    assert data["dimensions"] == []
    assert data["scores"] == {}
    assert data["overall_score"] is None
    assert data["human_review"] == "PENDING"

    assert data["audit"]["part1_status"] == "PASS"
    assert data["claim_traces"][0]["status"] == "traceable"

    assert any(
        "no ChinaStory judge configured" in issue
        for issue in data["issues"]
    )
    assert len(evaluations) == 1


def test_04_missing_evidence_pack_fails_closed(monkeypatch):
    client, _, _, _, evaluations, version = setup_api(
        monkeypatch,
        include_pack=False,
    )

    response = run(client, version)

    assert response.status_code == 200
    data = response.json()["data"]

    assert data["status"] == "RETURN_TO_PART1"
    assert data["return_to_part1"] is True
    assert any(
        "missing evidence pack" in issue
        for issue in data["issues"]
    )
    assert len(evaluations) == 1


def test_05_missing_claim_snapshot_is_not_ignored(monkeypatch):
    client, _, _, _, evaluations, version = setup_api(
        monkeypatch,
        include_claim=False,
    )

    response = run(client, version)

    assert response.status_code == 409
    assert len(evaluations) == 0
    assert "claim snapshots unavailable" in str(
        response.json()["detail"]
    )


def test_06_wrong_task_id_is_rejected(monkeypatch):
    client, _, _, _, evaluations, version = setup_api(
        monkeypatch,
    )

    response = client.post(
        "/api/evaluations/run",
        json={
            "content_version_id": version.content_version_id,
            "task_id": "another-task",
        },
    )

    assert response.status_code == 409
    assert len(evaluations) == 0


def test_07_unknown_version_returns_404(monkeypatch):
    client, _, _, _, evaluations, _ = setup_api(
        monkeypatch,
    )

    response = client.post(
        "/api/evaluations/run",
        json={"content_version_id": "unknown-version"},
    )

    assert response.status_code == 404
    assert len(evaluations) == 0


def test_08_unknown_evaluation_returns_404(monkeypatch):
    client, _, _, _, evaluations, _ = setup_api(
        monkeypatch,
    )

    response = client.get(
        "/api/evaluations/unknown-evaluation"
    )

    assert response.status_code == 404
    assert len(evaluations) == 0


def test_09_get_task_binding_mismatch(monkeypatch):
    client, _, _, _, evaluations, version = setup_api(
        monkeypatch,
    )

    response = run(client, version)
    assert response.status_code == 200

    evaluation_id = response.json()["data"]["evaluation_id"]

    fetched = client.get(
        f"/api/evaluations/{evaluation_id}",
        params={"task_id": "another-task"},
    )

    assert fetched.status_code == 409
    assert len(evaluations) == 1


def test_10_caller_cannot_inject_claims_or_scores(monkeypatch):
    client, _, _, _, evaluations, version = setup_api(
        monkeypatch,
    )

    response = client.post(
        "/api/evaluations/run",
        json={
            "content_version_id": version.content_version_id,
            "claims": {
                CLAIM_ID: {
                    "text": "fabricated",
                    "evidence_ids": ["ev_eval_fixture"],
                }
            },
            "scores": {"made_up_score": 5},
        },
    )

    assert response.status_code == 422
    assert len(evaluations) == 0


def test_11_repeated_evaluation_preserves_source_stores(
    monkeypatch,
):
    client, versions, packs, claims, evaluations, version = (
        setup_api(monkeypatch)
    )

    first = run(client, version)
    second = run(client, version)

    assert first.status_code == second.status_code == 200

    a = first.json()["data"]
    b = second.json()["data"]

    assert a["evaluation_id"] != b["evaluation_id"]
    assert a["content_version_id"] == b["content_version_id"]
    assert a["status"] == b["status"]

    assert len(evaluations) == 2
    assert len(versions.get_history(TASK_ID)) == 1
    assert len(packs) == 1
    assert len(claims) == 1


def test_12_empty_version_id_rejected(monkeypatch):
    client, _, _, _, evaluations, _ = setup_api(
        monkeypatch,
    )

    response = client.post(
        "/api/evaluations/run",
        json={"content_version_id": "   "},
    )

    assert response.status_code == 400
    assert len(evaluations) == 0
