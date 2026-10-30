"""Drive the six-stage workbench in headless Chrome via CDP.

Used for the midterm demo proof: performs real clicks/typing (not static
screenshots), captures each stage, and returns a JSON trace that the report
quotes. Screenshots are written outside the repository by default.

Usage:
    python scripts/frontend_e2e_capture.py --base http://127.0.0.1:8090 \
        --out D:/dachuang/midterm_frontend_shots
"""
from __future__ import annotations

import argparse
import base64
import json
import subprocess
import tempfile
import time
import urllib.parse
import urllib.request
from pathlib import Path

import websocket  # websocket-client


CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]


def find_chrome() -> str:
    for path in CHROME_CANDIDATES:
        if Path(path).is_file():
            return path
    raise SystemExit("STOP: no Chrome/Edge binary found")


class Page:
    def __init__(self, port: int, ws_url: str):
        self.ws = websocket.create_connection(ws_url, timeout=40)
        self.port = port
        self._id = 0

    def send(self, method: str, params: dict | None = None, wait: bool = True):
        self._id += 1
        msg_id = self._id
        self.ws.send(json.dumps({"id": msg_id, "method": method, "params": params or {}}))
        if not wait:
            return None
        deadline = time.time() + 40
        while time.time() < deadline:
            raw = self.ws.recv()
            data = json.loads(raw)
            if data.get("id") == msg_id:
                if "error" in data:
                    raise RuntimeError(f"{method} failed: {data['error']}")
                return data.get("result", {})
        raise TimeoutError(method)

    def js(self, expression: str, await_promise: bool = True):
        res = self.send("Runtime.evaluate", {
            "expression": expression,
            "returnByValue": True,
            "awaitPromise": await_promise,
            "userGesture": True,
        })
        result = res.get("result", {})
        if result.get("subtype") == "error":
            raise RuntimeError(result.get("description", "js error"))
        return result.get("value")

    def wait_for(self, expression: str, timeout: float = 25.0, label: str = "") -> None:
        deadline = time.time() + timeout
        last = None
        while time.time() < deadline:
            try:
                last = self.js(expression, await_promise=False)
            except RuntimeError as exc:  # page still navigating
                last = str(exc)
            if last:
                return
            time.sleep(0.25)
        raise TimeoutError(f"wait_for({label or expression}) timed out; last={last!r}")

    def shot(self, path: Path) -> None:
        data = self.send("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": False})
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(base64.b64decode(data["data"]))


def open_page(port: int, url: str = "about:blank") -> Page:
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/json/new?{urllib.parse.quote(url, safe=':/?=&')}",
        method="PUT",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        target = json.loads(resp.read().decode("utf-8"))
    page = Page(port, target["webSocketDebuggerUrl"])
    page.send("Page.enable")
    page.send("Runtime.enable")
    return page


def goto(page: Page, url: str) -> None:
    page.send("Page.navigate", {"url": url})
    page.wait_for("document.readyState !== 'loading' && !!window.WB && !!window.WB.app", timeout=30, label=url)


def set_viewport(page: Page, width: int, height: int) -> None:
    page.send("Emulation.setDeviceMetricsOverride", {
        "width": width, "height": height, "deviceScaleFactor": 1, "mobile": width < 500,
    })


