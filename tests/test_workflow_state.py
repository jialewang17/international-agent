import pytest

from api.schemas import GateDecision
from api.workflow import WorkflowError, WorkflowStateMachine


def passed(gate):
    return GateDecision(gate=gate, decision="approved", reason="ok")


def test_normal_six_stage_progression():
    sm = WorkflowStateMachine(); sm.start("t")
    sm.decide_gate("t", passed("A")); sm.advance("t", "GROUND")
    sm.decide_gate("t", passed("B")); sm.advance("t", "PLAN"); sm.advance("t", "CREATE")
    sm.advance("t", "REVISE_AUDIT"); sm.decide_gate("t", passed("C")); sm.advance("t", "APPROVE")
    assert sm.get("t").stage == "APPROVE"


def test_gates_and_illegal_jumps_block_with_reason():
    sm = WorkflowStateMachine(); sm.start("t")
    with pytest.raises(WorkflowError, match="Gate B"):
        sm.decide_gate("t", passed("B"))
    with pytest.raises(WorkflowError, match="Gate C"):
        sm.decide_gate("t", passed("C"))
    with pytest.raises(WorkflowError, match="Gate A"):
        sm.advance("t", "GROUND")
    sm.decide_gate("t", GateDecision(gate="A", decision="rejected", reason="needs confirmation"))
    with pytest.raises(WorkflowError, match="needs confirmation"):
        sm.advance("t", "GROUND")
    sm.decide_gate("t", passed("A")); sm.advance("t", "GROUND")
    with pytest.raises(WorkflowError, match="Gate B"):
        sm.advance("t", "PLAN")
    with pytest.raises(WorkflowError, match="unknown decision"):
        sm.decide_gate("t", GateDecision(gate="B", decision="maybe"))
    sm.decide_gate("t", passed("B")); sm.advance("t", "PLAN"); sm.advance("t", "CREATE")
    with pytest.raises(WorkflowError, match="Gate C"):
        sm.decide_gate("t", passed("C"))
    with pytest.raises(WorkflowError, match="illegal transition"):
        sm.advance("t", "APPROVE")


def test_gate_c_required_before_approve():
    sm = WorkflowStateMachine(); sm.start("t"); sm.decide_gate("t", passed("A")); sm.advance("t", "GROUND")
    sm.decide_gate("t", passed("B")); sm.advance("t", "PLAN"); sm.advance("t", "CREATE"); sm.advance("t", "REVISE_AUDIT")
    with pytest.raises(WorkflowError, match="Gate C"):
        sm.advance("t", "APPROVE")
