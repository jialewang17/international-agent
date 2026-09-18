"""体裁路由：按用户提示词关键词映射到 post/news/feature/script/faq。"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from langchain_core.tools import tool

from utils.path import get_project_root

# 匹配顺序：feature → news → script → faq → post（与 skills/genres/README.md 一致）
_GENRE_PATTERNS: List[Tuple[str, List[str]]] = [
    (
        "feature",
        [
            r"深度报道",
            r"专题稿",
            r"特稿",
            r"长篇深度",
            r"\bfeature\b",
            r"\blongform\b",
            r"\bin[- ]?depth\b",
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

_FORMAT_TO_GENRE: Dict[str, str] = {
    "social_post": "post",
    "thread": "post",
    "caption_only": "post",
    "visual_story": "post",
    "news_article": "news",
    "newsletter_brief": "news",
    "press_kit": "news",
    "longform": "feature",
    "short_video": "script",
    "reel_hook": "script",
    "youtube_script": "script",
    "faq_mythbust": "faq",
    "faq": "faq",
}

_GENRE_STATUS: Dict[str, str] = {
    "post": "complete",
    "news": "complete",
    "feature": "methods_in",
    "script": "methods_in",
    "faq": "methods_in",
}

_GENRE_SKILL_REL: Dict[str, str] = {
    "post": "skills/genres/china-story-post.md",
    "news": "skills/genres/china-story-news.md",
    "feature": "skills/genres/china-story-feature.md",
    "script": "skills/genres/china-story-script.md",
    "faq": "skills/genres/china-story-faq-mythbust.md",
}

_DEFAULT_FORMAT: Dict[str, str] = {
    "post": "social_post",
    "news": "news_article",
    "feature": "longform",
    "script": "short_video",
    "faq": "faq_mythbust",
}


def resolve_format_alias(format_id: Optional[str]) -> Optional[str]:
    """将 zip content_formats ID 映射到仓库体裁 ID。"""
    if not format_id:
        return None
    key = str(format_id).strip().lower().replace("-", "_")
    return _FORMAT_TO_GENRE.get(key)


def detect_genre(text: str, format_hint: Optional[str] = None) -> Dict[str, str]:
    """根据提示词与可选 format 提示识别体裁。"""
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


def _pack(genre: str, matched_by: str) -> Dict[str, str]:
    return {
        "genre": genre,
        "status": _GENRE_STATUS.get(genre, "unknown"),
        "skill_file": _GENRE_SKILL_REL.get(genre, ""),
        "default_format": _DEFAULT_FORMAT.get(genre, "social_post"),
        "matched_by": matched_by,
    }


def load_genre_skill_text(genre: str, max_chars: int = 8000) -> str:
    """读取体裁 skill 正文（供注入或调试）。"""
    rel = _GENRE_SKILL_REL.get(genre)
    if not rel:
        return ""
    path = get_project_root() / rel
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    if max_chars > 0 and len(text) > max_chars:
        return text[:max_chars].rstrip() + "\n\n[...genre skill truncated...]"
    return text


@tool
def detect_content_genre(user_prompt: str, format_hint: str = "") -> str:
    """根据用户提示词识别讲好中国故事的体裁（post/news/feature/script/faq）。

    Args:
        user_prompt: 用户原始需求文本。
        format_hint: 可选，显式 format id（如 social_post、news_article、faq_mythbust）。

    Returns:
        JSON：genre、status、skill_file、default_format、matched_by。
    """
    result = detect_genre(user_prompt, format_hint=format_hint or None)
    return json.dumps(result, ensure_ascii=False)
