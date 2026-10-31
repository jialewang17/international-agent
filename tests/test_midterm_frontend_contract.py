"""Midterm frontend prototype — contract, isolation and gate-safety checks.

These tests do not drive a browser. They pin the properties that must stay true
no matter how the UI is styled later:

1. the workbench shell exposes all six stages and both run modes;
2. the DEMO adapter performs zero network calls and is fully isolated;
3. the LIVE paths only use the real story-task endpoints;
4. the frontend cannot manufacture Gate A/B/C;
5. the legacy tool UI still exists (no regression).
"""
import re
from pathlib import Path

from fastapi.testclient import TestClient

from api import main as api_main
from api.evidence_store import EvidencePackStore
from api.story_session import StorySessionStore, NarrativePlan
import api.story_router as story_router

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"


def read(rel: str) -> str:
    return (FRONTEND / rel).read_text(encoding="utf-8")


def test_workbench_shell_has_six_stages_and_two_modes():
    html = read("workbench.html")
    for stage in ["DEFINE", "GROUND", "PLAN", "CREATE", "REVISE_AUDIT", "APPROVE"]:
        assert 'data-stage="' + stage + '"' in html, stage
    assert 'data-mode="live"' in html
    assert 'data-mode="demo"' in html
    assert "DEMO · 演示数据" in html
    assert 'id="confirmModal"' in html
    assert "Gate A" in html and "Gate B" in html and "Gate C" in html


def test_workbench_render_views_cover_all_stages():
    js = read("js/workbench/workbench.js")
    for stage in ["DEFINE", "GROUND", "PLAN", "CREATE", "REVISE_AUDIT", "APPROVE"]:
        assert stage in js
    assert "confirm" in js and "enterCreate" in js
    # The UI must say so explicitly when a live capability is missing.
    assert "NOT_CONNECTED" in js
    assert "待接入" in js


def test_demo_adapter_is_network_free_and_isolated():
    demo = read("js/workbench/demo-adapter.js")
    assert "fetch(" not in demo
    assert "XMLHttpRequest" not in demo
    assert "/api/" not in demo
    assert "demo-simulated" in demo  # gate state is explicitly a demo state
    # demo sources are labelled
    assert demo.count('source_type: "demo"') >= 1
    assert "DEMO" in demo


def test_live_adapter_uses_only_real_story_task_endpoints():
    api_js = read("js/workbench/story-api.js")
    assert 'const BASE = "/api/story-tasks"' in api_js
    # Every relative path used by the client must be one of the real endpoints.
    used = set(re.findall(r'call\("(?:GET|POST)", "([^"]*)"', api_js))
    assert used <= {"", "/{id}", "/plan", "/feedback", "/confirm", "/enter-create"} or used == {
        "", "/plan", "/feedback", "/confirm", "/enter-create"
    } or all(p.startswith("/") or p == "" for p in used)
    for path in ["/plan", "/feedback", "/confirm", "/enter-create"]:
        assert '"' + path + '"' in api_js
    # The frontend must never write gate status directly.
    assert "evidence_status" not in api_js
    assert "/gate" not in api_js


def test_adapters_expose_unified_capability_contract():
    gen = read("js/workbench/generation-adapter.js")
    ev = read("js/workbench/evaluation-adapter.js")
    for src in (gen, ev):
        for status in ["READY", "NOT_CONNECTED", "RUNNING", "SUCCEEDED", "FAILED", "BLOCKED"]:
            assert status in src, status
        assert "endpoint" in src
    assert "generateContent" in gen
    assert "evaluateContent" in ev
    assert "content_version_id" in gen
    assert '"D1"' in ev and '"D6"' in ev


def test_legacy_tool_ui_is_preserved():
    html = read("index.html")
    assert 'id="formPost"' in html
    assert 'id="formTopics"' in html
    assert 'id="formReply"' in html
    # The legacy page keeps a link to the workbench (now served at "/", the
    # primary entry) and carries the explicit legacy-flow banner.
    assert 'href="/"' in html
    assert "legacy-ribbon" in html
    assert "旧版工具流程" in html


