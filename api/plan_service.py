"""P0-2: real Narrative Plan generation & revision via the existing model client.

Reuses ``model.factory.get_text_generation_model()`` (the same ChatOpenAI-
compatible client the generation path uses). No new model framework, no new
credentials path: config comes from ``config/model.yaml`` (profile
``text_generation``), keys from the environment (.env). No key -> explicit
``MODEL_UNAVAILABLE`` failure; there is **no** hardcoded fallback plan and
this service never invents sources, people, quotes, or findings.

Hard rules:
- Input is only the current Story Task, the attached Ground digest, and the
  canonical EvidencePack. The prompt shows evidence ids + statements (+ the
  existing 用户上传/本地库 distinction); the model may only reference ids
  from that menu.
- Every evidence id in a produced plan is validated against the pack. Ids
  that do not exist are dropped and recorded as evidence gaps (never kept,
  never silently rewritten).
- Plans produced here are DRAFT proposals: ``evidence_status`` semantics stay
  untouched (Gate B remains the only writer of SUFFICIENT).
- The plan_revision pipeline: a revision is only "SUCCEEDED" after it passed
  through ``StorySessionStore.save_plan`` (new version number, old plan
  invalidated by the existing workflow rules).
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Sequence

from pydantic import BaseModel, ConfigDict, Field

from api.schemas import EvidencePack
from api.story_session import DraftTaskContext, GroundDigest, NarrativePlan, StorySection

logger = logging.getLogger("chinastory.plan")

__all__ = [
    "PlanServiceError",
    "PlanCandidate",
    "generate_plan_candidates",
    "revise_plan",
]

#: Retrieval budget for one planning call.
PLAN_MODEL_TIMEOUT_SECONDS = 90
MIN_DIRECTIONS = 2
MAX_DIRECTIONS = 3
MAX_SECTIONS = 8


class PlanServiceError(RuntimeError):
    """Explicit planner failure. ``code`` is machine-readable for the router."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class PlanCandidate(BaseModel):
    """One generated direction. ``plan.version`` is always 0 until saved."""

    model_config = ConfigDict(extra="forbid")
    angle: str
    plan: NarrativePlan


# --------------------------------------------------------------------------- #
# model client
# --------------------------------------------------------------------------- #

def _default_model() -> Any:
    from model.factory import ModelFactory

    try:
        return ModelFactory.create(
            profile="text_generation", timeout=PLAN_MODEL_TIMEOUT_SECONDS
        )
    except Exception as exc:  # credentials missing, bad config, no sdk ...
        raise PlanServiceError(
            "MODEL_UNAVAILABLE",
            f"规划模型客户端不可用（未伪造方案）：{type(exc).__name__}: "
            + str(exc).splitlines()[0][:300],
        ) from exc


def _call_model(model: Any, prompt: str) -> str:
    from langchain_core.messages import HumanMessage

    try:
        result = model.invoke([HumanMessage(content=prompt)])
    except Exception as exc:
        raise PlanServiceError(
            "MODEL_CALL_FAILED",
            f"规划模型调用失败（未伪造方案）：{type(exc).__name__}: "
            + str(exc).splitlines()[0][:300],
        ) from exc
    try:
        return result.content or ""
    except AttributeError as exc:
        raise PlanServiceError(
            "MODEL_OUTPUT_INVALID", "模型返回缺少文本内容"
        ) from exc


# --------------------------------------------------------------------------- #
# prompt
# --------------------------------------------------------------------------- #

def _evidence_menu(pack: EvidencePack) -> List[Dict[str, str]]:
    sources = {s.source_id: s for s in pack.sources}
    menu: List[Dict[str, str]] = []
    for item in pack.items:
        src = sources.get(item.source_id)
        menu.append({
            "evidence_id": item.evidence_id,
            "statement": item.statement,
            "source_type": (src.source_type if src else "") or "未标注",
            "source_uri": (src.uri if src else "") or "",
        })
    return menu


def _task_brief(task: DraftTaskContext) -> str:
    lines = [f"- 主题 topic：{task.topic}"]
    if task.audience:
        lines.append(f"- 目标受众：{task.audience}")
    if task.audience_knowledge and task.audience_knowledge != "unknown":
        lines.append(f"- 受众了解程度：{task.audience_knowledge}")
    if task.genre:
        lines.append(f"- 内容形式：{task.genre}")
    if task.language:
        lines.append(f"- 目标语言：{task.language}")
    if task.platform:
        lines.append(f"- 传播平台：{task.platform}")
    if task.user_requirements:
        lines.append(f"- 用户补充要求：{task.user_requirements}")
    return "\n".join(lines)


