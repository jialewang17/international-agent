"""Frontend closeout checks: platform vocabulary, mobile shell grid, Gate A copy.

Three properties are pinned here:

1. the workbench shows "X" while the backend skills only understand "twitter",
   so every seam that leaves the browser must send the backend id and every
   value read back must be turned into the value the UI can render;
2. a shell collapsed on desktop must not keep its three-column CSS grid after
   the viewport shrinks to one column (mobile);
3. the Gate A dialog must not promise Create: Gate A alone never opens Create.

The JS assertions run through Node (skipped when Node is unavailable); the CSS
and copy assertions are static so they hold in any environment.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
JS_DIR = FRONTEND / "js" / "workbench"

NODE = shutil.which("node")

JS_HARNESS = r"""
const fs = require("fs"), path = require("path"), vm = require("vm");
const dir = process.env.WB_JS_DIR;
const document = { querySelector: () => null, querySelectorAll: () => [] };
const ctx = {
  window: { document },
  document,
  console,
  setTimeout,
  clearTimeout,
  AbortController,
  fetch: () => { throw new Error("network disabled in this harness"); },
};
ctx.window.window = ctx.window;
vm.createContext(ctx);

function load(name) {
  vm.runInContext(fs.readFileSync(path.join(dir, name), "utf8"), ctx, { filename: name });
}

load("utils.js");
const U = ctx.window.WB.util;

const captured = [];
U.getJSON = function (url, options) {
  captured.push({ url: url, body: options && options.body ? options.body : null });
  return Promise.resolve({ ok: true, status: 200, data: { data: {} } });
};

load("story-api.js");
load("generation-adapter.js");
load("evaluation-adapter.js");

