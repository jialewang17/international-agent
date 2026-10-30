import pytest

from api.schemas import GateDecision
from api.workflow import WorkflowError, WorkflowStateMachine


def passed(gate):
    return GateDecision(gate=gate, decision="approved", reason="ok", decided_by="human")


def user_passed(gate):
    return GateDecision(gate=gate, decision="approved", reason="ok", decided_by="user")


def reach_plan(sm, task_id):
    """DEFINE -> GROUND -> PLAN with a saved plan (plan_revision > 0)."""
    sm.advance(task_id, "GROUND")
    sm.advance(task_id, "PLAN")
    sm.mark_plan_updated(task_id)


def confirm_jointly(sm, task_id):
    sm.allow_joint_confirmation(task_id)
    sm.decide_gate(task_id, user_passed("A"))
    sm.set_evidence_status(task_id, "SUFFICIENT", "trusted assessment")


def test_normal_six_stage_progression():
    sm = WorkflowStateMachine(); sm.start("t")
    reach_plan(sm, "t")
    confirm_jointly(sm, "t")
    sm.advance("t", "CREATE")
    sm.advance("t", "REVISE_AUDIT"); sm.decide_gate("t", passed("C")); sm.advance("t", "APPROVE")
    assert sm.get("t").stage == "APPROVE"


def test_gates_and_illegal_jumps_block_with_reason():
    sm = WorkflowStateMachine(); sm.start("t")
    # Gate B is never publicly decidable: trusted assessment only.
    with pytest.raises(WorkflowError, match="Gate B"):
        sm.decide_gate("t", passed("B"))
    # Gate C can only be decided at REVISE_AUDIT.
    with pytest.raises(WorkflowError, match="Gate C"):
        sm.decide_gate("t", passed("C"))
    # Gate A needs a saved Plan plus explicit joint-confirmation readiness.
    with pytest.raises(WorkflowError, match="Gate A"):
        sm.decide_gate("t", user_passed("A"))
    with pytest.raises(WorkflowError, match="illegal transition"):
        sm.advance("t", "CREATE")
    reach_plan(sm, "t")
    # A blocked confirmation keeps its reason and blocks progression to CREATE.
    sm.allow_joint_confirmation("t")
    sm.decide_gate("t", GateDecision(gate="A", decision="rejected", decided_by="user", reason="needs confirmation"))
    assert sm.get("t").status == "blocked"
    assert sm.get("t").reason == "needs confirmation"
    with pytest.raises(WorkflowError, match="confirmation"):
        sm.advance("t", "CREATE")
    # A new plan revision invalidates the stale decision and re-enables confirmation.
    sm.mark_plan_updated("t")
    sm.allow_joint_confirmation("t")
    sm.decide_gate("t", user_passed("A"))
    # CREATE stays blocked until the trusted evidence check is SUFFICIENT (Gate B).
    with pytest.raises(WorkflowError, match="plan-specific evidence"):
        sm.advance("t", "CREATE")
    with pytest.raises(WorkflowError, match="unknown decision"):
        sm.decide_gate("t", GateDecision(gate="A", decision="maybe", decided_by="user"))


def test_gate_c_required_before_approve():
    sm = WorkflowStateMachine(); sm.start("t")
    reach_plan(sm, "t")
    confirm_jointly(sm, "t")
    sm.advance("t", "CREATE"); sm.advance("t", "REVISE_AUDIT")
    with pytest.raises(WorkflowError, match="Gate C"):
        sm.advance("t", "APPROVE")