def _plan_prompt(brief: str, menu: List[Dict[str, str]], revision: Optional[Dict[str, Any]] = None) -> str:
    lines = [f"- [{m['evidence_id']}] ({m['source_type']}) {m['statement']}" for m in menu]
    evidence_block = "\n".join(lines) if lines else "（当前证据包为空）"
    revision_block = ""
    if revision is not None:
        revision_block = (
            "\n\n当前方案（将被替换，需吸收以下用户要求后产出新版本）：\n"
            + json.dumps(revision, ensure_ascii=False, indent=2)
            + "\n\n用户修改要求："
            + str(revision.get("user_instruction", ""))
        )
    return (
        "你是中国故事国际传播的叙事策划。基于下面给出的【任务简报】和【证据清单】，"
        f"提出 {MIN_DIRECTIONS}–{MAX_DIRECTIONS} 个相互明显区别的故事方向。\n\n"
        "硬性规则：\n"
        "1. 只能引用【证据清单】中真实存在的 evidence_id；绝不虚构证据 ID、来源、"
        "人物、机构、引文或数据。\n"
        "2. 证据不足以支撑的内容，写进该方向的 evidence_gaps 或对应 section 的 "
        "fact_gaps，并说明需要补充什么资料；不得伪装成已有依据。\n"
        "3. 方向之间在切入角度与目标信息上必须实质不同。\n"
        "4. 每个方向给出 2–" + str(MAX_SECTIONS) + " 个 section 的大纲，"
        "每个 section 标注计划使用的 evidence_ids。\n\n"
        "【任务简报】\n" + brief + revision_block +
        "\n\n【证据清单】\n" + evidence_block +
        "\n\n只输出严格 JSON，不要任何其他文字，结构如下：\n"
        '{"directions": [{"title": "...", "angle": "...", '
        '"central_message": "...", '
        '"sections": [{"title": "...", "purpose": "...", '
        '"evidence_ids": ["..."], "fact_gaps": ["..."]}], '
        '"evidence_gaps": ["..."]}]}\n'
    )


# --------------------------------------------------------------------------- #
# parse & validate
# --------------------------------------------------------------------------- #

