"""本地知识库工具：论据检索与身份/态度模板（不调用大模型，不耗 API）。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import yaml
from langchain_core.tools import tool

from utils.path import get_project_root

_CATEGORIES = [
    "celebrity",
    "governance",
    "genocide",
    "forced labor",
    "concentration camp",
    "Chinese region",
    "Muslim region",
    "Western region",
    "manufactory",
    "culture",
    "food",
    "language",
    "women and children rights",
    "sports",
    "null",
]


def _knowledge_dir() -> Path:
    return get_project_root() / "knowledge"


def _load_evidence() -> Dict[str, Any]:
    path = _knowledge_dir() / "diplomacy" / "evidence.json"
    if not path.exists():
        return {"by_category": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def _load_personas() -> Dict[str, Any]:
    path = _knowledge_dir() / "personas.yaml"
    if not path.exists():
        return {"identities": {}, "tones": {}, "countries": {}}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def guess_categories(text: str, top_k: int = 3) -> List[str]:
    """廉价关键词猜测主题，用于本地取论据，不调用 API。"""
    t = (text or "").lower()
    rules = [
        ("forced labor", ["forced labor", "slave labor", "slave", "强迫劳动", "奴工", "cotton", "棉花"]),
        ("genocide", ["genocide", "种族灭绝", "massacre", "屠杀"]),
        ("concentration camp", ["camp", "detention", "internment", "集中营", "拘禁", "再教育"]),
        ("Muslim region", ["muslim", "islam", "ramadan", "mosque", "穆斯林", "斋月", "清真寺"]),
        ("culture", ["culture", "dance", "food", "cuisine", "文化", "美食", "舞蹈"]),
        ("food", ["food", "cuisine", "pork", "餐厅", "美食"]),
        ("sports", ["olympic", "olympics", "冬奥", "sport", "比赛"]),
        ("women and children rights", ["women", "children", "steriliz", "妇女", "儿童"]),
        ("governance", ["governance", "government", "ccp", "政策", "治理", "人权", "human right"]),
        ("manufactory", ["factory", "manufacture", "supply chain", "工厂", "供应链"]),
        ("Chinese region", ["xinjiang", "uyghur", "uighur", "新疆", "维吾尔"]),
    ]
    scored: List[tuple[int, str]] = []
    for cat, keys in rules:
        score = sum(1 for k in keys if k in t)
        if score:
            scored.append((score, cat))
    scored.sort(reverse=True)
    cats = [c for _, c in scored[:top_k]]
    if not cats and any(k in t for k in ["xinjiang", "uyghur", "uighur", "新疆"]):
        cats = ["governance"]
    return cats


def retrieve_statements(categories: List[str], limit_per_cat: int = 1) -> List[Dict[str, str]]:
    data = _load_evidence().get("by_category", {})
    out: List[Dict[str, str]] = []
    for cat in categories:
        items = data.get(cat) or []
        for it in items[:limit_per_cat]:
            out.append(
                {
                    "category": cat,
                    "statement": it.get("statement", ""),
                    "source": it.get("source", ""),
                }
            )
    return out


@tool
def retrieve_evidence(categories: str, limit_per_category: int = 1) -> str:
    """
    描述：按主题类别从本地外交部论据库检索参考论点（不调用大模型）。
    使用时机：已识别出评论主题类别后，需要为中国立场回复提供事实依据时。
    输入：
    - categories（必填）：主题类别，逗号分隔。可选值包括 governance, genocide, forced labor,
      concentration camp, culture, food, sports, women and children rights, Muslim region 等。
    - limit_per_category（可选）：每个类别取几条，默认 1。
    输出：JSON，含 results（论据列表）、count。
    """
    cats = [c.strip() for c in (categories or "").split(",") if c.strip()]
    if not cats:
        return json.dumps({"error": "categories 不能为空", "results": [], "count": 0}, ensure_ascii=False)
    results = retrieve_statements(cats, limit_per_cat=max(1, int(limit_per_category)))
    return json.dumps(
        {
            "results": results,
            "count": len(results),
            "valid_categories": _CATEGORIES,
        },
        ensure_ascii=False,
    )


def build_persona(identity: str = "political_commentator", tone: str = "sarcastic", country: str = "America") -> Dict[str, Any]:
    personas = _load_personas()
    identities = personas.get("identities", {})
    tones = personas.get("tones", {})
    countries = personas.get("countries", {})

    id_key = (identity or "political_commentator").strip().lower().replace(" ", "_")
    tone_key = (tone or "sarcastic").strip().lower().replace(" ", "_")
    country_key = (country or "America").strip()

    id_obj = identities.get(id_key) or identities.get("political_commentator") or {}
    tone_obj = tones.get(tone_key) or tones.get("sarcastic") or {}
    country_obj = countries.get(country_key) or countries.get("America") or {}

    return {
        "identity_key": id_key,
        "tone_key": tone_key,
        "country": country_key,
        "identity_label": id_obj.get("label", id_key),
        "tone_label": tone_obj.get("label", tone_key),
        "identity_prompt": (id_obj.get("prompt") or "").strip(),
        "tone_prompt": (tone_obj.get("prompt") or "").strip(),
        "country_hint": (country_obj.get("hint") or "").strip(),
    }


def resolve_platform(platform: str = "twitter") -> Dict[str, str]:
    """按专利『来自（平台）』解析平台标签与表达风格。"""
    personas = _load_personas()
    platforms = personas.get("platforms", {}) or {}
    key = (platform or "twitter").strip().lower().replace(" ", "")
    aliases = {
        "twitter/x": "twitter",
        "twitterx": "twitter",
        "x.com": "twitter",
        "fb": "facebook",
        "ig": "instagram",
        "抖音": "tiktok",
        "微博": "weibo",
    }
    key = aliases.get(key, key)
    obj = platforms.get(key) or platforms.get("twitter") or {}
    return {
        "platform_key": key,
        "platform_label": str(obj.get("label") or key or "twitter"),
        "platform_style": str(obj.get("style") or "").strip(),
    }


@tool
def get_persona_style(
    identity: str = "political_commentator",
    tone: str = "sarcastic",
    country: str = "America",
    platform: str = "twitter",
) -> str:
    """
    描述：获取身份、态度、目标国、平台的本地风格模板（不调用大模型）。
    使用时机：生成拟人回复前，需要身份/语气/国家/平台提示词时。
    输入：
    - identity：political_commentator / comedian / online_influencer / scientist / rapper
    - tone：sarcastic / humorous / serious / optimistic / cold
    - country：America / Japan / UK 等
    - platform：twitter / facebook / instagram / tiktok / youtube / weibo
    输出：JSON，含 identity_prompt、tone_prompt、country_hint、platform_label、platform_style。
    """
    data = build_persona(identity, tone, country)
    data.update(resolve_platform(platform))
    return json.dumps(data, ensure_ascii=False)
