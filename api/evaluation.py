"""Evaluation integration orchestrator for P0.6.

    ContentVersion
         |
         +-- Part 1  Fact / Evidence      (api.evaluation_part1)
         +-- Part 3  ChinaStory quality   (api.evaluation_part3)
         |
    EvaluationResult

Scope stops at ``EvaluationResult``. There is deliberately no revision
instruction execution, no ``create_revision`` call, no V2, and no re-evaluation
loop — that whole revision loop is P0.7, and final approval is P0.8 (Gate C).
"""
from __future__ import annotations

from typing import Any, Dict, Mapping, Optional, Tuple
from uuid import uuid4

from api.evaluation_part1 import PART1, STATUS_PASS as PART1_PASS, evaluate_part1
from api.evaluation_part3 import (
    STATUS_INSUFFICIENT_CONTEXT,
    STATUS_RETURN_TO_PART1,
    STATUS_HUMAN_REVIEW_PENDING,
    ChinaStoryJudge,
    evaluate_part3,
)
from api.rubric_loader import Rubric, load_rubric
from api.schemas import Claim, EvaluationResult, EvidencePack
from api.versioning import ContentVersionStore

PART_EVALUATION = "evaluation"


def evaluate_content_version(
    content_version_id: str,
    version_store: ContentVersionStore,
    claims: Mapping[str, Claim],
    evidence_pack: Optional[EvidencePack],
    *,
    judge: Optional[ChinaStoryJudge] = None,
    registry: Any = None,
    rubric: Optional[Rubric] = None,
    task_context: Optional[Dict[str, Any]] = None,
    evaluation_id: str = "",
) -> EvaluationResult:
    """Evaluate one ContentVersion through Part 1 and (conditionally) Part 3.

    The store is only *read*. No new version is created anywhere on this path.
    """
    rubric = rubric or load_rubric()
    evaluation_id = evaluation_id or str(uuid4())

    part1 = evaluate_part1(
        content_version_id,
        version_store,
        claims,
        evidence_pack,
        registry,
        evaluation_id=f"{evaluation_id}-p1",
    )

    # SKILL_SPEC §3: a blocked Part 1 does not proceed to a normal Part 3 rating.
    if part1.status != PART1_PASS:
        return EvaluationResult(
            evaluation_id=evaluation_id,
            content_version_id=content_version_id,
            part=PART_EVALUATION,
            status=STATUS_RETURN_TO_PART1,
            issues=list(part1.issues),
            claim_traces=list(part1.claim_traces),
            task_id=part1.task_id,
            rubric_version=rubric.rubric_version,
            return_to_part1=True,
            human_review="PENDING",
            audit=part1.audit,
        )

    version = version_store.get_version(content_version_id)
    part3 = evaluate_part3(
        content_version_id,
        version.content,
        task_context,
        judge,
        rubric=rubric,
        part1_status=part1.status,
        evaluation_id=f"{evaluation_id}-p3",
        task_id=part1.task_id,
    )

    return EvaluationResult(
        evaluation_id=evaluation_id,
        content_version_id=content_version_id,
        part=PART_EVALUATION,
        status=part3.status,
        issues=list(part3.issues),
        claim_traces=list(part1.claim_traces),
        task_id=part1.task_id,
        rubric_version=part3.rubric_version,
        dimensions=part3.dimensions,
        priority_issues=part3.priority_issues,
        revision_suggestions=part3.revision_suggestions,
        overall_score=part3.overall_score,
        return_to_part1=part3.return_to_part1,
        real_audience_evaluation=part3.real_audience_evaluation,
        human_review=part3.human_review,
        audit=part3.audit,
    )
