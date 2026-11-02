"""Skills Layer：加载 skills/*.md 并按场景自动激活。"""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from utils.path import get_config_path, get_project_root


@dataclass
class SkillRegistryConfig:
    enabled: bool = True
    auto_activate: bool = True
    discover_files: bool = True
    max_chars_per_skill: int = 1800
    max_active_skills: int = 3
    max_total_chars: int = 4200
    always_on: List[str] = field(default_factory=list)
    disabled: List[str] = field(default_factory=list)


@dataclass
class SkillInfo:
    skill_id: str
    title: str
    file_path: Path
    enabled: bool
    priority: int
    keywords: List[str]
    content: str
    summary: str
    truncated: bool = False
    source: str = "configured"
    error: Optional[str] = None
    raw_chars: int = 0


class SkillLoadError(RuntimeError):
    """必需 Skill 无法完整加载时抛出（P0 §3：不允许带着空 Skill 继续生成）。"""

    def __init__(self, reason: str, message: str, detail: Optional[Dict[str, object]] = None):
        super().__init__(message)
        self.reason = reason
        self.detail: Dict[str, object] = detail or {}


@dataclass(frozen=True)
class LoadedSkillSet:
    """严格加载成功后的结果：正文、来源文件、字符数与内容指纹。"""

    text: str
    skill_ids: tuple[str, ...]
    files: tuple[str, ...]
    chars: int
    sha256: str


@dataclass
class SkillRegistry:
    config_path: Path
    config: SkillRegistryConfig
    skills: Dict[str, SkillInfo]
    load_errors: List[Dict[str, str]]


_registry_cache: Optional[SkillRegistry] = None
_registry_cache_key: Optional[tuple[Optional[float]]] = None


def _normalize_list(value) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if not isinstance(value, list):
        return []
    result: List[str] = []
    for item in value:
        text = str(item).strip()
        if text:
            result.append(text)
    return result


def _to_skill_id(raw: str) -> str:
    return str(raw).strip().lower().replace(" ", "_").replace("-", "_")


def _clamp(text: str, max_chars: int) -> tuple[str, bool]:
    if max_chars <= 0:
        return text, False
    if len(text) <= max_chars:
        return text, False
    return text[:max_chars].rstrip() + "\n\n[...skill content truncated...]", True


def _summary_from_content(content: str) -> str:
    lines = [line.strip() for line in (content or "").splitlines() if line.strip()]
    if not lines:
        return "无描述"

    # 跳过 markdown 标题和列表符号，取第一句有效内容
    for line in lines:
        if line.startswith("#"):
            continue
        candidate = line.lstrip("- ").strip()
        if candidate:
            return candidate[:140]
    return lines[0][:140]


def _load_yaml(path: Path) -> Dict:
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _build_cache_key(config_path: Path) -> tuple[Optional[float]]:
    if not config_path.exists():
        return (None,)
    try:
        return (config_path.stat().st_mtime,)
    except Exception:
        return (None,)


def _load_skill_file(path: Path, max_chars: int) -> tuple[str, bool, Optional[str], int]:
    if not path.exists():
        return "", False, "file_not_found", 0
    try:
        raw = path.read_text(encoding="utf-8", errors="replace").strip()
        text, truncated = _clamp(raw, max_chars)
        return text, truncated, None, len(raw)
    except Exception as exc:
        return "", False, str(exc), 0


def clear_skill_registry_cache() -> None:
    """清空 skills 缓存。"""
    global _registry_cache, _registry_cache_key
    _registry_cache = None
    _registry_cache_key = None


