"""Thin HTTP endpoints for the in-memory Plan-centered session prototype.

Trusted evidence assessment and actual Plan model inference are NOT HTTP
endpoints here. Integrate them from the existing Ground and Plan services.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, ConfigDict

from api.story_session import (
    JointConfirmation, NarrativePlan, UserPlanFeedback, story_session_store,
)
from api.workflow import WorkflowError

router = APIRouter(prefix="/api/story-tasks", tags=["story-workflow"])


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
    return story_session_store.snapshot(session.task.task_id)


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
