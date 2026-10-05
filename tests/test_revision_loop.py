"""P0.7 — Minimal Revision Loop tests.

The executor injected here is a deterministic fake. Production ships no
executor (and no LLM/Skill) on purpose — a real Revision Skill plugs into the
same interface later.
"""
from __future__ import annotations

from typing import List, Optional

import pytest

from api.fact_safety import ClaimIdentityRegistry
from api.evaluation_part3 import (
    STATUS_COMPLETED,
    STATUS_HUMAN_REVIEW_PENDING,
    STATUS_INSUFFICIENT_CONTEXT,
    STATUS_RETURN_TO_PART1,
    STATUS_REVISION_RECOMMENDED,
)
from api.revision_loop import (
    ALLOWED_LOOP_OUTCOMES,
    FORBIDDEN_STATUSES,
    READY_FOR_HUMAN_REVIEW,
    STOP_EXECUTOR_FAILED,
    STOP_FACT_LOCK_FAILED,
    STOP_INSUFFICIENT_CONTEXT,
    STOP_MAX_ITERATIONS_REACHED,
    STOP_RETURN_TO_PART1,
    RevisionExecutorError,
    RevisionLoopError,
    RevisionLoopRunner,
    compile_revision_instructions,
)
from api.schemas import (
    Claim,
    EvaluationResult,
    EvidenceItem,
    EvidencePack,
    EvidenceSpan,
    RevisionInstruction,
    RevisionSuggestion,
    Source,
)
from api.versioning import ContentVersionStore

DIMS = [
    "cross_cultural_comprehensibility",
    "cultural_expression_quality",
    "audience_fit",
    "narrative_engagement_potential",
    "genre_platform_fit",
    "naturalness_non_sloganeering",
]


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def make_pack(pack_id: str = "pack-1") -> EvidencePack:
    return EvidencePack(
        evidence_pack_id=pack_id,
        items=[
            EvidenceItem(
                evidence_id="e1",
                source_id="s1",
                statement="fact",
                spans=[EvidenceSpan(span_id="sp1", source_id="s1", text="fact")],
            )
        ],
        sources=[Source(source_id="s1", uri="u", title="t")],
    )


class StubJudge:
    """Deterministic judge returning an explicit status shape per call."""

    def __init__(self, behaviour: Optional[List[str]] = None):
        # A queue of part-3 statuses to emit; empty -> clean COMPLETED.
        self._behaviour = list(behaviour or [])
        self.calls = 0
        self.prompt_version = "test"

    @property
    def name(self) -> str:
        return "stub"

    def judge(self, content, task_context, rubric):
        from api.evaluation_part3 import JudgeDimensionOutput, JudgeOutput

        self.calls += 1
        status = self._behaviour[min(self.calls - 1, len(self._behaviour) - 1)] if self._behaviour else "clean"

        dims = [
            JudgeDimensionOutput(
                dimension_id=d,
                score=4,
                confidence=0.9,
                rationale="ok",
                problems=["needs polish"] if status == "revise" else [],
                revision_suggestion=(
                    "tighten the opening" if status == "revise" else ""
                ),
            )
            for d in DIMS
        ]

        issues = []
        suggestions = []
        if status == "revise":
            issues = [
                {
                    "issue_id": "pi-1",
                    "dimension_id": "cross_cultural_comprehensibility",
                    "problem": "opening is abstract",
                }
            ]
            suggestions = [
                {
                    "target_dimension": "cross_cultural_comprehensibility",
                    "problem": "opening is abstract",
                    "instruction": "tighten the opening",
                    "preserve": ["verified_facts"],
                }
            ]

        return JudgeOutput(
            dimensions=dims,
            priority_issues=issues,
            revision_suggestions=suggestions,
            return_to_part1=(status == "return"),
        )


class FakeExecutor:
    """Deterministic executor: appends a marker per instruction."""

    def __init__(self, name: str = "rev"):
        self.name = name
        self.seen: List[str] = []

    def execute(self, instruction: RevisionInstruction, current_content: str) -> str:
        self.seen.append(instruction.instruction_id)
        return f"{current_content} | revised:{instruction.instruction}"


def build_task(store: ContentVersionStore, claim_ids: List[str]):
    pack = make_pack()
    claims = {
        cid: Claim(claim_id=cid, text=f"{cid} text", evidence_ids=["e1"])
        for cid in claim_ids
    }
    version = store.create_initial_version(
        "task-1", "hello world", evidence_pack_id=pack.evidence_pack_id, claim_ids=list(claim_ids)
    )
    return pack, claims, version