def get_skill_registry(force_reload: bool = False) -> SkillRegistry:
    """获取技能注册中心（带缓存）。"""
    global _registry_cache, _registry_cache_key

    config_path = get_config_path("skills.yaml")
    cache_key = _build_cache_key(config_path)
    if not force_reload and _registry_cache is not None and _registry_cache_key == cache_key:
        return _registry_cache

    raw = _load_yaml(config_path)
    manual = raw.get("manual_activation") if isinstance(raw.get("manual_activation"), dict) else {}
    config = SkillRegistryConfig(
        enabled=bool(raw.get("enabled", True)),
        auto_activate=bool(raw.get("auto_activate", True)),
        discover_files=bool(raw.get("discover_files", True)),
        max_chars_per_skill=int(raw.get("max_chars_per_skill", 1800) or 1800),
        max_active_skills=int(raw.get("max_active_skills", 3) or 3),
        max_total_chars=int(raw.get("max_total_chars", 4200) or 4200),
        always_on=[_to_skill_id(x) for x in _normalize_list(manual.get("always_on"))],
        disabled=[_to_skill_id(x) for x in _normalize_list(manual.get("disabled"))],
    )

    skills: Dict[str, SkillInfo] = {}
    load_errors: List[Dict[str, str]] = []
    root = get_project_root()

    cfg_skills = raw.get("skills") if isinstance(raw.get("skills"), dict) else {}
    for key, meta in cfg_skills.items():
        skill_id = _to_skill_id(key)
        meta_dict = meta if isinstance(meta, dict) else {}
        rel_file = str(meta_dict.get("file", f"skills/{skill_id}.md")).strip()
        file_path = (root / rel_file).resolve()
        enabled = bool(meta_dict.get("enabled", True))
        priority = int(meta_dict.get("priority", 50) or 50)
        keywords = _normalize_list(meta_dict.get("keywords"))
        title = str(meta_dict.get("title", skill_id)).strip() or skill_id

        content, truncated, err, raw_chars = _load_skill_file(file_path, config.max_chars_per_skill)
        if err:
            load_errors.append({"skill_id": skill_id, "error": err, "file": str(file_path)})

        skills[skill_id] = SkillInfo(
            skill_id=skill_id,
            title=title,
            file_path=file_path,
            enabled=enabled,
            priority=priority,
            keywords=keywords,
            content=content,
            summary=_summary_from_content(content) if content else "无描述",
            truncated=truncated,
            source="configured",
            error=err,
            raw_chars=raw_chars,
        )

    if config.discover_files:
        skills_dir = root / "skills"
        if skills_dir.exists() and skills_dir.is_dir():
            for path in sorted(skills_dir.glob("*.md")):
                sid = _to_skill_id(path.stem)
                if sid in skills:
                    continue
                content, truncated, err, raw_chars = _load_skill_file(path, config.max_chars_per_skill)
                if err:
                    load_errors.append({"skill_id": sid, "error": err, "file": str(path)})
                skills[sid] = SkillInfo(
                    skill_id=sid,
                    title=path.stem,
                    file_path=path,
                    enabled=True,
                    priority=40,
                    keywords=[],
                    content=content,
                    summary=_summary_from_content(content) if content else "无描述",
                    truncated=truncated,
                    source="discovered",
                    error=err,
                    raw_chars=raw_chars,
                )

    registry = SkillRegistry(
        config_path=config_path,
        config=config,
        skills=skills,
        load_errors=load_errors,
    )
    _registry_cache = registry
    _registry_cache_key = cache_key
    return registry


def _score_skill(skill: SkillInfo, query: str) -> float:
    text = (query or "").strip().lower()
    if not text:
        return 0.0

    score = 0.0
    if skill.skill_id in text:
        score += 4.0
    if skill.title and skill.title.lower() in text:
        score += 2.0
    for kw in skill.keywords:
        token = kw.strip().lower()
        if token and token in text:
            score += 1.0
    score += skill.priority / 100.0
    return score


