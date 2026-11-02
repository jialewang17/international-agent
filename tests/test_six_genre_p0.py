"""P0 六体裁 Skill 接入修复：路由 / 严格加载 / Prompt 注入 / 输出状态回归测试。

对应任务书 §三 的 8 条 P0 项与 §四 验收标准。全部测试**不调用真实大模型**：
``_llm_text`` 一律用替身替换，检索与对齐门控用固定桩，
以便把断言集中在"体裁契约、加载状态与注入内容"本身。
"""

from __future__ import annotations

import json
import pathlib

import pytest
import yaml

from tools import story_post_gen
from tools.genre_router import detect_genre, resolve_selection, skill_ids_for_genre
from utils import skill_registry
from utils.genre_contracts import (
    FORMAT_ALIASES,
    GENRE_CONTRACTS,
    GENRES,
    METHOD_DIR,
    consistency_report,
)
from utils.skill_registry import (
    SkillInfo,
    SkillLoadError,
    SkillRegistry,
    SkillRegistryConfig,
    load_required_skills,
)

ROOT = pathlib.Path(__file__).resolve().parents[1]
SKILLS_YAML = ROOT / "config" / "skills.yaml"


# --------------------------------------------------------------------------
# 测试替身
# --------------------------------------------------------------------------

def _evidence_rows():
    return [
        {
            "category": "culture",
            "statement": "苏绣于2006年列入国家级非物质文化遗产名录",
            "source": "https://www.ihchina.cn/suxiu",
            "source_type": "本地库",
            "retrieval": "kb",
        },
        {
            "category": "culture",
            "statement": "镇湖绣品街聚集数千名绣娘，双面绣需数月完成",
            "source": "https://www.suzhou.gov.cn/zhenhu",
            "source_type": "本地库",
            "retrieval": "kb",
        },
    ]