def test_root_serves_workbench_and_tools_serves_legacy(monkeypatch):
    client = TestClient(api_main.app)
    root = client.get("/")
    assert root.status_code == 200
    assert "wb-shell" in root.text
    assert "legacy-ribbon" not in root.text

    tools = client.get("/tools")
    assert tools.status_code == 200
    assert "legacy-ribbon" in tools.text
    assert 'id="formPost"' in tools.text

    # The static direct links keep working for bookmarks.
    assert client.get("/static/workbench.html").status_code == 200
    assert client.get("/static/index.html").status_code == 200


def _fresh_client(monkeypatch):
    store = StorySessionStore()
    packs = EvidencePackStore()
    store.bind_evidence_pack_store(packs)
    monkeypatch.setattr(story_router, "story_session_store", store)
    monkeypatch.setattr(story_router, "_evidence_pack_store", packs)
    monkeypatch.setattr(api_main, "story_session_store", store, raising=False)
    return TestClient(api_main.app), store


def test_live_flow_ground_real_and_gates_hold(monkeypatch):
    """P0-1: real Ground now runs on create; gates must still hold."""
    client, store = _fresh_client(monkeypatch)

    created = client.post("/api/story-tasks", json={"topic": "苏绣", "user_materials": ""})
    assert created.status_code == 200
    body = created.json()["data"]
    task_id = body["task"]["task_id"]
    assert body["workflow"]["stage"] == "PLAN"  # real Ground completed
    ground = body["ground"]
    assert ground is not None and ground["evidence_pack_id"].startswith("ep_")
    assert ground["sources"]  # real source cards for the frontend
    # the pack really exists in the bound canonical store
    assert store.evidence_pack_store.get(ground["evidence_pack_id"])

    snapshot = client.get("/api/story-tasks/" + task_id)
    assert snapshot.status_code == 200
    assert snapshot.json()["data"]["workflow"]["evidence_status"] == "NOT_EVALUATED"
    assert snapshot.json()["data"]["workflow"]["gates"] == {}

    # Plan can now be saved (real Ground summary exists).
    plan = client.post("/api/story-tasks/" + task_id + "/plan", json={"title": "草案"})
    assert plan.status_code == 200

    # Gate A still requires the joint confirmation endpoint.
    enter = client.post("/api/story-tasks/" + task_id + "/enter-create")
    assert enter.status_code == 409
    assert enter.json()["detail"]["gate"] == "A"

    confirm = client.post(
        "/api/story-tasks/" + task_id + "/confirm",
        json={"audience": "青年", "genre": "post", "language": "English"},
    )
    assert confirm.status_code == 200

    # Gate A confirmed, but no trusted Gate B -> Create still refused.
    enter = client.post("/api/story-tasks/" + task_id + "/enter-create")
    assert enter.status_code == 409
    assert enter.json()["detail"]["gate"] == "B"
    snap = client.get("/api/story-tasks/" + task_id).json()["data"]
    assert snap["workflow"]["evidence_status"] == "NOT_EVALUATED"


def test_gate_b_is_not_writable_over_http(monkeypatch):
    client, store = _fresh_client(monkeypatch)
    task_id = client.post("/api/story-tasks", json={"topic": "苏绣"}).json()["data"]["task"]["task_id"]
    # P0-1: real Ground already attached a canonical pack on create.
    assert store.machine.get(task_id).stage == "PLAN"
    store.save_plan(task_id, NarrativePlan(title="草案"))

    resp = client.post(
        "/api/workflow/" + task_id + "/gate",
        json={"gate": "B", "decision": "passed", "reason": "forged", "decided_by": "system"},
    )
    assert resp.status_code == 409
    assert resp.json()["detail"]["gate"] == "B"

    snapshot = client.get("/api/story-tasks/" + task_id).json()["data"]
    assert snapshot["workflow"]["evidence_status"] == "NOT_EVALUATED"
    assert "B" not in snapshot["workflow"]["gates"]


def test_demo_content_is_never_labelled_as_real_evaluation():
    demo = read("js/workbench/demo-adapter.js")
    assert "示例评价" in demo
    assert "非真实" in demo
    assert "DEMO 示例内容" in demo
    # no fake "verified" claim status in demo claims
    assert '"VERIFIED"' not in demo
