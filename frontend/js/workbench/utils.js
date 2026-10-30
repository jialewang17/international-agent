/* Shared helpers for the six-stage workbench. No framework, no build step. */
(function (global) {
  "use strict";

  function $(sel, root) { return (root || document).querySelector(sel); }
  function $$(sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); }

  function esc(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  function el(tag, attrs, children) {
    const node = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (key) {
      if (key === "class") node.className = attrs[key];
      else if (key === "text") node.textContent = attrs[key];
      else if (key === "html") node.innerHTML = attrs[key];
      else if (key.slice(0, 2) === "on") node.addEventListener(key.slice(2).toLowerCase(), attrs[key]);
      else if (attrs[key] === true) node.setAttribute(key, "");
      else if (attrs[key] !== false && attrs[key] != null) node.setAttribute(key, attrs[key]);
    });
    (children || []).forEach(function (child) {
      if (child == null) return;
      node.appendChild(typeof child === "string" ? document.createTextNode(child) : child);
    });
    return node;
  }

  const sleep = function (ms) { return new Promise(function (r) { setTimeout(r, ms); }); };

  async function getJSON(url, options) {
    const opts = options || {};
    const controller = new AbortController();
    const timeout = setTimeout(function () { controller.abort(); }, opts.timeout || 20000);
    try {
      const res = await fetch(url, {
        method: opts.method || "GET",
        headers: { "Content-Type": "application/json" },
        body: opts.body ? JSON.stringify(opts.body) : undefined,
        signal: controller.signal,
      });
      const text = await res.text();
      let data = {};
      try { data = text ? JSON.parse(text) : {}; } catch (e) { data = { raw: text }; }
      return { ok: res.ok, status: res.status, data: data };
    } catch (err) {
      const aborted = err && err.name === "AbortError";
      return {
        ok: false,
        status: 0,
        data: {},
        networkError: aborted ? "请求超时（20s）。请检查后端是否在运行。" : "网络连接失败：" + (err && err.message ? err.message : "未知错误"),
      };
    } finally {
      clearTimeout(timeout);
    }
  }

  /* Normalize backend errors: FastAPI may return {detail: str} or {detail: {...}}. */
  function parseError(res) {
    if (res && res.networkError) return { code: "NETWORK", message: res.networkError };
    const status = res ? res.status : 0;
    const detail = res && res.data ? res.data.detail || res.data.error : null;
    let message = "";
    let gate = null;
    if (typeof detail === "string") message = detail;
    else if (detail && typeof detail === "object") {
      message = detail.reason || detail.message || JSON.stringify(detail);
      gate = detail.gate || null;
    } else if (res && res.data && res.data.raw) message = String(res.data.raw).slice(0, 300);
    if (!message) {
      if (status === 400) message = "参数错误（400）。";
      else if (status === 404) message = "任务不存在（404）。";
      else if (status === 409) message = "工作流状态冲突或门禁拒绝（409）。";
      else if (status >= 500) message = "服务端错误（" + status + "）。";
      else message = "请求失败（" + status + "）。";
    }
    return { code: status || "ERROR", status: status, gate: gate, message: message };
  }

  /* Platform vocabulary. The workbench UI says "X"; the backend skills and
     knowledge base only know "twitter". Mapping lives here so neither the pages
     nor the adapters have to carry both vocabularies. */
  const PLATFORM_BACKEND = {
    x: "twitter", "twitter/x": "twitter", twitterx: "twitter", "x.com": "twitter",
  };
  const PLATFORM_LABEL = {
    x: "X", twitter: "X", instagram: "Instagram", tiktok: "TikTok",
    youtube: "YouTube", facebook: "Facebook", weibo: "微博",
    other: "其他", undecided: "暂不确定",
  };

  /* "X" -> "twitter"; unknown values pass through lowercased; empty -> null. */
  function platformToBackend(value) {
    const raw = String(value == null ? "" : value).trim().toLowerCase();
    if (!raw) return null;
    return PLATFORM_BACKEND[raw] || raw;
  }

  /* Backend value -> the value used by the <select>, so re-rendering a saved
     task never blanks the platform field. */
  function platformToUi(value) {
    const backend = platformToBackend(value);
    if (!backend) return "";
    return backend === "twitter" ? "x" : backend;
  }

  function platformLabel(value) {
    const backend = platformToBackend(value);
    return backend ? PLATFORM_LABEL[backend] || backend : "";
  }

  /* Copy of a capability request whose platform fields use backend ids. The
     caller's object is never mutated. Used by the generation/evaluation seams. */
  function normalizePlatformRequest(request) {
    const out = Object.assign({}, request || {});
    if ("platform" in out) out.platform = platformToBackend(out.platform);
    if (out.task_context && typeof out.task_context === "object") {
      out.task_context = Object.assign({}, out.task_context, {
        platform: platformToBackend(out.task_context.platform),
      });
    }
    return out;
  }

  function fmtTime(iso) {
    if (!iso) return "—";
    const d = new Date(iso);
    if (isNaN(d.getTime())) return String(iso);
    const pad = function (n) { return String(n).padStart(2, "0"); };
    return d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate()) +
      " " + pad(d.getHours()) + ":" + pad(d.getMinutes());
  }

  let toastTimer = null;
  function toast(message, kind) {
    const box = $("#wbToast");
    if (!box) return;
    box.textContent = message;
    box.classList.toggle("is-bad", kind === "bad");
    box.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { box.hidden = true; }, 2600);
  }

  function setLoading(button, loading) {
    if (!button) return;
    button.classList.toggle("is-loading", Boolean(loading));
    button.disabled = Boolean(loading);
  }

  global.WB = global.WB || {};
  global.WB.util = {
    $: $, $$: $$, esc: esc, el: el, sleep: sleep, getJSON: getJSON, parseError: parseError,
    fmtTime: fmtTime, toast: toast, setLoading: setLoading,
    platformToBackend: platformToBackend, platformToUi: platformToUi,
    platformLabel: platformLabel, normalizePlatformRequest: normalizePlatformRequest,
  };
})(window);
