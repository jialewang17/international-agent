"""Run in repository root: pytest tests/test_story_workflow_v1.py -q"""
import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI

from api.schemas import GateDecision
from api.workflow import WorkflowError, WorkflowStateMachine
from api.story_session import (
    StorySessionStore, GroundDigest, NarrativePlan, StorySection,
    JointConfirmation, UserPlanFeedback,
)


def new_service():
    return StorySessionStore(state_machine=WorkflowStateMachine())


def basic(service):
    s = service.start("苏绣", "已提交资料")
    tid = s.task.task_id
    assert service.machine.get(tid).stage == "GROUND"
    service.attach_ground(tid, GroundDigest(
        evidence_pack_id="EP-1", source_ids=["S1"], evidence_ids=["E1"],
        evidence_gaps=["需要更多人物证据"],
    ))
    assert service.machine.get(tid).stage == "PLAN"
    service.save_plan(tid, NarrativePlan(
        title="传承与年轻人", selected_angles=["传承人物"],
        sections=[StorySection(title="传承人物", fact_gaps=["人物经历"])]
    ))
    return tid


def test_plan_entry_needs_no_user_gate_or_b():
    s = new_service()
    tid = basic(s)
    state = s.machine.get(tid)
    assert state.stage == "PLAN"
    assert state.gates == {}


def test_one_joint_confirmation_and_persisted_fields():
    s = new_service()
    tid = basic(s)
    s.confirm(tid, JointConfirmation(audience="美国青年", genre="feature", language="English"))
    snap = s.snapshot(tid)
    assert snap["joint_confirmed"]
    assert snap["task"]["genre"] == "feature"
    assert snap["workflow"]["gates"]["A"]["decided_by"] == "user"
    with pytest.raises(WorkflowError):
        s.confirm(tid, JointConfirmation(audience="美国青年", genre="feature", language="English"))


def test_not_sufficient_denies_create_even_after_confirmation():
    s = new_service()
    tid = basic(s)
    s.confirm(tid, JointConfirmation(audience="美国青年", genre="feature", language="English"))
    with pytest.raises(WorkflowError) as exc:
        s.enter_create(tid)
    assert exc.value.gate == "B"
    assert s.machine.get(tid).stage == "PLAN"


def test_sufficient_current_evidence_allows_create():
    s = new_service()
    tid = basic(s)
    s.record_trusted_evidence_check(tid, "SUFFICIENT", "trusted assessment")
    s.confirm(tid, JointConfirmation(audience="青年", genre="post", language="English"))
    s.enter_create(tid)
    assert s.machine.get(tid).stage == "CREATE"
    s.machine.assert_create_ready(tid)


def test_sufficient_without_pack_is_rejected():
    s = new_service()
    t = s.start("苏绣").task.task_id
    s.attach_ground(t, GroundDigest(evidence_gaps=["缺少来源"]))
    s.save_plan(t, NarrativePlan(title="暂定"))
    with pytest.raises(WorkflowError) as exc:
        s.record_trusted_evidence_check(t, "SUFFICIENT")
    assert exc.value.gate == "B"


def test_plan_change_invalidates_confirmation_and_evidence():
    s = new_service()
    t = basic(s)
    s.record_trusted_evidence_check(t, "SUFFICIENT")
    s.confirm(t, JointConfirmation(audience="青年", genre="post", language="English"))
    s.save_plan(t, NarrativePlan(title="新版"))
    assert "A" not in s.machine.get(t).gates
    assert "B" not in s.machine.get(t).gates
    with pytest.raises(WorkflowError):
        s.enter_create(t)


def test_feedback_requires_real_new_plan_before_confirm():
    s = new_service()
    t = basic(s)
    s.feedback_text(t, "历史背景少一些，重点写传承人物")
    assert s.get(t).plan is None
    assert s.snapshot(t)["plan_update_pending"] is True
    with pytest.raises(WorkflowError):
        s.confirm(t, JointConfirmation(audience="青年", genre="post", language="English"))
    s.save_plan(t, NarrativePlan(title="修改版：人物故事"))
    assert s.snapshot(t)["plan_update_pending"] is False


def test_explicit_genre_must_be_valid():
    s = new_service()
    t = basic(s)
    with pytest.raises(WorkflowError):
        s.confirm(t, JointConfirmation(audience="青年", genre="automatic", language="English"))


def test_public_gate_b_cannot_forge_evidence():
    s = new_service()
    t = basic(s)
    with pytest.raises(WorkflowError):
        s.machine.decide_gate(t, GateDecision(gate="B", decision="passed", decided_by="system"))


def test_duplicate_start_fails_no_reset():
    s = new_service()
    s.start("苏绣", task_id="same")
    with pytest.raises(WorkflowError):
        s.start("高铁", task_id="same")


def test_illegal_jump_fails():
    s = new_service()
    t = s.start("苏绣").task.task_id
    with pytest.raises(WorkflowError):
        s.machine.advance(t, "CREATE")


def test_router_feedback_is_not_claimed_completed(monkeypatch):
    import api.story_router as sr
    service = new_service()
    monkeypatch.setattr(sr, "story_session_store", service)
    app = FastAPI()
    app.include_router(sr.router)
    client = TestClient(app)
    start = client.post("/api/story-tasks", json={"topic":"苏绣"})
    assert start.status_code == 200
    tid = start.json()["data"]["task"]["task_id"]
    service.attach_ground(tid, GroundDigest(evidence_pack_id="EP-TEST"))
    service.save_plan(tid, NarrativePlan(title="旧计划"))
    r = client.post(f"/api/story-tasks/{tid}/feedback", json={"instruction":"人物优先"})
    assert r.status_code == 200
    assert r.json()["data"]["planner_update_pending"] is True
    r = client.post(f"/api/story-tasks/{tid}/confirm", json={"audience":"青年","genre":"post","language":"English"})
    assert r.status_code == 409
