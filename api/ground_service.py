"""P0-1 Ground integration: real local retrieval. No LLM, no API keys.

Reuses the existing deterministic evidence chain, unchanged:

    normalize_user_materials -> guess_categories -> retrieve_statements
        -> merge_evidence -> build_evidence_pack

Hard rules (P0-1 authorization):
- Never invents sources, web titles, quoted text, or facts. The canonical
  ``build_evidence_pack`` adapter is the only way rows become evidence.
- User-provided materials keep ``source_type="用户上传"``; local KB rows keep
  ``source_type="本地库"``. The distinction is preserved verbatim; nothing
  here claims any evidence has been fact-verified (that is Gate B's job and
  stays NOT_EVALUATED).
- Deterministic: same inputs -> same ``evidence_pack_id`` (sha256 over the
  sorted canonical identities).
- Exceptions are caught per stage and recorded on the outcome (with
  ``logger.exception``); they never fabricate a successful pack.
- ``spans`` stays ``[]``: legacy retrieval has no char offsets, and empty
  spans must not be presented as completed source-text grounding.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional

from api.evidence_adapter import EvidenceAdapterError, build_evidence_pack
from api.schemas import EvidencePack
from api.story_session import GroundDigest
from tools.kb_local import guess_categories, retrieve_statements
from tools.user_materials import merge_evidence, normalize_user_materials

logger = logging.getLogger("chinastory.ground")

#: Retrieval budget. Small and deterministic on purpose: the local KB is a
#: curated evidence file, not a search engine, and Ground must stay cheap.
TOP_K_CATEGORIES = 3
LIMIT_PER_CATEGORY = 3


@dataclass
class GroundOutcome:
    """Result of one Ground run. ``pack is None`` means: no usable evidence."""

    digest: GroundDigest
    pack: Optional[EvidencePack] = None
    error: Optional[str] = None
    categories: List[str] = field(default_factory=list)
    user_row_count: int = 0
    local_row_count: int = 0

    @property
    def succeeded(self) -> bool:
        return self.pack is not None


def _empty_digest(gaps: List[str], note: str) -> GroundDigest:
    return GroundDigest(
        evidence_pack_id=None,
        source_ids=[],
        evidence_ids=[],
        suggestions=[],
        evidence_gaps=gaps,
        retrieval_note=note,
    )


def run_ground(
    topic: str,
    user_materials: str = "",
    *,
    top_k_categories: int = TOP_K_CATEGORIES,
    limit_per_cat: int = LIMIT_PER_CATEGORY,
) -> GroundOutcome:
    """Run the deterministic Ground chain. Never raises by contract.

    Every stage failure is logged (``logger.exception``/``logger.warning``)
    and recorded on the returned outcome; a partially failed run simply
    contributes fewer (or zero) rows. An EMPTY outcome keeps the task in
    GROUND upstream and never pretends evidence exists.
    """
    topic = (topic or "").strip()
    errors: List[str] = []
    gaps: List[str] = []

    # --- Stage 1: user materials (用户上传; verbatim, no cleanup of facts) ---
    user_rows: List[dict] = []
    if user_materials and user_materials.strip():
        try:
            user_rows = normalize_user_materials(user_materials, theme=topic)
        except Exception:  # noqa: BLE001 - recorded, never swallowed silently
            logger.exception("normalize_user_materials failed (topic=%r)", topic)
            errors.append("用户资料解析失败，本轮未纳入用户材料")
            user_rows = []
    else:
        gaps.append("用户未提供参考资料（user_materials 为空）")

    # --- Stage 2: local KB retrieval (本地库; deterministic, offline) ---
    categories: List[str] = []
    local_rows: List[dict] = []
    try:
        categories = guess_categories(topic, top_k=top_k_categories)
    except Exception:  # noqa: BLE001
        logger.exception("guess_categories failed (topic=%r)", topic)
        errors.append("本地知识库类目匹配异常")
    if categories:
        try:
            local_rows = retrieve_statements(
                categories, limit_per_cat=limit_per_cat, query=topic
            )
        except Exception:  # noqa: BLE001
            logger.exception("retrieve_statements failed (topic=%r)", topic)
            errors.append("本地知识库检索异常")
        if not local_rows:
            gaps.append(
                "本地知识库在类目 [" + "、".join(categories) + "] 中未检索到证据条目"
            )
    else:
        gaps.append("本地知识库未命中与主题相关的类目")

    # --- Stage 3: merge (order preserved, source_type preserved) ---
    try:
        merged = merge_evidence(user_rows, local_rows, prefer_user_first=True)
    except Exception:  # noqa: BLE001
        logger.exception("merge_evidence failed (topic=%r)", topic)
        errors.append("证据合并异常")
        merged = []

    # --- Stage 4: canonical pack (fail closed on zero valid rows) ---
    try:
        pack = build_evidence_pack(merged)
    except EvidenceAdapterError as exc:
        logger.warning(
            "ground produced no usable evidence (topic=%r): %s", topic, exc
        )
        if errors:
            gaps.extend(errors)
        note = (
            "Ground 检索未产生可用证据；任务保持 GROUND 阶段，"
            "不伪造证据包（evidence_status 保持 NOT_EVALUATED）。"
        )
        return GroundOutcome(
            digest=_empty_digest(gaps, note),
            pack=None,
            error="; ".join(errors) if errors else None,
            categories=categories,
            user_row_count=len(user_rows),
            local_row_count=len(local_rows),
        )

    note = (
        f"本地检索 {len(local_rows)} 条、用户材料 {len(user_rows)} 条，"
        f"合并去重后 {len(pack.items)} 条证据 / {len(pack.sources)} 个来源；"
        "证据尚未经过任何事实核查（evidence_status=NOT_EVALUATED）。"
    )
    digest = GroundDigest(
        evidence_pack_id=pack.evidence_pack_id,
        source_ids=[s.source_id for s in pack.sources],
        evidence_ids=[i.evidence_id for i in pack.items],
        suggestions=[],  # suggestion generation is a planner capability, not Ground
        evidence_gaps=[],
        retrieval_note=note,
        sources=list(pack.sources),
    )
    return GroundOutcome(
        digest=digest,
        pack=pack,
        error=None,
        categories=categories,
        user_row_count=len(user_rows),
        local_row_count=len(local_rows),
    )
