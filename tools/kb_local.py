"""本地知识库工具：论据检索与身份/态度模板（不调用大模型，不耗 API）。"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

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


def normalize_category(cat: str) -> str:
    """把 ABSA / 口语类别名映射到 evidence.json 键名。"""
    c = (cat or "").strip()
    if not c or c.lower() == "null":
        return ""
    key = c.lower().replace("_", " ").strip()
    aliases = {
        "human rights": "governance",
        "human right": "governance",
        "chinese cuisine": "food",
        "cuisine": "food",
        "chinese food": "food",
        "takeout": "food",
        "street food": "food",
        "intangible cultural heritage": "culture",
        "ich": "culture",
        "spring festival": "culture",
        "chinese new year": "culture",
        "new year": "culture",
        "heritage": "culture",
        "youtuber": "celebrity",
        "influencer": "celebrity",
        "vlogger": "celebrity",
        "foreign vlogger": "celebrity",
        "xinjiang": "Chinese region",
        "uyghur": "Chinese region",
        "chinese region": "Chinese region",
        "muslim region": "Muslim region",
        "western region": "Western region",
        "forced labour": "forced labor",
        "women rights": "women and children rights",
        "children rights": "women and children rights",
        "women and children": "women and children rights",
    }
    mapped = aliases.get(key, c)
    # 大小写不敏感匹配正式类别；无法识别则返回空（避免把整句主题当类别）
    lower_map = {x.lower(): x for x in _CATEGORIES}
    return lower_map.get(mapped.lower(), "")


def guess_categories(text: str, top_k: int = 3) -> List[str]:
    """廉价关键词猜测主题，用于本地取论据，不调用 API。"""
    t = (text or "").lower()
    rules = [
        ("forced labor", ["forced labor", "slave labor", "slave", "强迫劳动", "奴工", "cotton", "棉花"]),
        ("genocide", ["genocide", "种族灭绝", "massacre", "屠杀"]),
        ("concentration camp", ["camp", "detention", "internment", "集中营", "拘禁", "再教育"]),
        ("Muslim region", ["muslim", "islam", "ramadan", "mosque", "穆斯林", "斋月", "清真寺"]),
        ("language", ["mandarin", "chinese language", "汉字", "中文", "汉语", "cangjie", "language day"]),
        (
            "culture",
            [
                "culture",
                "dance",
                "silk road",
                "calligraphy",
                "opera",
                "unesco",
                "intangible",
                "heritage",
                "paper-cut",
                "papercut",
                "spring festival",
                "chinese new year",
                "lunar new year",
                "tea ceremony",
                "文化",
                "舞蹈",
                "非遗",
                "春节",
                "书法",
                "京剧",
            ],
        ),
        (
            "food",
            [
                "food",
                "cuisine",
                "hot pot",
                "hotpot",
                "dumpling",
                "noodles",
                "pork",
                "takeout",
                "take-out",
                "greasy",
                "oily",
                "street food",
                "sichuan",
                "chuan",
                "xinjiang cuisine",
                "chinese food",
                "餐厅",
                "美食",
                "火锅",
                "饺子",
                "外卖",
                "油腻",
            ],
        ),
        (
            "sports",
            [
                "olympic",
                "olympics",
                "winter olympic",
                "冬奥",
                "sport",
                "skiing",
                "冰雪",
                "比赛",
                "英超",
                "premier league",
                "football",
                "soccer",
            ],
        ),
        ("women and children rights", ["women", "girls", "children", "gender", "spring bud", "steriliz", "妇女", "女童", "儿童"]),
        ("governance", ["governance", "government", "ccp", "政策", "治理", "人权", "human right"]),
        ("manufactory", ["factory", "manufacture", "supply chain", "工厂", "供应链"]),
        (
            "Chinese region",
            [
                "xinjiang",
                "uyghur",
                "uighur",
                "新疆",
                "维吾尔",
                "high-speed",
                "high speed rail",
                "高铁",
                "hutong",
                "胡同",
                "panda",
                "大熊猫",
                "alipay",
                "wechat pay",
                "beijing",
                "sichuan",
                "shanghai",
                "上海",
                "kashgar",
                "喀什",
            ],
        ),
        (
            "celebrity",
            [
                "influencer",
                "kol",
                "vlogger",
                "youtuber",
                "youtube",
                "网红",
                "laowai",
                "foreigner",
                "expat",
                "洋网红",
                "food ranger",
                "strictly dumpling",
                "fuchsia dunlop",
                "blondie",
                "lost plate",
                "propaganda",
            ],
        ),
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


# 明显非「讲好中国故事」的库外题（足球俱乐部、梗图等）
_FOREIGN_OFF_TOPIC_MARKERS = [
    "manchester united",
    "曼联",
    "premier league",
    "英超",
    "wifi cat",
    "wifi meme",
    "cat meme",
    "nba",
    "湖人",
    "lakers",
    "iphone",
    "跑分",
    "安卓旗舰",
    "w-2",
    "报税",
    "billboard",
    "榜单预测",
]

_SPECIFIC_ANCHOR_GROUPS: List[Tuple[List[str], List[str]]] = [
    (["八仙", "eight immortal", "eight immortals"], ["八仙", "eight immortal", "eight immortals"]),
    (
        ["脸谱", "京剧脸谱", "face mask", "face masks", "opera mask", "opera masks"],
        ["脸谱", "face mask", "face masks", "opera mask", "peking opera", "beijing opera", "京剧"],
    ),
    (
        ["京剧", "peking opera", "beijing opera", "chinese opera", "戏曲脸谱"],
        ["京剧", "peking opera", "beijing opera", "chinese opera", "脸谱", "opera mask", "face mask"],
    ),
    (["庙会", "庙会巡游", "temple fair", "temple fairs"], ["庙会", "temple fair", "temple fairs"]),
    (["哪吒", "nezha", "法宝"], ["哪吒", "nezha"]),
    (["十二生肖", "生肖", "属相", "zodiac"], ["生肖", "zodiac", "属相"]),
    (["昆曲", "水磨调", "kunqu"], ["昆曲", "kunqu", "水磨"]),
    (
        ["秦篆", "汉隶", "魏碑", "唐楷", "笔法口诀"],
        ["篆", "隶", "魏碑", "楷", "calligraphy", "书法"],
    ),
]

_CHINA_STORY_MARKERS = [
    "china",
    "chinese",
    "中国",
    "中华",
    "beijing",
    "北京",
    "shanghai",
    "上海",
    "xinjiang",
    "新疆",
    "sichuan",
    "四川",
    "spring festival",
    "春节",
    "unesco",
    "非遗",
    "tea",
    "茶",
    "food",
    "美食",
    "culture",
    "文化",
    "silk road",
    "丝路",
    "丝绸之路",
    "olympic",
    "冬奥",
    "youtube",
    "influencer",
    "网红",
    "讲好中国故事",
]


def _theme_blob(theme: str) -> str:
    return (theme or "").strip().lower()


def _evidence_blob(evidence: List[Dict[str, str]]) -> str:
    parts: List[str] = []
    for ev in evidence or []:
        parts.append(str(ev.get("statement") or ""))
        parts.append(str(ev.get("category") or ""))
    return " ".join(parts).lower()


def _contains_any(text: str, markers: List[str]) -> bool:
    t = text or ""
    return any(m.lower() in t for m in markers if m)


def _is_foreign_off_topic_theme(theme: str) -> bool:
    t = _theme_blob(theme)
    if not _contains_any(t, _FOREIGN_OFF_TOPIC_MARKERS):
        return False
    # 含曼联/梗图等库外标记时，除非主题文本本身明确是中国故事语境
    china_in_theme = _contains_any(
        t,
        [
            "china",
            "chinese",
            "中国",
            "中华",
            "beijing",
            "北京",
            "冬奥",
            "olympic",
            "xinjiang",
            "新疆",
            "spring festival",
            "春节",
            "讲好中国故事",
        ],
    )
    return not china_in_theme


def _has_china_story_signal(theme: str) -> bool:
    t = _theme_blob(theme)
    if _contains_any(t, _CHINA_STORY_MARKERS):
        return True
    return bool(guess_categories(theme, top_k=1))


def _missing_specific_anchors(theme: str, evidence_text: str) -> List[str]:
    t = _theme_blob(theme)
    missing: List[str] = []
    for triggers, supports in _SPECIFIC_ANCHOR_GROUPS:
        if not _contains_any(t, triggers):
            continue
        if not _contains_any(evidence_text, supports):
            label = triggers[0]
            missing.append(label)
    return missing


def check_theme_evidence_alignment(theme: str, evidence: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    主动发帖门控：检索结果与主题是否对齐。
    返回 ok=True 方可进入 LLM 成稿；否则由调用方返回 error 并 STOP。
    """
    theme = (theme or "").strip()
    if not theme:
        return {
            "ok": False,
            "reason": "empty_theme",
            "message": "主题为空，已跳过帖文生成。",
        }
    if not evidence:
        return {
            "ok": False,
            "reason": "no_evidence",
            "message": "未检索到可用本地论据，已跳过帖文生成。请换更具体的中国故事主题，或补充 knowledge/diplomacy/evidence.json。",
        }

    ev_text = _evidence_blob(evidence)

    if _is_foreign_off_topic_theme(theme):
        return {
            "ok": False,
            "reason": "off_topic_foreign",
            "message": (
                "主题与「讲好中国故事」库外域（如海外足球俱乐部、网络梗图），"
                "且本地论据无法支撑该题，已跳过帖文生成。请换中国故事相关主题。"
            ),
        }

    missing = _missing_specific_anchors(theme, ev_text)
    if missing:
        joined = "、".join(missing)
        return {
            "ok": False,
            "reason": "subtopic_unsupported",
            "missing_anchors": missing,
            "message": (
                f"主题涉及「{joined}」等专名细节，但当前 evidence_used 中无对应素材，"
                "已跳过帖文生成。请换题（如春节/剪纸等库内角度）或补充 knowledge 素材。"
            ),
        }

    # 主题关键词弱、但用户上传/合并论据已含中国故事信号 → 放行（老师：先喂资料再生成）
    theme_ok = _has_china_story_signal(theme)
    combined_ok = _has_china_story_signal(f"{theme} {ev_text}")
    if not theme_ok and not combined_ok:
        return {
            "ok": False,
            "reason": "not_china_story",
            "message": (
                "主题未识别为中国故事相关方向，且检索论据与主题不对齐，"
                "已跳过帖文生成。请换更具体的中国故事主题，或补充 knowledge/diplomacy/evidence.json。"
            ),
        }

    return {"ok": True, "reason": "aligned"}