def make_runner(store, claims, pack, **kwargs):
    kwargs.setdefault("judge", StubJudge())
    return RevisionLoopRunner(store, claims, pack, **kwargs)


# --------------------------------------------------------------------------- #
# compile: the pure suggestion -> instruction step
# --------------------------------------------------------------------------- #
def test_instruction_fields_are_all_bound():
    result = EvaluationResult(
        evaluation_id="eval-42",
        content_version_id="v1",
        part="evaluation",
        status=STATUS_REVISION_RECOMMENDED,
        task_id="task-1",
        revision_suggestions=[
            RevisionSuggestion(
                target_dimension="audience_fit",
                problem="too dense",
                instruction="shorten sentences",
                preserve=["verified_facts"],
            )
        ],
    )

    out = compile_revision_instructions(result, base_version_id="v1", task_id="task-1")

    assert len(out) == 1
    instr = out[0]
    assert instr.instruction_id
    assert instr.task_id == "task-1"
    assert instr.base_version_id == "v1"
    assert instr.source_evaluation_id == "eval-42"
    assert instr.target_dimension == "audience_fit"
    assert instr.problem == "too dense"
    assert instr.instruction == "shorten sentences"
    assert instr.preserve == ["verified_facts"]


def test_compile_does_not_mutate_the_suggestion():
    suggestion = RevisionSuggestion(instruction="do a thing", target_dimension="audience_fit")
    before = suggestion.model_dump()
    result = EvaluationResult(
        evaluation_id="e1",
        content_version_id="v1",
        part="evaluation",
        status=STATUS_REVISION_RECOMMENDED,
        revision_suggestions=[suggestion],
    )

    compile_revision_instructions(result, base_version_id="v1", task_id="t")

    assert suggestion.model_dump() == before


def test_compile_rejects_empty_instruction():
    result = EvaluationResult(
        evaluation_id="e1",
        content_version_id="v1",
        part="evaluation",
        status=STATUS_REVISION_RECOMMENDED,
        revision_suggestions=[RevisionSuggestion(problem="something")],
    )
    with pytest.raises(RevisionLoopError):
        compile_revision_instructions(result, base_version_id="v1", task_id="t")


# --------------------------------------------------------------------------- #
# clean -> READY_FOR_HUMAN_REVIEW
# --------------------------------------------------------------------------- #
def test_clean_evaluation_reaches_ready_for_human_review():
    store = ContentVersionStore()
    pack, claims, version = build_task(store, ["c1"])
    runner = make_runner(store, claims, pack)
    state = runner.start("task-1", version.content_version_id, max_iterations=3)

    runner.run("task-1")

    assert state.stop_reason == READY_FOR_HUMAN_REVIEW
    assert state.final_status == READY_FOR_HUMAN_REVIEW
    # not a single new version was created
    assert len(store.get_history("task-1")) == 1


def test_clean_loop_never_outputs_approved():
    store = ContentVersionStore()
    pack, claims, version = build_task(store, ["c1"])
    runner = make_runner(store, claims, pack)
    runner.start("task-1", version.content_version_id, max_iterations=3)
    runner.run("task-1")

    state = runner.get("task-1")
    assert state.final_status not in FORBIDDEN_STATUSES
    assert state.final_status in ALLOWED_LOOP_OUTCOMES


# --------------------------------------------------------------------------- #
# revision -> V2, then safe -> re-evaluation
# --------------------------------------------------------------------------- #
def test_revision_creates_v2_from_v1():
    store = ContentVersionStore()
    pack, claims, version = build_task(store, ["c1"])
    judge = StubJudge(["revise", "clean"])
    runner = make_runner(store, claims, pack, judge=judge, revision_executor=FakeExecutor())
    runner.start("task-1", version.content_version_id, max_iterations=3)

    state = runner.step("task-1")

    history = store.get_history("task-1")
    assert len(history) == 2
    v2 = history[-1]
    assert v2.parent_version_id == version.content_version_id
    assert state.current_version_id == v2.content_version_id
    # A clean re-evaluation lands on HUMAN_REVIEW_PENDING (P0.6 never returns
    # COMPLETED-from-Part-3 without an explicit judge status; a clean pass goes
    # to human review, never to approval).
    assert state.latest_evaluation.status in {STATUS_COMPLETED, STATUS_HUMAN_REVIEW_PENDING}
    assert state.stop_reason == READY_FOR_HUMAN_REVIEW


