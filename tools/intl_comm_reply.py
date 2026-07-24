"""国际传播：按材料原版 Prompt 做主题识别（ABSA）与评论回复（两次模型调用）。"""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any, Dict, List, Tuple

from langchain_core.messages import HumanMessage
from langchain_core.tools import tool

from model.factory import get_element_extraction_model, get_text_generation_model
from tools.kb_local import build_persona, resolve_platform, retrieve_statements
from utils.path import ensure_task_dirs, get_prompt_dir
from utils.task_context import get_task_id


def _load_template(name: str) -> str:
    path = get_prompt_dir() / name
    return path.read_text(encoding="utf-8")


def _save_reply_outputs(payload: Dict[str, Any]) -> Dict[str, str]:
    """
    将本次生成的英文回复写入 sandbox/<task_id>/。
    返回 output_reply_path / output_json_path；无 task_id 或失败时返回空路径与说明。
    """
    task_id = get_task_id()
    if not task_id:
        return {
            "output_reply_path": "",
            "output_json_path": "",
            "save_note": "未找到任务 ID，跳过写入 sandbox",
        }

    try:
        task_dir = ensure_task_dirs(task_id)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        reply_path = task_dir / f"reply_{stamp}.txt"
        json_path = task_dir / f"reply_{stamp}.json"

        reply_text = str(payload.get("reply") or "").strip()
        reply_path.write_text(reply_text + ("\n" if reply_text else ""), encoding="utf-8")

        out = dict(payload)
        out["saved_at"] = datetime.now().isoformat()
        out["output_reply_path"] = str(reply_path)
        out["output_json_path"] = str(json_path)
        json_path.write_text(
            json.dumps(out, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return {
            "output_reply_path": str(reply_path),
            "output_json_path": str(json_path),
            "save_note": "已写入 sandbox",
        }
    except Exception as e:
        return {
            "output_reply_path": "",
            "output_json_path": "",
            "save_note": f"写入 sandbox 失败: {e}",
        }


def _llm_text(model: Any, prompt: str) -> str:
    result = model.invoke([HumanMessage(content=prompt)])
    raw = getattr(result, "content", "") or ""
    if isinstance(raw, list):
        raw = "".join(
            (x.get("text", "") if isinstance(x, dict) else str(x)) for x in raw
        )
    return str(raw).strip()


def _parse_triplets(raw: str) -> List[Dict[str, str]]:
    """解析材料格式: [aspect, category, polarity] 或偶发四段。"""
    topics: List[Dict[str, str]] = []
    for m in re.finditer(r"\[([^\]]+)\]", raw or ""):
        parts = [p.strip().strip("'\"") for p in m.group(1).split(",")]
        parts = [p for p in parts if p]
        if len(parts) >= 3:
            # 兼容参考案例里偶发的四段：[a, b, category, polarity]
            if len(parts) >= 4:
                aspect = parts[0]
                category = parts[-2]
                polarity = parts[-1]
            else:
                aspect, category, polarity = parts[0], parts[1], parts[2]
            polarity_l = polarity.lower()
            if "positive" in polarity_l:
                polarity = "positive"
            elif "negative" in polarity_l:
                polarity = "negative"
            topics.append(
                {
                    "aspect": aspect,
                    "category": category,
                    "polarity": polarity,
                }
            )
    return topics


def _categories_from_topics(topics: List[Dict[str, str]]) -> List[str]:
    cats: List[str] = []
    for t in topics:
        cat = (t.get("category") or "").strip()
        if not cat or cat.lower() == "null":
            continue
        # 材料参考案例里出现过 human rights，映射到本地库可用类别
        if cat.lower() in {"human rights", "human right"}:
            cat = "governance"
        if cat not in cats:
            cats.append(cat)
    return cats


def build_absa_prompt(text: str) -> str:
    tpl = _load_template("absa_topic_prompt.txt")
    return tpl.replace("{text}", text)


def build_reply_prompt(
    *,
    comment: str,
    tendency: str,
    identity_label: str,
    identity_prompt: str,
    tone_label: str,
    tone_prompt: str,
    max_words: int,
    use_emoji: bool,
    topics: List[Dict[str, str]],
    evidence: List[Dict[str, str]],
    country: str,
    platform: str = "twitter",
    platform_style: str = "",
) -> str:
    tpl = _load_template("reply_generation_prompt.txt")
    topic_summary = ", ".join(
        f"{t.get('aspect')}|{t.get('category')}|{t.get('polarity')}" for t in topics
    ) or "null"
    evidence_lines: List[str] = []
    if evidence:
        for ev in evidence:
            evidence_lines.append(
                f"As for ({ev.get('category')}), you can refer to the information given from ({ev.get('statement')})"
            )
    else:
        evidence_lines.append(
            "As for (governance), you can refer to the information given from "
            "(Xinjiang's development, social stability, and people's improving livelihoods "
            "are best shown through facts and local people's lived experience.)"
        )
    emoji_instruction = (
        "you can add some emojis to make it looks more naturally."
        if use_emoji
        else "do not use emojis."
    )
    plat = resolve_platform(platform)
    platform_label = plat.get("platform_label", "twitter")
    style = (platform_style or plat.get("platform_style") or "").strip()

    return (
        tpl.replace("{platform}", platform_label)
        .replace("{comment}", comment)
        .replace("{tendency}", tendency)
        .replace("{identity_label}", identity_label)
        .replace("{tone_label}", tone_label)
        .replace("{max_words}", str(max_words))
        .replace("{emoji_instruction}", emoji_instruction)
        .replace("{identity_prompt}", identity_prompt.strip())
        .replace("{tone_prompt}", tone_prompt.strip())
        .replace("{platform_style}", style)
        .replace("{topic_summary}", topic_summary)
        .replace("{evidence_block}", "\n".join(evidence_lines))
        .replace("{country}", country)
    )


def run_absa(text: str) -> Tuple[List[Dict[str, str]], str]:
    prompt = build_absa_prompt(text)
    raw = _llm_text(get_element_extraction_model(), prompt)
    return _parse_triplets(raw), raw


def run_reply_generation(
    *,
    comment: str,
    country: str,
    identity: str,
    tone: str,
    tendency: str,
    max_words: int,
    use_emoji: bool,
    topics: List[Dict[str, str]],
    platform: str = "twitter",
) -> Tuple[str, List[Dict[str, str]], str, Dict[str, Any]]:
    persona = build_persona(identity=identity, tone=tone, country=country)
    plat = resolve_platform(platform)
    persona.update(plat)
    cats = _categories_from_topics(topics)
    evidence = retrieve_statements(cats or ["governance"], limit_per_cat=2)
    prompt = build_reply_prompt(
        comment=comment,
        tendency=tendency,
        identity_label=persona.get("identity_label", identity),
        identity_prompt=persona.get("identity_prompt", ""),
        tone_label=persona.get("tone_label", tone),
        tone_prompt=persona.get("tone_prompt", ""),
        max_words=max_words,
        use_emoji=use_emoji,
        topics=topics,
        evidence=evidence,
        country=country,
        platform=plat.get("platform_label", "twitter"),
        platform_style=plat.get("platform_style", ""),
    )
    raw = _llm_text(get_text_generation_model(), prompt)
    return raw, evidence, prompt, persona


@tool
def analyze_topic(text: str) -> str:
    """
    描述：按材料原版 ABSA 提示词识别评论主题三元组 [aspect, category, polarity]。
    使用时机：需要对海外社媒文本做主题/方面情感分析时。
    输入：
    - text（必填）：待识别文本
    输出：JSON，含 topics、absa_raw
    """
    text = (text or "").strip()
    if not text:
        return json.dumps({"error": "text 不能为空", "topics": []}, ensure_ascii=False)
    try:
        topics, raw = run_absa(text)
        return json.dumps(
            {
                "topics": topics,
                "absa_raw": raw,
                "prompt_file": "prompt/absa_topic_prompt.txt",
            },
            ensure_ascii=False,
        )
    except Exception as e:
        return json.dumps({"error": f"主题识别失败: {e}", "topics": []}, ensure_ascii=False)


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
    描述：国际传播评论自动回复（讲好中国故事：澄清 + 事实叙事 + 平台适配）。
    流程：1) ABSA 提示词识别主题；2) 按主题检索本地论据；
    3) 叙事向回复提示词生成拟人回复（澄清不实后落到可分享的正面事实），并按平台调整风格。
    使用时机：用户给出海外社媒评论，需要完整「主题识别+中国立场拟人回复/讲好中国故事」时。
    输入：
    - comment（必填）：待回复评论原文
    - country：发帖人国家，默认 America
    - identity：political_commentator / comedian / online_influencer / scientist / rapper
    - tone：serious / optimistic / humorous / sarcastic / cold（默认 serious；勿默认 sarcastic）
    - tendency：negative 或 positive，默认 negative
    - max_words：回复字数限制，默认 50
    - use_emoji：是否使用表情，默认 true
    - platform：twitter / facebook / instagram / tiktok / youtube / weibo，默认 twitter
    输出：JSON，含 topics、absa_raw、evidence_used、reply、platform、prompt_files；
         成功时另含 output_reply_path（英文回复 .txt）、output_json_path（完整结果 .json），
         写入当前会话 sandbox/<task_id>/。
    """
    comment = (comment or "").strip()
    if not comment:
        return json.dumps({"error": "comment 不能为空", "topics": [], "reply": ""}, ensure_ascii=False)

    try:
        topics, absa_raw = run_absa(comment)
        reply, evidence, _reply_prompt, persona = run_reply_generation(
            comment=comment,
            country=country,
            identity=identity,
            tone=tone,
            tendency=tendency,
            max_words=int(max_words),
            use_emoji=bool(use_emoji),
            topics=topics,
            platform=platform,
        )
        if not reply:
            return json.dumps(
                {
                    "error": "回复生成为空（可能触发模型安全限制）",
                    "topics": topics,
                    "absa_raw": absa_raw,
                    "evidence_used": evidence,
                    "reply": "",
                    "platform": persona.get("platform_label", platform),
                    "prompt_files": [
                        "prompt/absa_topic_prompt.txt",
                        "prompt/reply_generation_prompt.txt",
                    ],
                    "output_reply_path": "",
                    "output_json_path": "",
                },
                ensure_ascii=False,
            )

        result: Dict[str, Any] = {
            "topics": topics,
            "absa_raw": absa_raw,
            "evidence_used": evidence,
            "reply": reply,
            "identity": persona.get("identity_label"),
            "tone": persona.get("tone_label"),
            "country": country,
            "platform": persona.get("platform_label", platform),
            "source_comment": comment,
            "prompt_files": [
                "prompt/absa_topic_prompt.txt",
                "prompt/reply_generation_prompt.txt",
            ],
            "pipeline": "ABSA(full prompt) -> local evidence -> reply(full 7-module + platform style)",
        }
        result.update(_save_reply_outputs(result))
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps(
            {
                "error": f"生成失败: {e}",
                "topics": [],
                "reply": "",
            },
            ensure_ascii=False,
        )
