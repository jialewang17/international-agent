"""评论理解与回应工具：ABSA -> 本地证据 -> 人设化回复。"""

from __future__ import annotations
import ast
import json
import re
from typing import Any, Dict, List
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool

from model.factory import get_text_generation_model
from tools.kb_local import build_persona, resolve_platform, retrieve_statements
from utils.path import get_prompt_dir
from utils.skill_registry import format_skills_by_ids

VALID_CATEGORIES = {
    "celebrity", "governance", "genocide", "forced labor", "concentration camp",
    "Chinese region", "Muslim region", "Western region", "manufactory", "culture",
    "food", "language", "women and children rights", "sports", "null",
}

def _llm_text(prompt: str) -> str:
    result = get_text_generation_model().invoke([HumanMessage(content=prompt)])
    raw = getattr(result, "content", "") or ""
    if isinstance(raw, list):
        raw = "".join(x.get("text", "") if isinstance(x, dict) else str(x) for x in raw)
    return str(raw).strip()

def _parse_topics(raw: str) -> List[Dict[str, str]]:
    topics: List[Dict[str, str]] = []
    # Prompt historically returns bracket triplets; accept 3+ element lists defensively.
    for chunk in re.findall(r"\[[^\[\]]+\]", raw or ""):
        try:
            vals = ast.literal_eval(chunk)
        except Exception:
            continue
        if not isinstance(vals, (list, tuple)) or len(vals) < 3:
            continue
        aspect = str(vals[0]).strip()
        # Historical examples are not perfectly schema-consistent; choose recognized category.
        category = next((str(v).strip() for v in vals[1:] if str(v).strip() in VALID_CATEGORIES), "null")
        polarity = next((str(v).strip().lower() for v in vals[1:] if str(v).strip().lower() in {"positive", "negative"}), "negative")
        topics.append({"aspect": aspect, "category": category, "polarity": polarity})
    if not topics:
        topics = [{"aspect": "", "category": "null", "polarity": "negative"}]
    return topics

def run_absa(text: str) -> Dict[str, Any]:
    text = (text or "").strip()
    if not text:
        return {"topics": [], "absa_raw": "", "error": "text 不能为空"}
    template = (get_prompt_dir() / "absa_topic_prompt.txt").read_text(encoding="utf-8")
    raw = _llm_text(template.format(text=text))
    return {"topics": _parse_topics(raw), "absa_raw": raw}

@tool
def analyze_topic(text: str) -> str:
    """
    描述：对评论执行主题/方面识别，输出 topics 与 ABSA 原始结果。
    使用时机：用户只要求识别评论主题，而不是生成完整回复时。
    """
    return json.dumps(run_absa(text), ensure_ascii=False)

@tool
def intl_comm_reply(
    comment: str,
    country: str = "America",
    identity: str = "political_commentator",
    tone: str = "serious",
    tendency: str = "negative",
    max_words: int = 50,
    use_emoji: bool = True,
    platform: str = "twitter",
) -> str:
    """
    描述：【评论回应工具】评论主题识别 -> 本地证据检索 -> 人设/平台约束回复；结果仅供人工审核。
    """
    comment = (comment or "").strip()
    if not comment:
        return json.dumps({"error": "comment 不能为空", "reply": "", "topics": [], "evidence_used": []}, ensure_ascii=False)

    absa = run_absa(comment)
    topics = absa.get("topics", [])
    categories = [t["category"] for t in topics if t.get("category") and t["category"] != "null"]
    evidence = retrieve_statements(categories, limit_per_cat=1, query=comment) if categories else []

    persona = build_persona(identity, tone, country)
    plat = resolve_platform(platform)
    template = (get_prompt_dir() / "reply_generation_prompt.txt").read_text(encoding="utf-8")
    skill_block = format_skills_by_ids(["intl_comm"])
    evidence_block = "\n".join(
        f"- [{e.get('category','')}] {e.get('statement','')} (source: {e.get('source','')})"
        for e in evidence
    ) or "- No verified local evidence was retrieved. Keep factual claims general and do not invent details."
    topic_summary = ", ".join(
        f"{t.get('aspect') or 'topic'} / {t.get('category')} / {t.get('polarity')}" for t in topics
    )

    prompt = template.format(
        platform=plat["platform_label"],
        comment=comment,
        tendency=tendency,
        identity_label=persona["identity_label"],
        tone_label=persona["tone_label"],
        max_words=max(1, int(max_words)),
        emoji_instruction="emoji may be used sparingly." if use_emoji else "do not use emoji.",
        identity_prompt=persona["identity_prompt"],
        tone_prompt=persona["tone_prompt"],
        platform_style=plat["platform_style"],
        topic_summary=topic_summary,
        skill_block=skill_block,
        evidence_block=evidence_block,
        country=country,
    )
    try:
        reply = _llm_text(prompt)
    except Exception as exc:
        return json.dumps({
            "error": f"回复生成失败: {exc}",
            "topics": topics, "absa_raw": absa.get("absa_raw", ""),
            "evidence_used": evidence, "reply": "",
        }, ensure_ascii=False)

    return json.dumps({
        "topics": topics,
        "absa_raw": absa.get("absa_raw", ""),
        "evidence_used": evidence,
        "reply": reply,
        "identity": persona["identity_label"],
        "tone": persona["tone_label"],
        "country": country,
        "platform": plat["platform_label"],
        "prompt_files": ["prompt/absa_topic_prompt.txt", "prompt/reply_generation_prompt.txt"],
        "pipeline": "Define -> Ground -> Plan -> Create -> Revise & Audit -> Approve",
        "pipeline_steps": [
            {"id": "DEFINE", "label": "Define", "status": "ok", "detail": "reply task"},
            {"id": "GROUND", "label": "Ground", "status": "ok" if evidence else "warn", "detail": f"evidence={len(evidence)}"},
            {"id": "PLAN", "label": "Plan", "status": "ok", "detail": f"{identity}/{tone}"},
            {"id": "CREATE", "label": "Create", "status": "ok" if reply else "warn", "detail": "reply draft"},
            {"id": "REVISE_AUDIT", "label": "Revise & Audit", "status": "warn", "detail": "human review available"},
            {"id": "APPROVE", "label": "Approve", "status": "warn", "detail": "awaiting human approval"},
        ],
        "gates": [
            {"id": "A", "label": "Task Confirmation", "status": "ok", "detail": "reply task confirmed"},
            {"id": "B", "label": "Evidence Exception", "status": "ok" if evidence else "warn", "detail": "thin evidence" if not evidence else "clear"},
            {"id": "C", "label": "Final Approval", "status": "warn", "detail": "awaiting human approval"},
        ],
    }, ensure_ascii=False)