def retrieve_statements(
    categories: List[str],
    limit_per_cat: int = 2,
    query: str = "",
) -> List[Dict[str, str]]:
    """
    混合检索：
    1) 若已建 Chroma 且提供 query → 语义检索（带距离阈值）
    2) 再按「关键词确认过的类别」从 evidence.json 补齐
    3) 库外主题防护：有 query，但关键词未命中且语义也无近邻 → 返回空，禁止仅凭 ABSA 类别硬补
    4) 无 query 时保持纯类别检索（兼容只按类查库）
    """
    limit_per_cat = max(1, int(limit_per_cat))
    asked: List[str] = []
    for c in categories or []:
        nc = normalize_category(c)
        if nc and nc not in asked and nc != "null":
            asked.append(nc)

    q = (query or "").strip()
    keyword_cats = guess_categories(q, top_k=3) if q else []

    want = max(limit_per_cat * max(len(asked) or len(keyword_cats), 1), limit_per_cat, 4)
    out: List[Dict[str, str]] = []
    seen = set()

    def _add(item: Dict[str, str]) -> None:
        key = (item.get("source", ""), item.get("statement", ""))
        if not item.get("statement") or key in seen:
            return
        seen.add(key)
        out.append(
            {
                "category": item.get("category", ""),
                "statement": item.get("statement", ""),
                "source": item.get("source", ""),
                "retrieval": item.get("retrieval", "category"),
            }
        )

    # --- Chroma 语义 ---
    if q:
        try:
            from tools.chroma_kb import chroma_ready, query_chroma

            if chroma_ready():
                # 语义阶段用 asked∪keyword，便于同主题召回；距离阈值在 chroma 内过滤
                sem_cats = list(dict.fromkeys(asked + keyword_cats)) or None
                for hit in query_chroma(q, categories=sem_cats, top_k=want):
                    _add(hit)
        except Exception:
            pass

    # --- 库外主题：禁止「ABSA 乱标 governance 后再按类硬补」---
    if q and not keyword_cats and not out:
        return []

    # --- 类别补齐：有 query 时只补关键词命中的类，避免 WiFi→governance 误补 ---
    if q:
        pad_cats = keyword_cats
    else:
        pad_cats = asked

    data = _load_evidence().get("by_category", {})
    for cat in pad_cats:
        items = data.get(cat) or []
        taken = 0
        for it in items:
            if taken >= limit_per_cat:
                break
            before = len(out)
            _add(
                {
                    "category": cat,
                    "statement": it.get("statement", ""),
                    "source": it.get("source", ""),
                    "retrieval": "category",
                }
            )
            if len(out) > before:
                taken += 1

    return out[:want]


