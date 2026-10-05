"""P0.7 — Minimal Revision Loop.

Closed loop, exactly as specified:

    V(n)
      -> evaluate_content_version        (P0.6; Part 1 + Part 3)
      -> RevisionInstruction             (compiled from revision_suggestions)
      -> revision_executor               (injected callable)
      -> create_revision -> V(n+1)       (P0.4)
      -> Fact Safety                     (P0.5, inside re-evaluation)
      -> re-evaluate
      -> repeat / stop

Design constraints this module obeys
------------------------------------
* It **reuses** P0.4/P0.5/P0.6 primitives outright and rewrites none of them.
* ``revision_executor`` is an injectable callable. No LLM/Skill is implemented
  here; tests inject a deterministic fake.
* ``ClaimIdentityRegistry`` is **task-level**: seeded once before the first
  revision, shared by V1->V2->V3 and by branches, and never updated by a
  failed revision.
* A failed revision is **retained for audit** but never becomes the current
  version: the cursor does not advance, the registry is not touched, and
  Part 3 is not re-run.
* ``max_iterations`` must be supplied by the caller as a positive integer.
  There is deliberately no product default (SPEC §23 / PIPELINE_SPEC §11 list
  "自动修改最大轮数" as TBD).
* The highest status this loop can reach is ``READY_FOR_HUMAN_REVIEW``.
  ``APPROVED`` / Gate C / publication are P0.8 and are never produced here.
* ``RETURN_TO_PART1`` only yields an explicit routing outcome. This module
  never touches Gate B and never mutates ``WorkflowStateMachine``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence
from uuid import uuid4

from api.evaluation import PART_EVALUATION, evaluate_content_version
from api.fact_safety import ClaimIdentityRegistry
from api.rubric_loader import Rubric
from api.schemas import (
    Claim,
    EvaluationResult,
    EvidencePack,
    RevisionInstruction,
)
from api.versioning import ContentVersionStore

# --------------------------------------------------------------------------- #
# loop statuses
# --------------------------------------------------------------------------- #
#: The loop finished normally and the content is ready for a human. This is the
#: ceiling of P0.7 — never an approval.
READY_FOR_HUMAN_REVIEW = "READY_FOR_HUMAN_REVIEW"

# --- P0.6 evaluation statuses consumed by this loop, kept local on purpose ---
# Importing them from evaluation_part3 would couple the loop to Part 3 internals;
# these are string contracts, so they are re-declared as literals and asserted
# against the live constants in tests.
STATUS_COMPLETED = "COMPLETED"
STATUS_HUMAN_REVIEW_PENDING = "HUMAN_REVIEW_PENDING"
STATUS_REVISION_RECOMMENDED = "REVISION_RECOMMENDED"
STATUS_RETURN_TO_PART1 = "RETURN_TO_PART1"
STATUS_INSUFFICIENT_CONTEXT = "INSUFFICIENT_CONTEXT"

#: Loop-level outcomes that are NOT terminal-with-version-advance.
STOP_READY_FOR_HUMAN_REVIEW = READY_FOR_HUMAN_REVIEW
STOP_RETURN_TO_PART1 = "RETURN_TO_PART1"
STOP_INSUFFICIENT_CONTEXT = "INSUFFICIENT_CONTEXT"
STOP_FACT_LOCK_FAILED = "FACT_LOCK_FAILED"
STOP_MAX_ITERATIONS_REACHED = "MAX_ITERATIONS_REACHED"
STOP_EXECUTOR_FAILED = "EXECUTOR_FAILED"

#: Statuses that mean "the loop is done, hand off to a human".
_SUCCESS_STATUSES = frozenset({STATUS_COMPLETED, STATUS_HUMAN_REVIEW_PENDING})

#: Statuses this loop may ever write into a loop outcome. ``APPROVED`` absent.
ALLOWED_LOOP_OUTCOMES = frozenset(
    {
        STOP_READY_FOR_HUMAN_REVIEW,
        STOP_RETURN_TO_PART1,
        STOP_INSUFFICIENT_CONTEXT,
        STOP_FACT_LOCK_FAILED,
        STOP_MAX_ITERATIONS_REACHED,
        STOP_EXECUTOR_FAILED,
    }
)

FORBIDDEN_STATUSES = frozenset({"APPROVED", "PUBLISHED"})


class RevisionLoopError(ValueError):
    """Raised when the loop is misconfigured (never used to mask failures)."""


class RevisionExecutorError(RuntimeError):
    """Raised when an injected executor violates its contract."""


class RevisionExecutor:
    """Interface an executable revision producer must satisfy.

    P0.7 ships **no** implementation. A real Revision / Transcreation Skill will
    implement this and be injected. Returning a ``str`` is the whole contract:
    the new content of the next version.
    """

    def execute(
        self,
        instruction: RevisionInstruction,
        current_content: str,
    ) -> str:  # pragma: no cover - protocol only
        raise NotImplementedError


#: Either an object with ``.execute(instruction, content)`` or a bare callable
#: ``(instruction, content) -> str``.
ExecutorLike = Any


# --------------------------------------------------------------------------- #
# instruction compilation (pure)
# --------------------------------------------------------------------------- #
def compile_revision_instructions(
    result: EvaluationResult,
    *,
    base_version_id: str,
    task_id: str,
) -> List[RevisionInstruction]:
    """Turn one evaluation's advisory suggestions into executable commands.

    Pure function: reads ``result.revision_suggestions`` and binds them to a
    base version. It never touches the store, the registry, or the original
    suggestion objects.
    """
    if not base_version_id:
        raise RevisionLoopError("base_version_id is required to compile instructions")

    instructions: List[RevisionInstruction] = []
    for index, suggestion in enumerate(result.revision_suggestions or []):
        text = str(getattr(suggestion, "instruction", "") or "").strip()
        if not text:
            # Mirror Part 3's fail-closed stance: a command with no instruction
            # is malformed, not something to silently drop.
            raise RevisionLoopError(
                f"revision suggestion {index + 1} has no instruction to compile"
            )
        instructions.append(
            RevisionInstruction(
                instruction_id=str(uuid4()),
                task_id=task_id or result.task_id,
                base_version_id=base_version_id,
                source_evaluation_id=result.evaluation_id,
                target_dimension=str(getattr(suggestion, "target_dimension", "") or ""),
                problem=str(getattr(suggestion, "problem", "") or ""),
                instruction=text,
                preserve=[str(p) for p in (getattr(suggestion, "preserve", None) or [])],
            )
        )
    return instructions


def _run_executor(
    executor: ExecutorLike,
    instruction: RevisionInstruction,
    current_content: str,
) -> str:
    """Call an injected executor, normalising contract violations to errors.

    Every failure mode here is a *runtime* executor failure, so it is reported
    as :class:`RevisionExecutorError` and the loop stops fail-closed. A missing
    or non-callable executor is a misconfiguration, but at loop-run time it is
    indistinguishable from an executor that refuses to run — and either way the
    correct behaviour is to stop rather than to mutate content.
    """
    if executor is None:
        raise RevisionExecutorError("no revision_executor configured")

    try:
        if hasattr(executor, "execute"):
            produced = executor.execute(instruction, current_content)
        elif callable(executor):
            produced = executor(instruction, current_content)
        else:
            raise RevisionExecutorError(
                "revision_executor must be callable or expose execute(instruction, content)"
            )
    except RevisionExecutorError:
        raise
    except Exception as exc:  # executor blew up -> the loop must stop, not guess
        raise RevisionExecutorError(f"revision executor failed: {exc}") from exc

    if not isinstance(produced, str) or not produced.strip():
        raise RevisionExecutorError("revision executor must return non-empty content")
    return produced


# --------------------------------------------------------------------------- #
# loop state
# --------------------------------------------------------------------------- #
@dataclass
class RevisionLoopState:
    """Task-level state owned by :class:`RevisionLoopRunner`.

    Version *history* is deliberately not stored here — it is derived from
    ``ContentVersionStore.get_history(task_id)`` / ``get_lineage(...)`` so there
    is exactly one authoritative version chain.
    """

    task_id: str
    current_version_id: str
    claim_registry: ClaimIdentityRegistry
    max_iterations: int
    latest_evaluation: Optional[EvaluationResult] = None
    instructions: List[RevisionInstruction] = field(default_factory=list)
    iteration_count: int = 0
    stop_reason: str = ""
    final_status: str = ""


# --------------------------------------------------------------------------- #
# runner
# --------------------------------------------------------------------------- #
class RevisionLoopRunner:
    """Drives the closed revision loop for one task at a time."""

    def __init__(
        self,
        version_store: ContentVersionStore,
        claims: Mapping[str, Claim],
        evidence_pack: Optional[EvidencePack],
        *,
        revision_executor: Optional[ExecutorLike] = None,
        judge: Any = None,
        rubric: Optional[Rubric] = None,
        task_context: Optional[Dict[str, Any]] = None,
    ):
        self._store = version_store
        self._claims = claims
        self._evidence_pack = evidence_pack
        self._executor = revision_executor
        self._judge = judge
        self._rubric = rubric
        self._task_context = task_context
        self._states: Dict[str, RevisionLoopState] = {}

    # -- public API -------------------------------------------------------- #
    def start(
        self,
        task_id: str,
        initial_version_id: str,
        *,
        max_iterations: int,
    ) -> RevisionLoopState:
        """Begin a loop and **seed the task-level registry** from V1.

        Seeding is mandatory: P0.5 only auto-registers *added* claims, so every
        retained claim must already be known before the first revision.
        """
        self._require_positive_int(max_iterations)

        version = self._store.get_version(initial_version_id)
        if version.task_id != task_id:
            raise RevisionLoopError(
                f"task_id mismatch: {task_id!r} != version task {version.task_id!r}"
            )
        if version.parent_version_id is not None:
            raise RevisionLoopError(
                f"loop must start from an initial version, got revision {initial_version_id}"
            )

        registry = ClaimIdentityRegistry()
        seed = {
            claim_id: self._claims[claim_id]
            for claim_id in version.claim_ids
            if claim_id in self._claims
        }
        registry.commit(seed)

        state = RevisionLoopState(
            task_id=task_id,
            current_version_id=initial_version_id,
            claim_registry=registry,
            max_iterations=max_iterations,
        )
        self._states[task_id] = state
        return state

    def get(self, task_id: str) -> RevisionLoopState:
        try:
            return self._states[task_id]
        except KeyError as exc:
            raise RevisionLoopError(f"unknown revision loop task: {task_id}") from exc

    def run(self, task_id: str) -> RevisionLoopState:
        """Run until a terminal condition, then return the state."""
        while True:
            state = self.get(task_id)
            if state.stop_reason:
                return state
            self.step(task_id)
            if self.get(task_id).stop_reason:
                return self.get(task_id)

    def step(self, task_id: str) -> RevisionLoopState:
        """Advance the loop by exactly one evaluation/revision cycle."""
        state = self.get(task_id)

        if state.stop_reason:
            return state

        if state.iteration_count >= state.max_iterations:
            return self._stop(state, STOP_MAX_ITERATIONS_REACHED)

        result = self._evaluate(state.current_version_id)
        state.latest_evaluation = result

        outcome = self._classify(result)
        if outcome is not None:
            return self._stop(state, outcome)

        # status is REVISION_RECOMMENDED from here on.
        instructions = compile_revision_instructions(
            result,
            base_version_id=state.current_version_id,
            task_id=state.task_id,
        )
        if not instructions:
            # "Revision recommended" with nothing to execute would loop forever
            # on the same version. Fail closed instead of spinning.
            return self._stop(state, STOP_FACT_LOCK_FAILED)

        state.instructions.extend(instructions)

        try:
            new_content = self._advance_content(state.current_version_id, instructions)
        except RevisionExecutorError:
            # Executor failure must not corrupt state: nothing was created yet.
            return self._stop(state, STOP_EXECUTOR_FAILED)

        candidate = self._store.create_revision(
            state.current_version_id,
            new_content,
            task_id=state.task_id,
            claim_ids=list(self._store.get_version(state.current_version_id).claim_ids),
        )

        recheck = self._evaluate(candidate.content_version_id)

        if recheck.status not in _SUCCESS_STATUSES:
            # Fact Safety failed (or Part 3 was inconclusive): keep the version
            # for audit, do NOT advance the cursor, do NOT touch the registry.
            state.latest_evaluation = recheck
            return self._stop(state, STOP_FACT_LOCK_FAILED)

        # Safe revision: the cursor advances. The registry was already updated
        # inside the P0.5 engine for the added claims, atomically.
        state.current_version_id = candidate.content_version_id
        state.latest_evaluation = recheck
        state.iteration_count += 1

        follow_up = self._classify(recheck)
        if follow_up is not None:
            return self._stop(state, follow_up)

        if state.iteration_count >= state.max_iterations:
            return self._stop(state, STOP_MAX_ITERATIONS_REACHED)

        return state

    # -- internals --------------------------------------------------------- #
    @staticmethod
    def _require_positive_int(max_iterations: Any) -> None:
        if isinstance(max_iterations, bool) or not isinstance(max_iterations, int):
            raise RevisionLoopError("max_iterations must be a positive integer")
        if max_iterations < 1:
            raise RevisionLoopError("max_iterations must be a positive integer")

    def _evaluate(self, content_version_id: str) -> EvaluationResult:
        return evaluate_content_version(
            content_version_id,
            self._store,
            self._claims,
            self._evidence_pack,
            judge=self._judge,
            registry=self._current_registry(),
            rubric=self._rubric,
            task_context=self._task_context,
        )

    def _current_registry(self) -> Optional[ClaimIdentityRegistry]:
        for state in self._states.values():
            return state.claim_registry
        return None

    def _advance_content(
        self,
        current_version_id: str,
        instructions: Sequence[RevisionInstruction],
    ) -> str:
        """Apply instructions in order through the injected executor."""
        content = self._store.get_version(current_version_id).content
        for instruction in instructions:
            if instruction.base_version_id != current_version_id:
                raise RevisionExecutorError(
                    f"instruction {instruction.instruction_id} bound to "
                    f"{instruction.base_version_id}, expected {current_version_id}"
                )
            content = _run_executor(self._executor, instruction, content)
        return content

    @staticmethod
    def _classify(result: EvaluationResult) -> Optional[str]:
        """Map an evaluation result to a terminal loop outcome, if any."""
        if result.status in _SUCCESS_STATUSES:
            return STOP_READY_FOR_HUMAN_REVIEW
        if result.status == STATUS_RETURN_TO_PART1 or result.return_to_part1:
            return STOP_RETURN_TO_PART1
        if result.status == STATUS_INSUFFICIENT_CONTEXT:
            return STOP_INSUFFICIENT_CONTEXT
        if result.status == STATUS_REVISION_RECOMMENDED:
            return None  # not terminal: continue the loop
        # Any unknown status is treated as inconclusive, never as success.
        return STOP_INSUFFICIENT_CONTEXT

    def _stop(self, state: RevisionLoopState, reason: str) -> RevisionLoopState:
        if reason not in ALLOWED_LOOP_OUTCOMES:
            raise RevisionLoopError(f"illegal loop outcome: {reason}")
        if reason in FORBIDDEN_STATUSES:
            raise RevisionLoopError(f"forbidden outcome: {reason}")
        state.stop_reason = reason
        state.final_status = reason
        return state