def run_viewport(port: int, base: str, out: Path, width: int, height: int, full: bool) -> dict:
    tag = f"{width}x{height}"
    page = open_page(port)
    set_viewport(page, width, height)
    goto(page, f"{base}/static/workbench.html?mode=demo")
    trace = {"viewport": tag, "steps": []}

    page.shot(out / tag / "01-define-demo.png")
    trace["steps"].append("01 define (DEMO)")

    page.js("""(() => {
      const t = document.querySelector('#topicInput');
      t.value = '苏绣';
      t.dispatchEvent(new Event('input', {bubbles: true}));
      document.querySelector('[data-topic-hint="苏绣"]').click();
      document.querySelector('#btnStartExplore').click();
      return true;
    })()""")
    page.wait_for("document.querySelectorAll('#groundSources .wb-source').length >= 3", label="ground")
    page.shot(out / tag / "02-ground-demo.png")
    trace["steps"].append("02 ground with %d demo sources" % page.js("document.querySelectorAll('#groundSources .wb-source').length"))

    page.js("document.querySelector('#btnGroundNext').click()")
    page.wait_for("document.querySelectorAll('#planDirections .wb-direction').length === 3", label="directions")
    page.shot(out / tag / "03-plan-directions.png")
    trace["steps"].append("03 three directions")

    page.js("document.querySelector('[data-choose=\"B\"]').click()")
    page.wait_for("document.querySelector('#planVersionBadge').textContent.trim() !== 'v0'", label="plan v1")
    page.shot(out / tag / "04-plan-selected.png")
    trace["steps"].append("04 plan selected v" + page.js("document.querySelector('#planVersionBadge').textContent.trim()"))

    page.js("""(() => {
      const f = document.querySelector('#feedbackInput');
      f.value = '我更想突出年轻传承人，希望开头更有故事感。';
      f.dispatchEvent(new Event('input', {bubbles: true}));
      document.querySelector('#btnSendFeedback').click();
      return true;
    })()""")
    page.wait_for("document.querySelector('#planVersionBadge').textContent.trim() === 'v2'", label="plan v2")
    page.shot(out / tag / "05-plan-after-feedback.png")
    trace["steps"].append("05 feedback applied -> v2, title=" + page.js("document.querySelector('#planPreview strong').textContent"))

    page.js("""(() => {
      document.querySelector('#btnDefineCheck').click();
      document.querySelector('#confAudience').value = '18-30 岁对中国文化好奇的美国青年';
      document.querySelector('#confGenre').value = 'post';
      document.querySelector('#confLanguage').value = 'English';
      document.querySelector('#confPlatform').value = 'instagram';
      document.querySelector('#confKnowledge').value = 'limited';
      return true;
    })()""")
    page.shot(out / tag / "06-plan-define-check.png")
    trace["steps"].append("06 define decision panel filled")

    page.js("document.querySelector('#btnOpenConfirm').click()")
    page.wait_for("document.querySelector('#confirmModal').hidden === false", label="modal")
    page.shot(out / tag / "07-gate-a-modal.png")
    trace["steps"].append("07 Gate A confirmation modal")

    page.js("document.querySelector('#btnSubmitConfirm').click()")
    page.wait_for("document.querySelector('#confirmModal').hidden === true", label="gate A done")
    page.shot(out / tag / "08-gate-a-confirmed.png")
    trace["steps"].append("08 Gate A passed (DEMO): " + page.js("document.querySelector('.wb-gate[data-gate=\"A\"] [data-gate-state]').textContent"))

    if not full:
        page.ws.close()
        return trace

    page.js("document.querySelector('.wb-stage-item[data-stage=\"CREATE\"]').click()")
    page.js("document.querySelector('#btnGenerate').click()")
    page.wait_for("document.querySelector('#contentEditor').value.length > 120", timeout=30, label="content")
    page.shot(out / tag / "09-create.png")
    trace["steps"].append("09 create: %d chars, version %s" % (
        page.js("document.querySelector('#contentEditor').value.length"),
        page.js("document.querySelector('#contentVersionBadge').textContent"),
    ))

    page.js("document.querySelector('#btnGoAudit').click()")
    page.wait_for("document.querySelectorAll('#claimList .wb-claim').length >= 3", label="claims")
    page.js("document.querySelector('#btnRunEval').click()")
    page.wait_for("document.querySelectorAll('#evalGrid .wb-eval-dim').length >= 6", label="eval dims")
    page.shot(out / tag / "10-audit.png")
    trace["steps"].append("10 audit claims=%d evalDims=%d (sample evaluation)" % (
        page.js("document.querySelectorAll('#claimList .wb-claim').length"),
        page.js("document.querySelectorAll('#evalGrid .wb-eval-dim').length"),
    ))

    page.js("""(() => {
      document.querySelector('#reviseInstruction').value = '把第二段的技术细节换成人物细节';
      document.querySelector('#btnRevise').click();
      return true;
    })()""")
    time.sleep(1.6)
    page.shot(out / tag / "11-audit-revised.png")
    trace["steps"].append("11 revised -> v" + page.js("(document.querySelector('#contentVersionBadge')||{textContent:'?'}).textContent") + ", eval cleared (新版本待重新评价)")

    page.js("document.querySelector('#btnGoApprove').click()")
    page.wait_for("document.querySelector('#btnApprove').disabled === false", label="approve enabled")
    page.shot(out / tag / "12-approve-ready.png")
    page.js("document.querySelector('#btnApprove').click()")
    page.wait_for("document.querySelector('#approveDone').hidden === false", label="approved")
    page.shot(out / tag / "13-approve-done.png")
    trace["steps"].append("12 approved: " + page.js("document.querySelector('#approveDone').textContent"))

    page.ws.close()
    return trace


