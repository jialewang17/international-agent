"""Thin HTTP endpoints for the in-memory Plan-centered session prototype.

Trusted evidence assessment and actual Plan model inference are NOT HTTP
endpoints here. Integrate them from the existing Ground and Plan services.

P0-1: ``POST /api/story-tasks`` now runs the real deterministic Ground chain
(api/ground_service.py) after creating the session. Success attaches a real
EvidencePack (stored in the shared canonical store) and advances to PLAN;
an empty result keeps the task in GROUND with truthful gaps. It never writes
``evidence_status``, never touches Gate B, and never fakes completion.
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, ConfigDict

from api import ground_service
from api.evidence_store import EvidencePackStore
from api.story_session import (
    JointConfirmation, NarrativePlan, UserPlanFeedback, story_session_store,
)
from api.workflow import WorkflowError

logger = logging.getLogger("chinastory.story_router")

router = APIRouter(prefix="/api/story-tasks", tags=["story-workflow"])

#: Bound by api/main.py to the *shared* canonical EvidencePackStore so packs
#: built here are visible to Coverage/Binding/Claim paths. Not bound in
#: standalone test apps, where tests must bind their own store explicitly.
_evidence_pack_store: Optional[EvidencePackStore] = None


def bind_evidence_pack_store(store: EvidencePackStore) -> None:
    global _evidence_pack_store
    _evidence_pack_store = store


class StoryStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    topic: str = Field(min_length=1)
    user_materials: str = ""


def _call(action):
    try:
        return {"ok": True, "data": action()}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="story task not found") from exc
    except (ValueError, WorkflowError) as exc:
        raise HTTPException(status_code=409, detail={"gate": getattr(exc, "gate", "input"), "reason": str(exc)}) from exc


@router.post("")
def start_story(body: StoryStartRequest):
    return _call(lambda: _start(body))


def _start(body: StoryStartRequest):
    session = story_session_store.start(body.topic, body.user_materials)
    task_id = session.task.task_id
    try:
        outcome = ground_service.run_ground(body.topic, body.user_materials)
    except Exception:  # noqa: BLE001 - task creation must not 500 on ground faults
        logger.exception("ground integration crashed for task %s", task_id)
        story_session_store.record_ground_failure(
            task_id,
            ["Ground 检索服务发生未预期异常，原因已记录日志；不伪造证据包。"],
            "ground_unexpected_error",
        )
        return story_session_store.snapshot(task_id)
    if outcome.succeeded:
        if _evidence_pack_store is None:
            logger.error(
                "evidence pack store not bound in story_router; cannot persist "
                "the pack for task %s", task_id,
            )
            story_session_store.record_ground_failure(
                task_id,
                ["Ground 检索成功，但 EvidencePack 存储未绑定，已按未完成处理。"],
                "evidence_store_not_bound",
            )
        else:
            _evidence_pack_store.put(outcome.pack)
            story_session_store.attach_ground(task_id, outcome.digest)
    else:
        logger.warning(
            "ground empty for task %s (error=%r); keeping GROUND stage",
            task_id, outcome.error,
        )
        story_session_store.record_ground_failure(
            task_id, outcome.digest.evidence_gaps, outcome.digest.retrieval_note
        )
    return story_session_store.snapshot(task_id)


@router.get("/{task_id}")
def read_story(task_id: str):
    return _call(lambda: story_session_store.snapshot(task_id))


@router.post("/{task_id}/plan")
def receive_plan(task_id: str, body: NarrativePlan):
    # A draft Plan is not a factual claim, and does not mark evidence sufficient.
    return _call(lambda: _save_plan(task_id, body))


def _save_plan(task_id: str, body: NarrativePlan):
    story_session_store.save_plan(task_id, body)
    return story_session_store.snapshot(task_id)


@router.post("/{task_id}/feedback")
def feedback(task_id: str, body: UserPlanFeedback):
    return _call(lambda: _feedback(task_id, body.instruction))


def _feedback(task_id: str, instruction: str):
    story_session_store.feedback_text(task_id, instruction)
    # Do not pretend feedback text was interpreted into a new Plan by an LLM.
    return {"feedback_recorded": True, "planner_update_pending": True,
            "task": story_session_store.snapshot(task_id)}


@router.post("/{task_id}/confirm")
def confirm(task_id: str, body: JointConfirmation):
    return _call(lambda: _confirm(task_id, body))


def _confirm(task_id: str, body: JointConfirmation):
    story_session_store.confirm(task_id, body)
    return story_session_store.snapshot(task_id)


@router.post("/{task_id}/enter-create")
def enter_create(task_id: str):
    return _call(lambda: _enter_create(task_id))


def _enter_create(task_id: str):
    story_session_store.enter_create(task_id)
    return story_session_store.snapshot(task_id)