def _extract_json(raw: str) -> Dict[str, Any]:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise PlanServiceError(
            "MODEL_OUTPUT_INVALID", f"模型输出不是合法 JSON：{exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise PlanServiceError("MODEL_OUTPUT_INVALID", "模型输出不是 JSON 对象")
    return payload


def _clean_str(value: Any, *, required: bool = False, field: str = "") -> str:
    text = str(value).strip() if value is not None else ""
    if required and not text:
        raise PlanServiceError("MODEL_OUTPUT_INVALID", f"模型输出缺少必填字段：{field}")
    return text


def _clean_str_list(value: Any) -> List[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise PlanServiceError("MODEL_OUTPUT_INVALID", "字符串列表字段格式错误")
    return [str(v).strip() for v in value if str(v).strip()]


def _validated_plan(direction: Any, valid_ids: set, pack: EvidencePack) -> NarrativePlan:
    if not isinstance(direction, dict):
        raise PlanServiceError("MODEL_OUTPUT_INVALID", "direction 必须是对象")
    title = _clean_str(direction.get("title"), required=True, field="title")
    angle = _clean_str(direction.get("angle")) or title
    central = _clean_str(direction.get("central_message"), required=True,
                         field="central_message")
    raw_sections = direction.get("sections")
    if not isinstance(raw_sections, list) or not (1 <= len(raw_sections) <= MAX_SECTIONS):
        raise PlanServiceError(
            "MODEL_OUTPUT_INVALID",
            f"每个方向需要 1–{MAX_SECTIONS} 个 section",
        )
    gaps: List[str] = _clean_str_list(direction.get("evidence_gaps"))
    sections: List[StorySection] = []
    for raw in raw_sections:
        if not isinstance(raw, dict):
            raise PlanServiceError("MODEL_OUTPUT_INVALID", "section 必须是对象")
        s_title = _clean_str(raw.get("title"), required=True, field="section.title")
        referenced = _clean_str_list(raw.get("evidence_ids"))
        unknown = [eid for eid in referenced if eid not in valid_ids]
        kept = [eid for eid in referenced if eid in valid_ids]
        s_gaps = _clean_str_list(raw.get("fact_gaps"))
        if unknown:
            # 模型引用了不存在的证据：剔除并如实记缺口，绝不保留假引用。
            s_gaps = s_gaps + [
                f"已剔除当前证据包中不存在的引用 {eid}；该处证据不足，需补检"
                for eid in unknown
            ]
            gaps = gaps + [
                f"「{s_title}」引用了不存在的证据 {eid}，已剔除" for eid in unknown
            ]
        sections.append(StorySection(
            title=s_title,
            purpose=_clean_str(raw.get("purpose")),
            evidence_ids=kept,
            fact_gaps=s_gaps,
        ))
    return NarrativePlan(
        version=0,
        title=title,
        central_message=central,
        selected_angles=[angle],
        excluded_angles=[],
        sections=sections,
        evidence_gaps=gaps,
        planning_status="DRAFT",
    )


def _validate_payload(payload: Dict[str, Any], pack: EvidencePack) -> List[PlanCandidate]:
    directions = payload.get("directions")
    if not isinstance(directions, list):
        raise PlanServiceError("MODEL_OUTPUT_INVALID", "模型输出缺少 directions 列表")
    if not (MIN_DIRECTIONS <= len(directions) <= MAX_DIRECTIONS):
        raise PlanServiceError(
            "MODEL_OUTPUT_INVALID",
            f"模型返回 {len(directions)} 个方向，要求 {MIN_DIRECTIONS}–{MAX_DIRECTIONS} 个",
        )
    valid_ids = {item.evidence_id for item in pack.items}
    candidates: List[PlanCandidate] = []
    seen_angles: set = set()
    for direction in directions:
        plan = _validated_plan(direction, valid_ids, pack)
        angle = plan.selected_angles[0] if plan.selected_angles else plan.title
        if angle in seen_angles:
            raise PlanServiceError(
                "MODEL_OUTPUT_INVALID", "模型返回的方向切入角度重复，不满足相互区别要求"
            )
        seen_angles.add(angle)
        candidates.append(PlanCandidate(angle=angle, plan=plan))
    return candidates


def _plan_to_revision_dict(plan: NarrativePlan) -> Dict[str, Any]:
    return plan.model_dump(mode="json", exclude={"version"})


# --------------------------------------------------------------------------- #
# public API
# --------------------------------------------------------------------------- #

def generate_plan_candidates(
    task: DraftTaskContext,
    ground: GroundDigest,
    pack: EvidencePack,
    *,
    model: Optional[Any] = None,
) -> List[PlanCandidate]:
    """Generate 2–3 distinct direction candidates from task + evidence."""
    if not pack.items:
        raise PlanServiceError(
            "PLAN_CONTEXT_INVALID",
            "当前证据包没有证据条目，无法生成方案（Ground 资料不充分，请补充主题或资料）",
        )
    model = model or _default_model()
    menu = _evidence_menu(pack)
    raw = _call_model(model, _plan_prompt(_task_brief(task), menu))
    return _validate_payload(_extract_json(raw), pack)


def revise_plan(
    task: DraftTaskContext,
    prior_plan: NarrativePlan,
    instruction: str,
    ground: GroundDigest,
    pack: EvidencePack,
    *,
    model: Optional[Any] = None,
) -> NarrativePlan:
    """Produce ONE revised plan from the prior plan + user instruction.

    Returns the (version=0) draft; the caller stores it via
    ``StorySessionStore.save_plan`` so the workflow assigns the real version.
    """
    if not pack.items:
        raise PlanServiceError(
            "PLAN_CONTEXT_INVALID",
            "当前证据包没有证据条目，无法修订方案（Ground 资料不充分）",
        )
    model = model or _default_model()
    menu = _evidence_menu(pack)
    revision = _plan_to_revision_dict(prior_plan)
    revision["user_instruction"] = instruction
    raw = _call_model(model, _plan_prompt(_task_brief(task), menu, revision=revision))
    candidates = _validate_payload(_extract_json(raw), pack)
    # A revision merges the user's intent into one coherent plan: use the
    # first direction as the revised plan (the model was asked to revise, not
    # to brainstorm; extra directions would duplicate the same intent).
    revised = candidates[0].plan
    return revised
