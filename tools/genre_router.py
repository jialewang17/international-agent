"""体裁路由：按用户提示词关键词映射到 post/news/feature/indepth/script/faq 六体裁。

映射表（genre ↔ skill_id ↔ 方法卡路径 ↔ format）统一由 utils.genre_contracts 提供，
本模块只负责"关键词识别"与"显式选择的优先级处理"，不再维护第二份映射。
依据：P0 六体裁接入修复任务 §1（统一映射）、§2（保护显式选择）。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from langchain_core.tools import tool

from utils.genre_contracts import (
    GENRE_CONTRACTS,
    SelectionIssue,
    canonicalize_format,
    check_selection,
    contract_for,
    skill_ids_for,
)
from utils.path import get_project_root

# 匹配顺序：indepth → feature → news → script → faq → post（与 skills/README.md 一致）
# indepth 必须排在 feature 之前，且 feature 不再包含「深度报道 / 专题稿 / 长篇深度 / in-depth」，
# 否则深度报道会被 feature 抢走。依据：docs/chinastory_v6.1/history/handoff-to-backend/04-code-integration-patch.md §1.1
_GENRE_PATTERNS: List[Tuple[str, List[str]]] = [
    (
        "indepth",
        [
            r"深度报道",
            r"解释性报道",
            r"调查报道",
            r"专题报道",
            r"长篇深度",
            r"in[- ]?depth(?:\s+report|\s+story)?",
            r"explainer\s+(?:report|longform|story)",
        ],
    ),
    (
        "feature",
        [
            r"特稿",
            r"非虚构长文",
            r"长篇特写",
            r"专题稿",
            r"\bfeature\b",
            r"\blongform\b",
        ],
    ),
    (
        "news",
        [
            r"新闻稿",
            r"新闻通稿",
            r"通稿",
            r"消息稿",
            r"通讯",
            r"新华体",
            r"press\s*release",
            r"news\s*wire",
            r"across\s*china",
            r"\bnews_article\b",
            r"press_kit",
            r"newsletter",
        ],
    ),
    (
        "script",
        [
            r"短视频脚本",
            r"视频脚本",
            r"口播",
            r"分镜",
            r"reels?\s*script",
            r"tiktok\s*script",
            r"video\s*script",
            r"\bshort_video\b",
            r"\breel_hook\b",
            r"youtube\s*script",
        ],
    ),
    (
        "faq",
        [
            r"误解澄清",
            r"澄清误解",
            r"澄清[^。！？\n]{0,8}误解",
            r"辟谣",
            r"常见误解",
            r"常见误区",
            r"\bFAQ\b",
            r"faq_mythbust",
            r"myth\s*bust",
            r"mythbust",
            r"debunk(ing)?\s+(china\s+)?myths?",
            r"myth\s+vs\s+fact",
            r"misconceptions?",
            r"\bmyths?\s+about\b",
        ],
    ),
    (
        "post",
        [
            r"帖文",
            r"贴文",
            r"发帖",
            r"社交媒体",
            r"instagram",
            r"twitter",
            r"微博",
            r"hashtag",
            r"social\s*post",
            r"\bthread\b",
            r"长帖",
            r"图文",
            r"\bvisual_story\b",
            r"caption_only",
        ],
    ),
]

# 兼容旧调用方：分期状态现在由契约给出，避免两处写法不一致。
GENRE_STATUS: Dict[str, str] = {
    genre: contract.status for genre, contract in GENRE_CONTRACTS.items()
}


@dataclass(frozen=True)
class GenreSelection:
    """一次生成请求的最终体裁/格式选择结果。"""

    genre: str
    format: str
    source: str  # user_override | format | format_eq | keyword | default
    matched_by: str
    issue: Optional[SelectionIssue] = None
    requested_genre: Optional[str] = None
    requested_format: Optional[str] = None

    def as_dict(self) -> Dict[str, object]:
        return {
            "genre": self.genre,
            "format": self.format,
            "source": self.source,
            "matched_by": self.matched_by,
            "requested_genre": self.requested_genre,
            "requested_format": self.requested_format,
            "issue": None
            if self.issue is None
            else {"code": self.issue.code, "message": self.issue.message, "detail": self.issue.detail},
        }


def skill_ids_for_genre(genre: str) -> List[str]:
    """返回该体裁在 skills.yaml 注册的兼容 skill id；非法体裁返回空列表。

    不再回落到 ``china_story_post``：静默回落会让非法体裁伪装成 post 生成成功
    （P0 §2）。空列表交给严格加载器显式报错。
    """
    return skill_ids_for(genre)


def resolve_format_alias(format_id: Optional[str]) -> Optional[str]:
    """将 zip content_formats ID 映射到仓库体裁 ID。"""
    canonical = canonicalize_format(format_id)
    return canonical[0] if canonical else None


def detect_genre(text: str, format_hint: Optional[str] = None) -> Dict[str, str]:
    """根据提示词与可选 format 提示识别体裁（自动识别，不含显式选择校验）。"""
    hint_genre = resolve_format_alias(format_hint)
    if hint_genre:
        return _pack(hint_genre, matched_by=f"format:{format_hint}")

    blob = text or ""
    m = re.search(r"format\s*=\s*([a-zA-Z0-9_\-]+)", blob, re.I)
    if m:
        mapped = resolve_format_alias(m.group(1))
        if mapped:
            return _pack(mapped, matched_by=f"format_eq:{m.group(1)}")

    for genre, patterns in _GENRE_PATTERNS:
        for pat in patterns:
            if re.search(pat, blob, re.I):
                return _pack(genre, matched_by=pat)

    return _pack("post", matched_by="default")


def resolve_selection(
    *,
    genre: Optional[str] = None,
    format_id: Optional[str] = None,
    text: str = "",
) -> GenreSelection:
    """显式选择优先于关键词推断，并校验 genre/format 组合。

    优先级（P0 §2）：
    1. 调用方显式给出的合法 genre（用户在前端选择）
    2. 调用方显式给出的合法 format
    3. 提示词中的 ``format=...``
    4. 关键词自动识别
    5. 仅当以上都没有时才落到默认 post，并标记 source=default
    """
    explicit_genre = str(genre or "").strip()
    explicit_format = str(format_id or "").strip()

    resolved_genre, resolved_format, issue = check_selection(explicit_genre, explicit_format)
    if issue is not None:
        return GenreSelection(
            genre=resolved_genre or "",
            format=resolved_format or "",
            source="user_override" if explicit_genre else "format",
            matched_by=f"rejected:{issue.code}",
            issue=issue,
            requested_genre=explicit_genre or None,
            requested_format=explicit_format or None,
        )

    if explicit_genre:
        contract = GENRE_CONTRACTS[resolved_genre]
        return GenreSelection(
            genre=resolved_genre,
            format=resolved_format or contract.default_format,
            source="user_override",
            matched_by="frontend_select",
            requested_genre=explicit_genre,
            requested_format=explicit_format or None,
        )

    if explicit_format:
        return GenreSelection(
            genre=resolved_genre,
            format=resolved_format,
            source="format",
            matched_by=f"format:{explicit_format}",
            requested_format=explicit_format,
        )

    blob = text or ""
    m = re.search(r"format\s*=\s*([a-zA-Z0-9_\-]+)", blob, re.I)
    detected = detect_genre(blob, format_hint=m.group(1) if m else None)
    detected_genre = detected.get("genre") or "post"
    contract = contract_for(detected_genre)
    is_default = detected.get("matched_by") == "default"
    source = "default" if is_default else ("format_eq" if str(detected.get("matched_by", "")).startswith("format_eq") else "keyword")
    return GenreSelection(
        genre=detected_genre,
        format=contract.default_format if contract else "",
        source=source,
        matched_by=str(detected.get("matched_by", "")),
        requested_genre=None,
        requested_format=None,
    )


def _pack(genre: str, matched_by: str) -> Dict[str, str]:
    contract = contract_for(genre)
    return {
        "genre": genre,
        "status": contract.status if contract else "unknown",
        "skill_file": contract.method_path if contract else "",
        "default_format": contract.default_format if contract else "",
        "matched_by": matched_by,
    }


def load_genre_skill_text(genre: str, max_chars: int = 8000) -> str:
    """读取体裁 skill 正文（仅用于调试/检视；生成链路走严格加载器）。"""
    contract = contract_for(genre)
    if not contract:
        return ""
    path = get_project_root() / contract.method_path
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    if max_chars > 0 and len(text) > max_chars:
        return text[:max_chars].rstrip() + "\n\n[...genre skill truncated...]"
    return text


@tool
def detect_content_genre(user_prompt: str, format_hint: str = "") -> str:
    """根据用户提示词识别讲好中国故事的体裁（post/news/feature/indepth/script/faq）。

    Args:
        user_prompt: 用户原始需求文本。
        format_hint: 可选，显式 format id（如 social_post、news_article、in_depth_report、faq_mythbust）。

    Returns:
        JSON：genre、status、skill_file、default_format、matched_by。
    """
    result = detect_genre(user_prompt, format_hint=format_hint or None)
    return json.dumps(result, ensure_ascii=False)