class PromptSpy:
    """记录真实组装出的 prompt，并返回预设 JSON。"""

    def __init__(self, payload):
        self.payload = payload
        self.prompts: list[str] = []

    def __call__(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if isinstance(self.payload, str):
            return self.payload
        return json.dumps(self.payload, ensure_ascii=False)

    @property
    def prompt(self) -> str:
        assert self.prompts, "模型未被调用，prompt 为空"
        return self.prompts[0]


PAYLOADS = {
    "post": {
        "5w": {
            "who": "culture explainer",
            "says_what": "Suzhou embroidery is living heritage",
            "channel": "Instagram, single post",
            "to_whom": "readers interested in craft",
            "effect": "curiosity",
        },
        "post": "Suzhou embroidery turned thread into a language of its own.",
        "hashtags": ["#SuzhouEmbroidery", "#IntangibleHeritage"],
        "title_or_hook": "",
        "ops_tips": [],
        "evidence_notes": ["Evidence#1 -> ICH listing"],
    },
    "news": {
        "wire_plan": {"editorial_mode": "institutional_release", "angle": "ICH listing"},
        "headline": "Suzhou embroidery marks two decades on national ICH list",
        "dek": "",
        "dateline": "",
        "article": "Suzhou embroidery entered the national ICH list in 2006.",
        "quotes_used": [],
        "ops_tips": [],
        "evidence_notes": ["Evidence#1 -> ICH listing"],
    },
    "feature": {
        "genre": "feature",
        "title": "The hands behind the thread",
        "body": "A workshop in Zhenhu, where embroidery frames line the wall.",
        "ops_tips": [],
        "missing_fields": [],
        "evidence_notes": ["Evidence#1 -> ICH listing"],
    },
    "indepth": {
        "genre": "indepth",
        "title": "Why heritage crafts need a market, not just a list",
        "body": "The listing is only the first link in a longer chain.",
        "ops_tips": [],
        "missing_fields": [],
        "evidence_notes": ["Evidence#1 -> ICH listing"],
    },
    "script": {
        "genre": "script",
        "title": "Fifteen seconds on Suzhou embroidery",
        "body": "SHOT 1: a needle enters silk. VO: one thread, two faces.",
        "ops_tips": [],
        "missing_fields": [],
        "evidence_notes": ["Evidence#1 -> ICH listing"],
    },
    "faq": {
        "genre": "faq",
        "title": "Is Suzhou embroidery only a museum craft?",
        "body": "Myth: it survives only behind glass. Fact: workshops still train embroiderers.",
        "ops_tips": [],
        "missing_fields": [],
        "evidence_notes": ["Evidence#1 -> ICH listing"],
    },
}


@pytest.fixture
def stub_gates(monkeypatch):
    """固定检索与对齐门控，让测试聚焦在体裁契约与加载行为上。"""
    monkeypatch.setattr(story_post_gen, "retrieve_statements", lambda *a, **k: _evidence_rows())
    monkeypatch.setattr(
        story_post_gen,
        "check_theme_evidence_alignment",
        lambda *a, **k: {"ok": True, "reason": "stub"},
    )


def _skill_info(
    root: pathlib.Path,
    skill_id: str,
    rel: str,
    content: str,
    *,
    enabled: bool = True,
    truncated: bool = False,
    raw_chars: int | None = None,
) -> SkillInfo:
    return SkillInfo(
        skill_id=skill_id,
        title=skill_id,
        file_path=(root / rel),
        enabled=enabled,
        priority=90,
        keywords=[],
        content=content,
        summary=skill_id,
        truncated=truncated,
        source="configured",
        error=None,
        raw_chars=len(content) if raw_chars is None else raw_chars,
    )


def _fake_registry(skill_infos) -> SkillRegistry:
    config = SkillRegistryConfig(
        enabled=True,
        auto_activate=True,
        discover_files=False,
        max_chars_per_skill=16000,
        max_active_skills=3,
        max_total_chars=24000,
        always_on=[],
        disabled=[],
    )
    return SkillRegistry(
        config_path=SKILLS_YAML,
        config=config,
        skills={info.skill_id: info for info in skill_infos},
        load_errors=[],
    )


def _use_registry(monkeypatch, skill_infos) -> None:
    registry = _fake_registry(skill_infos)
    monkeypatch.setattr(skill_registry, "get_skill_registry", lambda force_reload=False: registry)


def _post_skill(content: str, **kwargs) -> SkillInfo:
    return _skill_info(
        ROOT, "china_story_post", GENRE_CONTRACTS["post"].method_path, content, **kwargs
    )


# --------------------------------------------------------------------------
# §1 六体裁映射：单一事实源 + 与 skills.yaml 一致 + feature/indepth 不混用
# --------------------------------------------------------------------------

def test_genre_mapping_matches_skills_yaml():
    cfg = yaml.safe_load(SKILLS_YAML.read_text(encoding="utf-8"))
    assert consistency_report(cfg) == []


def test_every_genre_has_existing_method_card():
    for genre in GENRES:
        contract = GENRE_CONTRACTS[genre]
        path = ROOT / contract.method_path
        assert contract.method_path.startswith(f"{METHOD_DIR}/"), genre
        assert path.is_file(), f"{genre} 方法卡缺失：{contract.method_path}"
        assert path.read_text(encoding="utf-8").strip(), f"{genre} 方法卡为空"


def test_feature_and_indepth_are_distinct():
    feature = GENRE_CONTRACTS["feature"]
    indepth = GENRE_CONTRACTS["indepth"]
    assert feature.method_path != indepth.method_path
    assert feature.default_format != indepth.default_format
    assert feature.skill_id != indepth.skill_id
    assert detect_genre("写一篇关于苏绣的深度报道")["genre"] == "indepth"
    assert detect_genre("写一篇关于苏绣的特稿")["genre"] == "feature"


def test_format_aliases_point_to_declaring_genre():
    for alias, (genre, fmt) in FORMAT_ALIASES.items():
        contract = GENRE_CONTRACTS[genre]
        assert fmt in contract.declared_formats, f"{alias} -> {genre}/{fmt} 未在契约声明"


def test_unknown_genre_yields_no_skill_id():
    assert skill_ids_for_genre("post") == ["china_story_post"]
    # 非法体裁返回空列表，绝不静默回落 china_story_post
    assert skill_ids_for_genre("story") == []
    assert skill_ids_for_genre("") == []


# --------------------------------------------------------------------------
# §2 保护显式选择
# --------------------------------------------------------------------------

def test_explicit_genre_beats_keyword(stub_gates, monkeypatch):
    spy = PromptSpy(PAYLOADS["post"])
    monkeypatch.setattr(story_post_gen, "_llm_text", spy)

    # 提示词里写着"深度报道"，但用户显式选了 post
    result = story_post_gen.run_story_post_generation(
        theme="写一篇关于苏绣的深度报道", genre="post"
    )
    assert result.get("error") is None
    assert result["genre"] == "post"
    assert result["genre_meta"]["source"] == "user_override"
    assert "### TeamSkill::china_story_post" in spy.prompt
    assert "### TeamSkill::china_story_indepth" not in spy.prompt


def test_explicit_indepth_beats_post_keyword(stub_gates, monkeypatch):
    spy = PromptSpy(PAYLOADS["indepth"])
    monkeypatch.setattr(story_post_gen, "_llm_text", spy)

    result = story_post_gen.run_story_post_generation(
        theme="写一条 instagram 帖文介绍苏绣", genre="indepth"
    )
    assert result.get("error") is None
    assert result["genre"] == "indepth"
    assert result["prompt_file"] == "prompt/story_genre_prompt.txt"


def test_keyword_autodetect_still_works(stub_gates, monkeypatch):
    spy = PromptSpy(PAYLOADS["indepth"])
    monkeypatch.setattr(story_post_gen, "_llm_text", spy)

    result = story_post_gen.run_story_post_generation(theme="写一篇关于苏绣的深度报道")
    assert result.get("error") is None
    assert result["genre"] == "indepth"
    assert result["genre_meta"]["source"] == "keyword"


def test_invalid_genre_is_rejected_not_turned_into_post(stub_gates, monkeypatch):
    spy = PromptSpy(PAYLOADS["post"])
    monkeypatch.setattr(story_post_gen, "_llm_text", spy)

    result = story_post_gen.run_story_post_generation(theme="苏绣", genre="story")
    assert result["generation_status"] == "INVALID_GENRE"
    assert result["genre"] == ""
    assert result["post"] == ""
    assert "post" not in result["skills_applied"]
    assert spy.prompts == [], "非法体裁不得进入模型调用"


def test_genre_format_conflict_is_rejected(stub_gates, monkeypatch):
    spy = PromptSpy(PAYLOADS["news"])
    monkeypatch.setattr(story_post_gen, "_llm_text", spy)

    result = story_post_gen.run_story_post_generation(
        theme="苏绣", genre="news", format="social_post"
    )
    assert result["generation_status"] == "GENRE_FORMAT_CONFLICT"
    assert result["post"] == ""
    assert spy.prompts == []


def test_unsupported_format_is_explicit(stub_gates, monkeypatch):
    spy = PromptSpy(PAYLOADS["post"])
    monkeypatch.setattr(story_post_gen, "_llm_text", spy)

    # post.md v3.2 定义了 thread，但后端尚未实现独立输出结构
    result = story_post_gen.run_story_post_generation(
        theme="苏绣", genre="post", format="thread"
    )
    assert result["generation_status"] == "UNSUPPORTED_GENERATION"
    assert result["post"] == ""
    assert spy.prompts == []


# --------------------------------------------------------------------------
# §3 严格加载必需 Skill
# --------------------------------------------------------------------------

def test_missing_skill_blocks_generation(stub_gates, monkeypatch):
    spy = PromptSpy(PAYLOADS["post"])
    monkeypatch.setattr(story_post_gen, "_llm_text", spy)
    _use_registry(monkeypatch, [])

    result = story_post_gen.run_story_post_generation(theme="苏绣", genre="post")
    assert result["generation_status"] == "SKILL_UNAVAILABLE"
    assert result["post"] == ""
    assert result["skill_load"]["load_status"] == "failed"
    assert result["skill_load"]["error_reason"] == "skill_not_registered"
    assert spy.prompts == [], "缺卡时不得调用模型"


def test_empty_skill_blocks_generation(stub_gates, monkeypatch):
    spy = PromptSpy(PAYLOADS["post"])
    monkeypatch.setattr(story_post_gen, "_llm_text", spy)
    _use_registry(monkeypatch, [_post_skill("   ")])

    result = story_post_gen.run_story_post_generation(theme="苏绣", genre="post")
    assert result["generation_status"] == "SKILL_UNAVAILABLE"
    assert result["skill_load"]["error_reason"] == "skill_empty"
    assert spy.prompts == []


def test_disabled_skill_blocks_generation(stub_gates, monkeypatch):
    spy = PromptSpy(PAYLOADS["post"])
    monkeypatch.setattr(story_post_gen, "_llm_text", spy)
    _use_registry(monkeypatch, [_post_skill("卡片正文" * 50, enabled=False)])

    result = story_post_gen.run_story_post_generation(theme="苏绣", genre="post")
    assert result["generation_status"] == "SKILL_UNAVAILABLE"
    assert result["skill_load"]["error_reason"] == "skill_disabled"
    assert spy.prompts == []


def test_truncated_skill_blocks_generation(stub_gates, monkeypatch):
    spy = PromptSpy(PAYLOADS["post"])
    monkeypatch.setattr(story_post_gen, "_llm_text", spy)
    _use_registry(
        monkeypatch,
        [_post_skill("卡片正文" * 50, truncated=True, raw_chars=20000)],
    )

    result = story_post_gen.run_story_post_generation(theme="苏绣", genre="post")
    assert result["generation_status"] == "SKILL_UNAVAILABLE"
    assert result["skill_load"]["error_reason"] == "skill_truncated"
    assert result["skill_load"]["raw_chars"] == 20000
    assert spy.prompts == []


def test_loader_rejects_over_budget_context():
    with pytest.raises(SkillLoadError) as exc:
        load_required_skills("china_story_post", max_total_chars=10)
    assert exc.value.reason == "skill_budget_exceeded"


def test_loader_reports_real_loaded_files():
    loaded = load_required_skills("china_story_news")
    assert loaded.skill_ids == ("china_story_news",)
    assert loaded.files == (GENRE_CONTRACTS["news"].method_path,)
    assert loaded.chars > 0 and len(loaded.sha256) == 64


# --------------------------------------------------------------------------
# §4/§5 Prompt 注入与体裁隔离
# --------------------------------------------------------------------------

@pytest.mark.parametrize("genre", GENRES)
def test_prompt_injects_exactly_one_genre_card(genre, stub_gates, monkeypatch):
    spy = PromptSpy(PAYLOADS[genre])
    monkeypatch.setattr(story_post_gen, "_llm_text", spy)

    result = story_post_gen.run_story_post_generation(theme="苏绣", genre=genre)
    assert result.get("error") is None, result.get("error")
    assert len(spy.prompts) == 1

    contract = GENRE_CONTRACTS[genre]
    assert f"### TeamSkill::{contract.skill_id}" in spy.prompt

    # 其他体裁的方法卡一张都不许出现（防止串卡）
    for other in GENRES:
        if other == genre:
            continue
        assert f"### TeamSkill::{GENRE_CONTRACTS[other].skill_id}" not in spy.prompt

    # 本体裁卡必须完整注入（未被截断）
    card = (ROOT / contract.method_path).read_text(encoding="utf-8").strip()
    assert card in spy.prompt


def test_news_prompt_has_no_post_caption_rules(stub_gates, monkeypatch):
    spy = PromptSpy(PAYLOADS["news"])
    monkeypatch.setattr(story_post_gen, "_llm_text", spy)

    result = story_post_gen.run_story_post_generation(theme="苏绣造像馆开幕", genre="news")
    assert result.get("error") is None
    assert result["prompt_file"] == "prompt/story_news_prompt.txt"
    assert "Lasswell 5W is the PLANNING spine" not in spy.prompt
    # 通稿模板自带"禁止 emoji"的独立规则，而不是沿用帖文的 emoji 开关说明
    assert "never use emojis" in spy.prompt
    assert "engagement bait" not in spy.prompt


@pytest.mark.parametrize("genre", ["feature", "indepth", "script", "faq"])
def test_professional_genres_do_not_fall_back_to_post_template(genre, stub_gates, monkeypatch):
    spy = PromptSpy(PAYLOADS[genre])
    monkeypatch.setattr(story_post_gen, "_llm_text", spy)

    result = story_post_gen.run_story_post_generation(theme="苏绣", genre=genre)
    assert result.get("error") is None
    assert result["prompt_file"] == "prompt/story_genre_prompt.txt"
    assert "Lasswell 5W is the PLANNING spine" not in spy.prompt
    assert "### TeamSkill::china_story_post" not in spy.prompt


# --------------------------------------------------------------------------
# §6 输出与失败状态
# --------------------------------------------------------------------------

def test_unparsable_output_is_output_invalid(stub_gates, monkeypatch):
    monkeypatch.setattr(
        story_post_gen, "_llm_text", lambda _p: "这一段是普通文本，不是 JSON。"
    )
    result = story_post_gen.run_story_post_generation(theme="苏绣", genre="post")
    assert result["generation_status"] == "OUTPUT_INVALID"
    assert result["post"] == "", "不得把原始文本当合格成稿返回"
    assert result["output_error"] == "invalid_json"


def test_output_missing_body_is_output_invalid(stub_gates, monkeypatch):
    monkeypatch.setattr(
        story_post_gen, "_llm_text", lambda _p: json.dumps({"title": "only a title"})
    )
    result = story_post_gen.run_story_post_generation(theme="苏绣", genre="post")
    assert result["generation_status"] == "OUTPUT_INVALID"
    assert result["post"] == ""


@pytest.mark.parametrize("genre", GENRES)
def test_success_keeps_genre_specific_fields(genre, stub_gates, monkeypatch):
    spy = PromptSpy(PAYLOADS[genre])
    monkeypatch.setattr(story_post_gen, "_llm_text", spy)

    result = story_post_gen.run_story_post_generation(theme="苏绣", genre=genre)
    assert result["generation_status"] == "OK"
    assert result["genre"] == genre
    assert result["format"] == GENRE_CONTRACTS[genre].default_format
    assert result["output_contract"] == GENRE_CONTRACTS[genre].output_contract
    assert result["post"], "成功路径必须有正文"

    if genre == "post":
        assert result["hashtags"] == PAYLOADS["post"]["hashtags"]
        assert result["five_w"]["who"]
    elif genre == "news":
        assert result["article"] == PAYLOADS["news"]["article"]
        assert result["headline"] == PAYLOADS["news"]["headline"]
        assert result["hashtags"] == []
    else:
        assert result["article"] == PAYLOADS[genre]["body"]


# --------------------------------------------------------------------------
# §7 可审计诊断
# --------------------------------------------------------------------------

def test_skill_load_diagnostics_are_complete_and_safe(stub_gates, monkeypatch):
    spy = PromptSpy(PAYLOADS["post"])
    monkeypatch.setattr(story_post_gen, "_llm_text", spy)

    result = story_post_gen.run_story_post_generation(theme="苏绣", genre="post")
    diag = result["skill_load"]

    assert diag["requested_method_id"] == "china_story_post"
    assert diag["loaded_method_id"] == "china_story_post"
    assert diag["loaded_files"] == [GENRE_CONTRACTS["post"].method_path]
    assert diag["load_status"] == "ok"
    assert diag["error_reason"] is None
    assert diag["routing_source"] == "user_override"
    assert diag["resolved_genre"] == "post"
    assert diag["resolved_format"] == "social_post"
    assert diag["prompt_template"] == "prompt/story_post_prompt.txt"
    assert diag["truncated"] is False
    assert len(diag["skill_sha256"]) == 64
    assert diag["skill_chars"] > 0

    # 诊断只带安全元数据，不携带完整 Prompt
    assert "prompt" not in diag
    assert spy.prompt not in json.dumps(result, ensure_ascii=False)


def test_routing_reports_failed_load_not_expected_id(stub_gates, monkeypatch):
    """加载失败时 loaded_method_id 必须为空，不能拿期望 id 冒充加载成功。"""
    spy = PromptSpy(PAYLOADS["post"])
    monkeypatch.setattr(story_post_gen, "_llm_text", spy)
    _use_registry(monkeypatch, [])

    result = story_post_gen.run_story_post_generation(theme="苏绣", genre="post")
    diag = result["skill_load"]
    assert diag["requested_method_id"] == "china_story_post"
    assert diag["loaded_method_id"] is None
    assert diag["loaded_files"] == []


# --------------------------------------------------------------------------
# API 层：失败状态必须透传，且只返回安全元数据
# --------------------------------------------------------------------------

def test_api_propagates_selection_failures():
    from fastapi.testclient import TestClient

    import api.main as api_main

    client = TestClient(api_main.app)
    cases = [
        ({"theme": "苏绣", "genre": "story"}, "INVALID_GENRE"),
        ({"theme": "苏绣", "genre": "post", "format": "thread"}, "UNSUPPORTED_GENERATION"),
        ({"theme": "苏绣", "genre": "news", "format": "social_post"}, "GENRE_FORMAT_CONFLICT"),
    ]
    for body, expected in cases:
        resp = client.post("/api/posts/generate", json=body)
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["ok"] is False, body
        assert payload["data"]["generation_status"] == expected, body
        assert payload["data"]["post"] == "", body


def test_api_skill_failure_returns_diagnostics_not_prompt(stub_gates, monkeypatch):
    from fastapi.testclient import TestClient

    import api.main as api_main

    spy = PromptSpy(PAYLOADS["post"])
    monkeypatch.setattr(story_post_gen, "_llm_text", spy)
    _use_registry(monkeypatch, [])

    client = TestClient(api_main.app)
    resp = client.post(
        "/api/posts/generate",
        json={"theme": "苏绣", "genre": "post", "task_id": "task-p0-skill-missing"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["ok"] is False
    data = payload["data"]
    assert data["generation_status"] == "SKILL_UNAVAILABLE"
    assert data["skill_load"]["error_reason"] == "skill_not_registered"
    assert "prompt" not in data["skill_load"]
    assert "_evidence_pack" not in data
    assert spy.prompts == []
