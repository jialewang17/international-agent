"""六体裁契约：genre ↔ 兼容 skill_id ↔ 体裁方法卡路径 ↔ format 的单一事实源。

P0 修复依据（六体裁 Skill 接入修复任务）：
- §1 统一六体裁映射：此前同一份映射分散在三处（genre_router._GENRE_SKILL_REL、
  config/skills.yaml 的 file 字段、utils/chinastory_skill_loader_v61.py 的硬编码路径），
  任一处漂移都会造成"路由说 A、实际注入 B"。本模块为唯一权威。
- §2 保护显式选择：非法 genre / format 必须有明确错误码，不得静默落到 post。
- §5 隔离体裁模板：每个 genre 只有自己的一张方法卡，不对其他体裁开放。
- §6 规范输出及失败状态：`supported_formats` 之外的 format 必须显式 UNSUPPORTED，
  不得用同一份输出结构伪装成功。

本模块只放静态契约与纯函数校验：不做关键词检测（在 tools.genre_router）、
不做文件读取（在 utils.skill_registry），以避免循环依赖。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

# 六体裁方法卡的唯一存放目录（相对仓库根）。
METHOD_DIR = "skills/china-story-generation/references/genres"

# 输出契约类型：决定生成结果必须带回哪些字段。
# - post5w : 社交帖文，必须有 post 正文（5w/hashtags 为配套字段）
# - wire   : 新闻通稿，必须有 article 正文
# - body   : 特稿/深度/脚本/问答，必须有 body 正文
OUTPUT_POST = "post5w"
OUTPUT_WIRE = "wire"
OUTPUT_BODY = "body"


@dataclass(frozen=True)
class GenreContract:
    """一个体裁的全部接入契约。"""

    genre: str
    label: str
    skill_id: str
    method_path: str
    default_format: str
    declared_formats: Tuple[str, ...]
    supported_formats: Tuple[str, ...]
    status: str
    output_contract: str


GENRE_CONTRACTS: Dict[str, GenreContract] = {
    "post": GenreContract(
        genre="post",
        label="社交帖文",
        skill_id="china_story_post",
        method_path=f"{METHOD_DIR}/post.md",
        default_format="social_post",
        # post.md v3.2 已定义四种 format，但后端仅有 social_post 的输出结构与验证器；
        # 其余三种按 §6 显式报 UNSUPPORTED，不得用单条 post 字段冒充完成。
        declared_formats=("social_post", "thread", "visual_story", "caption_only"),
        supported_formats=("social_post",),
        status="complete",
        output_contract=OUTPUT_POST,
    ),
    "news": GenreContract(
        genre="news",
        label="新闻通稿",
        skill_id="china_story_news",
        method_path=f"{METHOD_DIR}/news.md",
        default_format="news_article",
        # news.md 定义三种用途；后端目前只有 news_article 的 headline/article 结构。
        declared_formats=("news_article", "newsletter_brief", "press_kit"),
        supported_formats=("news_article",),
        status="complete",
        output_contract=OUTPUT_WIRE,
    ),
    "feature": GenreContract(
        genre="feature",
        label="新闻特稿",
        skill_id="china_story_feature",
        method_path=f"{METHOD_DIR}/feature.md",
        default_format="longform",
        declared_formats=("longform",),
        supported_formats=("longform",),
        status="methods_in",
        output_contract=OUTPUT_BODY,
    ),
    "indepth": GenreContract(
        genre="indepth",
        label="深度报道",
        skill_id="china_story_indepth",
        method_path=f"{METHOD_DIR}/indepth.md",
        default_format="in_depth_report",
        declared_formats=("in_depth_report",),
        supported_formats=("in_depth_report",),
        status="methods_in",
        output_contract=OUTPUT_BODY,
    ),
    "script": GenreContract(
        genre="script",
        label="短视频脚本",
        skill_id="china_story_script",
        method_path=f"{METHOD_DIR}/script.md",
        default_format="short_video",
        declared_formats=("short_video", "reel_hook"),
        supported_formats=("short_video",),
        status="methods_in",
        output_contract=OUTPUT_BODY,
    ),
    "faq": GenreContract(
        genre="faq",
        label="误解澄清",
        skill_id="china_story_faq",
        method_path=f"{METHOD_DIR}/faq.md",
        default_format="faq_mythbust",
        declared_formats=("faq_mythbust",),
        supported_formats=("faq_mythbust",),
        status="methods_in",
        output_contract=OUTPUT_BODY,
    ),
}

GENRES: Tuple[str, ...] = tuple(GENRE_CONTRACTS)

# 输入 format 别名 → (规范 genre, 规范 format)。
# 保留旧调用方使用的别名（youtube_script / deep_dive_report / faq 等），
# 但一律归一到该体裁已实现的 format，避免出现第二套 format 语义。
FORMAT_ALIASES: Dict[str, Tuple[str, str]] = {
    "social_post": ("post", "social_post"),
    "thread": ("post", "thread"),
    "caption_only": ("post", "caption_only"),
    "visual_story": ("post", "visual_story"),
    "news_article": ("news", "news_article"),
    "newsletter_brief": ("news", "newsletter_brief"),
    "press_kit": ("news", "press_kit"),
    "longform": ("feature", "longform"),
    "in_depth_report": ("indepth", "in_depth_report"),
    "indepth": ("indepth", "in_depth_report"),
    "deep_dive_report": ("indepth", "in_depth_report"),
    "short_video": ("script", "short_video"),
    "reel_hook": ("script", "short_video"),
    "youtube_script": ("script", "short_video"),
    "faq_mythbust": ("faq", "faq_mythbust"),
    "faq": ("faq", "faq_mythbust"),
}

FORMAT_TO_GENRE: Dict[str, str] = {alias: g for alias, (g, _) in FORMAT_ALIASES.items()}

# 错误码（§2 / §6）
INVALID_GENRE = "INVALID_GENRE"
INVALID_FORMAT = "INVALID_FORMAT"
GENRE_FORMAT_CONFLICT = "GENRE_FORMAT_CONFLICT"
UNSUPPORTED_GENERATION = "UNSUPPORTED_GENERATION"

_SUPPORTED_HINT = "可选体裁：post / news / feature / indepth / script / faq。"


@dataclass(frozen=True)
class SelectionIssue:
    """体裁/格式选择不合法时的机器可读原因。"""

    code: str
    message: str
    detail: Dict[str, object]


def normalize_genre(genre: Optional[str]) -> Optional[str]:
    """规范化 genre；不合法返回 None（不回落 post）。"""
    key = str(genre or "").strip().lower().replace("-", "_")
    return key if key in GENRE_CONTRACTS else None


def canonicalize_format(format_id: Optional[str]) -> Optional[Tuple[str, str]]:
    """规范化 format，返回 (genre, format)；未知返回 None。"""
    key = str(format_id or "").strip().lower().replace("-", "_")
    return FORMAT_ALIASES.get(key)


def contract_for(genre: str) -> Optional[GenreContract]:
    key = normalize_genre(genre)
    return GENRE_CONTRACTS.get(key) if key else None


def skill_ids_for(genre: str) -> List[str]:
    contract = contract_for(genre)
    # 非法 genre 返回空列表，由严格加载器显式失败；绝不静默转成 post。
    return [contract.skill_id] if contract else []


def check_selection(
    genre: Optional[str],
    format_id: Optional[str] = None,
) -> Tuple[Optional[str], Optional[str], Optional[SelectionIssue]]:
    """校验调用方显式给出的 genre / format。

    返回 (genre, format, issue)。issue 为 None 时表示可以生成。
    """
    explicit_genre = str(genre or "").strip()
    explicit_format = str(format_id or "").strip()

    if explicit_genre:
        normalized = normalize_genre(explicit_genre)
        if normalized is None:
            return None, None, SelectionIssue(
                code=INVALID_GENRE,
                message=f"不支持的体裁：{explicit_genre}。{_SUPPORTED_HINT}",
                detail={"requested_genre": explicit_genre, "allowed_genres": list(GENRES)},
            )
    else:
        normalized = None

    canonical: Optional[Tuple[str, str]] = None
    if explicit_format:
        canonical = canonicalize_format(explicit_format)
        if canonical is None:
            return normalized, None, SelectionIssue(
                code=INVALID_FORMAT,
                message=(
                    f"不支持的 format：{explicit_format}。"
                    "请使用 social_post / news_article / longform / in_depth_report / "
                    "short_video / faq_mythbust 等已登记 format。"
                ),
                detail={"requested_format": explicit_format},
            )

    if canonical and normalized and canonical[0] != normalized:
        return normalized, None, SelectionIssue(
            code=GENRE_FORMAT_CONFLICT,
            message=(
                f"体裁与格式冲突：genre={normalized} 不接受 format={explicit_format}"
                f"（该 format 属于 {canonical[0]}）。请只指定其中一个，或改为匹配的组合。"
            ),
            detail={
                "requested_genre": normalized,
                "requested_format": explicit_format,
                "format_genre": canonical[0],
            },
        )

    resolved_genre = normalized or (canonical[0] if canonical else None)
    if resolved_genre is None:
        return None, None, None

    contract = GENRE_CONTRACTS[resolved_genre]
    resolved_format = canonical[1] if canonical else contract.default_format

    if resolved_format not in contract.supported_formats:
        return resolved_genre, resolved_format, SelectionIssue(
            code=UNSUPPORTED_GENERATION,
            message=(
                f"{contract.genre} 的 format={resolved_format} 目前只有方法定义、"
                "尚无独立输出结构与验证器，已拒绝生成，避免用其他格式的字段伪装成功。"
            ),
            detail={
                "genre": contract.genre,
                "requested_format": resolved_format,
                "declared_formats": list(contract.declared_formats),
                "supported_formats": list(contract.supported_formats),
            },
        )

    return resolved_genre, resolved_format, None


def consistency_report(skills_config: Dict) -> List[str]:
    """校验 skills.yaml 与契约是否一致；返回问题列表（空表示一致）。

    §1 要求"避免不同文件维护的映射产生不一致"，修复后仍可能有人只改 YAML，
    因此把这项校验做成可测试的纯函数，并在回归测试中强制通过。
    """
    problems: List[str] = []
    configured = (skills_config or {}).get("skills") or {}
    configured = {
        str(k).strip().lower().replace("-", "_"): (v or {})
        for k, v in configured.items()
        if isinstance(v, dict)
    }

    for genre, contract in GENRE_CONTRACTS.items():
        meta = configured.get(contract.skill_id)
        if meta is None:
            problems.append(f"[{genre}] skills.yaml 缺少技能条目 {contract.skill_id}")
            continue
        rel = str(meta.get("file", "")).strip().replace("\\", "/")
        if rel != contract.method_path:
            problems.append(
                f"[{genre}] {contract.skill_id} 的 file={rel!r} 与方法卡 {contract.method_path!r} 不一致"
            )
        if not bool(meta.get("enabled", True)):
            problems.append(f"[{genre}] 技能 {contract.skill_id} 处于 enabled=false")

    # feature 与 indepth 不得共用同一张卡或同一 format（§1 明确要求）。
    feature = GENRE_CONTRACTS["feature"]
    indepth = GENRE_CONTRACTS["indepth"]
    if feature.method_path == indepth.method_path:
        problems.append("[feature/indepth] 共用同一方法卡，违反体裁隔离")
    if feature.default_format == indepth.default_format:
        problems.append("[feature/indepth] 默认 format 相同，无法区分两类体裁")
    return problems
