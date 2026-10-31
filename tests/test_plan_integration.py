"""P0-2 Narrative Plan generation & revision tests.

Model calls in this file use an explicitly-labelled TEST DOUBLE
(``_FakePlanModel`` / stubbed ``plan_service._default_model``): no network,
no credentials, no cost. A separate real-credential smoke is reported
manually in the delivery report (no key was configured in this environment).

Covers:
- suzhou-style evidence pack yields multiple distinct plan candidates;
- every referenced evidence id exists in the current EvidencePack;
- unknown evidence ids are dropped AND recorded as gaps (never kept);
- no usable evidence -> no fabricated plan (PLAN_CONTEXT_INVALID);
- model unavailable / call failed / bad output -> explicit typed failures;
- feedback with a working model produces a real new version;
- after feedback (failed or succeeded) Gate A cannot confirm a stale plan;
- Gate B stays NOT_EVALUATED; no new frontend gate-write surface;
- DEMO stays isolated (demo code path unchanged, zero-fetch contract intact).
"""
import json
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import api.plan_service as plan_service
import api.story_router as sr
from api.evidence_adapter import build_evidence_pack
from api.evidence_store import EvidencePackStore
from api.schemas import EvidencePack
from api.story_session import (
    DraftTaskContext, GroundDigest, JointConfirmation, NarrativePlan,
    StorySessionStore,
)
from api.workflow import WorkflowError

SUZHOU = "苏绣"


def _sample_pack() -> EvidencePack:
    return build_evidence_pack([
        {"category": "工艺", "statement": "苏绣为中国四大名绣之一，以精细雅洁著称",
         "source": "https://www.ihchina.cn/project_details/13978/", "source_type": "本地库"},
        {"category": "传承", "statement": "镇湖聚集大量绣娘，形成苏绣产业聚集地",
         "source": "https://dfzb.suzhou.gov.cn/dfzb/szdq/", "source_type": "本地库"},
        {"category": "历史", "statement": "苏绣技艺历史悠久，可追溯至两千多年前",
         "source": "https://dfzb.suzhou.gov.cn/dfzb/szdq/", "source_type": "本地库"},
    ])


def _model_output(directions: list) -> str:
    return json.dumps({"directions": directions}, ensure_ascii=False)


def _three_directions_output() -> str:
    pack = _sample_pack()
    ids = [i.evidence_id for i in pack.items]
    return _model_output([
        {
            "title": "一线千针：把「精细」讲成看得见的画面",
            "angle": "工艺技法",
            "central_message": "一针一线的极限控制力就是中国工匠精神的当代注脚",
            "sections": [
                {"title": "一根丝线剖成几十分之一", "purpose": "建立惊叹",
                 "evidence_ids": [ids[0]], "fact_gaps": ["劈丝的具体数据"]},
                {"title": "绣娘的一天", "purpose": "落到人",
                 "evidence_ids": [ids[1]], "fact_gaps": []},
            ],
            "evidence_gaps": ["缺少具体劈丝股数的量化来源"],
        },
        {
            "title": "绣架前的年轻人：一门手艺如何被接住",
            "angle": "技艺传承",
            "central_message": "老手艺正在被年轻人用新方式接住",
            "sections": [
                {"title": " Who is 接班人", "purpose": "人物切入",
                 "evidence_ids": [ids[1], ids[2]], "fact_gaps": ["具体青年传承人案例"]},
            ],
            "evidence_gaps": [],
        },
        {
            "title": "从绣片到日常：传统工艺今天怎么用",
            "angle": "当代生活",
            "central_message": "苏绣不只是展柜里的非遗，也是可穿戴的日常",
            "sections": [
                {"title": "非遗的日常面孔", "purpose": "拉近距离",
                 "evidence_ids": [ids[0]], "fact_gaps": ["当代应用实例"]},
            ],
            "evidence_gaps": [],
        },
    ])


class _FakePlanModel:
    """测试替身（TEST DOUBLE）：返回预置文本，绝不发起网络调用。"""

    def __init__(self, text: str):
        self.text = text
        self.prompts: list = []

    def invoke(self, messages):
        self.prompts.append(messages[0].content)
        return SimpleNamespace(content=self.text)


def _task() -> DraftTaskContext:
    return DraftTaskContext(topic=SUZHOU)


def _ground_and_pack():
    pack = _sample_pack()
    ground = GroundDigest(
        evidence_pack_id=pack.evidence_pack_id,
        source_ids=[s.source_id for s in pack.sources],
        evidence_ids=[i.evidence_id for i in pack.items],
    )
    return ground, pack


# ---------------------------------------------------------------------------
# service level: generation
# ---------------------------------------------------------------------------

