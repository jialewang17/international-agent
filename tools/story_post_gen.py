"""主动传播：基于 5W + 本地论据 RAG，生成「讲好中国故事」海外平台帖文（供人工审核）。"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage
from langchain_core.tools import tool

from model.factory import get_text_generation_model
from tools.kb_local import (
    build_persona,
    check_theme_evidence_alignment,
    guess_categories,
    normalize_category,
    resolve_platform,
    retrieve_statements,
)
from utils.path import get_prompt_dir
from tools.genre_router import detect_genre, skill_ids_for_genre
from tools.user_materials import merge_evidence, normalize_user_materials
from utils.skill_registry import format_skills_by_ids


STORY_THEMES = [
    "food",
    "culture",
    "Chinese region",
    "celebrity",
    "language",
    "sports",
    "women and children rights",
    "governance",
]


def _load_template(name: str) -> str:
    return (get_prompt_dir() / name).read_text(encoding="utf-8")


def _llm_text(prompt: str) -> str:
    model = get_text_generation_model()
    result = model.invoke([HumanMessage(content=prompt)])
    raw = getattr(result, "content", "") or ""
    if isinstance(raw, list):
        raw = "".join((x.get("text", "") if isinstance(x, dict) else str(x)) for x in raw)
    return str(raw).strip()


def _extract_json(raw: str) -> Dict[str, Any]:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except Exception:
        m = re.search(r"\{[\s\S]*\}", text)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                pass
    return {
        "5w": {},
        "post": text,
        "hashtags": [],
        "title_or_hook": "",
        "ops_tips": [],
        "evidence_notes": [],
        "parse_warning": "model output was not valid JSON; raw text put into post",
    }


def _theme_to_categories(theme: str) -> List[str]:
    t = (theme or "").strip()
    if not t:
        return []
    # allow comma-separated categories
    parts = [p.strip() for p in re.split(r"[,，/;|]", t) if p.strip()]
    cats: List[str] = []
    for p in parts:
        nc = normalize_category(p)
        if nc and nc not in cats:
            cats.append(nc)
        else:
            # free-text theme → keyword guess
            for g in guess_categories(p, top_k=2):
                if g not in cats:
                    cats.append(g)
    if not cats:
        cats = guess_categories(t, top_k=3)
    return cats


def build_story_post_prompt(
    *,
    theme: str,
    evidence: List[Dict[str, str]],
    country: str,
    identity: str,
    tone: str,
    platform: str,
    language: str,
    max_words: int,
    use_emoji: bool,
    desired_effect: str,
    genre: str = "post",
    skill_ids: Optional[List[str]] = None,
) -> str:
    persona = build_persona(identity=identity, tone=tone, country=country)
    plat = resolve_platform(platform)
    evidence_lines = []
    for i, ev in enumerate(evidence, 1):
        src_type = ev.get("source_type") or "本地库"
        line = (
            f"Evidence#{i} [{src_type}] ({ev.get('category')}): {ev.get('statement')}"
        )
        if ev.get("source"):
            line += f" | source: {ev.get('source')}"
        evidence_lines.append(line)
    evidence_block = (
        "\n".join(evidence_lines)
        if evidence_lines
        else "(no verified evidence from user materials or local KB)"
    )
    emoji_instruction = (
        "you may use a few tasteful emojis."
        if use_emoji
        else "do not use emojis."
    )
    tpl = _load_template("story_post_prompt.txt")
    ids = list(skill_ids) if skill_ids else list(skill_ids_for_genre(genre))
    skill_block = format_skills_by_ids(*ids) or "(no skill loaded)"
    genre_note = (
        f"Detected content genre: {genre}. "
        "For social posts, keep it short (Lasswell 5W + caption), NOT Southern Weekly longform."
        if genre == "post"
        else (
            f"Detected content genre: {genre}. "
            "Genre-specific long templates may be placeholder; do not invent Southern Weekly "
            "section structures; keep claims grounded in evidence only."
        )
    )
    dual_note = (
        "Evidence may include [用户上传] and [本地库]. Prefer on-theme user facts; "
        "do not invent beyond either source."
    )
    return (
        tpl.replace("{identity_label}", persona.get("identity_label", identity))
        .replace("{identity_prompt}", persona.get("identity_prompt", ""))
        .replace("{tone_label}", persona.get("tone_label", tone))
        .replace("{tone_prompt}", persona.get("tone_prompt", ""))
        .replace("{platform}", plat.get("platform_label", platform))
        .replace("{platform_style}", plat.get("platform_style", ""))
        .replace("{country}", country)
        .replace("{desired_effect}", desired_effect)
        .replace("{theme}", theme)
        .replace("{language}", language)
        .replace("{max_words}", str(max_words))
        .replace("{emoji_instruction}", emoji_instruction)
        .replace("{skill_block}", skill_block + "\n\n" + genre_note + "\n" + dual_note)
        .replace("{evidence_block}", evidence_block)
    )


def build_story_news_prompt(
    *,
    theme: str,
    evidence: List[Dict[str, str]],
    country: str,
    identity: str,
    tone: str,
    language: str,
    max_words: int,
    desired_effect: str,
    skill_ids: Optional[List[str]] = None,
) -> str:
    """新闻通稿专用 prompt：与帖文 5W 模板完全分离。"""
    persona = build_persona(identity=identity, tone=tone, country=country)
    evidence_lines = []
    for i, ev in enumerate(evidence, 1):
        src_type = ev.get("source_type") or "本地库"
        line = (
            f"Evidence#{i} [{src_type}] ({ev.get('category')}): {ev.get('statement')}"
        )
        if ev.get("source"):
            line += f" | source: {ev.get('source')}"
        evidence_lines.append(line)
    evidence_block = (
        "\n".join(evidence_lines)
        if evidence_lines
        else "(no verified evidence from user materials or local KB)"
    )
    ids = list(skill_ids) if skill_ids else list(skill_ids_for_genre("news"))
    skill_block = format_skills_by_ids(*ids) or "(no skill loaded)"
    genre_note = (
        "Detected content genre: news. Use china_story_news wire structure only. "
        "Do NOT apply china_story_post 5W caption rules, emojis, or Gen Z CTA."
    )
    dual_note = (
        "Evidence may include [用户上传] and [本地库]. Prefer on-theme user facts; "
        "do not invent beyond either source."
    )
    tpl = _load_template("story_news_prompt.txt")
    return (
        tpl.replace("{identity_label}", persona.get("identity_label", identity))
        .replace("{identity_prompt}", persona.get("identity_prompt", ""))
        .replace("{tone_label}", persona.get("tone_label", tone))
        .replace("{tone_prompt}", persona.get("tone_prompt", ""))
        .replace("{country}", country)
        .replace("{desired_effect}", desired_effect)
        .replace("{theme}", theme)
        .replace("{language}", language)
        .replace("{max_words}", str(max_words))
        .replace("{skill_block}", skill_block + "\n\n" + genre_note + "\n" + dual_note)
        .replace("{evidence_block}", evidence_block)
    )


def run_story_post_generation(
    *,
    theme: str,
    country: str = "America",
    identity: str = "online_influencer",
    tone: str = "optimistic",
    platform: str = "instagram",
    language: str = "English",
    max_words: int = 80,
    use_emoji: bool = True,
    desired_effect: str = "Increase curiosity and positive understanding of China through a concrete, shareable story.",
    user_materials: Optional[Any] = None,
    user_brief: Optional[str] = None,
) -> Dict[str, Any]:
    cats = _theme_to_categories(theme)
    genre_info = detect_genre((user_brief or "") + " " + theme)
    genre = genre_info.get("genre") or "post"
    skill_ids = list(skill_ids_for_genre(genre))

    # 通稿默认：更长篇幅、无 emoji、偏严肃/乐观外宣口径（不改用户明确指定）
    if genre == "news":
        if max_words <= 120:
            max_words = 700
        use_emoji = False
        if identity == "online_influencer":
            identity = "political_commentator"
        if tone in ("sarcastic", "humorous", "cold"):
            tone = "optimistic"
        if not (desired_effect or "").strip() or "shareable story" in (desired_effect or ""):
            desired_effect = (
                "Help international readers understand a concrete China development "
                "model with verifiable ecology, energy and livelihood outcomes."
            )

    user_ev = normalize_user_materials(user_materials, theme=theme)
    if user_ev and "evidence_user_materials" not in skill_ids:
        skill_ids.append("evidence_user_materials")

    # 检索用「故事角度」theme；成稿提示用完整用户问法 user_brief（多样长短提示）
    retrieve_q = (theme or "").strip() or (user_brief or "").strip()
    local_ev = retrieve_statements(cats, limit_per_cat=3, query=retrieve_q)
    if not local_ev and cats and not user_ev:
        local_ev = retrieve_statements(cats, limit_per_cat=2, query=" ".join(cats))

    evidence = merge_evidence(user_ev, local_ev, prefer_user_first=True)
    persona = build_persona(identity=identity, tone=tone, country=country)
    plat = resolve_platform(platform)
    n_user = sum(1 for e in evidence if e.get("source_type") == "用户上传")
    n_local = sum(1 for e in evidence if e.get("source_type") != "用户上传")
    brief_for_prompt = (user_brief or theme or "").strip()

    if not evidence:
        return {
            "error": (
                "未检索到可用论据（本地库为空且未提供用户资料），已跳过成稿生成。"
                "请粘贴/上传资料，或换更具体主题并补充 knowledge。"
            ),
            "theme": theme,
            "user_brief": user_brief or "",
            "categories": cats,
            "genre": genre,
            "genre_meta": genre_info,
            "evidence_used": [],
            "evidence_stats": {"user": 0, "local": 0},
            "post": "",
            "article": "",
            "platform": plat.get("platform_label", platform),
            "pipeline": "theme -> genre -> user_materials+retrieve (empty) -> STOP",
            "skills_applied": skill_ids,
        }

    alignment = check_theme_evidence_alignment(retrieve_q, evidence)
    if not alignment.get("ok"):
        return {
            "error": alignment.get("message", "主题与论据不对齐，已跳过成稿生成。"),
            "gate_reason": alignment.get("reason"),
            "missing_anchors": alignment.get("missing_anchors", []),
            "theme": theme,
            "user_brief": user_brief or "",
            "categories": cats,
            "genre": genre,
            "genre_meta": genre_info,
            "evidence_used": evidence,
            "evidence_stats": {"user": n_user, "local": n_local},
            "post": "",
            "article": "",
            "platform": plat.get("platform_label", platform),
            "pipeline": "theme -> genre -> dual evidence -> alignment gate -> STOP",
            "skills_applied": skill_ids,
        }

    if genre == "news":
        prompt = build_story_news_prompt(
            theme=brief_for_prompt,
            evidence=evidence,
            country=country,
            identity=identity,
            tone=tone,
            language=language,
            max_words=max_words,
            desired_effect=desired_effect,
            skill_ids=skill_ids,
        )
        prompt_file = "prompt/story_news_prompt.txt"
    else:
        prompt = build_story_post_prompt(
            theme=brief_for_prompt,
            evidence=evidence,
            country=country,
            identity=identity,
            tone=tone,
            platform=platform,
            language=language,
            max_words=max_words,
            use_emoji=use_emoji,
            desired_effect=desired_effect,
            genre=genre,
            skill_ids=skill_ids,
        )
        prompt_file = "prompt/story_post_prompt.txt"

    raw = _llm_text(prompt)
    parsed = _extract_json(raw)

    if genre == "news":
        article = (parsed.get("article") or parsed.get("post") or "").strip()
        headline = (parsed.get("headline") or parsed.get("title_or_hook") or "").strip()
        dateline = (parsed.get("dateline") or "").strip()
        body_out = article
        if headline and not body_out.startswith(headline):
            body_out = f"{headline}\n\n{dateline + chr(10) + chr(10) if dateline else ''}{body_out}".strip()
        elif dateline and dateline not in body_out[:120]:
            body_out = f"{dateline}\n\n{body_out}".strip()
        return {
            "theme": theme,
            "user_brief": user_brief or "",
            "categories": cats,
            "genre": genre,
            "genre_meta": genre_info,
            "evidence_used": evidence,
            "evidence_stats": {"user": n_user, "local": n_local},
            "wire_plan": parsed.get("wire_plan") or {},
            "headline": headline,
            "dateline": dateline,
            "article": article,
            "quotes_used": parsed.get("quotes_used") or [],
            "five_w": {},
            "title_or_hook": headline,
            "post": body_out,
            "hashtags": [],
            "ops_tips": parsed.get("ops_tips") or [],
            "evidence_notes": parsed.get("evidence_notes") or [],
            "identity": persona.get("identity_label"),
            "tone": persona.get("tone_label"),
            "country": country,
            "platform": plat.get("platform_label", platform),
            "language": language,
            "max_words": max_words,
            "pipeline": (
                f"skill({'+'.join(skill_ids)}) -> genre=news -> "
                f"dual_evidence(user={n_user},local={n_local}) -> gate -> news wire"
            ),
            "skills_applied": skill_ids,
            "prompt_file": prompt_file,
            "raw_model": raw if parsed.get("parse_warning") else None,
            "parse_warning": parsed.get("parse_warning"),
        }

    return {
        "theme": theme,
        "user_brief": user_brief or "",
        "categories": cats,
        "genre": genre,
        "genre_meta": genre_info,
        "evidence_used": evidence,
        "evidence_stats": {"user": n_user, "local": n_local},
        "five_w": parsed.get("5w") or parsed.get("five_w") or {},
        "title_or_hook": parsed.get("title_or_hook", ""),
        "post": parsed.get("post", ""),
        "article": "",
        "hashtags": parsed.get("hashtags", []),
        "ops_tips": parsed.get("ops_tips", []),
        "evidence_notes": parsed.get("evidence_notes", []),
        "identity": persona.get("identity_label"),
        "tone": persona.get("tone_label"),
        "country": country,
        "platform": plat.get("platform_label", platform),
        "language": language,
        "pipeline": (
            f"skill({'+'.join(skill_ids)}) -> genre={genre} -> "
            f"dual_evidence(user={n_user},local={n_local}) -> gate -> active post"
        ),
        "skills_applied": skill_ids,
        "prompt_file": prompt_file,
        "raw_model": raw if parsed.get("parse_warning") else None,
        "parse_warning": parsed.get("parse_warning"),
    }


@tool
def generate_china_story_post(
    theme: str,
    country: str = "America",
    identity: str = "online_influencer",
    tone: str = "optimistic",
    platform: str = "instagram",
    language: str = "English",
    max_words: int = 80,
    use_emoji: bool = True,
    desired_effect: str = "Increase curiosity and positive understanding of China through a concrete, shareable story.",
    user_materials: str = "",
) -> str:
    """
    描述：【主动传播主工具】生成「讲好中国故事」成稿（默认社交帖文；提示含「新闻通稿/通稿」等则走新闻体裁）。
    流程：主题解析 → 体裁识别 → 用户资料 + 本地检索 → 对齐门控 → 帖文(5W)或通稿(wire)生成（人工审核）。
    使用时机：用户要发帖、写新闻通稿、策划内容、生成中国故事草稿时（不是回复别人评论时）。
    输入：
    - theme（必填）：主题/角度；写「新闻通稿」等词可路由到 news skill
    - country：目标受众国家，默认 America
    - identity：political_commentator / comedian / online_influencer / scientist / rapper
    - tone：sarcastic / humorous / serious / optimistic / cold
    - platform：twitter / facebook / Instagram / tiktok / youtube / weibo，默认 instagram
    - language：成稿语言，默认 English
    - max_words：正文大约词数；帖文默认约 80，通稿建议 600–900（≤120 会自动抬到 700）
    - use_emoji：是否可用 emoji（通稿强制关闭）
    - desired_effect：期望传播效果（一句话）
    - user_materials：用户粘贴资料（可空行分段）；与本地库合并进 evidence_used
    输出：JSON；帖文含 five_w/post/hashtags；通稿含 wire_plan/headline/article（并镜像到 post 便于前端展示）。
    """
    theme = (theme or "").strip()
    if not theme:
        return json.dumps({"error": "theme 不能为空", "post": ""}, ensure_ascii=False)
    try:
        result = run_story_post_generation(
            theme=theme,
            country=country,
            identity=identity,
            tone=tone,
            platform=platform,
            language=language,
            max_words=int(max_words),
            use_emoji=bool(use_emoji),
            desired_effect=desired_effect,
            user_materials=user_materials or None,
        )
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"帖文生成失败: {e}", "post": ""}, ensure_ascii=False)


@tool
def plan_china_story_topics(
    seed: str = "讲好中国故事",
    platform: str = "instagram",
    n: int = 5,
) -> str:
    """
    描述：根据种子主题，从本地知识库方向给出可执行的中国故事选题清单（不调用大模型）。
    使用时机：用户还没想好发什么、需要选题/策划灵感时。
    输入：seed 种子词；platform 平台；n 条数（1-8）。
    输出：JSON，含 topics 列表（theme、category、why、suggested_hashtags）。
    """
    n = max(1, min(8, int(n)))
    seed_l = (seed or "").lower()
    catalog = [
        {
            "theme": "Xinjiang flavors beyond stereotypes: big-plate chicken, hand-pulled noodles, naan",
            "category": "food",
            "why": "Concrete food story; strong visuals for IG/TikTok",
            "suggested_hashtags": ["#XinjiangFood", "#TasteOfChina", "#StreetFood"],
        },
        {
            "theme": "Spring Festival as UNESCO ICH: reunion, rituals, living heritage",
            "category": "culture",
            "why": "Authoritative cultural narrative; seasonal campaign angle",
            "suggested_hashtags": ["#SpringFestival", "#ICH", "#ChineseNewYear"],
        },
        {
            "theme": "Chinese tea craft as shared living heritage",
            "category": "culture",
            "why": "Soft power + craftsmanship; calm aesthetic for Instagram",
            "suggested_hashtags": ["#ChineseTea", "#LivingHeritage", "#TeaCulture"],
        },
        {
            "theme": "Foreign creators filming Chinese street food with curiosity, not politics",
            "category": "celebrity",
            "why": "Third-party lens increases trust for overseas audiences",
            "suggested_hashtags": ["#FoodRanger", "#ChinaThroughFood", "#TravelChina"],
        },
        {
            "theme": "Everyday China: hutong life / high-speed rail / digital payments as lived modernity",
            "category": "Chinese region",
            "why": "Daily-life storytelling beats abstract slogans",
            "suggested_hashtags": ["#EverydayChina", "#ModernChina", "#LifeInChina"],
        },
        {
            "theme": "Paper-cutting / calligraphy / Peking opera as accessible cultural entry points",
            "category": "culture",
            "why": "Classic ICH icons; easy carousel / Reels structure",
            "suggested_hashtags": ["#ChineseCulture", "#Calligraphy", "#PekingOpera"],
        },
        {
            "theme": "Women and youth development stories with verifiable public programs",
            "category": "women and children rights",
            "why": "Values narrative with policy/program anchors",
            "suggested_hashtags": ["#WomenInChina", "#YouthExchange", "#ChinaStories"],
        },
        {
            "theme": "Winter sports / Olympics legacy as shared excitement",
            "category": "sports",
            "why": "High emotion, cross-cultural fandom language",
            "suggested_hashtags": ["#WinterSports", "#ChinaSports", "#OlympicSpirit"],
        },
    ]
    scored = []
    for item in catalog:
        score = 0
        blob = (item["theme"] + item["category"] + seed_l).lower()
        for token in re.findall(r"[\w\u4e00-\u9fff]+", seed_l):
            if token and token in blob:
                score += 1
        if any(k in seed_l for k in ["food", "美食", "cuisine", "小吃"]):
            if item["category"] == "food":
                score += 3
        if any(k in seed_l for k in ["culture", "文化", "非遗", "春节", "festival"]):
            if item["category"] == "culture":
                score += 3
        if any(k in seed_l for k in ["youtuber", "网红", "influencer", "vlog"]):
            if item["category"] == "celebrity":
                score += 3
        scored.append((score, item))
    scored.sort(key=lambda x: (-x[0], x[1]["category"]))
    picked = [x[1] for x in scored[:n]]
    # attach platform hint
    plat = resolve_platform(platform)
    return json.dumps(
        {
            "seed": seed,
            "platform": plat.get("platform_label", platform),
            "platform_style": plat.get("platform_style", ""),
            "topics": picked,
            "note": "选题来自本地策划模板；生成成稿请继续调用 generate_china_story_post",
        },
        ensure_ascii=False,
    )