def run_live(port: int, base: str, out: Path) -> dict:
    page = open_page(port)
    set_viewport(page, 1920, 1080)
    goto(page, f"{base}/static/workbench.html")
    page.shot(out / "1920x1080" / "live-01-define.png")

    page.js("""(() => {
      const t = document.querySelector('#topicInput');
      t.value = '苏绣 LIVE 校验';
      t.dispatchEvent(new Event('input', {bubbles: true}));
      document.querySelector('#btnStartExplore').click();
      return true;
    })()""")
    page.wait_for("document.querySelector('#groundLiveGap') && document.querySelector('#groundLiveGap').hidden === false", label="live ground gap")
    page.shot(out / "1920x1080" / "live-02-ground-gap.png")
    state = page.js("JSON.stringify({stage: document.querySelector('#stageChip').textContent, gap: document.querySelector('#groundLiveGapText').textContent.slice(0,60), raw: document.querySelector('#ctxRaw').textContent.slice(0,160)})")

    page.js("document.querySelector('.wb-stage-item[data-stage=\"PLAN\"]').click()")
    time.sleep(0.6)
    page.shot(out / "1920x1080" / "live-03-plan-not-connected.png")

    page.js("document.querySelector('.wb-stage-item[data-stage=\"CREATE\"]').click()")
    time.sleep(0.4)
    page.shot(out / "1920x1080" / "live-04-create-blocked.png")
    page.js("document.querySelector('#btnShowBlockReason').click()")
    time.sleep(1.2)
    reason = page.js("document.querySelector('#createGateBText').textContent")
    page.shot(out / "1920x1080" / "live-05-create-blocked-reason.png")
    page.ws.close()
    return {"live_state": state, "create_block_reason": reason}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8090")
    ap.add_argument("--out", default="D:/dachuang/midterm_frontend_shots")
    ap.add_argument("--port", type=int, default=9333)
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    profile = tempfile.mkdtemp(prefix="wb-chrome-")
    proc = subprocess.Popen([
        find_chrome(), "--headless=new", f"--remote-debugging-port={args.port}",
        f"--user-data-dir={profile}", "--no-first-run", "--no-default-browser-check",
        "--hide-scrollbars", "--disable-gpu", "about:blank",
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    try:
        for _ in range(60):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{args.port}/json/version", timeout=1)
                break
            except Exception:
                time.sleep(0.3)
        traces = []
        for w, h, full in [(1920, 1080, True), (1440, 900, False), (1366, 768, False), (375, 812, False)]:
            traces.append(run_viewport(args.port, args.base, out, w, h, full))
        live = run_live(args.port, args.base, out)
        print(json.dumps({"demo": traces, "live": live}, ensure_ascii=False, indent=2))
        return 0
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    raise SystemExit(main())
