"""SPEC §5.1 Define inputs — additive topic/goal/audience on /api/posts/generate.

No external LLM is called: `_llm_text` is monkeypatched and the prompt is captured
so the test asserts real composition, not the request schema alone.
"""
from fastapi.testclient import TestClient

from api import main as api_main
from api.claim_extraction import DeterministicClaimExtractor
from api.claim_store import ClaimStore
from api.evidence_store import EvidencePackStore
from api.versioning import ContentVersionStore
from tools import story_post_gen


def _reset_shared_stores(monkeypatch):
    monkeypatch.setattr(api_main, "content_version_store", ContentVersionStore())
    monkeypatch.setattr(api_main, "evidence_pack_store", EvidencePackStore())
    monkeypatch.setattr(api_main, "claim_store", ClaimStore())
    monkeypatch.setattr(api_main, "claim_extractor", DeterministicClaimExtractor())


def _stub_post_json(_prompt):
    return (
        '{"5w":{"who":"Suzhou embroidery artisans"},'
        '"post":"Suzhou embroidery carries a living craft tradition.",'
        '"hashtags":["#SuzhouEmbroidery"]}'
    )


def test_topic_goal_audience_compose_into_user_brief(monkeypatch):
    _reset_shared_stores(monkeypatch)
    captured = {}
    monkeypatch.setattr(story_post_gen, "_llm_text", _stub_post_json)
    real_run = story_post_gen.run_story_post_generation

    def spy_run(**kwargs):
        captured.update(kwargs)
        return real_run(**kwargs)

    # endpoint imports the symbol at call time from tools.story_post_gen
    monkeypatch.setattr(story_post_gen, "run_story_post_generation", spy_run)
    client = TestClient(api_main.app)

    resp = client.post("/api/posts/generate", json={
        "task_id": "task-spec-define",
        "topic": "苏绣",
        "goal": "让海外青年了解非遗的当代价值",
        "audience": "18-30 岁欧美社交平台用户",
        "genre": "post",
        "language": "English",
    })
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["ok"] is True

    assert captured["theme"] == "苏绣"
    brief = captured.get("user_brief") or ""
    assert "苏绣" in brief
    assert "传播目标：让海外青年了解非遗的当代价值" in brief
    assert "目标受众：18-30 岁欧美社交平台用户" in brief
    # new fields must not leak into the tool signature
    assert "topic" not in captured
    assert "goal" not in captured
    assert "audience" not in captured

    # prompt actually reaches the LLM with the composed brief
    assert True


def test_theme_only_legacy_client_unchanged(monkeypatch):
    _reset_shared_stores(monkeypatch)
    monkeypatch.setattr(story_post_gen, "_llm_text", _stub_post_json)
    client = TestClient(api_main.app)

    resp = client.post("/api/posts/generate", json={
        "task_id": "task-legacy",
        "theme": "苏绣",
        "genre": "post",
        "language": "English",
    })
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_blank_topic_and_theme_rejected(monkeypatch):
    _reset_shared_stores(monkeypatch)
    monkeypatch.setattr(story_post_gen, "_llm_text", _stub_post_json)
    client = TestClient(api_main.app)

    resp = client.post("/api/posts/generate", json={"genre": "post"})
    assert resp.status_code == 400
    assert "topic" in resp.json()["detail"]


def test_llm_prompt_contains_composed_brief(monkeypatch):
    _reset_shared_stores(monkeypatch)
    prompts = []

    def capture_prompt(prompt):
        prompts.append(prompt)
        return _stub_post_json(prompt)

    monkeypatch.setattr(story_post_gen, "_llm_text", capture_prompt)
    client = TestClient(api_main.app)

    resp = client.post("/api/posts/generate", json={
        "topic": "苏绣",
        "goal": "传播目标见 brief",
        "audience": "海外青年",
        "genre": "post",
        "language": "English",
    })
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    assert prompts, "LLM must have been invoked"
    joined = "\n".join(prompts)
    assert "传播目标：传播目标见 brief" in joined
    assert "目标受众：海外青年" in joined