def test_safe_v2_is_re_evaluated_and_advances():
    store = ContentVersionStore()
    pack, claims, version = build_task(store, ["c1"])
    judge = StubJudge(["revise", "clean"])
    runner = make_runner(store, claims, pack, judge=judge, revision_executor=FakeExecutor())
    runner.start("task-1", version.content_version_id, max_iterations=3)

    runner.run("task-1")

    # V1 evaluated, V2 created, V2 evaluated => judge called twice
    assert judge.calls == 2
    assert runner.get("task-1").iteration_count == 1


def test_revision_instruction_is_recorded_for_audit():
    store = ContentVersionStore()
    pack, claims, version = build_task(store, ["c1"])
    judge = StubJudge(["revise", "clean"])
    runner = make_runner(store, claims, pack, judge=judge, revision_executor=FakeExecutor())
    runner.start("task-1", version.content_version_id, max_iterations=3)
    runner.run("task-1")

    instructions = runner.get("task-1").instructions
    # The first cycle compiles one instruction per evaluation suggestion. The
    # stub judge emits one explicit suggestion, but Part 3 also derives one
    # suggestion per dimension carrying a revision_suggestion, so assert the
    # audit-critical properties instead of a brittle exact count.
    assert instructions
    assert all(i.base_version_id == version.content_version_id for i in instructions)
    assert all(i.source_evaluation_id for i in instructions)
    assert all(i.instruction for i in instructions)


# --------------------------------------------------------------------------- #
# V2 blocked -> current stays V1, failed V2 retained for audit
# --------------------------------------------------------------------------- #
def test_blocked_v2_keeps_current_at_v1():
    store = ContentVersionStore()
    pack, claims, version = build_task(store, ["c1"])
    # V2 adds an unbound claim c2 -> Part 1 Fact Safety locks.
    claims["c2"] = Claim(claim_id="c2", text="unsupported brand new fact")

    judge = StubJudge(["revise"])
    runner = make_runner(store, claims, pack, judge=judge, revision_executor=FakeExecutor())
    runner.start("task-1", version.content_version_id, max_iterations=3)

    # Make the created revision introduce c2.
    original_create = store.create_revision

    def create_with_c2(parent_version_id, content, **kwargs):
        kwargs["claim_ids"] = ["c1", "c2"]
        return original_create(parent_version_id, content, **kwargs)

    store.create_revision = create_with_c2  # type: ignore[assignment]

    state = runner.step("task-1")

    assert state.current_version_id == version.content_version_id
    assert state.stop_reason == STOP_FACT_LOCK_FAILED
    assert state.iteration_count == 0


def test_failed_v2_is_retained_in_store_for_audit():
    store = ContentVersionStore()
    pack, claims, version = build_task(store, ["c1"])
    claims["c2"] = Claim(claim_id="c2", text="unsupported brand new fact")
    judge = StubJudge(["revise"])
    runner = make_runner(store, claims, pack, judge=judge, revision_executor=FakeExecutor())
    runner.start("task-1", version.content_version_id, max_iterations=3)

    original_create = store.create_revision

    def create_with_c2(parent_version_id, content, **kwargs):
        kwargs["claim_ids"] = ["c1", "c2"]
        return original_create(parent_version_id, content, **kwargs)

    store.create_revision = create_with_c2  # type: ignore[assignment]
    runner.step("task-1")

    history = store.get_history("task-1")
    assert len(history) == 2  # failed V2 still exists
    failed = history[-1]
    assert failed.parent_version_id == version.content_version_id
    # but it is not the cursor
    assert runner.get("task-1").current_version_id == version.content_version_id


def test_failed_revision_does_not_pollute_registry():
    store = ContentVersionStore()
    pack, claims, version = build_task(store, ["c1"])
    claims["c2"] = Claim(claim_id="c2", text="unsupported brand new fact")
    judge = StubJudge(["revise"])
    runner = make_runner(store, claims, pack, judge=judge, revision_executor=FakeExecutor())
    runner.start("task-1", version.content_version_id, max_iterations=3)

    original_create = store.create_revision

    def create_with_c2(parent_version_id, content, **kwargs):
        kwargs["claim_ids"] = ["c1", "c2"]
        return original_create(parent_version_id, content, **kwargs)

    store.create_revision = create_with_c2  # type: ignore[assignment]
    runner.step("task-1")

    registry = runner.get("task-1").claim_registry
    # c2 must NOT have been committed by the failed revision
    with pytest.raises(Exception):
        registry.check(claims["c2"])


