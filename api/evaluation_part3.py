"""Part 3 — ChinaStory Evaluation Skill (D1-D6 content quality).

Design stance for P0.6
----------------------
There is no real LLM judge runtime yet, and inventing one from keyword/length
heuristics would produce numbers with no research basis. So this module ships
*no* scoring logic at all:

  * :class:`ChinaStoryJudge` is a protocol that a real judge must implement.
  * With no judge configured, Part 3 fails closed as ``INSUFFICIENT_CONTEXT``;
    it never fabricates a D1-D6 score.
  * Tests inject a stub judge (``tests/`` only) to exercise the pipeline.

Everything the judge returns is validated against the loaded rubric before it
is accepted. Malformed output is rejected, never silently repaired.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol, Sequence
from uuid import uuid4

from api.rubric_loader import (
    MAX_SCORE,
    MIN_SCORE,
    CANONICAL_DIMENSION_IDS,
    Rubric,
    load_rubric,
)
from api.schemas import (
    DimensionResult,
    EvaluationAuditMetadata,
    EvaluationIssue,
    EvaluationResult,
    RevisionSuggestion,
)

PART3 = "part3_chinastory_quality"

# Part 3 statuses. ``APPROVED`` is deliberately absent: final approval is
# Gate C / P0.8, never something the evaluation skill may grant.
STATUS_CREATED = "CREATED"
STATUS_PRECHECK = "PRECHECK"
STATUS_INSUFFICIENT_CONTEXT = "INSUFFICIENT_CONTEXT"
STATUS_SCORING = "SCORING"
STATUS_COMPLETED = "COMPLETED"
STATUS_REVISION_RECOMMENDED = "REVISION_RECOMMENDED"
STATUS_RETURN_TO_PART1 = "RETURN_TO_PART1"
STATUS_HUMAN_REVIEW_PENDING = "HUMAN_REVIEW_PENDING"

ALLOWED_STATUSES = frozenset(
    {
        STATUS_CREATED,
        STATUS_PRECHECK,
        STATUS_INSUFFICIENT_CONTEXT,
        STATUS_SCORING,
        STATUS_COMPLETED,
        STATUS_REVISION_RECOMMENDED,
        STATUS_RETURN_TO_PART1,
        STATUS_HUMAN_REVIEW_PENDING,
    }
)

FORBIDDEN_STATUSES = frozenset({"APPROVED", "PUBLISHED"})

#: Judge priorities from SKILL_SPEC §10, used only for deterministic ordering.
PRIORITY_ORDER: Sequence[str] = (
    "cultural_misreading",
    "cross_cultural_comprehensibility",
    "audience_fit",
    "genre_platform_fit",
    "narrative_engagement_potential",
    "naturalness_non_sloganeering",
)

#: System-level issue/suggestion targets the spec allows outside D1-D6.
#: Anything else must be a canonical dimension id.
SYSTEM_TARGETS = frozenset({"system", "part1"})


class Part3Error(ValueError):
    """Raised when Part 3 cannot produce a trustworthy result."""


@dataclass
class JudgeDimensionOutput:
    """Raw judge output for one dimension (pre-validation)."""

    dimension_id: str
    score: Any
    confidence: Any
    rationale: str = ""
    evidence_spans: List[Dict[str, Any]] = None  # type: ignore[assignment]
    problems: List[str] = None  # type: ignore[assignment]
    revision_suggestion: str = ""


@dataclass
class JudgeOutput:
    dimensions: List[JudgeDimensionOutput]
    priority_issues: List[Dict[str, Any]] = None  # type: ignore[assignment]
    revision_suggestions: List[Dict[str, Any]] = None  # type: ignore[assignment]
    #: Structured Part 3 -> Part 1 routing signal (SKILL_SPEC §9
    #: ``return_to_part1``). Routing is driven by this flag alone; the wording of
    #: any rationale/problem text must never influence it.
    return_to_part1: bool = False


class ChinaStoryJudge(Protocol):
    """Interface a real D1-D6 judge must satisfy."""

    @property
    def name(self) -> str: ...

    @property
    def model(self) -> str: ...

    def judge(self, content: str, task_context: Dict[str, Any], rubric: Rubric) -> JudgeOutput: ...


def evaluate_part3(
    content_version_id: str,
    content: str,
    task_context: Optional[Dict[str, Any]],
    judge: Optional[ChinaStoryJudge],
    *,
    rubric: Optional[Rubric] = None,
    part1_status: str = "",
    evaluation_id: str = "",
    task_id: str = "",
) -> EvaluationResult:
    """Run Part 3 content-quality evaluation. Fails closed by design."""
    rubric = rubric or load_rubric()
    evaluation_id = evaluation_id or str(uuid4())

    base = dict(
        evaluation_id=evaluation_id,
        content_version_id=content_version_id,
        part=PART3,
        task_id=task_id,
    )

    if judge is None:
        return EvaluationResult(
            **base,
            status=STATUS_INSUFFICIENT_CONTEXT,
            issues=["no ChinaStory judge configured; refusing to fabricate dimension scores"],
            rubric_version=rubric.rubric_version,
            human_review="PENDING",
            audit=EvaluationAuditMetadata(
                evaluator="none",
                evaluator_type="unconfigured",
                rubric_version=rubric.rubric_version,
                part1_status=part1_status,
            ),
        )

    if not content or not content.strip():
        return EvaluationResult(
            **base,
            status=STATUS_INSUFFICIENT_CONTEXT,
            issues=["empty content"],
            rubric_version=rubric.rubric_version,
            audit=EvaluationAuditMetadata(
                evaluator=judge.name,
                evaluator_type="judge",
                rubric_version=rubric.rubric_version,
                part1_status=part1_status,
            ),
        )

    try:
        raw = judge.judge(content, task_context or {}, rubric)
    except Part3Error:
        raise
    except Exception as exc:  # judge blew up -> never silently pass
        raise Part3Error(f"judge failed: {exc}") from exc

    dimensions = _validate_dimensions(raw, rubric)
    issues, suggestions = _collect_issues(raw, rubric)
    returns_to_part1 = _structured_return_to_part1(raw)

    status = STATUS_RETURN_TO_PART1 if returns_to_part1 else _resolve_status(dimensions, issues)

    audit = EvaluationAuditMetadata(
        evaluator=judge.name,
        evaluator_type="judge",
        rubric_version=rubric.rubric_version,
        prompt_version=getattr(judge, "prompt_version", ""),
        calibration_set_version=getattr(judge, "calibration_set_version", ""),
        task_context_version=str((task_context or {}).get("version", "")),
        part1_status=part1_status,
    )

    return EvaluationResult(
        **base,
        status=status,
        issues=[i.problem for i in issues],
        scores={d.dimension_id: float(d.score) for d in dimensions},
        rubric_version=rubric.rubric_version,
        dimensions=dimensions,
        priority_issues=issues,
        revision_suggestions=suggestions,
        overall_score=None,  # rubric §5.2: no default aggregation
        return_to_part1=returns_to_part1,
        human_review="PENDING",
        audit=audit,
    )


# --------------------------------------------------------------------------- #
# validation
# --------------------------------------------------------------------------- #
def _validate_dimensions(raw: JudgeOutput, rubric: Rubric) -> List[DimensionResult]:
    if raw is None or not getattr(raw, "dimensions", None):
        raise Part3Error("judge returned no dimensions")

    expected = rubric.dimension_ids
    seen: Dict[str, DimensionResult] = {}

    for item in raw.dimensions:
        dimension_id = getattr(item, "dimension_id", None)
        if dimension_id not in CANONICAL_DIMENSION_IDS:
            raise Part3Error(f"unknown dimension from judge: {dimension_id!r}")
        if dimension_id in seen:
            raise Part3Error(f"duplicate dimension from judge: {dimension_id}")
        if dimension_id not in expected:
            raise Part3Error(f"dimension not in rubric: {dimension_id}")

        score = item.score
        if isinstance(score, bool) or not isinstance(score, int):
            raise Part3Error(f"{dimension_id}: score must be an integer, got {score!r}")
        if not MIN_SCORE <= score <= MAX_SCORE:
            raise Part3Error(
                f"{dimension_id}: score {score} outside allowed range {MIN_SCORE}-{MAX_SCORE}"
            )

        confidence = item.confidence
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
            raise Part3Error(f"{dimension_id}: confidence must be numeric, got {confidence!r}")
        if not 0.0 <= float(confidence) <= 1.0:
            raise Part3Error(f"{dimension_id}: confidence {confidence} outside 0.0-1.0")

        seen[dimension_id] = DimensionResult(
            dimension_id=dimension_id,
            score=int(score),
            confidence=float(confidence),
            rationale=str(item.rationale or ""),
            evidence_spans=_normalize_spans(item.evidence_spans),
            problems=[str(p) for p in (item.problems or [])],
            revision_suggestion=str(item.revision_suggestion or ""),
        )

    missing = [d for d in expected if d not in seen]
    if missing:
        raise Part3Error(f"missing dimensions from judge: {', '.join(missing)}")

    # Canonical order, independent of the order the judge emitted.
    return [seen[d] for d in expected]


def _normalize_spans(spans: Any) -> List[Any]:
    from api.schemas import EvidenceSpan

    normalized = []
    for span in spans or []:
        if isinstance(span, EvidenceSpan):
            normalized.append(span)
        elif isinstance(span, dict):
            normalized.append(
                EvidenceSpan(
                    span_id=str(span.get("span_id", "")),
                    source_id=str(span.get("source_id", "")),
                    text=str(span.get("text", "")),
                    start=span.get("start"),
                    end=span.get("end"),
                )
            )
        else:
            raise Part3Error(f"malformed evidence span: {span!r}")
    return normalized


def _valid_target(target: str, *, field: str) -> None:
    """A target must be a canonical dimension id or an allowed system target."""
    if target in SYSTEM_TARGETS or target in CANONICAL_DIMENSION_IDS:
        return
    raise Part3Error(f"{field}: unknown dimension target: {target!r}")


def _collect_issues(raw: JudgeOutput, rubric: Rubric):
    issues: List[EvaluationIssue] = []
    suggestions: List[RevisionSuggestion] = []

    for index, item in enumerate(raw.priority_issues or []):
        if not isinstance(item, dict):
            raise Part3Error(f"malformed priority issue: {item!r}")

        problem = str(item.get("problem") or "").strip()
        if not problem:
            raise Part3Error(f"priority issue {index + 1} has no problem content")

        dimension_id = str(item.get("dimension_id") or "").strip()
        if dimension_id:
            _valid_target(dimension_id, field=f"priority issue {index + 1}")

        issues.append(
            EvaluationIssue(
                issue_id=str(item.get("issue_id") or f"pi-{index + 1}"),
                dimension_id=dimension_id,
                severity=str(item.get("severity", "")),
                problem=problem,
                reason=str(item.get("reason", "")),
                evidence_spans=_normalize_spans(item.get("evidence_spans")),
            )
        )

    # Derive issues from per-dimension problems when the judge only reported
    # problems inside dimensions (allowed by rubric §13).
    reported = {(i.dimension_id, i.problem) for i in issues}
    for dimension in raw.dimensions:
        for problem in dimension.problems or []:
            text = str(problem).strip()
            if not text:
                raise Part3Error(f"{dimension.dimension_id}: empty problem text")
            key = (dimension.dimension_id, text)
            if key in reported:
                continue
            reported.add(key)
            issues.append(
                EvaluationIssue(
                    issue_id=f"{dimension.dimension_id}-{len(issues) + 1}",
                    dimension_id=dimension.dimension_id,
                    problem=text,
                )
            )

    for index, item in enumerate(raw.revision_suggestions or []):
        if not isinstance(item, dict):
            raise Part3Error(f"malformed revision suggestion: {item!r}")

        instruction = str(item.get("instruction") or "").strip()
        if not instruction:
            raise Part3Error(f"revision suggestion {index + 1} has no instruction")

        target = str(item.get("target_dimension") or "").strip()
        if target:
            _valid_target(target, field=f"revision suggestion {index + 1}")

        suggestions.append(
            RevisionSuggestion(
                target_dimension=target,
                problem=str(item.get("problem", "")),
                instruction=instruction,
                preserve=[str(p) for p in (item.get("preserve") or [])],
            )
        )

    # Fall back to per-dimension suggestions so no advice is lost.
    covered = {s.target_dimension for s in suggestions}
    for dimension in raw.dimensions:
        if dimension.dimension_id in covered:
            continue
        if dimension.revision_suggestion:
            suggestions.append(
                RevisionSuggestion(
                    target_dimension=dimension.dimension_id,
                    instruction=str(dimension.revision_suggestion),
                )
            )

    issues.sort(key=_issue_sort_key)
    return issues, suggestions


def _issue_sort_key(issue: EvaluationIssue):
    try:
        rank = PRIORITY_ORDER.index(issue.dimension_id)
    except ValueError:
        rank = len(PRIORITY_ORDER)
    return (rank, issue.issue_id)


def _structured_return_to_part1(raw: JudgeOutput) -> bool:
    """Read the structured Part 3 -> Part 1 routing signal.

    Part 3 never adjudicates factual truth. It only forwards a suspicion back to
    Part 1, and it does so via the explicit ``return_to_part1`` flag declared by
    the SKILL_SPEC §9 output contract. Free-text wording is deliberately ignored
    so behaviour cannot drift with a judge's phrasing.
    """
    return bool(getattr(raw, "return_to_part1", False))


def _resolve_status(dimensions: List[DimensionResult], issues: List[EvaluationIssue]) -> str:
    """Map findings to a permitted status. Never returns ``APPROVED``."""
    if issues:
        return STATUS_REVISION_RECOMMENDED
    # A clean pass still needs a human; the skill has no approval authority.
    return STATUS_HUMAN_REVIEW_PENDING