def test_suzhou_evidence_yields_multiple_distinct_candidates():
    ground, pack = _ground_and_pack()
    fake = _FakePlanModel(_three_directions_output())
    candidates = plan_service.generate_plan_candidates(_task(), ground, pack, model=fake)
    assert len(candidates) == 3
    angles = {c.angle for c in candidates}
    assert len(angles) == 3  # mutually distinct
    valid = {i.evidence_id for i in pack.items}
    for c in candidates:
        for s in c.plan.sections:
            for eid in s.evidence_ids:
                assert eid in valid  # every reference exists in the pack
    # prompt only shows real evidence ids
    assert "ev_" in fake.prompts[0]
    assert "只输出严格 JSON" in fake.prompts[0]


def test_unknown_evidence_reference_dropped_and_recorded_as_gap():
    ground, pack = _ground_and_pack()
    payload = json.loads(_three_directions_output())
    payload["directions"][0]["sections"][0]["evidence_ids"].append("ev_forged_by_model")
    fake = _FakePlanModel(json.dumps(payload, ensure_ascii=False))
    candidates = plan_service.generate_plan_candidates(_task(), ground, pack, model=fake)
    first = candidates[0].plan
    all_ids = [eid for s in first.sections for eid in s.evidence_ids]
    assert "ev_forged_by_model" not in all_ids  # never kept
    joined = json.dumps(first.model_dump(mode="json"), ensure_ascii=False)
    assert "ev_forged_by_model" in joined  # surfaced as a real gap


def test_no_evidence_means_no_plan_not_a_fake_one():
    from api.schemas import EvidencePack
    empty = EvidencePack(evidence_pack_id="ep_empty", items=[], sources=[])
    assert not empty.items
    with pytest.raises(plan_service.PlanServiceError) as exc:
        plan_service.generate_plan_candidates(
            _task(), GroundDigest(evidence_pack_id="ep_empty"), empty,
            model=_FakePlanModel(_three_directions_output()),
        )
    assert exc.value.code == "PLAN_CONTEXT_INVALID"


def test_model_output_errors_are_explicit():
    ground, pack = _ground_and_pack()
    # not JSON
    with pytest.raises(plan_service.PlanServiceError) as exc:
        plan_service.generate_plan_candidates(
            _task(), ground, pack, model=_FakePlanModel("抱歉，我无法输出 JSON。"))
    assert exc.value.code == "MODEL_OUTPUT_INVALID"
    # wrong direction count
    payload = json.loads(_three_directions_output())
    payload["directions"] = payload["directions"][:1]
    with pytest.raises(plan_service.PlanServiceError) as exc:
        plan_service.generate_plan_candidates(
            _task(), ground, pack,
            model=_FakePlanModel(json.dumps(payload, ensure_ascii=False)))
    assert exc.value.code == "MODEL_OUTPUT_INVALID"
    # duplicated angles
    payload = json.loads(_three_directions_output())
    payload["directions"][1]["angle"] = payload["directions"][0]["angle"]
    with pytest.raises(plan_service.PlanServiceError) as exc:
        plan_service.generate_plan_candidates(
            _task(), ground, pack,
            model=_FakePlanModel(json.dumps(payload, ensure_ascii=False)))
    assert exc.value.code == "MODEL_OUTPUT_INVALID"
    # model raises mid-call (timeout etc.)
    class _Boom:
        def invoke(self, messages):
            raise TimeoutError("timed out after 90s")

    with pytest.raises(plan_service.PlanServiceError) as exc:
        plan_service.generate_plan_candidates(_task(), ground, pack, model=_Boom())
    assert exc.value.code == "MODEL_CALL_FAILED"
    assert "TimeoutError" in str(exc.value)


def test_model_unavailable_when_no_credentials(monkeypatch):
    for key in ("QWEN_APIKEY", "OPENAI_APIKEY", "DASHSCOPE_APIKEY",
                "DEEPSEEK_APIKEY", "KIMI_APIKEY", "GEMINI_APIKEY"):
        monkeypatch.delenv(key, raising=False)
    ground, pack = _ground_and_pack()
    with pytest.raises(plan_service.PlanServiceError) as exc:
        plan_service.generate_plan_candidates(_task(), ground, pack)
    assert exc.value.code == "MODEL_UNAVAILABLE"
    assert "苏绣" not in str(exc.value)  # no hardcoded plan smuggled through


# ---------------------------------------------------------------------------
# service level: revision
# ---------------------------------------------------------------------------