def get_active_skills_for_query(query: str, force_reload: bool = False) -> List[SkillInfo]:
    """按 query 返回应激活的技能列表。"""
    registry = get_skill_registry(force_reload=force_reload)
    cfg = registry.config
    if not cfg.enabled:
        return []

    disabled_set = set(cfg.disabled)
    available: Dict[str, SkillInfo] = {}
    for sid, skill in registry.skills.items():
        if not skill.enabled:
            continue
        if sid in disabled_set:
            continue
        if skill.error:
            continue
        available[sid] = skill

    active: List[SkillInfo] = []
    used = set()

    # G-10：always_on（立场 + 证据硬约束）先占位，且**不参与** max_active_skills
    # 与总字符预算竞争——此前它和普通技能一起排队，预算不足时会被 `continue` 掉，
    # 等于把证据规则挤出上下文。
    always_on: List[SkillInfo] = []
    for sid in cfg.always_on:
        skill = available.get(sid)
        if not skill:
            continue
        always_on.append(skill)
        used.add(sid)
    reserved_chars = sum(len(s.content or "") for s in always_on)
    active.extend(always_on)

    if cfg.auto_activate:
        scored: List[tuple[float, SkillInfo]] = []
        for sid, skill in available.items():
            if sid in used:
                continue
            score = _score_skill(skill, query)
            if score > (skill.priority / 100.0):  # 至少命中一个显式信号
                scored.append((score, skill))
        scored.sort(key=lambda x: x[0], reverse=True)
        for _, skill in scored[: max(0, cfg.max_active_skills)]:
            active.append(skill)

    # 控制总字符预算（always_on 已占的额度先扣掉，剩余额度只影响普通技能）
    limited: List[SkillInfo] = list(always_on)
    total_chars = reserved_chars
    for skill in active:
        if skill.skill_id in {s.skill_id for s in always_on}:
            continue
        content_len = len(skill.content or "")
        if cfg.max_total_chars > 0 and total_chars + content_len > cfg.max_total_chars:
            continue
        limited.append(skill)
        total_chars += content_len
    return limited


def format_active_skills_for_prompt(query: str, force_reload: bool = False) -> str:
    """将激活技能渲染成 prompt 片段。"""
    skills = get_active_skills_for_query(query, force_reload=force_reload)
    if not skills:
        return ""

    parts = [
        "以下是本轮根据用户需求自动激活的技能指令。它们是补充约束，若与用户当前明确指令冲突，请以用户当前指令为准。"
    ]
    for skill in skills:
        parts.append(f"### ActiveSkill::{skill.skill_id}\n{skill.content.strip()}")
    return "\n\n".join(parts).strip()


def format_skills_by_ids(*skill_ids: str, force_reload: bool = False) -> str:
    """按 skill_id 列表加载技能正文，供后端工具注入 prompt。"""
    registry = get_skill_registry(force_reload=force_reload)
    parts: List[str] = []
    for raw in skill_ids:
        sid = _to_skill_id(raw)
        skill = registry.skills.get(sid)
        if not skill or not skill.content or skill.error:
            continue
        parts.append(f"### TeamSkill::{skill.skill_id}\n{skill.content.strip()}")
    return "\n\n".join(parts).strip()


def _rel_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(get_project_root().resolve())).replace("\\", "/")
    except Exception:
        return str(path)


