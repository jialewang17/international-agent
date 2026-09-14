"""体裁识别：根据用户主题/提示词选择 genre skill。

权威依据：
- 老师 2026-08-22：贴文用 5W；南方周末长模板不适合作短帖；不同体裁不同框架。
- skills/genres/README.md（含 zip content_formats 对照）
"""

from __future__ import annotations

from typing import Dict, List, Tuple

# (genre_id, display_name, keyword_patterns)
# 更具体的体裁放前面，避免「长文」误伤「新闻」。
_GENRE_RULES: List[Tuple[str, str, List[str]]] = [
    (
        "feature",
        "深度报道/专题",
        [
            "深度报道",
            "深度稿",
            "专题稿",
            "专题报道",
            "长篇深度",
            "特稿",
            "非虚构",
            "调查报道",
            "南方周末",
            "南周",
            "feature article",
            "longform",
            "in-depth",
            "in depth",
        ],
    ),
    (
        "news",
        "新闻通稿",
        [
            "新闻稿",
            "新闻通稿",
            "通稿",
            "消息稿",
            "通讯稿",
            "通讯",
            "新闻报道",
            "新华体",
            "新华社",
            "Across China",
            "across china",
            "press release",
            "press kit",
            "news article",
            "news story",
            "news wire",
            "newsletter",
            "news_article",
            "press_kit",
            "newsletter_brief",
        ],
    ),
    (
        "script",
        "短视频脚本",
        [
            "短视频脚本",
            "视频脚本",
            "口播稿",
            "口播脚本",
            "分镜",
            "分镜脚本",
            "reels script",
            "tiktok script",
            "video script",
            "short video",
            "short_video",
            "reel_hook",
            "youtube script",
            "youtube_script",
        ],
    ),
    (
        "reply",
        "评论回复",
        [
            "回复评论",
            "回复这条",
            "帮我回",
            "回一下",
            "reply to",
            "respond to this comment",
            "comment reply",
        ],
    ),
    (
        "post",
        "社交帖文",
        [
            "帖文",
            "贴文",
            "发帖",
            "社交媒体",
            "海外社交",
            "instagram",
            "twitter",
            "微博",
            "tiktok",
            "hashtag",
            "标签",
            "social post",
            "social media post",
            "social_post",
            "thread",
            "长帖",
            "推文串",
            "图文",
            "画册",
            "visual_story",
            "caption_only",
            "caption",
        ],
    ),
]

# 主动内容生成默认体裁（老师：先把贴文做好）
DEFAULT_ACTIVE_GENRE = "post"

GENRE_SKILL_IDS: Dict[str, Tuple[str, ...]] = {
    "post": ("intl_comm", "china_story_post"),
    "news": ("intl_comm", "china_story_news"),
    "feature": ("intl_comm", "china_story_feature"),
    "script": ("intl_comm", "china_story_script"),
    "reply": ("intl_comm",),
}

GENRE_STATUS: Dict[str, str] = {
    "post": "active",
    "news": "active",
    "feature": "active",
    "script": "placeholder",
    "reply": "active_via_intl_comm_reply",
}

# zip content_formats ID → 本仓库 genre
FORMAT_ALIAS_TO_GENRE: Dict[str, str] = {
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
    "podcast_script": "script",
    "reply": "reply",
}


def detect_genre(text: str, *, default: str = DEFAULT_ACTIVE_GENRE) -> Dict[str, str]:
    """从用户提示/主题中识别体裁。返回 genre / label / matched_keyword / status。"""
    raw = (text or "").strip()
    lower = raw.lower()

    # 显式 format= / 体裁= 优先
    for alias, genre_id in FORMAT_ALIAS_TO_GENRE.items():
        markers = (
            f"format={alias}",
            f"format: {alias}",
            f"体裁={alias}",
            f"体裁：{alias}",
            f"文本类型={alias}",
            f"文本类型：{alias}",
        )
        if any(m in lower for m in markers) or any(
            m in raw for m in markers if not m.isascii()
        ):
            label = next(
                (lb for gid, lb, _ in _GENRE_RULES if gid == genre_id), genre_id
            )
            return {
                "genre": genre_id,
                "label": label,
                "matched_keyword": f"format={alias}",
                "status": GENRE_STATUS.get(genre_id, "unknown"),
            }

    for genre_id, label, patterns in _GENRE_RULES:
        for p in patterns:
            if not p:
                continue
            needle = p.lower() if p.isascii() else p
            hay = lower if p.isascii() else raw
            if needle in hay:
                return {
                    "genre": genre_id,
                    "label": label,
                    "matched_keyword": p,
                    "status": GENRE_STATUS.get(genre_id, "unknown"),
                }
    return {
        "genre": default,
        "label": "社交帖文(默认)",
        "matched_keyword": "",
        "status": GENRE_STATUS.get(default, "unknown"),
    }


def skill_ids_for_genre(genre: str) -> Tuple[str, ...]:
    return GENRE_SKILL_IDS.get(genre, GENRE_SKILL_IDS[DEFAULT_ACTIVE_GENRE])


def resolve_format_alias(format_id: str) -> str:
    """将 zip/content_formats 的 format ID 解析为本仓库 genre。"""
    key = (format_id or "").strip().lower()
    return FORMAT_ALIAS_TO_GENRE.get(key, DEFAULT_ACTIVE_GENRE)