def test_revision_produces_new_plan_with_revalidated_evidence():
    ground, pack = _ground_and_pack()
    prior = NarrativePlan(
        title="旧方案", central_message="旧的中心信息",
        sections=[{"title": "旧章节", "evidence_ids": [
            i.evidence_id for i in pack.items][:1]}],
    )
    payload = json.loads(_three_directions_output())
    # revised plan keeps only real ids plus one forged one (must be dropped)
    payload["directions"][0]["sections"][0]["evidence_ids"].append("ev_forged_2")
    fake = _FakePlanModel(json.dumps(payload, ensure_ascii=False))
    revised = plan_service.revise_plan(
        _task(), prior, "更突出年轻传承人", ground, pack, model=fake)
    assert revised.title != prior.title  # a genuinely new plan object
    assert revised.version == 0  # real version assigned by save_plan, not here
    all_ids = [eid for s in revised.sections for eid in s.evidence_ids]
    valid = {i.evidence_id for i in pack.items}
    assert all(eid in valid for eid in all_ids)
    assert "用户修改要求" in fake.prompts[0]  # instruction reached the model


# ---------------------------------------------------------------------------
# router level
# ---------------------------------------------------------------------------

def _fresh_client(monkeypatch, model_text=None, fake_model=None):
    store = StorySessionStore()
    packs = EvidencePackStore()
    store.bind_evidence_pack_store(packs)
    monkeypatch.setattr(sr, "story_session_store", store)
    monkeypatch.setattr(sr, "_evidence_pack_store", packs)
    if fake_model is not None or model_text is not None:
        model = fake_model or _FakePlanModel(model_text)
        monkeypatch.setattr(plan_service, "_default_model", lambda: model)
    app = FastAPI()
    app.include_router(sr.router)
    return TestClient(app), store, packs


def test_router_generate_and_save_and_gates(monkeypatch):
    client, store, packs = _fresh_client(monkeypatch, model_text=_three_directions_output())
    tid = client.post("/api/story-tasks", json={"topic": SUZHOU}).json()["data"]["task"]["task_id"]

    r = client.post(f"/api/story-tasks/{tid}/plan/generate")
    assert r.status_code == 200
    data = r.json()["data"]
    assert len(data["candidates"]) == 3
    assert data["evidence_pack_id"].startswith("ep_")
    valid = {i.evidence_id for i in packs.get(data["evidence_pack_id"]).items}
    for cand in data["candidates"]:
        assert cand["plan"]["version"] == 0  # draft: no version yet
        for s in cand["plan"]["sections"]:
            assert all(eid in valid for eid in s["evidence_ids"])

    # saving the first candidate assigns the REAL version via the workflow
    chosen = data["candidates"][0]["plan"]
    r = client.post(f"/api/story-tasks/{tid}/plan", json=chosen)
    assert r.status_code == 200
    snap = r.json()["data"]
    assert snap["plan"]["version"] == 1
    assert snap["plan"]["title"] == chosen["title"]

    # Gate B untouched
    assert snap["workflow"]["evidence_status"] == "NOT_EVALUATED"
    assert "B" not in snap["workflow"]["gates"]

    # Gate A can confirm the saved plan, but Create still blocked without Gate B
    r = client.post(f"/api/story-tasks/{tid}/confirm",
                    json={"audience": "青年", "genre": "post", "language": "English"})
    assert r.status_code == 200
    r = client.post(f"/api/story-tasks/{tid}/enter-create")
    assert r.status_code == 409
    assert r.json()["detail"]["gate"] == "B"


def test_router_generate_without_model_is_explicit_503(monkeypatch):
    client, _store, _packs = _fresh_client(monkeypatch, fake_model=None, model_text=None)
    tid = client.post("/api/story-tasks", json={"topic": SUZHOU}).json()["data"]["task"]["task_id"]
    # make sure no credentials path is hit: stub the factory to fail closed
    def _no_model():
        raise plan_service.PlanServiceError("MODEL_UNAVAILABLE", "no credentials")
    monkeypatch.setattr(plan_service, "_default_model", _no_model)
    r = client.post(f"/api/story-tasks/{tid}/plan/generate")
    assert r.status_code == 503
    detail = r.json()["detail"]
    assert detail["code"] == "MODEL_UNAVAILABLE"


