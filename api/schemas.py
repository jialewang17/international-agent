from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


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


class EvaluationResult(BaseModel):
    evaluation_id: str
    content_version_id: str
    part: str
    status: str
    issues: List[str] = Field(default_factory=list)
    scores: Dict[str, float] = Field(default_factory=dict)


class Approval(BaseModel):
    approval_id: str
    content_version_id: str
    approved: bool
    approver: str
    approved_at: Optional[datetime] = None
    note: str = ""


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
    post: str
    approved: bool = True
    approver: str = "human"
    note: str = ""
