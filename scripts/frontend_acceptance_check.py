"""Acceptance checks for the midterm six-stage workbench.

Complements scripts/frontend_e2e_capture.py (which produces the screenshots):
this script asserts the behaviours the midterm review has to sign off on, and
prints PASS/FAIL per check with the evidence read back from the live DOM.

Covered:
  * entry points ( / -> workbench, /tools -> legacy tools, both reachable )
  * DEMO: three distinct directions, visible plan change on feedback, version
    bump, Gate A once per plan revision, cancel keeps Gate A pending, editing
    the plan invalidates Gate A, reload resumes the demo stage
  * DEMO isolation: zero /api/ requests, no data bleed on mode switch
  * input safety: an HTML/JS payload in topic and feedback never executes
  * LIVE: real task created, Gate A not faked, Gate B not faked, enter-create
    rejected by the backend

Usage:
    python scripts/frontend_acceptance_check.py --base http://127.0.0.1:8090
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from frontend_e2e_capture import goto, open_page, set_viewport  # noqa: E402

RESULTS: list[dict] = []
XSS_PAYLOAD = "<img src=x onerror=\"window.__xss++\">"


def check(name: str, ok: bool, evidence: object = "") -> None:
    RESULTS.append({"check": name, "ok": bool(ok), "evidence": str(evidence)[:500]})
    mark = "PASS" if ok else "FAIL"
    extra = (" | " + str(evidence)[:200]) if evidence != "" else ""
    print(f"{mark}  {name}{extra}")


def http_text(url: str) -> tuple[int, str]:
    with urllib.request.urlopen(url, timeout=20) as resp:
        return resp.status, resp.read().decode("utf-8", "replace")


def instrument(page) -> None:
    """Count /api/ traffic and record any XSS payload that actually executes."""
    page.send("Page.addScriptToEvaluateOnNewDocument", {"source": """
      window.__xss = 0;
      window.__req = [];
      const _fetch = window.fetch;
      window.fetch = function () {
        try {
          const arg = arguments[0];
          const url = String((arg && arg.url) || arg || "");
          if (url.indexOf('/api/') >= 0) window.__req.push(url);
        } catch (e) {}
        return _fetch.apply(this, arguments);
      };
      const _open = XMLHttpRequest.prototype.open;
      XMLHttpRequest.prototype.open = function (m, u) {
        try { if (String(u).indexOf('/api/') >= 0) window.__req.push(String(u)); } catch (e) {}
        return _open.apply(this, arguments);
      };
    """})


def demo_directions(page) -> dict:
    raw = page.js("JSON.stringify(WB.demo.getState().directions)")
    return json.loads(raw)


def plan_state(page) -> dict:
    return json.loads(page.js("JSON.stringify(WB.demo.getState().plan || {})"))


def gate(page, key: str) -> str:
    return str(page.js(f"WB.demo.getState().gates.{key}.status"))


def run_checks(base: str) -> int:
    # ---------- task 1: entry points ----------
    status, body = http_text(base + "/")
    check("入口 / 返回六阶段工作台", status == 200 and "wb-shell" in body and "legacy-ribbon" not in body, f"HTTP {status}")

    status, body = http_text(base + "/tools")
    check(
        "入口 /tools 返回旧版工具并带旧版标识",
        status == 200 and "legacy-ribbon" in body and "旧版工具流程" in body,
        f"HTTP {status}",
    )

    status, body = http_text(base + "/static/workbench.html")
    check("静态直达 /static/workbench.html 仍可用", status == 200 and "wb-shell" in body, f"HTTP {status}")

    status, tools_body = http_text(base + "/tools")
    check("旧版工具页有返回工作台链接", 'href="/"' in tools_body and "返回六阶段工作台" in tools_body, "")

    status, wb_body = http_text(base + "/")
    check("工作台「已有工具」指向 /tools", 'href="/tools"' in wb_body, "")

    # ---------- task 2/3: DEMO walkthrough ----------
    page = open_page(_port)
    set_viewport(page, 1920, 1080)
    instrument(page)
    goto(page, f"{base}/static/workbench.html?mode=demo&fresh=1")
    page.js("window.confirm = () => true;")

    check("DEMO 顶部标识可见", page.js("document.querySelector('#demoBadge').hidden === false"), page.js(
        "document.querySelector('#demoBadge').textContent.trim()"))

    # DEFINE -> GROUND, with an HTML payload as the topic
    page.js(
        "(() => { const t = document.querySelector('#topicInput');"
        f" t.value = {json.dumps(XSS_PAYLOAD + '苏绣')};"
        " t.dispatchEvent(new Event('input', {bubbles: true}));"
        " document.querySelector('#btnStartExplore').click(); return true; })()"
    )
    page.wait_for("document.querySelectorAll('#groundSources .wb-source').length >= 3", label="demo ground")
    check("DEFINE 自动进入 Ground（无用户门禁）", page.js("WB.demo.getState().stage") == "GROUND", page.js("WB.demo.getState().stage"))
    n_sources = page.js("document.querySelectorAll('#groundSources .wb-source').length")
    check("Ground 展示 DEMO 来源卡片", n_sources >= 3, f"{n_sources} 张")
    check(
        "Ground 来源均标注 demo 类型",
        page.js("Array.prototype.every.call(document.querySelectorAll('#groundSources .wb-source'), n => n.textContent.indexOf('DEMO') >= 0)"),
        "",
    )

    page.js("document.querySelector('#btnGroundNext').click()")
    page.wait_for("document.querySelectorAll('#planDirections .wb-direction').length === 3", label="three directions")

    dirs = demo_directions(page)
    titles = [d["title"] for d in dirs]
    angles = [d["angle"] for d in dirs]
    section_sets = [tuple(s["title"] for s in d["sections"]) for d in dirs]
    distinct = len(set(titles)) == 3 and len(set(angles)) == 3 and len(set(section_sets)) == 3
    check("Plan 三个方向存在真实差异", distinct, "titles/angles/sections 均两两不同")

    dom_titles = json.loads(page.js(
        "JSON.stringify(Array.prototype.map.call(document.querySelectorAll('#planDirections .wb-direction h3'), n => n.textContent.trim()))"
    ))
    check("三个方向在页面上可见且互不相同", len(dom_titles) == 3 and len(set(dom_titles)) == 3, dom_titles)

    # choose direction B, then send feedback
    page.js("document.querySelector('[data-choose=\"B\"]').click()")
    page.wait_for("document.querySelector('#planVersionBadge').textContent.trim() === 'v1'", label="plan v1")
    before = plan_state(page)

    feedback = "我更想突出年轻传承人，希望开头更有故事感。" + XSS_PAYLOAD
    page.js(
        "(() => { const f = document.querySelector('#feedbackInput');"
        f" f.value = {json.dumps(feedback)};"
        " f.dispatchEvent(new Event('input', {bubbles: true}));"
        " document.querySelector('#btnSendFeedback').click(); return true; })()"
    )
    page.wait_for("document.querySelector('#planVersionBadge').textContent.trim() === 'v2'", label="plan v2")
    after = plan_state(page)

    changed = (
        after.get("title") != before.get("title")
        or after.get("central_message") != before.get("central_message")
        or [s["title"] for s in after.get("sections", [])] != [s["title"] for s in before.get("sections", [])]
    )
    check("自然语言反馈后方案发生可见变化", changed, f"{before.get('title')} -> {after.get('title')}")
    check("NarrativePlan 版本号递增", before.get("version") == 1 and after.get("version") == 2, f"v{before.get('version')} -> v{after.get('version')}")
    check(
        "反馈被记录为一条用户要求",
        len(json.loads(page.js("JSON.stringify(WB.demo.getState().feedback)"))) == 1,
        "",
    )

    # ---------- confirmation panel ----------
    page.js("document.querySelector('#btnDefineCheck').click()")
    check(
        "Define 决策核对面板可展开并包含关键项",
        page.js("document.querySelector('#defineCheckBody').hidden === false")
        and page.js("document.body.textContent.indexOf('内容形式') >= 0 && document.body.textContent.indexOf('目标语言') >= 0"),
        "",
    )

    page.js(
        "(() => {"
        " document.querySelector('#confAudience').value = '18-30 岁对中国文化好奇的美国青年';"
        " document.querySelector('#confGenre').value = 'post';"
        " document.querySelector('#confLanguage').value = 'English';"
        " document.querySelector('#confPlatform').value = 'x';"
        " document.querySelector('#confKnowledge').value = 'limited';"
        " return true; })()"
    )

    # cancel must not touch Gate A
    page.js("document.querySelector('#btnOpenConfirm').click()")
    page.wait_for("document.querySelector('#confirmModal').hidden === false", label="modal open")
    modal_text = page.js("document.querySelector('#confirmModal').textContent")
    check(
        "确认弹窗同时给出 Define 摘要与 Plan 摘要",
        "18-30 岁" in modal_text and str(after.get("title"))[:8] in modal_text,
        "",
    )
    check(
        "X 平台在界面显示为 X，交给后端的是 twitter",
        page.js("WB.util.platformToBackend('x')") == "twitter"
        and page.js("WB.util.platformToUi('twitter')") == "x"
        and page.js("document.querySelector('#confirmDefineSummary').innerHTML.indexOf('平台</dt><dd>X</dd>') >= 0"),
        page.js("document.querySelector('#confirmDefineSummary').textContent.slice(-24)"),
    )
    check(
        "Gate A 弹窗不承诺进入 Create，并写明仍需 Gate B",
        "确认并进入 Create" not in modal_text
        and "Gate A" in str(page.js("document.querySelector('#btnSubmitConfirm').textContent"))
        and "Gate B" in str(page.js("document.querySelector('#confirmGateBNote').textContent"))
        and "Create" in str(page.js("document.querySelector('#confirmGateBNote').textContent")),
        page.js("document.querySelector('#btnSubmitConfirm').textContent.trim()"),
    )
    page.js("document.querySelector('#btnCancelConfirm').click()")
    check(
        "取消确认后弹窗关闭且 Gate A 仍为未确认",
        page.js("document.querySelector('#confirmModal').hidden === true") and gate(page, "A") == "pending",
        f"gateA={gate(page, 'A')}",
    )

    # confirm once
    page.js("document.querySelector('#btnOpenConfirm').click()")
    page.wait_for("document.querySelector('#confirmModal').hidden === false", label="modal open 2")
    page.js("document.querySelector('#btnSubmitConfirm').click()")
    page.wait_for("document.querySelector('#confirmModal').hidden === true", label="gate a pass")
    check("Gate A 联合确认通过（DEMO）", gate(page, "A") == "pass", page.js(
        "document.querySelector('.wb-gate[data-gate=\"A\"] [data-gate-state]').textContent"))
    check("Gate A 记录确认时的 Plan 版本", page.js("WB.demo.getState().gates.A.planVersion") == 2, "")

    dup = page.js("(async () => { try { await WB.demo.confirm(WB.demo.getState().confirmation); return 'NO_THROW'; }"
                  " catch (e) { return 'THREW:' + e.message; } })()")
    check("同一 Plan 版本不能重复确认", str(dup).startswith("THREW:"), dup)

    # editing the plan after confirmation must invalidate Gate A
    page.js(
        "(() => { const f = document.querySelector('#feedbackInput');"
        " f.value = '把中段改得更紧凑一些';"
        " f.dispatchEvent(new Event('input', {bubbles: true}));"
        " document.querySelector('#btnSendFeedback').click(); return true; })()"
    )
    page.wait_for("document.querySelector('#planVersionBadge').textContent.trim() === 'v3'", label="plan v3")
    check("修改已确认的方案后 Gate A 失效", gate(page, "A") == "pending", page.js(
        "WB.demo.getState().gates.A.detail"))
    blocked = page.js("(async () => { try { await WB.demo.enterCreate(); return 'NO_THROW'; }"
                      " catch (e) { return 'THREW:' + e.message; } })()")
    check("Gate A 失效后无法进入 Create", str(blocked).startswith("THREW:"), blocked)

    # ---------- safety: payloads never executed ----------
    xss = page.js("window.__xss")
    injected = page.js("document.querySelectorAll('img[src=\"x\"]').length")
    check("用户输入/反馈中的 HTML 载荷未被执行", xss == 0 and injected == 0, f"__xss={xss}, img[src=x]={injected}")

    api_calls = json.loads(page.js("JSON.stringify(window.__req)"))
    check("DEMO 全程未调用真实业务 API", len(api_calls) == 0, api_calls[:3])

    # ---------- reload resumes the demo ----------
    url_now = page.js("location.href")
    check("fresh 参数已被移除，刷新不会重置演示", "fresh=1" not in str(url_now), url_now)
    goto(page, url_now)
    page.js("window.confirm = () => true;")
    stage_chip = page.js("document.querySelector('#stageChip').textContent")
    restored_version = page.js("WB.demo.getState().planVersion")
    check(
        "刷新后仍在 Plan 且方案版本保留",
        stage_chip == "Plan" and restored_version == 3,
        f"stage={stage_chip}, planVersion={restored_version}",
    )
    check("刷新后仍处于 DEMO 且标识可见", page.js("WB.app.mode") == "demo" and page.js("document.querySelector('#demoBadge').hidden === false"), "")

    # ---------- mode switch isolation ----------
    page.js("document.querySelector('.wb-mode-btn[data-mode=\"live\"]').click()")
    page.js("(async () => { await new Promise(r => setTimeout(r, 400)); return true; })()")
    live_mode = page.js("WB.app.mode")
    live_snapshot = page.js("JSON.stringify(WB.app.live.snapshot)")
    check("切到 LIVE 后不再使用演示数据", live_mode == "live" and '"demo":true' not in str(live_snapshot), f"mode={live_mode}")
    check("LIVE 下 DEMO 标识隐藏", page.js("document.querySelector('#demoBadge').hidden === true"), "")

    page.js("document.querySelector('.wb-mode-btn[data-mode=\"demo\"]').click()")
    page.js("(async () => { await new Promise(r => setTimeout(r, 400)); return true; })()")
    check(
        "切回 DEMO 后演示进度保留",
        page.js("WB.app.mode") == "demo" and page.js("WB.demo.getState().planVersion") == 3,
        f"planVersion={page.js('WB.demo.getState().planVersion')}",
    )

    # ---------- LIVE gate behaviour ----------
    page.js("document.querySelector('.wb-mode-btn[data-mode=\"live\"]').click()")
    page.js("(async () => { await new Promise(r => setTimeout(r, 400)); return true; })()")
    page.js("document.querySelector('.wb-stage-item[data-stage=\"DEFINE\"]').click()")
    page.js(
        "(() => { const t = document.querySelector('#topicInput');"
        " t.value = '苏绣';"
        " t.dispatchEvent(new Event('input', {bubbles: true}));"
        " document.querySelector('#btnStartExplore').click(); return true; })()"
    )
    page.wait_for("WB.app.live.taskId && WB.app.live.snapshot && WB.app.live.snapshot.ground", timeout=30, label="live task")
    task_id = page.js("WB.app.live.taskId")
    check("LIVE 可通过真实 API 创建任务", bool(task_id) and not str(task_id).startswith("demo-"), task_id)
    check(
        "LIVE Ground 回填真实证据包与来源（P0-1）",
        page.js("WB.app.live.snapshot.ground.evidence_pack_id.indexOf('ep_') === 0")
        and page.js("WB.app.live.snapshot.ground.sources.length") > 0
        and page.js("document.querySelector('#groundLiveGap').hidden === true"),
        page.js("JSON.stringify({pack: WB.app.live.snapshot.ground.evidence_pack_id,"
                " sources: WB.app.live.snapshot.ground.sources.length,"
                " stage: WB.app.live.snapshot.workflow.stage})"),
    )
    check(
        "LIVE 证据状态保持 NOT_EVALUATED 且 Gate B 未写入",
        page.js("WB.app.live.snapshot.workflow.evidence_status") == "NOT_EVALUATED"
        and page.js("JSON.stringify(WB.app.live.snapshot.workflow.gates).indexOf('\"B\"') < 0"),
        page.js("WB.app.live.snapshot.workflow.evidence_status"),
    )

    page.js("document.querySelector('.wb-stage-item[data-stage=\"PLAN\"]').click()")
    page.js("(async () => { await new Promise(r => setTimeout(r, 300)); return true; })()")
    check(
        "LIVE Plan 不伪造方向且提供真实生成入口（P0-2）",
        page.js("document.querySelectorAll('#planDirections .wb-direction').length") == 0
        and page.js("document.querySelector('#btnGeneratePlan').hidden === false")
        and page.js("document.querySelector('#planDirections').textContent.indexOf('生成故事方向') >= 0"),
        "",
    )
    check("LIVE Gate A 保持未确认", page.js(
        "document.querySelector('.wb-gate[data-gate=\"A\"] [data-gate-state]').textContent") != "已确认", "")
    check(
        "LIVE Gate B 未伪造 SUFFICIENT",
        page.js("document.querySelector('.wb-gate[data-gate=\"B\"] [data-gate-state]').textContent") != "SUFFICIENT",
        page.js("document.querySelector('.wb-gate[data-gate=\"B\"] [data-gate-state]').textContent"),
    )
    check("LIVE 确认按钮在无方案时禁用", page.js("document.querySelector('#btnOpenConfirm').disabled === true"), "")

    enter = page.js(
        "(async () => { const r = await WB.storyApi.enterCreate(WB.app.live.taskId);"
        " return JSON.stringify(r).slice(0, 240); })()"
    )
    check("Gate B 未通过时后端拒绝进入 Create", ('"code":409' in str(enter)) or ('"status":409' in str(enter)), enter)

    # ---------- mobile: a collapsed desktop shell must not break the grid ----------
    set_viewport(page, 375, 812)
    page.js("(async () => { await new Promise(r => setTimeout(r, 300)); return true; })()")
    page.js("document.querySelector('.wb-shell').classList.add('is-ctx-collapsed')")
    page.js("(async () => { await new Promise(r => setTimeout(r, 200)); return true; })()")
    cols = page.js("getComputedStyle(document.querySelector('.wb-shell')).gridTemplateColumns")
    mov = json.loads(page.js(
        "JSON.stringify({nav: document.querySelector('.wb-stages').getBoundingClientRect().width,"
        " main: document.querySelector('.wb-main').getBoundingClientRect().width,"
        " vw: window.innerWidth})"
    ))
    check(
        "移动端折叠上下文后仍是单列布局",
        len(str(cols).split()) == 1
        and abs(float(mov["nav"]) - float(mov["vw"])) <= 2
        and abs(float(mov["main"]) - float(mov["vw"])) <= 2,
        f"cols={cols}, nav={mov['nav']}, main={mov['main']}, vw={mov['vw']}",
    )
    page.js("document.querySelector('.wb-shell').classList.remove('is-ctx-collapsed')")

    page.ws.close()
    return 0


def main() -> int:
    global _port
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8090")
    ap.add_argument("--port", type=int, default=9471, help="Chrome remote debugging port")
    ap.add_argument("--out", default="", help="optional JSON report path (write outside the repo)")
    args = ap.parse_args()
    _port = args.port

    import subprocess
    import tempfile
    import time

    from frontend_e2e_capture import find_chrome

    chrome = find_chrome()
    profile = tempfile.mkdtemp(prefix="wb-accept-")
    proc = subprocess.Popen(
        [chrome, "--headless=new", f"--remote-debugging-port={args.port}", f"--user-data-dir={profile}",
         "--disable-gpu", "--no-first-run", "--no-default-browser-check", "about:blank"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        time.sleep(3)
        run_checks(args.base.rstrip("/"))
    finally:
        proc.terminate()

    passed = sum(1 for r in RESULTS if r["ok"])
    failed = len(RESULTS) - passed
    print(f"\n{passed} passed, {failed} failed")
    if args.out:
        path = Path(args.out)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"results": RESULTS, "passed": passed, "failed": failed},
                                   ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"report: {path}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