def test_router_feedback_success_produces_new_version(monkeypatch):
    client, store, packs = _fresh_client(monkeypatch, model_text=_three_directions_output())
    tid = client.post("/api/story-tasks", json={"topic": SUZHOU}).json()["data"]["task"]["task_id"]
    client.post(f"/api/story-tasks/{tid}/plan/generate")
    client.post(f"/api/story-tasks/{tid}/plan",
                json={"title": "v1 方案", "central_message": "m",
                      "sections": [{"title": "s1", "evidence_ids": [
                          i.evidence_id for i in packs.all_packs()[0].items][:1]}]})

    def _fake_revise(task, prior_plan, instruction, ground, pack, **kw):
        return NarrativePlan(
            title="修订版：突出年轻传承人", central_message="新的中心信息",
            sections=[{"title": "新章节", "evidence_ids": [
                i.evidence_id for i in pack.items][:2]}],
        )

    monkeypatch.setattr(sr.plan_service, "revise_plan", _fake_revise)
    r = client.post(f"/api/story-tasks/{tid}/feedback",
                    json={"instruction": "更突出年轻传承人"})
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["feedback_recorded"] is True
    assert data["plan_revision"]["status"] == "SUCCEEDED"
    # real NEW version (feedback invalidates + save re-numbers: strictly > 1)
    assert data["plan_revision"]["plan_version"] > 1
    assert data["planner_update_pending"] is False
    assert data["task"]["plan"]["version"] == data["plan_revision"]["plan_version"]
    assert data["task"]["plan"]["title"] == "修订版：突出年轻传承人"

    # the OLD plan is gone from the session; Gate A only sees the new one
    snap = client.get(f"/api/story-tasks/{tid}").json()["data"]
    assert snap["plan"]["version"] == data["plan_revision"]["plan_version"]
    # stale-plan confirmation is impossible: joint confirmation was reset
    assert snap["joint_confirmed"] is False


def test_router_feedback_failure_blocks_gate_a_on_stale_plan(monkeypatch):
    client, _store, _packs = _fresh_client(monkeypatch, model_text=_three_directions_output())
    tid = client.post("/api/story-tasks", json={"topic": SUZHOU}).json()["data"]["task"]["task_id"]
    client.post(f"/api/story-tasks/{tid}/plan/generate")
    r = client.post(f"/api/story-tasks/{tid}/plan",
                    json={"title": "v1 方案", "central_message": "m",
                          "sections": [{"title": "s1", "evidence_ids": []}]})
    assert r.status_code == 200

    def _unavailable(*a, **kw):
        raise plan_service.PlanServiceError("MODEL_UNAVAILABLE", "no model")

    monkeypatch.setattr(sr.plan_service, "revise_plan", _unavailable)
    r = client.post(f"/api/story-tasks/{tid}/feedback", json={"instruction": "改一下"})
    data = r.json()["data"]
    assert data["plan_revision"]["status"] == "FAILED"
    assert data["planner_update_pending"] is True

    # Gate A must NOT confirm the invalidated plan
    r = client.post(f"/api/story-tasks/{tid}/confirm",
                    json={"audience": "青年", "genre": "post", "language": "English"})
    assert r.status_code == 409
    assert r.json()["detail"]["gate"] == "A"
    # and Create stays blocked
    r = client.post(f"/api/story-tasks/{tid}/enter-create")
    assert r.status_code == 409


# ---------------------------------------------------------------------------
# invariants: gates, demo isolation
# ---------------------------------------------------------------------------

def test_gate_b_untouched_and_no_frontend_gate_write(monkeypatch):
    client, _store, _packs = _fresh_client(monkeypatch, model_text=_three_directions_output())
    tid = client.post("/api/story-tasks", json={"topic": SUZHOU}).json()["data"]["task"]["task_id"]
    client.post(f"/api/story-tasks/{tid}/plan/generate")
    client.post(f"/api/story-tasks/{tid}/plan",
                json={"title": "草案", "central_message": "m", "sections": []})
    r = client.post(f"/api/workflow/{tid}/gate",
                    json={"gate": "B", "decision": "passed", "reason": "forged",
                          "decided_by": "system"})
    # /api/workflow gate belongs to api.main; on the bare story router it is 404,
    # which itself proves the story router exposes NO gate-write endpoint.
    assert r.status_code == 404

    from pathlib import Path
    js = (Path(__file__).resolve().parents[1] / "frontend/js/workbench").joinpath("story-api.js").read_text(encoding="utf-8")
    assert "evidence_status" not in js and "/gate" not in js  # no gate-write surface


def test_demo_path_untouched_by_p02_frontend_changes():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1] / "frontend"
    js = (root / "js/workbench/workbench.js").read_text(encoding="utf-8")
    # generate is LIVE-only and returns early in demo mode
    assert 'if (APP.mode === "demo") { U.toast("演示模式使用本地方向，无需生成", "bad"); return; }' in js
    # candidates are only read from APP.live, never from the demo adapter
    assert "APP.live.candidates" in js
    demo = (root / "js/workbench/demo-adapter.js").read_text(encoding="utf-8")
    assert "candidates" not in demo and "generatePlan" not in demo
