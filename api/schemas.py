from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field


class TaskContext(BaseModel):
    """统一任务上下文；兼容现有生成请求字段。"""

    task_id: str
    topic: str = ""
    goal: str = ""
    genre: str = "post"
    platform: str = ""
    audience: str = ""
    language: str = "English"
    user_materials: Optional[str] = ""


class Source(BaseModel):
    source_id: str
    uri: str = ""
    title: str = ""
    source_type: str = ""


class EvidenceSpan(BaseModel):
    span_id: str
    source_id: str
    text: str
    start: Optional[int] = Field(default=None, ge=0)
    end: Optional[int] = Field(default=None, ge=0)


class EvidenceItem(BaseModel):
    evidence_id: str
    source_id: str
    statement: str
    spans: List[EvidenceSpan] = Field(default_factory=list)
    category: str = ""


class EvidencePack(BaseModel):
    evidence_pack_id: str
    items: List[EvidenceItem] = Field(default_factory=list)
    sources: List[Source] = Field(default_factory=list)
    status: str = "ready"


class Claim(BaseModel):
    claim_id: str
    text: str
    evidence_ids: List[str] = Field(default_factory=list)

    @property
    def evidence_refs(self) -> List[str]:
        """Canonical binding name; evidence_ids remains the compatibility field."""
        return self.evidence_ids


class ContentVersion(BaseModel):
    content_version_id: str
    content: str
    task_id: str = ""
    parent_version_id: Optional[str] = None
    evidence_pack_id: Optional[str] = None
    claim_ids: List[str] = Field(default_factory=list)
    status: str = "Draft"
    created_at: Optional[datetime] = None


class GateDecision(BaseModel):
    gate: str
    decision: str
    reason: str = ""
    decided_by: str = "system"
    decided_at: Optional[datetime] = None


class EvaluationIssue(BaseModel):
    """A diagnosable problem found by an evaluation part.

    ``issue_id`` is part-local and deterministic. ``evidence_spans`` reuses the
    existing :class:`EvidenceSpan` shape so span anchors stay one canonical type
    across evidence binding and content evaluation.
    """

    issue_id: str
    dimension_id: str = ""
    severity: str = ""
    problem: str
    reason: str = ""
    evidence_spans: List[EvidenceSpan] = Field(default_factory=list)


class DimensionResult(BaseModel):
    """Single-dimension output of the Part 3 ChinaStory Evaluation Skill."""

    dimension_id: str
    score: int
    confidence: float
    rationale: str = ""
    evidence_spans: List[EvidenceSpan] = Field(default_factory=list)
    problems: List[str] = Field(default_factory=list)
    revision_suggestion: str = ""


class RevisionSuggestion(BaseModel):
    """An advisory suggestion attached to an :class:`EvaluationResult`.

    This is an *evaluation finding only*. It is not the executable
    ``RevisionInstruction`` of the revision loop, which is defined below in
    P0.7. Keeping them separate stops an evaluation finding from silently
    becoming a mutation command.
    """

    target_dimension: str = ""
    problem: str = ""
    instruction: str = ""
    preserve: List[str] = Field(default_factory=list)


class RevisionInstruction(BaseModel):
    """An executable revision command for one content version (P0.7).

    ``RevisionSuggestion`` is an evaluation *finding* about a version;
    ``RevisionInstruction`` is a *command* bound to that version. The extra
    fields are exactly what makes it executable and auditable:

    * ``base_version_id`` - the only legal ``create_revision`` parent, so an
      instruction can never be applied to a version it was not written for.
    * ``source_evaluation_id`` - closes the audit chain back to the evaluation
      that produced the finding.
    * ``instruction_id`` / ``task_id`` - addressable and task-scoped.
    """

    instruction_id: str
    task_id: str
    base_version_id: str
    source_evaluation_id: str
    target_dimension: str = ""
    problem: str = ""
    instruction: str = ""
    preserve: List[str] = Field(default_factory=list)


class EvaluationAuditMetadata(BaseModel):
    """Deterministic, serializable provenance for one evaluation run."""

    evaluator: str = ""
    evaluator_type: str = ""
    rubric_version: str = ""
    calibration_set_version: str = ""
    prompt_version: str = ""
    task_context_version: str = ""
    part1_status: str = ""
    created_at: Optional[datetime] = None


class EvaluationClaimTrace(BaseModel):
    """Part 1 per-claim fact/evidence verdict.

    Kept separate from ``EvaluationResult.scores`` so the legacy
    ``Dict[str, float]`` contract stays numeric and backward compatible.
    """

    claim_id: str
    status: str
    detail: str = ""