# --------------------------------------------------------------------------- #
# registry lifecycle
# --------------------------------------------------------------------------- #
def test_registry_is_seeded_from_v1():
    store = ContentVersionStore()
    pack, claims, version = build_task(store, ["c1", "c2x"])
    runner = make_runner(store, claims, pack)
    state = runner.start("task-1", version.content_version_id, max_iterations=2)

    # both V1 claims are already known -> retained checks pass
    state.claim_registry.check(claims["c1"])
    state.claim_registry.check(claims["c2x"])


def test_registry_is_shared_across_v1_v2_v3():
    store = ContentVersionStore()
    pack, claims, version = build_task(store, ["c1"])
    judge = StubJudge(["revise", "revise", "clean"])
    runner = make_runner(store, claims, pack, judge=judge, revision_executor=FakeExecutor())
    state = runner.start("task-1", version.content_version_id, max_iterations=3)

    registry = state.claim_registry
    runner.run("task-1")

    # same object identity across every revision
    assert runner.get("task-1").claim_registry is registry
    # c1 is retained throughout, so it must still resolve to one identity
    registry.check(claims["c1"])


def test_registry_requires_positive_max_iterations():
    store = ContentVersionStore()
    pack, claims, version = build_task(store, ["c1"])
    runner = make_runner(store, claims, pack)

    with pytest.raises(RevisionLoopError):
        runner.start("task-1", version.content_version_id, max_iterations=0)
    with pytest.raises(RevisionLoopError):
        runner.start("task-1", version.content_version_id, max_iterations=-1)
    with pytest.raises(RevisionLoopError):
        runner.start("task-1", version.content_version_id, max_iterations=True)


# --------------------------------------------------------------------------- #
# terminal statuses
# --------------------------------------------------------------------------- #
def test_return_to_part1_stops_without_creating_a_version():
    store = ContentVersionStore()
    pack, claims, version = build_task(store, ["c1"])
    judge = StubJudge(["return"])
    runner = make_runner(store, claims, pack, judge=judge, revision_executor=FakeExecutor())
    runner.start("task-1", version.content_version_id, max_iterations=3)

    runner.run("task-1")

    state = runner.get("task-1")
    assert state.stop_reason == STOP_RETURN_TO_PART1
    assert len(store.get_history("task-1")) == 1  # no V2


def test_return_to_part1_is_only_routing_not_a_gate():
    """The loop must not touch Gate B or WorkflowStateMachine."""
    import api.revision_loop as rl

    assert not hasattr(rl, "workflow_state_machine")
    assert not hasattr(rl, "GateDecision")


def test_insufficient_context_stops():
    store = ContentVersionStore()
    pack, claims, version = build_task(store, ["c1"])
    runner = make_runner(store, claims, pack, judge=None, revision_executor=FakeExecutor())
    runner.start("task-1", version.content_version_id, max_iterations=3)

    runner.run("task-1")

    state = runner.get("task-1")
    assert state.stop_reason == STOP_INSUFFICIENT_CONTEXT
    assert len(store.get_history("task-1")) == 1


def test_max_iterations_stops_finite():
    store = ContentVersionStore()
    pack, claims, version = build_task(store, ["c1"])
    judge = StubJudge(["revise"])  # always recommends revision
    executor = FakeExecutor()
    runner = make_runner(store, claims, pack, judge=judge, revision_executor=executor)
    runner.start("task-1", version.content_version_id, max_iterations=2)

    runner.run("task-1")

    state = runner.get("task-1")
    assert state.stop_reason in {STOP_MAX_ITERATIONS_REACHED, STOP_FACT_LOCK_FAILED}
    assert state.iteration_count <= 2
    assert len(store.get_history("task-1")) <= 3


def test_revision_recommended_without_instructions_fails_closed():
    store = ContentVersionStore()
    pack, claims, version = build_task(store, ["c1"])

    class NoSuggestionJudge(StubJudge):
        def judge(self, content, task_context, rubric):
            from api.evaluation_part3 import JudgeDimensionOutput, JudgeOutput

            dims = [
                JudgeDimensionOutput(
                    dimension_id=d, score=4, confidence=0.9, problems=["a problem"]
                )
                for d in DIMS
            ]
            return JudgeOutput(dimensions=dims)

    runner = make_runner(
        store, claims, pack, judge=NoSuggestionJudge(), revision_executor=FakeExecutor()
    )
    runner.start("task-1", version.content_version_id, max_iterations=3)
    runner.run("task-1")

    state = runner.get("task-1")
    # issues exist -> REVISION_RECOMMENDED, but nothing executable -> stop
    assert state.latest_evaluation.status == STATUS_REVISION_RECOMMENDED
    assert state.stop_reason == STOP_FACT_LOCK_FAILED


