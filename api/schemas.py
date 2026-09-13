from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


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
