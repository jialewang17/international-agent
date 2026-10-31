"""P0-1 Ground integration tests — real local retrieval, no LLM, no keys.

Covers (P0-1 authorization §3):
1. Su embroidery real retrieval returns a legal EvidencePack + source cards.
2. Same inputs -> deterministic evidence_pack_id.
3. No retrieval results -> task stays GROUND with truthful gaps, no fake pack.
4. Forged evidence_pack_id is rejected (attach_ground verifies existence).
5. Gate B stays NOT_EVALUATED / untouched; Create gates still hold (409).
6. Ground runs without any model API keys.
7. User materials keep the 用户上传 / 本地库 source-type distinction.
8. record_ground_failure is GROUND-only and never advances the stage.
9. Six genres (v6.1) still recognized by the joint confirmation.
"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import api.story_router as sr
from api.evidence_adapter import build_evidence_pack
from api.evidence_store import EvidencePackStore
from api.ground_service import run_ground
from api.story_session import (
    GroundDigest, JointConfirmation, NarrativePlan, StorySessionStore,
)
from api.workflow import WorkflowError

SUZHOU = "苏绣"
NOISE_TOPIC = "zxq豁然开朗镭射qqq"  # deliberately off-KB gibberish


def _fresh_client(monkeypatch):
    """Router-level isolation: fresh stores bound to each other."""
    service = StorySessionStore()
    packs = EvidencePackStore()
    service.bind_evidence_pack_store(packs)
    monkeypatch.setattr(sr, "story_session_store", service)
    monkeypatch.setattr(sr, "_evidence_pack_store", packs)
    app = FastAPI()
    app.include_router(sr.router)
    return TestClient(app), service, packs


# ---------------------------------------------------------------------------
# 1. Su embroidery real retrieval
# ---------------------------------------------------------------------------

def test_suzhou_ground_returns_real_pack_and_sources(monkeypatch):
    client, _service, packs = _fresh_client(monkeypatch)
    r = client.post("/api/story-tasks", json={"topic": SUZHOU, "user_materials": ""})
    assert r.status_code == 200
    data = r.json()["data"]

    assert data["workflow"]["stage"] == "PLAN"  # Ground completed -> PLAN
    ground = data["ground"]
    assert ground is not None
    pack_id = ground["evidence_pack_id"]
    assert pack_id and pack_id.startswith("ep_")

    # The pack actually exists in the shared canonical store.
    stored = packs.get(pack_id)
    assert stored.evidence_pack_id == pack_id
    assert stored.items and stored.sources

    # GroundDigest projections match the canonical pack.
    assert ground["source_ids"] == [s["source_id"] for s in ground["sources"]]
    assert sorted(ground["evidence_ids"]) == sorted(
        i["evidence_id"] for i in stored.model_dump()["items"]
    )
    assert sorted(ground["source_ids"]) == sorted(
        s["source_id"] for s in stored.model_dump()["sources"]
    )

    # Real source cards: URLs verbatim, local-KB type preserved, spans honest.
    assert ground["sources"], "frontend needs sources for source cards"
    for src in ground["sources"]:
        assert src["uri"].startswith("https://")
        assert src["source_type"] == "本地库"
    assert all(i["spans"] == [] for i in stored.model_dump()["items"])

    # Security invariants: nothing is evaluated, no gate is touched.
    assert data["workflow"]["evidence_status"] == "NOT_EVALUATED"
    assert data["workflow"]["gates"] == {}
    assert "NOT_EVALUATED" in ground["retrieval_note"]


# ---------------------------------------------------------------------------
# 2. Determinism
# ---------------------------------------------------------------------------

def test_ground_pack_id_is_deterministic():
    a = run_ground(SUZHOU, "")
    b = run_ground(SUZHOU, "")
    assert a.succeeded and b.succeeded
    assert a.digest.evidence_pack_id == b.digest.evidence_pack_id
    assert a.digest.retrieval_note == b.digest.retrieval_note


def test_repeated_api_creates_share_one_pack_id(monkeypatch):
    client, _service, _packs = _fresh_client(monkeypatch)
    id1 = client.post("/api/story-tasks", json={"topic": SUZHOU}).json()["data"]["ground"]["evidence_pack_id"]
    id2 = client.post("/api/story-tasks", json={"topic": SUZHOU}).json()["data"]["ground"]["evidence_pack_id"]
    assert id1 == id2 and id1.startswith("ep_")


# ---------------------------------------------------------------------------
# 3. Empty retrieval: stay GROUND, truthful gaps, no fake pack
# ---------------------------------------------------------------------------

def test_no_results_keeps_ground_with_real_gaps(monkeypatch):
    client, service, packs = _fresh_client(monkeypatch)
    before = len(packs)
    r = client.post("/api/story-tasks", json={"topic": NOISE_TOPIC, "user_materials": ""})
    assert r.status_code == 200
    data = r.json()["data"]

    assert data["workflow"]["stage"] == "GROUND"      # NOT advanced
    assert data["ground"] is None                      # no fake digest
    assert data["ground_gaps"], "must report real gaps"
    assert len(packs) == before                        # nothing stored

    # Plan stays blocked until a real Ground summary exists.
    task_id = data["task"]["task_id"]
    plan = client.post("/api/story-tasks/" + task_id + "/plan", json={"title": "草案"})
    assert plan.status_code == 409
    assert "Ground" in plan.json()["detail"]["reason"]


def test_record_ground_failure_is_ground_only_and_never_advances():
    service = StorySessionStore()
    t = service.start(SUZHOU).task.task_id
    service.record_ground_failure(t, ["真实缺口"], "note")
    assert service.machine.get(t).stage == "GROUND"
    snap = service.snapshot(t)
    assert snap["ground"] is None and snap["ground_gaps"] == ["真实缺口"]
    # once the stage has moved on (no failure possible there), recording is refused
    service2 = StorySessionStore(evidence_pack_store=EvidencePackStore())
    t2 = service2.start(SUZHOU).task.task_id
    service2.machine.advance(t2, "PLAN")
    with pytest.raises(WorkflowError):
        service2.record_ground_failure(t2, ["x"])


# ---------------------------------------------------------------------------
# 4. Forged EvidencePack ids are rejected
# ---------------------------------------------------------------------------

def test_fake_evidence_pack_id_rejected():
    service = StorySessionStore(evidence_pack_store=EvidencePackStore())
    t = service.start(SUZHOU).task.task_id
    with pytest.raises(WorkflowError) as exc:
        service.attach_ground(t, GroundDigest(evidence_pack_id="ep_does_not_exist"))
    assert exc.value.gate == "B"
    assert service.machine.get(t).stage == "GROUND"


def test_attach_ground_without_pack_id_rejected():
    service = StorySessionStore(evidence_pack_store=EvidencePackStore())
    t = service.start(SUZHOU).task.task_id
    with pytest.raises(WorkflowError):
        service.attach_ground(t, GroundDigest(evidence_gaps=["缺少来源"]))


def test_attach_ground_without_bound_store_fails_closed():
    service = StorySessionStore()  # no store bound
    t = service.start(SUZHOU).task.task_id
    with pytest.raises(WorkflowError):
        service.attach_ground(t, GroundDigest(evidence_pack_id="ep_anything"))


def test_attach_ground_accepts_real_existing_pack():
    packs = EvidencePackStore()
    pack = build_evidence_pack([{
        "category": "工艺", "statement": "苏绣为中国四大名绣之一",
        "source": "https://www.ihchina.cn/project_details/13978/",
        "source_type": "本地库",
    }])
    packs.put(pack)
    service = StorySessionStore(evidence_pack_store=packs)
    t = service.start(SUZHOU).task.task_id
    service.attach_ground(t, GroundDigest(
        evidence_pack_id=pack.evidence_pack_id,
        source_ids=[s.source_id for s in pack.sources],
        evidence_ids=[i.evidence_id for i in pack.items],
    ))
    assert service.machine.get(t).stage == "PLAN"


# ---------------------------------------------------------------------------
# 5. Gate invariants after real Ground
# ---------------------------------------------------------------------------

def test_gate_b_untouched_and_create_still_gated(monkeypatch):
    client, service, _packs = _fresh_client(monkeypatch)
    data = client.post("/api/story-tasks", json={"topic": SUZHOU}).json()["data"]
    task_id = data["task"]["task_id"]

    assert data["workflow"]["evidence_status"] == "NOT_EVALUATED"
    assert "B" not in data["workflow"]["gates"]

    # Without Gate A joint confirmation, Create is refused (409, gate A).
    r = client.post("/api/story-tasks/" + task_id + "/enter-create")
    assert r.status_code == 409
    assert r.json()["detail"]["gate"] == "A"

    # With Gate A confirmed but no trusted Gate B, Create is still refused.
    client.post("/api/story-tasks/" + task_id + "/plan",
                json={"title": "草案", "sections": []})
    client.post("/api/story-tasks/" + task_id + "/confirm",
                json={"audience": "青年", "genre": "post", "language": "English"})
    r = client.post("/api/story-tasks/" + task_id + "/enter-create")
    assert r.status_code == 409
    assert r.json()["detail"]["gate"] == "B"
    snap = client.get("/api/story-tasks/" + task_id).json()["data"]
    assert snap["workflow"]["evidence_status"] == "NOT_EVALUATED"


# ---------------------------------------------------------------------------
# 6. No API keys required
# ---------------------------------------------------------------------------

def test_ground_runs_without_model_keys(monkeypatch):
    for key in ("QWEN_APIKEY", "OPENAI_APIKEY", "DASHSCOPE_API_KEY", "TOKEN_PLAN_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    outcome = run_ground(SUZHOU, "")
    assert outcome.succeeded
    assert outcome.pack.evidence_pack_id.startswith("ep_")


# ---------------------------------------------------------------------------
# 7. Source-type distinction survives the merge
# ---------------------------------------------------------------------------

def test_user_materials_keep_source_type_distinction():
    outcome = run_ground(SUZHOU, "苏绣是苏州地区的刺绣工艺，以精细雅洁著称。\n\n镇湖刺绣从业人员众多。")
    assert outcome.succeeded
    types = {s.source_type for s in outcome.pack.sources}
    assert "用户上传" in types
    assert "本地库" in types


# ---------------------------------------------------------------------------
# 9. v6.1 six genres still recognized
# ---------------------------------------------------------------------------

def test_six_genres_still_recognized():
    from api.story_session import GENRES
    assert GENRES == frozenset({"post", "news", "feature", "indepth", "script", "faq"})
    service = StorySessionStore(evidence_pack_store=EvidencePackStore())
    pack = build_evidence_pack([{
        "category": "工艺", "statement": "苏绣为中国四大名绣之一",
        "source": "https://www.ihchina.cn/project_details/13978/",
        "source_type": "本地库",
    }])
    service.evidence_pack_store.put(pack)
    for genre in ("indepth", "faq"):
        t = service.start(SUZHOU).task.task_id
        service.attach_ground(t, GroundDigest(
            evidence_pack_id=pack.evidence_pack_id,
            source_ids=[s.source_id for s in pack.sources],
            evidence_ids=[i.evidence_id for i in pack.items],
        ))
        service.save_plan(t, NarrativePlan(title="方案"))
        service.confirm(t, JointConfirmation(
            audience="青年", genre=genre, language="English"))
        snap = service.snapshot(t)
        assert snap["task"]["genre"] == genre
        assert snap["workflow"]["gates"]["A"]["decision"] == "approved"
