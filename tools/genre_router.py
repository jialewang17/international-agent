"""体裁识别：根据用户主题/提示词选择 genre skill。

权威依据：
- 老师 2026-08-22：贴文用 5W；南方周末长模板不适短帖；不同体裁不同框架。
- 详情见 skills/genres/README.md
"""

from __future__ import annotations

from typing import Dict, List, Tuple

# (genre_id, display_name, keyword_patterns)
# 更具体的体裁放前面，避免「帖文」被「故事」误伤
_GENRE_RULES: List[Tuple[str, str, List[str]]] = [
    (
        "feature",
        "深度报道/专题",
        [
            "深度报道",
            "深度稿",
            "专题稿",
            "专题深度",
            "长篇报道",
            "调查报道",
            "feature article",
            "longform",
            "in-depth",
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
            "外宣稿",
            "press release",
            "news article",
            "news story",
            "news wire",
            "across china",
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
            "reels script",
            "tiktok script",
            "video script",
        ],
    ),
    (
        "reply",
        "评论回复",
        [
            "回复评论",
            "回复以下",
            "请回复",
            "回帖",
            "reply to",
            "respond to this comment",
        ],
    ),
    (
        "post",
        "社交帖文",
        [
            "帖文",
            "发帖",
            "主动帖",
            "社交帖",
            "海外社交",
            "instagram",
            "twitter",
            "推特",
            "tiktok",
            "hashtag",
            "标签",
            "social post",
            "social media post",
        ],
    ),
]

# 主动生成工具默认体裁（老师：先把贴文做好）
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
    "feature": "placeholder",
    "script": "placeholder",
    "reply": "active_via_intl_comm_reply",
}


def detect_genre(text: str, *, default: str = DEFAULT_ACTIVE_GENRE) -> Dict[str, str]:
    """从用户提示/主题中识别体裁。返回 genre / label / matched_keyword / status。"""
    raw = (text or "").strip()
    lower = raw.lower()
    for genre_id, label, patterns in _GENRE_RULES:
        for p in patterns:
            if not p:
                continue
            # 中文保持原样包含；英文用 lower
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
