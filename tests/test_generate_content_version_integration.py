"""I1 — real generate seam -> canonical EvidencePack -> ContentVersion V1.

No external LLM is called: `_llm_text` is monkeypatched. Retrieval remains the real
tracked Suzhou path so this test crosses the I0/I1 boundary without faking evidence.
"""
from fastapi.testclient import TestClient

from api import main as api_main
from api.evidence_store import EvidencePackStore
from api.versioning import ContentVersionStore
from tools import story_post_gen


def _reset_shared_stores(monkeypatch):
    versions = ContentVersionStore()
    packs = EvidencePackStore()
    monkeypatch.setattr(api_main, "content_version_store", versions)
    monkeypatch.setattr(api_main, "evidence_pack_store", packs)
    return versions, packs


def _stub_post_json(_prompt):
    return (
        '{"5w":{"who":"Suzhou embroidery artisans"},'
        '"post":"Suzhou embroidery carries a living craft tradition.",'
        '"hashtags":["#SuzhouEmbroidery"]}'
    )


def test_generate_suzhou_creates_v1_bound_to_recoverable_pack(monkeypatch):
    versions, packs = _reset_shared_stores(monkeypatch)
    monkeypatch.setattr(story_post_gen, "_llm_text", _stub_post_json)
    client = TestClient(api_main.app)

    resp = client.post("/api/posts/generate", json={
        "task_id": "task-suzhou-i1",
        "theme": "苏绣",
        "genre": "post",
        "language": "English",
    })
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["ok"] is True
    data = payload["data"]

    assert data["task_id"] == "task-suzhou-i1"
    assert data["content_version_id"]
    assert data["evidence_pack_id"]
    assert "_evidence_pack" not in data

    v1 = versions.get_version(data["content_version_id"])
    assert v1.task_id == "task-suzhou-i1"
    assert v1.parent_version_id is None
    assert v1.content == data["post"]
    assert v1.evidence_pack_id == data["evidence_pack_id"]
    assert v1.claim_ids == []

    pack = packs.get(v1.evidence_pack_id)
    assert pack.evidence_pack_id == v1.evidence_pack_id
    assert pack.items
    assert any("苏绣" in item.statement or "苏州" in item.statement for item in pack.items)
    assert any(
        "ihchina.cn" in src.uri or "suzhou.gov.cn" in src.uri
        for src in pack.sources
    )


def test_generation_uses_projection_from_canonical_pack(monkeypatch):
    _reset_shared_stores(monkeypatch)
    monkeypatch.setattr(story_post_gen, "_llm_text", _stub_post_json)
    result = story_post_gen.run_story_post_generation(
        theme="苏绣", genre="post", language="English"
    )
    pack = result["_evidence_pack"]
    canonical_pairs = {
        (src["source_id"], src["uri"]) for src in pack["sources"]
    }
    source_uri_by_id = dict(canonical_pairs)
    canonical_rows = {
        (item["statement"], source_uri_by_id[item["source_id"]])
        for item in pack["items"]
    }
    legacy_rows = {
        (row["statement"], row["source"]) for row in result["evidence_used"]
    }
    assert legacy_rows == canonical_rows


def test_empty_model_output_creates_no_content_version(monkeypatch):
    versions, packs = _reset_shared_stores(monkeypatch)
    monkeypatch.setattr(story_post_gen, "_llm_text", lambda _prompt: "")
    client = TestClient(api_main.app)

    resp = client.post("/api/posts/generate", json={
        "task_id": "task-empty-i1",
        "theme": "苏绣",
        "genre": "post",
    })
    assert resp.status_code == 200
    assert resp.json()["ok"] is False
    assert versions.get_history("task-empty-i1") == []
    # Canonical pack is intentionally not persisted on a failed generation.
    assert len(packs) == 0


def test_gate_b_failure_creates_no_content_version(monkeypatch):
    versions, packs = _reset_shared_stores(monkeypatch)
    monkeypatch.setattr(
        story_post_gen,
        "retrieve_statements",
        lambda *args, **kwargs: [],
    )
    client = TestClient(api_main.app)

    resp = client.post("/api/posts/generate", json={
        "task_id": "task-no-evidence-i1",
        "theme": "definitely-no-evidence",
        "genre": "post",
    })
    assert resp.status_code == 200
    assert resp.json()["ok"] is False
    assert versions.get_history("task-no-evidence-i1") == []
    assert len(packs) == 0


def test_blank_task_id_gets_server_assigned_task(monkeypatch):
    versions, _ = _reset_shared_stores(monkeypatch)
    monkeypatch.setattr(story_post_gen, "_llm_text", _stub_post_json)
    client = TestClient(api_main.app)

    resp = client.post("/api/posts/generate", json={
        "theme": "苏绣",
        "genre": "post",
    })
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["task_id"]
    assert versions.get_version(data["content_version_id"]).task_id == data["task_id"]