class EvaluationResult(BaseModel):
    """Canonical evaluation output for the whole backend.

    Backward-compatible core fields (``evaluation_id``, ``content_version_id``,
    ``part``, ``status``, ``issues``, ``scores``) are preserved; everything else
    is additive. There is deliberately no second top-level evaluation model.
    """

    evaluation_id: str
    content_version_id: str
    part: str
    status: str
    issues: List[str] = Field(default_factory=list)
    scores: Dict[str, float] = Field(default_factory=dict)

    # --- P0.6 additive extension -------------------------------------------
    task_id: str = ""
    rubric_version: str = ""
    claim_traces: List[EvaluationClaimTrace] = Field(default_factory=list)
    dimensions: List[DimensionResult] = Field(default_factory=list)
    priority_issues: List[EvaluationIssue] = Field(default_factory=list)
    revision_suggestions: List[RevisionSuggestion] = Field(default_factory=list)
    # TBD per rubric §5.2: no default aggregation is defined, so this stays null.
    overall_score: Optional[float] = None
    return_to_part1: bool = False
    real_audience_evaluation: str = "NOT_EVALUATED"
    human_review: str = "PENDING"
    audit: Optional[EvaluationAuditMetadata] = None


class Approval(BaseModel):
    approval_id: str
    content_version_id: str
    approved: bool
    approver: str
    approved_at: Optional[datetime] = None
    note: str = ""


#: The only human review decisions P0.8 recognises. ``APPROVED`` is deliberately
#: absent: it is an *outcome* derived from ACCEPT, never a decision value.
HUMAN_REVIEW_DECISIONS = frozenset({"ACCEPT", "EDIT", "REJECT"})


class HumanReviewDecision(BaseModel):
    """Immutable, append-only audit record of one human review (P0.8-A).

    This is an *audit record*, not an approval object. It binds a review to
    exactly one evaluation of exactly one content version so an evaluation can
    never be used to approve a different version. ``published`` is always
    ``False``: P0.8-A has no publishing capability at all.

    Immutability is enforced, not merely documented:

    * ``model_config = ConfigDict(frozen=True)`` blocks attribute assignment, so
      a record handed out by the store cannot have ``decision`` / ``reviewer`` /
      ``published`` etc. silently rewritten.
    * ``unresolved_warnings`` is a ``tuple`` rather than a ``list`` because
      ``frozen=True`` does not protect nested mutable containers: a leaked
      ``list`` could still be mutated in place through ``get()`` /
      ``history_for()`` / ``all_records()``. A tuple has no mutating methods.

    An ACCEPT-derived outcome is *not* Gate C approval. Future P0.8-B must
    re-verify a persisted record from the shared store, bound to the exact
    task_id / content_version_id / evaluation_id.
    """

    model_config = ConfigDict(frozen=True)

    review_id: str
    task_id: str
    content_version_id: str
    evaluation_id: str
    decision: str
    reviewer: str
    reason: str = ""
    reviewed_at: Optional[datetime] = None
    unresolved_warnings: Tuple[str, ...] = ()
    evidence_pack_id: Optional[str] = None
    published: bool = False


class PostGenerateRequest(BaseModel):
    theme: str
    country: str = "America"
    identity: str = "online_influencer"
    tone: str = "optimistic"
    platform: str = "instagram"
    language: str = "English"
    max_words: int = Field(default=80, ge=20, le=1200)
    use_emoji: bool = True
    desired_effect: str = (
        "Increase curiosity and positive understanding of China through a concrete, shareable story."
    )
    user_materials: Optional[str] = Field(
        default="",
        description="用户粘贴资料；空行分段。与本地库合并为 evidence_used，source_type=用户上传",
    )
    genre: Optional[str] = Field(
        default="",
        description="体裁覆盖：post|news|feature|script；空则自动识别",
    )


class TopicsRequest(BaseModel):
    seed: str = "讲好中国故事"
    platform: str = "instagram"
    n: int = Field(default=5, ge=1, le=8)


class ReplyGenerateRequest(BaseModel):
    comment: str
    country: str = "America"
    identity: str = "political_commentator"
    tone: str = "serious"
    platform: str = "twitter"
    language: str = "English"
    max_words: int = Field(default=60, ge=20, le=200)


class EvidenceRequest(BaseModel):
    categories: str = "culture,food"
    limit_per_category: int = Field(default=2, ge=1, le=5)
    query: str = ""


class PolishRequest(BaseModel):
    post: str
    instruction: str
    language: str = "English"
    max_words: int = Field(default=100, ge=20, le=300)


class ApprovalRequest(BaseModel):
    """Legacy-compatible approval request (P0.8-B additively extended).

    ``approved=True`` is **no longer authorization**. Since P0.8-B, Gate C
    derives its result exclusively from a persisted ``HumanReviewDecision``
    in the application-level shared ``HumanReviewStore``. The additive binding
    fields locate that review; absence of them is fail-closed, never implicit
    approval.

    Trust rules for the additive fields:

    * ``content_version_id`` / ``evaluation_id`` — required to identify the
      exact approval target; verified against canonical stores.
    * ``task_id`` — at most a claim; a conflict with the canonical version task
      fails closed. Never used instead of canonical data.
    * ``review_id`` — at most a locator; still subject to exact-binding and
      supersession verification.
    * ``post`` — compatibility only; never hashed, never authorized on.
    """

    post: str
    approved: bool = True
    approver: str = "human"
    note: str = ""
    # --- P0.8-B additive binding fields -------------------------------------
    task_id: str = ""
    content_version_id: str = ""
    evaluation_id: str = ""
    review_id: str = ""
