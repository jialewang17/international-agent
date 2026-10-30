"""Six-stage state machine for Plan-centered, single task confirmation.

This remains in memory, compatible with the existing GateDecision model.
The /api/posts/approve endpoint and its persisted HumanReviewStore are the
*authoritative* Gate C approval; the workflow's C flag is only a stage marker.
"""
from dataclasses import dataclass, field
from typing import Dict

from api.schemas import GateDecision

STAGES = ("DEFINE", "GROUND", "PLAN", "CREATE", "REVISE_AUDIT", "APPROVE")
GATE_STAGE = {"A": "PLAN", "B": "PLAN", "C": "REVISE_AUDIT"}
PASS_DECISIONS = frozenset({"approved", "passed", "clear", "ok"})
BLOCK_DECISIONS = frozenset({"blocked", "rejected", "deny", "denied"})
EVIDENCE_STATUSES = frozenset({
    "NOT_EVALUATED", "SUFFICIENT", "PARTIAL", "MISSING_CRITICAL", "CONFLICT",
    "RETRIEVAL_EXHAUSTED",
})


@dataclass
class WorkflowState:
    task_id: str
    stage: str = "DEFINE"
    gates: Dict[str, GateDecision] = field(default_factory=dict)
    status: str = "active"
    reason: str = ""
    plan_revision: int = 0
    confirmed_plan_revision: int = -1
    evidence_checked_revision: int = -1
    evidence_status: str = "NOT_EVALUATED"
    confirmation_ready: bool = False


class WorkflowError(ValueError):
    def __init__(self, gate: str, reason: str):
        self.gate, self.reason = gate, reason
        super().__init__(reason)


class WorkflowStateMachine:
    def __init__(self):
        self._states: Dict[str, WorkflowState] = {}

    def start(self, task_id: str) -> WorkflowState:
        if not task_id.strip():
            raise WorkflowError("task", "task_id is required")
        if task_id in self._states:
            raise WorkflowError("task", "task already exists; cannot reset decisions")
        state = WorkflowState(task_id=task_id)
        self._states[task_id] = state
        return state

    def get(self, task_id: str) -> WorkflowState:
        if task_id not in self._states:
            raise KeyError(task_id)
        return self._states[task_id]

    def has(self, task_id: str) -> bool:
        return task_id in self._states

    def mark_plan_updated(self, task_id: str) -> WorkflowState:
        state = self.get(task_id)
        if state.stage != "PLAN":
            raise WorkflowError("stage", "plan can only be edited at PLAN")
        state.plan_revision += 1
        state.confirmed_plan_revision = -1
        state.confirmation_ready = False
        state.gates.pop("A", None)
        state.gates.pop("B", None)
        state.evidence_checked_revision = -1
        state.evidence_status = "NOT_EVALUATED"
        state.status, state.reason = "active", ""
        return state

    def set_evidence_status(self, task_id: str, status: str, reason: str = "") -> WorkflowState:
        """Trusted Ground/evaluator integration only; do not expose as public write API.

        SUFFICIENT must be the result of a real content/evidence assessment,
        not just a count of retrieved sources. A Plan revision invalidates it.
        """
        state = self.get(task_id)
        if state.stage not in {"GROUND", "PLAN"}:
            raise WorkflowError("B", "evidence assessment is only accepted in GROUND or PLAN")
        if status not in EVIDENCE_STATUSES:
            raise WorkflowError("B", f"unknown evidence status: {status}")
        state.evidence_status = status
        state.evidence_checked_revision = state.plan_revision if state.stage == "PLAN" else -1
        state.gates.pop("B", None)
        if status == "SUFFICIENT" and state.stage == "PLAN" and state.plan_revision > 0:
            state.gates["B"] = GateDecision(
                gate="B", decision="passed", reason=reason or "scope-specific evidence checked",
                decided_by="system",
            )
        state.status = "active"
        state.reason = reason
        return state

    def allow_joint_confirmation(self, task_id: str) -> None:
        state = self.get(task_id)
        if state.stage != "PLAN" or state.plan_revision == 0:
            raise WorkflowError("A", "joint confirmation requires a saved Plan")
        state.confirmation_ready = True

    def decide_gate(self, task_id: str, decision: GateDecision) -> WorkflowState:
        state = self.get(task_id)
        gate = decision.gate.upper().strip()
        if gate not in {"A", "B", "C"}:
            raise WorkflowError(gate, "unknown gate")
        expected = GATE_STAGE[gate]
        if state.stage != expected:
            raise WorkflowError(gate, f"Gate {gate} can only be decided at {expected}")
        value = decision.decision.lower().strip()
        if value not in PASS_DECISIONS and value not in BLOCK_DECISIONS:
            raise WorkflowError(gate, f"unknown decision: {decision.decision}")
        if gate == "A":
            if not state.confirmation_ready:
                raise WorkflowError("A", "task and plan must be validated before confirmation")
            if decision.decided_by.lower() not in {"human", "user"}:
                raise WorkflowError("A", "joint confirmation must be explicit user action")
            if value in PASS_DECISIONS:
                state.confirmed_plan_revision = state.plan_revision
        elif gate == "B":
            # A publicly supplied GateDecision is never an evidence evaluator.
            raise WorkflowError("B", "Gate B is calculated by trusted evidence assessment")
        elif gate == "C":
            if decision.decided_by.lower() not in {"human", "user"}:
                raise WorkflowError("C", "final approval requires human review")
        state.gates[gate] = decision
        state.status, state.reason = (
            ("blocked", decision.reason or f"Gate {gate} blocked")
            if value in BLOCK_DECISIONS else ("active", "")
        )
        return state

    def assert_create_ready(self, task_id: str) -> None:
        state = self.get(task_id)
        if state.stage != "CREATE":
            raise WorkflowError("stage", "workflow is not at CREATE")
        self._require_ready(state)

    def _require_ready(self, state: WorkflowState) -> None:
        a = state.gates.get("A")
        b = state.gates.get("B")
        if (not a or a.decision.lower().strip() not in PASS_DECISIONS
                or state.confirmed_plan_revision != state.plan_revision):
            raise WorkflowError("A", "joint Task Context + Plan confirmation missing or stale")
        if (not b or b.decision.lower().strip() not in PASS_DECISIONS
                or state.evidence_status != "SUFFICIENT"
                or state.evidence_checked_revision != state.plan_revision):
            raise WorkflowError("B", "plan-specific evidence is missing, insufficient or stale")

    def advance(self, task_id: str, target: str) -> WorkflowState:
        state = self.get(task_id)
        target = target.upper()
        if target not in STAGES:
            raise WorkflowError("stage", f"unknown stage: {target}")
        if STAGES.index(target) != STAGES.index(state.stage) + 1:
            raise WorkflowError("stage", f"illegal transition: {state.stage} -> {target}")
        if target == "CREATE":
            self._require_ready(state)
        if target == "APPROVE":
            c = state.gates.get("C")
            if not c or c.decision.lower().strip() not in PASS_DECISIONS:
                raise WorkflowError("C", "Gate C not satisfied (canonical human review still required)")
        state.stage, state.status, state.reason = target, "active", ""
        return state


workflow_state_machine = WorkflowStateMachine()