def load_required_skills(
    *skill_ids: str,
    max_total_chars: Optional[int] = None,
    force_reload: bool = False,
) -> LoadedSkillSet:
    """严格加载必需的 Skill；任何异常都抛错，绝不返回空内容让生成器继续。

    与 ``format_skills_by_ids`` 的区别：后者为兼容旧调用保留"跳过缺失项"的行为，
    会把空 Skill 静默注入 prompt（P0 §3 明确禁止）。生成链路必须使用本函数。
    """
    registry = get_skill_registry(force_reload=force_reload)
    if not registry.config.enabled:
        raise SkillLoadError(
            "skills_disabled",
            "技能层已被配置关闭（skills.yaml enabled=false），无法加载体裁方法卡",
            {"config_path": str(registry.config_path)},
        )

    requested = [_to_skill_id(raw) for raw in skill_ids if str(raw or "").strip()]
    if not requested:
        raise SkillLoadError("no_skill_requested", "未指定必需 Skill id")

    parts: List[str] = []
    files: List[str] = []
    used: List[str] = []
    for sid in requested:
        skill = registry.skills.get(sid)
        if skill is None:
            raise SkillLoadError(
                "skill_not_registered",
                f"Skill 未在 skills.yaml 注册：{sid}",
                {"skill_id": sid},
            )
        if not skill.enabled:
            raise SkillLoadError(
                "skill_disabled",
                f"Skill 已被禁用：{sid}",
                {"skill_id": sid, "file": _rel_path(skill.file_path)},
            )
        if skill.error:
            raise SkillLoadError(
                "skill_load_failed",
                f"Skill 读取失败：{sid}（{skill.error}）",
                {"skill_id": sid, "file": _rel_path(skill.file_path), "error": skill.error},
            )
        if not (skill.content or "").strip():
            raise SkillLoadError(
                "skill_empty",
                f"Skill 内容为空：{sid}",
                {"skill_id": sid, "file": _rel_path(skill.file_path)},
            )
        if skill.truncated:
            raise SkillLoadError(
                "skill_truncated",
                (
                    f"Skill 被截断：{sid} 需要 {skill.raw_chars} 字符，"
                    f"当前单卡预算 {registry.config.max_chars_per_skill} 字符"
                ),
                {
                    "skill_id": sid,
                    "file": _rel_path(skill.file_path),
                    "raw_chars": skill.raw_chars,
                    "budget": registry.config.max_chars_per_skill,
                },
            )
        parts.append(f"### TeamSkill::{skill.skill_id}\n{skill.content.strip()}")
        files.append(_rel_path(skill.file_path))
        used.append(sid)

    text = "\n\n".join(parts)
    if max_total_chars is not None and max_total_chars > 0 and len(text) > max_total_chars:
        raise SkillLoadError(
            "skill_budget_exceeded",
            f"Skill 合计 {len(text)} 字符，超出本轮预算 {max_total_chars}",
            {"chars": len(text), "budget": max_total_chars, "skill_ids": used},
        )

    return LoadedSkillSet(
        text=text,
        skill_ids=tuple(used),
        files=tuple(files),
        chars=len(text),
        sha256=sha256(text.encode("utf-8")).hexdigest(),
    )


def resolve_always_on(
    force_reload: bool = False,
) -> tuple[List[str], List[Dict[str, str]]]:
    """解析 `config/skills.yaml` 的 ``always_on``：返回 (可用 id 列表, 问题列表)。

    G-10 要求「任何实现不得把证据规则挤出上下文」。旧实现（含
    ``get_active_skills_for_query``）对不可用的 always_on 只做 ``continue``，
    等于**静默丢失**立场与证据硬约束。本函数把这件事变成可判定结果：

    * 返回的 id 列表按配置顺序，供调用方无条件并入本轮必需技能；
    * 问题列表逐条给出 ``skill_id`` + ``reason``（``not_registered`` /
      ``disabled`` / ``load_failed`` / ``empty``），由生成链路升级为硬失败。

    纯读取，不做加载决策，因此不会和 ``load_required_skills`` 的严格语义冲突。
    """
    registry = get_skill_registry(force_reload=force_reload)
    usable: List[str] = []
    problems: List[Dict[str, str]] = []
    if not registry.config.enabled:
        problems.append({"skill_id": "*", "reason": "skills_disabled"})
        return usable, problems

    for sid in registry.config.always_on:
        skill = registry.skills.get(sid)
        if skill is None:
            problems.append({"skill_id": sid, "reason": "not_registered"})
            continue
        if not skill.enabled:
            problems.append({"skill_id": sid, "reason": "disabled"})
            continue
        if skill.error:
            problems.append({"skill_id": sid, "reason": f"load_failed: {skill.error}"})
            continue
        if not (skill.content or "").strip():
            problems.append({"skill_id": sid, "reason": "empty"})
            continue
        usable.append(sid)
    return usable, problems


def format_skill_catalog_for_prompt(force_reload: bool = False) -> str:
    """渲染可用技能目录（用于全局 system prompt）。"""
    registry = get_skill_registry(force_reload=force_reload)
    cfg = registry.config
    if not cfg.enabled:
        return ""

    lines = ["## Skills Catalog", ""]
    for sid in sorted(registry.skills.keys()):
        skill = registry.skills[sid]
        if not skill.enabled or skill.error:
            continue
        kw = ", ".join(skill.keywords[:8]) if skill.keywords else "无关键词"
        lines.append(f"- **{sid}**: {skill.summary} (keywords: {kw})")
    return "\n".join(lines).strip()
