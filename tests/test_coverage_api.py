"""I2-C-001B-P1: canonical read-only Coverage API integration tests."""

from hashlib import sha256

import pytest
from fastapi.testclient import TestClient

from api import main as api_main
from api.claim_extraction import DeterministicClaimExtractor
from api.claim_store import ClaimStore
from api.evidence_store import EvidencePackStore
from api.schemas import Claim, EvidenceItem, EvidencePack, Source
from api.versioning import ContentVersionStore


PACK_ID = "ep_coverage_fixture"
TASK_ID = "task-coverage-fixture"


def make_pack(pack_id=PACK_ID):
    return EvidencePack(
        evidence_pack_id=pack_id,
        items=[
            EvidenceItem(
                evidence_id="ev_coverage_fixture",
                source_id="src_coverage_fixture",
                statement="Synthetic evidence statement.",
                spans=[],
            )
        ],
        sources=[
            Source(
                source_id="src_coverage_fixture",
                title="Synthetic coverage source",
                uri="https://example.org/synthetic-coverage",
                source_type="test",
            )
        ],
    )


@pytest.fixture
def ctx(monkeypatch):
    versions = ContentVersionStore()
    packs = EvidencePackStore()
    claims = ClaimStore()

    packs.put(make_pack())

    monkeypatch.setattr(
        api_main,
        "content_version_store",
        versions,
    )
    monkeypatch.setattr(
        api_main,
        "evidence_pack_store",
        packs,
    )
    monkeypatch.setattr(
        api_main,
        "claim_store",
        claims,
    )

    return {
        "client": TestClient(api_main.app),
        "versions": versions,
        "packs": packs,
        "claims": claims,
    }


def add_version(
    ctx,
    body,
    *,
    task_id=TASK_ID,
    pack_id=PACK_ID,
):
    extracted = DeterministicClaimExtractor().extract(body)

    version = ctx["versions"].create_initial_version(
        task_id,
        body,
        evidence_pack_id=pack_id,
        claim_ids=[c.claim_id for c in extracted],
    )

    ctx["claims"].put_many(
        pack_id,
        extracted,
    )

    return version, extracted


def request(ctx, version, **extras):
    payload = {
        "content_version_id": version.content_version_id,
        "task_id": version.task_id,
    }

    payload.update(extras)

    return ctx["client"].post(
        "/api/coverage/inspect",
        json=payload,
    )


def test_01_repeated_claim_has_two_positions_one_identity(ctx):
    version, claims = add_version(
        ctx,
        "Suzhou is a craft. Suzhou is a craft.",
    )

    response = request(ctx, version)

    assert response.status_code == 200
    data = response.json()["data"]

    assert data["coverage_review_status"] == "NOT_EVALUATED"
    assert data["review_required"] is True

    index = data["index"]

    assert len(claims) == 1
    assert len(index["unique_claim_ids"]) == 1
    assert len(index["occurrences"]) == 2

    assert (
        index["occurrences"][0]["claim_id"]
        == index["occurrences"][1]["claim_id"]
    )

    assert (
        index["occurrences"][0]["start"]
        != index["occurrences"][1]["start"]
    )

    assert index["semantic_support_status"] == "NOT_EVALUATED"
    assert index["claim_recall_status"] == "NOT_EVALUATED"


def test_02_compound_fact_risk_remains_unresolved(ctx):
    body = (
        "The project began in 2020, "
        "and revenue reached 100 million in 2024."
    )

    version, _ = add_version(ctx, body)
    response = request(ctx, version)

    assert response.status_code == 200

    data = response.json()["data"]
    segment = data["index"]["segments"][0]

    assert segment["status"] == "UNCERTAIN_REVIEW_REQUIRED"

    assert (
        "COMPOUND_CLAUSE_POSSIBLE"
        in segment["atomic_risks"]
    )

    assert (
        "MULTIPLE_NUMERIC_FACTS_POSSIBLE"
        in segment["atomic_risks"]
    )

    assert data["review_required"] is True


def test_03_zero_claim_is_not_coverage_pass(ctx):
    version, claims = add_version(
        ctx,
        "#Suzhou\n😀",
    )

    assert claims == []

    response = request(ctx, version)

    assert response.status_code == 200

    data = response.json()["data"]

    assert data["coverage_review_status"] == "NOT_EVALUATED"
    assert data["review_required"] is True

    assert data["index"]["unique_claim_ids"] == []
    assert data["index"]["claim_recall_status"] == "NOT_EVALUATED"

    assert all(
        s["status"] == "UNCERTAIN_REVIEW_REQUIRED"
        for s in data["index"]["segments"]
    )


def test_04_unknown_version_returns_404(ctx):
    response = ctx["client"].post(
        "/api/coverage/inspect",
        json={"content_version_id": "unknown-version"},
    )

    assert response.status_code == 404


def test_05_blank_version_id_returns_400(ctx):
    response = ctx["client"].post(
        "/api/coverage/inspect",
        json={"content_version_id": "   "},
    )

    assert response.status_code == 400


def test_06_wrong_task_id_is_rejected(ctx):
    version, _ = add_version(ctx, "A claim.")

    response = request(
        ctx,
        version,
        task_id="another-task",
    )

    assert response.status_code == 409


def test_07_missing_pack_id_is_rejected(ctx):
    version = ctx["versions"].create_initial_version(
        TASK_ID,
        "A claim.",
        evidence_pack_id=None,
        claim_ids=[],
    )

    response = request(ctx, version)

    assert response.status_code == 409
    assert "evidence_pack_id" in response.text


