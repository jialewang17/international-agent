"""Minimal executable six-stage workflow state machine (in-memory)."""
from dataclasses import dataclass, field
from typing import Dict, Optional

from api.schemas import GateDecision

STAGES = ("DEFINE", "GROUND", "PLAN", "CREATE", "REVISE_AUDIT", "APPROVE")
GATE_STAGE = {"A": "DEFINE", "B": "GROUND", "C": "REVISE_AUDIT"}
PASS_DECISIONS = frozenset({"approved", "passed", "clear", "ok"})
BLOCK_DECISIONS = frozenset({"blocked", "rejected", "deny", "denied"})


@dataclass
class WorkflowState:
    task_id: str
    stage: str = "DEFINE"
    gates: Dict[str, GateDecision] = field(default_factory=dict)
    status: str = "active"
    reason: str = ""


class WorkflowError(ValueError):
    def __init__(self, gate: str, reason: str):
        self.gate, self.reason = gate, reason
        super().__init__(reason)


class WorkflowStateMachine:
    def __init__(self):
        self._states: Dict[str, WorkflowState] = {}

    def start(self, task_id: str) -> WorkflowState:
        state = WorkflowState(task_id=task_id)
        self._states[task_id] = state
        return state

    def get(self, task_id: str) -> WorkflowState:
        if task_id not in self._states:
            raise KeyError(task_id)
        return self._states[task_id]

    def decide_gate(self, task_id: str, decision: GateDecision) -> WorkflowState:
        state = self.get(task_id)
        if decision.gate not in {"A", "B", "C"}:
            raise WorkflowError(decision.gate, "unknown gate")
        expected_stage = GATE_STAGE[decision.gate]
        if state.stage != expected_stage:
            raise WorkflowError(decision.gate, f"Gate {decision.gate} can only be decided at {expected_stage}")
        value = decision.decision.lower().strip()
        if value not in PASS_DECISIONS and value not in BLOCK_DECISIONS:
            raise WorkflowError(decision.gate, f"unknown decision: {decision.decision}")
        state.gates[decision.gate] = decision
        if value in BLOCK_DECISIONS:
            state.status, state.reason = "blocked", decision.reason
        else:
            state.status, state.reason = "active", ""
        return state

    def advance(self, task_id: str, target: str) -> WorkflowState:
        state = self.get(task_id)
        if target not in STAGES:
            raise WorkflowError("stage", f"unknown stage: {target}")
        current_i, target_i = STAGES.index(state.stage), STAGES.index(target)
        if target_i != current_i + 1:
            raise WorkflowError("stage", f"illegal transition: {state.stage} -> {target}")
        required = {"GROUND": "A", "PLAN": "B", "APPROVE": "C"}.get(target)
        if required:
            gate = state.gates.get(required)
            if not gate or gate.decision.lower() not in {"approved", "passed", "clear", "ok"}:
                reason = gate.reason if gate and gate.reason else f"Gate {required} not satisfied"
                state.status, state.reason = "blocked", reason
                raise WorkflowError(required, reason)
        state.stage, state.status, state.reason = target, "active", ""
        return state


workflow_state_machine = WorkflowStateMachine()