(async () => {
  const report = {
    toBackend: {
      lower: U.platformToBackend("x"),
      upper: U.platformToBackend("X"),
      padded: U.platformToBackend("  Twitter "),
      domain: U.platformToBackend("x.com"),
      slash: U.platformToBackend("twitter/x"),
      passthrough: U.platformToBackend("instagram"),
      empty: U.platformToBackend(""),
      missing: U.platformToBackend(null),
      undecided: U.platformToBackend("undecided"),
    },
    toUi: {
      twitter: U.platformToUi("twitter"),
      x: U.platformToUi("x"),
      instagram: U.platformToUi("instagram"),
      empty: U.platformToUi(null),
    },
    label: {
      twitter: U.platformLabel("twitter"),
      x: U.platformLabel("x"),
      instagram: U.platformLabel("instagram"),
      other: U.platformLabel("other"),
      none: U.platformLabel(""),
    },
    confirmBodies: [],
    generateBody: null,
    generateEcho: null,
    evaluateBody: null,
    normalizedIsCopy: null,
  };

  const base = { audience: "青年", genre: "post", language: "English", user_requirements: "" };
  await ctx.window.WB.storyApi.confirm("t-1", Object.assign({ platform: "x" }, base));
  await ctx.window.WB.storyApi.confirm("t-1", Object.assign({ platform: null }, base));
  await ctx.window.WB.storyApi.confirm("t-1", Object.assign({ platform: "instagram" }, base));
  report.confirmBodies = captured.filter(c => c.url.indexOf("/confirm") >= 0).map(c => c.body.platform);

  captured.length = 0;
  const gen = ctx.window.WB.generation;
  gen.endpoint = "/api/generation/run";
  const genResult = await gen.generateContent({
    task_id: "t-1",
    platform: "x",
    task_context: { topic: "苏绣", platform: "x" },
    genre: "post",
  }, "live");
  report.generateBody = captured[0] ? captured[0].body : null;
  report.generateEcho = genResult.request_echo;

  captured.length = 0;
  const ev = ctx.window.WB.evaluation;
  ev.endpoint = "/api/evaluation/run";
  await ev.evaluateContent({ task_id: "t-1", content: "abc", platform: "x", task_context: { platform: "x" } }, "live");
  report.evaluateBody = captured[0] ? captured[0].body : null;

  const original = { platform: "x", task_context: { platform: "x" } };
  const copy = U.normalizePlatformRequest(original);
  report.normalizedIsCopy = {
    original: Object.assign({}, original),
    copy: copy,
    sameRef: copy === original,
    taskContextSameRef: copy.task_context === original.task_context,
  };

  process.stdout.write(JSON.stringify(report));
})().catch(err => { console.error(err && err.stack || String(err)); process.exit(1); });
"""


@pytest.fixture(scope="module")
def js_report() -> dict:
    if NODE is None:
        pytest.skip("node is not installed")
    proc = subprocess.run(
        [NODE, "-e", JS_HARNESS],
        capture_output=True, text=True, timeout=120,
        env={**os.environ, "WB_JS_DIR": str(JS_DIR)},
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    return json.loads(proc.stdout)


# ---------- 1. platform vocabulary ----------

def test_x_platform_maps_to_twitter_for_the_backend(js_report):
    to_backend = js_report["toBackend"]
    assert to_backend["lower"] == "twitter"
    assert to_backend["upper"] == "twitter"
    assert to_backend["padded"] == "twitter"
    assert to_backend["domain"] == "twitter"
    assert to_backend["slash"] == "twitter"
    # Other platforms are not rewritten, and empty input stays empty.
    assert to_backend["passthrough"] == "instagram"
    assert to_backend["undecided"] == "undecided"
    assert to_backend["empty"] is None
    assert to_backend["missing"] is None


def test_backend_twitter_maps_back_to_the_ui_value(js_report):
    to_ui = js_report["toUi"]
    assert to_ui["twitter"] == "x"
    assert to_ui["x"] == "x"
    assert to_ui["instagram"] == "instagram"
    assert to_ui["empty"] == ""
    labels = js_report["label"]
    assert labels["twitter"] == "X" and labels["x"] == "X"
    assert labels["instagram"] == "Instagram"
    assert labels["other"] == "其他"
    assert labels["none"] == ""


def test_confirmation_sends_the_backend_platform_id(js_report):
    # "x" -> "twitter"; an empty choice stays null; other ids pass through.
    assert js_report["confirmBodies"] == ["twitter", None, "instagram"]


def test_capability_requests_are_normalized_before_they_leave_the_browser(js_report):
    body = js_report["generateBody"]
    assert body["platform"] == "twitter"
    assert body["task_context"]["platform"] == "twitter"
    assert js_report["generateEcho"]["platform"] == "twitter"

    evaluated = js_report["evaluateBody"]
    assert evaluated["platform"] == "twitter"
    assert evaluated["task_context"]["platform"] == "twitter"


def test_normalization_never_mutates_the_caller_object(js_report):
    payload = js_report["normalizedIsCopy"]
    assert payload["sameRef"] is False
    assert payload["taskContextSameRef"] is False
    assert payload["original"]["platform"] == "x"
    assert payload["original"]["task_context"]["platform"] == "x"
    assert payload["copy"]["platform"] == "twitter"


def test_platform_mapping_is_used_by_every_seam():
    utils = (JS_DIR / "utils.js").read_text(encoding="utf-8")
    for name in ["platformToBackend", "platformToUi", "platformLabel", "normalizePlatformRequest"]:
        assert name + ":" in utils, name

    story_api = (JS_DIR / "story-api.js").read_text(encoding="utf-8")
    assert "platform: U.platformToBackend(confirmation.platform)" in story_api

    for rel in ["generation-adapter.js", "evaluation-adapter.js"]:
        src = (JS_DIR / rel).read_text(encoding="utf-8")
        assert "const payload = U.normalizePlatformRequest(request);" in src, rel
        # The raw request must never reach the endpoint.
        assert "body: request" not in src, rel

    workbench = (JS_DIR / "workbench.js").read_text(encoding="utf-8")
    # Re-rendering a saved task must not blank the <select>.
    assert 'set("#confPlatform", U.platformToUi(t.platform));' in workbench


# ---------- 2. mobile shell grid ----------

def css_block(css: str, header: str) -> str:
    start = css.index(header)
    open_brace = css.index("{", start)
    depth = 0
    for i in range(open_brace, len(css)):
        if css[i] == "{":
            depth += 1
        elif css[i] == "}":
            depth -= 1
            if depth == 0:
                return css[open_brace + 1:i]
    raise AssertionError("unbalanced media block: " + header)


def test_collapsed_context_panel_keeps_the_single_column_grid_on_mobile():
    css = (FRONTEND / "css" / "workbench.css").read_text(encoding="utf-8")
    block = css_block(css, "@media (max-width: 860px)")
    match = re.search(
        r"\.wb-shell\.is-ctx-collapsed\s*\{[^}]*grid-template-columns:\s*minmax\(0,\s*1fr\)\s*;",
        block,
    )
    assert match, "860px block must restate .wb-shell.is-ctx-collapsed as one column"
    # The single-column declaration must not be a three-track template.
    assert "var(--wb-nav)" not in match.group(0)


def test_collapsed_context_panel_keeps_two_columns_on_tablet():
    css = (FRONTEND / "css" / "workbench.css").read_text(encoding="utf-8")
    block = css_block(css, "@media (max-width: 1280px)")
    match = re.search(
        r"\.wb-shell\.is-ctx-collapsed\s*\{[^}]*grid-template-columns:[^;]*;",
        block,
    )
    assert match, "1280px block must restate .wb-shell.is-ctx-collapsed"
    assert "0;" not in match.group(0).split("grid-template-columns:")[1]


# ---------- 3. Gate A copy ----------

def test_gate_a_dialog_does_not_promise_create():
    html = (FRONTEND / "workbench.html").read_text(encoding="utf-8")
    assert "确认并进入 Create" not in html
    button = re.search(r'id="btnSubmitConfirm"[^>]*>([^<]+)<', html)
    assert button, "submit button not found"
    label = button.group(1)
    assert "Gate A" in label
    assert "进入 Create" not in label
    assert "联合" in label


def test_gate_a_dialog_states_that_gate_b_is_still_required():
    html = (FRONTEND / "workbench.html").read_text(encoding="utf-8")
    note = re.search(r'id="confirmGateBNote"[^>]*>([^<]+)<', html)
    assert note, "the dialog must explain what Gate A does not open"
    text = note.group(1)
    assert "Gate B" in text
    assert "Create" in text
    # …and it must not claim the frontend can decide Gate B.
    assert "不会代替" in text or "可信评估器" in text
