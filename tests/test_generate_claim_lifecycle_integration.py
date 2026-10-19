"""I2-B-003 generated Claim lifecycle integration checks (offline)."""

from copy import deepcopy

from fastapi.testclient import TestClient

from api import main as api_main
from api.claim_extraction import DeterministicClaimExtractor
from api.claim_store import ClaimStore, ClaimStoreError
from api.evidence_store import EvidencePackStore
from api.versioning import ContentVersionStore
from tools import story_post_gen


PACK_ID = "ep_i2b003_fixture"

PACK = {
    "evidence_pack_id": PACK_ID,
    "items": [
        {
            "evidence_id": "ev_i2b003_fixture",
            "source_id": "src_i2b003_fixture",
            "statement": "苏绣是中国传统手工艺。",
            "category": "culture",
            "spans": [],
        }
    ],
    "sources": [
        {
            "source_id": "src_i2b003_fixture",
            "uri": "https://example.org/synthetic-fixture",
            "title": "Synthetic test source",
            "source_type": "test",
        }
    ],
    "status": "ready",
}


def _setup(
    monkeypatch,
    content="Suzhou is a traditional craft. It has a history.",
):
    versions = ContentVersionStore()
    packs = EvidencePackStore()
    claims = ClaimStore()
    holder = {"content": content}

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
        "claim_extractor",
        DeterministicClaimExtractor(),
    )

    def generate(**_kwargs):
        return {
            "post": holder["content"],
            "_evidence_pack": deepcopy(PACK),
            "hashtags": ["#SuzhouEmbroidery"],
        }

    monkeypatch.setattr(
        story_post_gen,
        "run_story_post_generation",
        generate,
    )

    return TestClient(api_main.app), versions, packs, claims, holder


def _request(client, task_id):
    return client.post(
        "/api/posts/generate",
        json={
            "task_id": task_id,
            "theme": "苏绣",
            "genre": "post",
        },
    )


def test_success_claim_ids_resolve_to_snapshots(monkeypatch):
    client, versions, packs, claims, holder = _setup(monkeypatch)
    response = _request(client, "task-003-success")

    assert response.status_code == 200
    data = response.json()["data"]
    assert response.json()["ok"] is True
    assert data["post"] == holder["content"]
    assert "_evidence_pack" not in data

    v1 = versions.get_version(data["content_version_id"])

    assert v1.content == data["post"]
    assert v1.evidence_pack_id == PACK_ID
    assert data["claim_ids"] == v1.claim_ids
    assert len(v1.claim_ids) == 2

    expected = DeterministicClaimExtractor().extract(v1.content)

    assert v1.claim_ids == [
        claim.claim_id for claim in expected
    ]

    actual = claims.get_many(PACK_ID, v1.claim_ids)

    assert actual == expected
    assert all(claim.evidence_ids == [] for claim in actual)
    assert len(packs) == 1


def test_repeated_generate_same_pack_is_idempotent(monkeypatch):
    client, versions, packs, claims, _holder = _setup(monkeypatch)

    first = _request(client, "task-003-a")
    second = _request(client, "task-003-b")

    assert first.status_code == second.status_code == 200

    one = first.json()["data"]
    two = second.json()["data"]

    assert one["content_version_id"] != two["content_version_id"]
    assert one["claim_ids"] == two["claim_ids"]

    assert len(versions.get_history("task-003-a")) == 1
    assert len(versions.get_history("task-003-b")) == 1
    assert len(packs) == 1
    assert len(claims) == 2


def test_same_pack_other_content_adds_without_overwrite(monkeypatch):
    client, versions, _packs, claims, holder = _setup(
        monkeypatch,
        "First statement.",
    )

    first = _request(client, "task-003-first")

    holder["content"] = "A different statement."

    second = _request(client, "task-003-second")

    assert first.status_code == second.status_code == 200

    c1 = first.json()["data"]["claim_ids"][0]
    c2 = second.json()["data"]["claim_ids"][0]

    assert c1 != c2
    assert claims.get(PACK_ID, c1).text == "First statement."
    assert claims.get(PACK_ID, c2).text == "A different statement."
    assert len(claims) == 2
    assert len(versions.get_history("task-003-first")) == 1


def test_generation_error_does_not_persist(monkeypatch):
    client, versions, packs, claims, _ = _setup(monkeypatch)

    monkeypatch.setattr(
        story_post_gen,
        "run_story_post_generation",
        lambda **_kw: {
            "error": "blocked",
            "_evidence_pack": deepcopy(PACK),
            "post": "Bad post.",
        },
    )

    resp = _request(client, "task-003-blocked")

    assert resp.status_code == 200
    assert resp.json()["ok"] is False
    assert "_evidence_pack" not in resp.json()["data"]
    assert versions.get_history("task-003-blocked") == []
    assert len(packs) == len(claims) == 0