@tool
def retrieve_evidence(categories: str, limit_per_category: int = 1, query: str = "") -> str:
    """
    描述：从本地论据库检索参考论点（类别检索 + 可选 Chroma 语义检索，不调用对话大模型）。
    使用时机：已识别出评论主题类别后，需要为中国立场回复提供事实依据时。
    输入：
    - categories（必填）：主题类别，逗号分隔。可选值包括 governance, genocide, forced labor,
      concentration camp, culture, food, sports, women and children rights, Muslim region 等。
    - limit_per_category（可选）：每个类别取几条，默认 1。
    - query（可选）：原始评论文本；提供后启用 Chroma 语义检索（需先运行 scripts/build_chroma_kb.py）。
    输出：JSON，含 results（论据列表）、count、chroma_enabled。
    """
    cats = [c.strip() for c in (categories or "").split(",") if c.strip()]
    if not cats:
        return json.dumps({"error": "categories 不能为空", "results": [], "count": 0}, ensure_ascii=False)
    chroma_on = False
    try:
        from tools.chroma_kb import chroma_ready

        chroma_on = bool((query or "").strip()) and chroma_ready()
    except Exception:
        chroma_on = False
    results = retrieve_statements(
        cats,
        limit_per_cat=max(1, int(limit_per_category)),
        query=query or "",
    )
    return json.dumps(
        {
            "results": results,
            "count": len(results),
            "chroma_enabled": chroma_on,
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