# --------------------------------------------------------------------------- #
# executor contract
# --------------------------------------------------------------------------- #
def test_missing_executor_fails_closed():
    store = ContentVersionStore()
    pack, claims, version = build_task(store, ["c1"])
    judge = StubJudge(["revise"])
    runner = make_runner(store, claims, pack, judge=judge, revision_executor=None)
    runner.start("task-1", version.content_version_id, max_iterations=3)

    runner.run("task-1")

    state = runner.get("task-1")
    assert state.stop_reason == STOP_EXECUTOR_FAILED
    assert state.current_version_id == version.content_version_id
    assert len(store.get_history("task-1")) == 1


def test_executor_exception_fails_closed():
    store = ContentVersionStore()
    pack, claims, version = build_task(store, ["c1"])

    def boom(instruction, content):
        raise RuntimeError("executor exploded")

    runner = make_runner(store, claims, pack, judge=StubJudge(["revise"]), revision_executor=boom)
    runner.start("task-1", version.content_version_id, max_iterations=3)
    runner.run("task-1")

    state = runner.get("task-1")
    assert state.stop_reason == STOP_EXECUTOR_FAILED
    assert state.current_version_id == version.content_version_id
    assert len(store.get_history("task-1")) == 1  # nothing was created


def test_executor_returning_empty_fails_closed():
    store = ContentVersionStore()
    pack, claims, version = build_task(store, ["c1"])
    runner = make_runner(
        store, claims, pack, judge=StubJudge(["revise"]), revision_executor=lambda i, c: ""
    )
    runner.start("task-1", version.content_version_id, max_iterations=3)
    runner.run("task-1")

    assert runner.get("task-1").stop_reason == STOP_EXECUTOR_FAILED


def test_executor_can_be_a_bare_callable():
    store = ContentVersionStore()
    pack, claims, version = build_task(store, ["c1"])
    judge = StubJudge(["revise", "clean"])
    runner = make_runner(
        store,
        claims,
        pack,
        judge=judge,
        revision_executor=lambda instruction, content: content + " [fixed]",
    )
    runner.start("task-1", version.content_version_id, max_iterations=3)
    runner.run("task-1")

    state = runner.get("task-1")
    assert state.stop_reason == READY_FOR_HUMAN_REVIEW
    assert state.current_version_id != version.content_version_id


def test_instruction_bound_to_wrong_version_is_rejected():
    store = ContentVersionStore()
    pack, claims, version = build_task(store, ["c1"])
    judge = StubJudge(["revise", "clean"])
    runner = make_runner(store, claims, pack, judge=judge, revision_executor=FakeExecutor())
    runner.start("task-1", version.content_version_id, max_iterations=3)

    bad = RevisionInstruction(
        instruction_id="i1",
        task_id="task-1",
        base_version_id="some-other-version",
        source_evaluation_id="e1",
        instruction="x",
    )
    with pytest.raises(RevisionExecutorError):
        runner._advance_content(version.content_version_id, [bad])


# --------------------------------------------------------------------------- #
# P0.7 / P0.8 boundary
# --------------------------------------------------------------------------- #
def test_no_outcome_is_approved_or_published():
    assert "APPROVED" not in ALLOWED_LOOP_OUTCOMES
    assert "PUBLISHED" not in ALLOWED_LOOP_OUTCOMES
    assert FORBIDDEN_STATUSES == {"APPROVED", "PUBLISHED"}


def test_start_rejects_a_revision_as_entry_point():
    store = ContentVersionStore()
    pack, claims, version = build_task(store, ["c1"])
    child = store.create_revision(version.content_version_id, "revised", claim_ids=["c1"])
    runner = make_runner(store, claims, pack)

    with pytest.raises(RevisionLoopError):
        runner.start("task-1", child.content_version_id, max_iterations=2)


def test_loop_does_not_create_new_evaluation_model():
    """There is exactly one EvaluationResult; the loop only consumes it."""
    import api.revision_loop as rl

    assert not hasattr(rl, "EvaluationResult2")
    assert not hasattr(rl, "LoopEvaluationResult")
