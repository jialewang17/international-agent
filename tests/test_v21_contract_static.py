from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]

def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")

def test_api_meta_six_stages_and_three_gates():
    s = read("api/main.py")
    for token in ["DEFINE", "GROUND", "PLAN", "CREATE", "REVISE_AUDIT", "APPROVE"]:
        assert token in s
    for token in ["Task Confirmation", "Evidence Exception", "Final Approval"]:
        assert token in s
    assert '@app.post("/api/posts/approve")' in s

def test_runtime_files_have_no_legacy_g_stage_ids():
    for rel in ["api/main.py", "frontend/js/app.js", "frontend/index.html", "tools/story_post_gen.py"]:
        s = read(rel)
        assert not re.search(r'["\\\']G[1-7]["\\\']', s), (rel, "legacy G-stage id")

def test_frontend_uses_backend_gate_c():
    s = read("frontend/js/app.js")
    assert 'api("/api/posts/approve"' in s
    assert 'step.id === "APPROVE"' in s
    assert 'g.id === "C"' in s

def test_required_tools_exist_and_are_enabled():
    cfg = read("config/tools.yaml")
    for name in ["load_story_knowledge", "detect_content_genre", "intl_comm_reply"]:
        assert (ROOT / ("tools/" + name + ".py")).exists() or name == "detect_content_genre"
        assert f"- {name}" in cfg