def test_08_missing_pack_snapshot_is_rejected(ctx):
    version = ctx["versions"].create_initial_version(
        TASK_ID,
        "A claim.",
        evidence_pack_id="ep_missing",
        claim_ids=[],
    )

    response = request(ctx, version)

    assert response.status_code == 409


def test_09_missing_claim_snapshot_is_rejected(ctx):
    version = ctx["versions"].create_initial_version(
        TASK_ID,
        "A claim.",
        evidence_pack_id=PACK_ID,
        claim_ids=["clm_missing"],
    )

    response = request(ctx, version)

    assert response.status_code == 409


def test_10_other_pack_claim_cannot_be_reused(ctx):
    extracted = DeterministicClaimExtractor().extract(
        "A claim."
    )

    ctx["claims"].put_many(
        "ep_other",
        extracted,
    )

    version = ctx["versions"].create_initial_version(
        TASK_ID,
        "A claim.",
        evidence_pack_id=PACK_ID,
        claim_ids=[extracted[0].claim_id],
    )

    response = request(ctx, version)

    assert response.status_code == 409


def test_11_forged_claim_id_is_rejected(ctx):
    forged = Claim(
        claim_id="clm_forged",
        text="A claim.",
        evidence_ids=[],
    )

    ctx["claims"].put(
        PACK_ID,
        forged,
    )

    version = ctx["versions"].create_initial_version(
        TASK_ID,
        "A claim.",
        evidence_pack_id=PACK_ID,
        claim_ids=["clm_forged"],
    )

    response = request(ctx, version)

    assert response.status_code == 409
    assert "fingerprint" in response.text


def test_12_client_cannot_inject_claim_or_audit_status(ctx):
    version, _ = add_version(ctx, "A claim.")

    response = request(
        ctx,
        version,
        claims=[
            {
                "claim_id": "clm_fake",
                "text": "Fabricated claim.",
            }
        ],
        evidence_pack_id="ep_other",
        coverage_status="PASS",
    )

    assert response.status_code == 422


def test_13_stale_digest_is_rejected_after_content_change(ctx):
    version, _ = add_version(ctx, "A claim.")

    first = request(ctx, version)

    assert first.status_code == 200

    old_hash = first.json()["data"]["index"][
        "content_sha256"
    ]

    version.content = "Changed content."

    stale = request(
        ctx,
        version,
        expected_content_sha256=old_hash,
    )

    assert stale.status_code == 409
    assert "digest mismatch" in stale.text

    # Without an expected digest, a fresh view may be computed.
    # It must NOT silently reuse the old occurrence positions.
    fresh = request(ctx, version)

    assert fresh.status_code == 200

    new_index = fresh.json()["data"]["index"]

    assert new_index["content_sha256"] != old_hash
    assert new_index["unlocated_claim_ids"] == list(
        version.claim_ids
    )
    assert fresh.json()["data"]["review_required"] is True


def test_14_mutation_during_inspection_is_rejected(
    ctx,
    monkeypatch,
):
    version, _ = add_version(ctx, "A claim.")

    versions = ctx["versions"]
    original_get = versions.get_version
    calls = {"count": 0}

    def mutating_get(version_id):
        calls["count"] += 1
        live = original_get(version_id)

        if calls["count"] == 2:
            live.content = "Changed during inspection."

        return live

    monkeypatch.setattr(
        versions,
        "get_version",
        mutating_get,
    )

    response = request(ctx, version)

    assert response.status_code == 409
    assert "changed during Coverage inspection" in response.text


def test_15_same_pack_different_versions_get_separate_indexes(ctx):
    a, _ = add_version(
        ctx,
        "A claim.",
        task_id="task-a",
    )

    b, _ = add_version(
        ctx,
        "A heading. A claim.",
        task_id="task-b",
    )

    ra = request(ctx, a)
    rb = request(ctx, b)

    assert ra.status_code == rb.status_code == 200

    ia = ra.json()["data"]["index"]
    ib = rb.json()["data"]["index"]

    assert ia["evidence_pack_id"] == ib["evidence_pack_id"]

    assert ia["content_version_id"] != ib["content_version_id"]
    assert ia["content_sha256"] != ib["content_sha256"]

    shared_id = DeterministicClaimExtractor().extract(
        "A claim."
    )[0].claim_id

    positions_a = [
        o["start"]
        for o in ia["occurrences"]
        if o["claim_id"] == shared_id
    ]

    positions_b = [
        o["start"]
        for o in ib["occurrences"]
        if o["claim_id"] == shared_id
    ]

    assert positions_a == [0]
    assert len(positions_b) == 1
    assert positions_b[0] > 0


def test_16_repeated_inspection_is_deterministic_and_read_only(ctx):
    version, _ = add_version(ctx, "A claim.")

    packs_before = len(ctx["packs"])
    claims_before = len(ctx["claims"])
    history_before = len(
        ctx["versions"].get_history(TASK_ID)
    )
    evaluations_before = len(
        api_main.evaluation_result_store
    )

    first = request(ctx, version)
    second = request(ctx, version)

    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()

    assert len(ctx["packs"]) == packs_before
    assert len(ctx["claims"]) == claims_before
    assert (
        len(ctx["versions"].get_history(TASK_ID))
        == history_before
    )
    assert (
        len(api_main.evaluation_result_store)
        == evaluations_before
    )