def test_blank_content_does_not_persist(monkeypatch):
    client, versions, packs, claims, holder = _setup(monkeypatch)

    holder["content"] = "   "

    resp = _request(client, "task-003-blank")

    assert resp.status_code == 200
    assert resp.json()["ok"] is False
    assert versions.get_history("task-003-blank") == []
    assert len(packs) == len(claims) == 0


def test_missing_pack_fails_before_writes(monkeypatch):
    client, versions, packs, claims, _ = _setup(monkeypatch)

    monkeypatch.setattr(
        story_post_gen,
        "run_story_post_generation",
        lambda **_kw: {
            "post": "One statement.",
        },
    )

    resp = _request(client, "task-003-missing-pack")

    assert resp.status_code == 500
    assert versions.get_history("task-003-missing-pack") == []
    assert len(packs) == len(claims) == 0


def test_extractor_failure_before_writes(monkeypatch):
    client, versions, packs, claims, _ = _setup(monkeypatch)

    class RaisingExtractor:
        def extract(self, _content):
            raise RuntimeError("injected extractor failure")

    monkeypatch.setattr(
        api_main,
        "claim_extractor",
        RaisingExtractor(),
    )

    resp = _request(client, "task-003-extract-fail")

    assert resp.status_code == 500
    assert versions.get_history("task-003-extract-fail") == []
    assert len(packs) == len(claims) == 0


def test_preflight_collision_fails_before_pack_persist(monkeypatch):
    client, versions, packs, claims, holder = _setup(
        monkeypatch,
        "First statement.",
    )

    extracted = DeterministicClaimExtractor().extract(
        holder["content"]
    )[0]

    conflicting = extracted.model_copy(deep=True)
    conflicting.evidence_ids = ["ev_i2b003_fixture"]

    claims.put(PACK_ID, conflicting)

    resp = _request(client, "task-003-conflict")

    assert resp.status_code == 500
    assert versions.get_history("task-003-conflict") == []
    assert len(packs) == 0
    assert len(claims) == 1
    assert claims.get(PACK_ID, extracted.claim_id) == conflicting


def test_zero_candidates_remains_draft_not_evaluated(monkeypatch):
    client, versions, packs, claims, holder = _setup(
        monkeypatch,
        "#Suzhou #Embroidery",
    )

    resp = _request(client, "task-003-zero")

    assert resp.status_code == 200

    # Successful generation is NOT an Evaluation PASS.
    assert resp.json()["ok"] is True

    data = resp.json()["data"]
    version = versions.get_version(data["content_version_id"])

    assert version.content == holder["content"]
    assert version.status == "Draft"
    assert version.claim_ids == []
    assert data["claim_ids"] == []
    assert len(packs) == 1
    assert len(claims) == 0


def test_claim_write_failure_has_no_version_but_may_orphan_pack(
    monkeypatch,
):
    client, versions, packs, claims, _ = _setup(monkeypatch)

    def fail_write(_pack_id, _claims):
        raise ClaimStoreError("injected claim write failure")

    monkeypatch.setattr(claims, "put_many", fail_write)

    resp = _request(client, "task-003-store-fail")

    assert resp.status_code == 500
    assert versions.get_history("task-003-store-fail") == []
    assert len(claims) == 0

    # Known limitation: the independent stores have no transaction.
    assert len(packs) == 1


def test_version_write_failure_has_no_version_but_may_orphan_data(
    monkeypatch,
):
    client, versions, packs, claims, _ = _setup(monkeypatch)

    def fail_version(*_args, **_kwargs):
        raise RuntimeError("injected version write failure")

    monkeypatch.setattr(
        versions,
        "create_initial_version",
        fail_version,
    )

    resp = _request(client, "task-003-version-fail")

    assert resp.status_code == 500
    assert versions.get_history("task-003-version-fail") == []

    # Known limitation: earlier writes cannot be rolled back here.
    assert len(claims) == 2
    assert len(packs) == 1


def test_empty_pack_id_fails_before_store_writes(monkeypatch):
    client, versions, packs, claims, _ = _setup(monkeypatch)

    def generate(**_kwargs):
        invalid = deepcopy(PACK)
        invalid["evidence_pack_id"] = ""
        return {
            "post": "One statement.",
            "_evidence_pack": invalid,
        }

    monkeypatch.setattr(
        story_post_gen,
        "run_story_post_generation",
        generate,
    )

    resp = _request(client, "task-003-bad-pack-id")

    assert resp.status_code == 500
    assert versions.get_history("task-003-bad-pack-id") == []
    assert len(packs) == len(claims) == 0
