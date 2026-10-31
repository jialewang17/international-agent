"""Plan-centered session contracts, no model calls or invented evidence.

In-memory prototype. Existing EvidencePack/Claim/ContentVersion stores remain
canonical, and the existing /api/posts/approve is authoritative for Gate C.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from api.evidence_store import EvidencePackStore, EvidenceStoreError
from api.schemas import GateDecision, Source
from api.workflow import WorkflowError, WorkflowStateMachine, workflow_state_machine

GENRES = frozenset({"post", "news", "feature", "indepth", "script", "faq"})


class DraftTaskContext(BaseModel):
    model_config = ConfigDict(extra="forbid")
    task_id: str = ""
    topic: str = Field(min_length=1)
    user_materials: str = ""
    audience: Optional[str] = None
    audience_knowledge: Literal["none", "limited", "some", "expert", "unknown"] = "unknown"
    genre: Optional[str] = None
    language: Optional[str] = None
    platform: Optional[str] = None
    user_requirements: str = ""


class StorySuggestion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str
    rationale: str = ""
    evidence_ids: List[str] = Field(default_factory=list)
    evidence_status: Literal["PRELIMINARY", "VERIFIED", "MISSING", "NOT_EVALUATED"] = "NOT_EVALUATED"


class GroundDigest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    evidence_pack_id: Optional[str] = None
    source_ids: List[str] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)
    suggestions: List[StorySuggestion] = Field(default_factory=list)
    evidence_gaps: List[str] = Field(default_factory=list)
    retrieval_note: str = ""
    # P0-1: verbatim projection of the canonical EvidencePack sources so the
    # frontend can render real source cards. Never fabricated; spans stay [].
    sources: List[Source] = Field(default_factory=list)


class StorySection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str
    purpose: str = ""
    evidence_ids: List[str] = Field(default_factory=list)
    fact_gaps: List[str] = Field(default_factory=list)


class NarrativePlan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: int = 0
    title: str = Field(min_length=1)
    central_message: str = ""
    selected_angles: List[str] = Field(default_factory=list)
    excluded_angles: List[str] = Field(default_factory=list)
    sections: List[StorySection] = Field(default_factory=list)
    evidence_gaps: List[str] = Field(default_factory=list)
    planning_status: Literal["DRAFT", "EVIDENCE_REFRESH_REQUIRED", "READY_FOR_REVIEW"] = "DRAFT"


class UserPlanFeedback(BaseModel):
    model_config = ConfigDict(extra="forbid")
    instruction: str = Field(min_length=1)


class JointConfirmation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    audience: str = Field(min_length=1)
    genre: str = Field(min_length=1)
    language: str = Field(min_length=1)
    audience_knowledge: Literal["none", "limited", "some", "expert", "unknown"] = "unknown"
    platform: Optional[str] = None
    user_requirements: str = ""


@dataclass
class StorySession:
    task: DraftTaskContext
    ground: Optional[GroundDigest] = None
    plan: Optional[NarrativePlan] = None
    feedback: List[str] = field(default_factory=list)
    joint_confirmed: bool = False
    plan_update_pending: bool = False
    # P0-1: truthful Ground failure info while ``ground`` is still None.
    # Only meaningful in the GROUND stage; never fakes a completed Ground.
    ground_gaps: List[str] = field(default_factory=list)
    ground_note: str = ""


class StorySessionStore:
    def __init__(self, state_machine: Optional[WorkflowStateMachine] = None,
                 evidence_pack_store: Optional[EvidencePackStore] = None):
        self.machine = state_machine or workflow_state_machine
        self._sessions: Dict[str, StorySession] = {}
        self.evidence_pack_store = evidence_pack_store

    def bind_evidence_pack_store(self, store: EvidencePackStore) -> None:
        """Bind the shared canonical EvidencePack store (P0-1).

        attach_ground refuses to trust any evidence_pack_id it cannot verify
        against this store; fail closed if no store is bound.
        """
        self.evidence_pack_store = store

    def exists(self, task_id: str) -> bool:
        return task_id in self._sessions

    def start(self, topic: str, user_materials: str = "", task_id: Optional[str] = None) -> StorySession:
        task_id = task_id or str(uuid4())
        if task_id in self._sessions:
            raise WorkflowError("task", "story session already exists")
        task = DraftTaskContext(task_id=task_id, topic=topic.strip(), user_materials=user_materials)
        self.machine.start(task_id)
        self.machine.advance(task_id, "GROUND")
        session = StorySession(task=task)
        self._sessions[task_id] = session
        return session

    def get(self, task_id: str) -> StorySession:
        return self._sessions[task_id]

    def attach_ground(self, task_id: str, digest: GroundDigest) -> StorySession:
        """Call from Ground integration only (not user-supplied evidence).

        P0-1: the digest must reference an EvidencePack that actually exists
        in the bound canonical store. A bare non-empty string is no longer
        accepted; a missing/unbound store fails closed.
        """
        session = self.get(task_id)
        state = self.machine.get(task_id)
        if state.stage != "GROUND":
            raise WorkflowError("stage", "Ground can only be attached in GROUND")
        if not digest.evidence_pack_id:
            raise WorkflowError(
                "B", "Ground digest must reference a canonical EvidencePack"
            )
        if self.evidence_pack_store is None:
            raise WorkflowError(
                "B", "evidence pack store not bound; cannot verify EvidencePack"
            )
        try:
            self.evidence_pack_store.get(digest.evidence_pack_id)
        except EvidenceStoreError as exc:
            raise WorkflowError(
                "B",
                f"evidence_pack_id {digest.evidence_pack_id} does not exist "
                "in the canonical store; refusing to attach Ground",
            ) from exc
        session.ground = digest
        session.ground_gaps = []
        session.ground_note = ""
        self.machine.advance(task_id, "PLAN")
        return session

    def record_ground_failure(self, task_id: str, gaps: List[str],
                              note: str = "") -> StorySession:
        """Record a real, empty Ground outcome. Task stays in GROUND.

        This does NOT attach a digest, does NOT advance the stage, and does
        NOT create any evidence: it only stores the truthful gaps so the UI
        can show why Plan is blocked.
        """
        session = self.get(task_id)
        state = self.machine.get(task_id)
        if state.stage != "GROUND":
            raise WorkflowError("stage", "Ground failure can only be recorded in GROUND")
        session.ground_gaps = list(gaps or [])
        session.ground_note = note or ""
        return session

    def save_plan(self, task_id: str, plan: NarrativePlan) -> StorySession:
        """Store a planner result, without claiming its facts have been verified."""
        session = self.get(task_id)
        if session.ground is None:
            raise WorkflowError("stage", "Ground summary is required before Plan")
        state = self.machine.mark_plan_updated(task_id)
        session.plan = plan.model_copy(update={"version": state.plan_revision})
        session.joint_confirmed = False
        session.plan_update_pending = False
        return session

    def feedback_text(self, task_id: str, instruction: str) -> StorySession:
        """Record a user instruction. A real planner must produce the revised Plan."""
        session = self.get(task_id)
        if self.machine.get(task_id).stage != "PLAN":
            raise WorkflowError("stage", "feedback is allowed only in PLAN")
        if not instruction.strip():
            raise ValueError("feedback must not be empty")
        session.feedback.append(instruction.strip())
        session.plan_update_pending = True
        session.joint_confirmed = False
        self.machine.mark_plan_updated(task_id)
        session.plan = None  # only a new planner result may resolve pending feedback
        return session

    def confirm(self, task_id: str, confirmation: JointConfirmation) -> StorySession:
        session = self.get(task_id)
        if session.plan is None or session.plan_update_pending:
            raise WorkflowError("A", "new Narrative Plan required after feedback")
        if confirmation.genre not in GENRES:
            raise WorkflowError("A", "unsupported genre; explicit choice required")
        if not confirmation.audience.strip() or not confirmation.language.strip():
            raise WorkflowError("A", "audience and language are required")
        if session.joint_confirmed:
            raise WorkflowError("A", "this Plan revision has already been confirmed")
        session.task = session.task.model_copy(update={
            "audience": confirmation.audience.strip(),
            "genre": confirmation.genre,
            "language": confirmation.language.strip(),
            "platform": confirmation.platform,
            "audience_knowledge": confirmation.audience_knowledge,
            "user_requirements": confirmation.user_requirements,
        })
        self.machine.allow_joint_confirmation(task_id)
        self.machine.decide_gate(task_id, GateDecision(
            gate="A", decision="approved", reason="Task Context + Narrative Plan jointly confirmed",
            decided_by="user",
        ))
        session.joint_confirmed = True
        return session

    def record_trusted_evidence_check(self, task_id: str, status: str, reason: str = "") -> StorySession:
        """Internal-only. Do not call on raw user-provided status or source count.

        Only a trusted Ground/semantic-evaluator can say SUFFICIENT for the
        *current* Narrative Plan. Semantic support must not be guessed.
        """
        session = self.get(task_id)
        if status == "SUFFICIENT" and (not session.ground or not session.ground.evidence_pack_id):
            raise WorkflowError("B", "a canonical EvidencePack is required")
        self.machine.set_evidence_status(task_id, status, reason)
        return session

    def enter_create(self, task_id: str) -> StorySession:
        session = self.get(task_id)
        if not session.joint_confirmed:
            raise WorkflowError("A", "joint confirmation missing")
        self.machine.advance(task_id, "CREATE")
        return session

    def snapshot(self, task_id: str) -> dict:
        session = self.get(task_id)
        state = self.machine.get(task_id)
        return {
            "task": session.task.model_dump(),
            "ground": session.ground.model_dump() if session.ground else None,
            "ground_gaps": list(session.ground_gaps),
            "ground_note": session.ground_note,
            "plan": session.plan.model_dump() if session.plan else None,
            "feedback": list(session.feedback),
            "joint_confirmed": session.joint_confirmed,
            "plan_update_pending": session.plan_update_pending,
            "workflow": {
                "task_id": state.task_id,
                "stage": state.stage,
                "status": state.status,
                "reason": state.reason,
                "plan_revision": state.plan_revision,
                "confirmed_plan_revision": state.confirmed_plan_revision,
                "evidence_status": state.evidence_status,
                "gates": {key: value.model_dump(mode="json") for key, value in state.gates.items()},
            },
        }


story_session_store = StorySessionStore()
