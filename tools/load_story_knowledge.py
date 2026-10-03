"""ChinaStory 写作知识门禁：在生成前加载叙事框架、方法论与形态规范。"""

from __future__ import annotations
import json
from pathlib import Path
from langchain_core.tools import tool

ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE = ROOT / "knowledge"

FORMAT_ALIASES = {
    "post": "social_post",
    "social_post": "social_post",
    "thread": "thread",
    "news": "news_article",
    "news_article": "news_article",
    "feature": "longform",
    "script": "short_video",
    "short_video": "short_video",
    "faq": "faq_mythbust",
    "faq_mythbust": "faq_mythbust",
    "visual_story": "visual_story",
    "press_kit": "press_kit",
}

def _read(name: str) -> str:
    path = KNOWLEDGE / name
    return path.read_text(encoding="utf-8") if path.exists() else ""

def _format_section(doc: str, fmt: str, max_chars: int = 7000) -> str:
    """尽量抽取指定形态附近内容；抽取失败则返回规范前部。"""
    aliases = [fmt, fmt.replace("_", " "), fmt.replace("_", "-")]
    lines = doc.splitlines()
    hit = None
    for i, line in enumerate(lines):
        low = line.lower()
        if any(a.lower() in low for a in aliases):
            hit = i
            break
    if hit is None:
        return doc[:max_chars]
    start = max(0, hit - 8)
    return "\n".join(lines[start:start + 90])[:max_chars]

@tool
def load_story_knowledge(
    format: str = "social_post",
    topic_hint: str = "",
    platform: str = "",
) -> str:
    """
    描述：【生成前知识门禁】加载 ChinaStory 叙事框架、写作方法和目标形态规范。
    使用时机：任何主动传播成稿生成之前调用一次；返回 gate=ready_to_generate 后再生成。
    输入：format 内容形态；topic_hint 主题提示；platform 目标平台。
    输出：JSON，含 framework / methodology / format_spec / gate / knowledge_loaded。
    """
    fmt = FORMAT_ALIASES.get((format or "social_post").strip().lower(), (format or "social_post").strip().lower())
    framework = _read("storytelling_framework.txt")
    methodology = _read("writing_methodology.txt")
    formats = _read("content_formats.md")
    missing = [
        name for name, content in (
            ("storytelling_framework.txt", framework),
            ("writing_methodology.txt", methodology),
            ("content_formats.md", formats),
        ) if not content
    ]
    if missing:
        return json.dumps({
            "gate": "blocked",
            "knowledge_loaded": False,
            "missing_files": missing,
            "format": fmt,
        }, ensure_ascii=False)

    return json.dumps({
        "gate": "ready_to_generate",
        "knowledge_loaded": True,
        "format": fmt,
        "topic_hint": (topic_hint or "").strip(),
        "platform": (platform or "").strip(),
        "framework": framework[:9000],
        "methodology": methodology[:9000],
        "format_spec": _format_section(formats, fmt),
        "source_files": [
            "knowledge/storytelling_framework.txt",
            "knowledge/writing_methodology.txt",
            "knowledge/content_formats.md",
        ],
    }, ensure_ascii=False)
