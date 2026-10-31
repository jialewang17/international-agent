/* Six-stage workbench application.
   State model:
     live : every field comes from GET /api/story-tasks/{id}; the page never
            writes Gate A/B/C locally.
     demo : fully local (WB.demo), never touches the network.
   The two state trees are kept apart; switching modes discards nothing on the
   server and never auto-falls back from LIVE to DEMO. */
(function (global) {
  "use strict";
  const U = global.WB.util;
  const $ = U.$;
  const $$ = U.$$;

  const STAGES = ["DEFINE", "GROUND", "PLAN", "CREATE", "REVISE_AUDIT", "APPROVE"];
  const STAGE_LABEL = {
    DEFINE: "Define", GROUND: "Ground", PLAN: "Plan",
    CREATE: "Create", REVISE_AUDIT: "Revise & Audit", APPROVE: "Approve",
  };
  const APP = {
    mode: "live",
    live: {
      taskId: null,
      snapshot: null,
      content: null,
      evaluation: null,
      genStatus: null,
      error: null,
      blocking: null,
    },
    ui: { stage: "DEFINE", preview: "instagram", ctxOpen: false, modal: false, lastEvent: "" },
  };

  /* ---------------- state helpers ---------------- */
  function currentSnapshot() {
    if (APP.mode === "demo") return global.WB.demo.toSnapshot();
    return APP.live.snapshot;
  }
  function currentStage() {
    const snap = currentSnapshot();
    if (!snap || !snap.workflow) return "DEFINE";
    return snap.workflow.stage || "DEFINE";
  }
  function stageIndex(stage) { return STAGES.indexOf(stage); }

  function stageStatus(stage) {
    const snap = currentSnapshot();
    const idx = stageIndex(stage);
    if (!snap || !snap.workflow) return idx === 0 ? "running" : "todo";
    const cur = stageIndex(snap.workflow.stage);
    if (snap.workflow.status === "blocked" && idx === cur) return "blocked";
    if (idx < cur) return "done";
    if (idx === cur) return "running";
    return "todo";
  }

  function gateView() {
    const snap = currentSnapshot();
    const out = {
      A: { state: "idle", text: "未确认" },
      B: { state: "idle", text: "未评估" },
      C: { state: "idle", text: "未批准" },
    };
    if (!snap || !snap.workflow) return out;
    const gates = snap.workflow.gates || {};
    const pass = function (d) { return ["approved", "passed", "clear", "ok"].indexOf(String(d || "").toLowerCase()) >= 0; };

    if (APP.mode === "demo") {
      const d = snap.workflow.gates || {};
      out.A = d.A && d.A.status === "pass" ? { state: "pass", text: "已确认" } : { state: "fail", text: "未确认" };
      out.B = { state: "fail", text: "DEMO 示例" };
      out.C = d.C && d.C.status === "pass" ? { state: "pass", text: "已批准" } : d.C && d.C.status === "rejected" ? { state: "fail", text: "已拒绝" } : { state: "idle", text: "未批准" };
      return out;
    }
    if (gates.A) out.A = pass(gates.A.decision) ? { state: "pass", text: "已确认" } : { state: "fail", text: "已拒绝" };
    const ev = snap.workflow.evidence_status || "NOT_EVALUATED";
    if (gates.B && pass(gates.B.decision)) out.B = { state: "pass", text: "SUFFICIENT" };
    else out.B = { state: ev === "NOT_EVALUATED" ? "idle" : "fail", text: ev };
    if (gates.C) out.C = pass(gates.C.decision) ? { state: "pass", text: "已批准" } : { state: "fail", text: "已拒绝" };
    return out;
  }

  function setView(stage) {
    APP.ui.stage = stage;
    $$(".wb-view").forEach(function (v) {
      const active = v.getAttribute("data-view") === stage;
      v.classList.toggle("is-active", active);
      v.hidden = !active;
    });
    $$(".wb-stage-item").forEach(function (b) {
      const on = b.getAttribute("data-stage") === stage;
      b.classList.toggle("is-active", on);
      b.setAttribute("aria-selected", on ? "true" : "false");
    });
    $("#stageChip").textContent = STAGE_LABEL[stage] || stage;
    if (stage === "GROUND") renderGround();
    if (stage === "PLAN") renderPlan();
    if (stage === "CREATE") renderCreate();
    if (stage === "REVISE_AUDIT") renderAudit();
    if (stage === "APPROVE") renderApprove();
  }

  function renderShell() {
    const snap = currentSnapshot();
    const stage = currentStage();
    const gates = gateView();

    $$(".wb-stage-item").forEach(function (b) {
      const s = stageStatus(b.getAttribute("data-stage"));
      b.setAttribute("data-status", s);
      const label = { done: "已完成", running: "进行中", todo: "待开始", blocked: "被阻断" }[s];
      const stateEl = b.querySelector("[data-state-label]");
      if (stateEl) stateEl.textContent = label;
    });

    Object.keys(gates).forEach(function (key) {
      const node = $('.wb-gate[data-gate="' + key + '"]');
      if (!node) return;
      node.setAttribute("data-state", gates[key].state === "pass" ? "pass" : gates[key].state === "fail" ? "fail" : "idle");
      node.querySelector("[data-gate-state]").textContent = gates[key].text;
    });

    $("#taskName").textContent = snap && snap.task && snap.task.topic
      ? "任务 · " + snap.task.topic + (snap.task.task_id ? "（" + String(snap.task.task_id).slice(0, 8) + "）" : "")
      : (APP.mode === "demo" ? "演示任务 · 苏绣" : "未开始任务");
    $("#stageChip").textContent = STAGE_LABEL[stage] || stage;
    $("#demoBadge").hidden = APP.mode !== "demo";
    $("#ctxMode").textContent = APP.mode === "demo" ? "DEMO" : "LIVE";
    document.body.setAttribute("data-mode", APP.mode);

    renderContext(snap, gates);
  }

  function renderContext(snap, gates) {
    const ctxTask = $("#ctxTask");
    const ctxSources = $("#ctxSources");
    const ctxWorkflow = $("#ctxWorkflow");
    const ctxVersions = $("#ctxVersions");
    const raw = $("#ctxRaw");

    if (!snap) {
      ctxTask.innerHTML = "<dt>状态</dt><dd>尚未开始任务</dd><dt>模式</dt><dd>" + (APP.mode === "demo" ? "DEMO" : "LIVE") + "</dd>";
      ctxSources.innerHTML = "<dt>来源</dt><dd>0</dd>";
      ctxWorkflow.innerHTML = "<dt>阶段</dt><dd>Define</dd>";
      ctxVersions.innerHTML = '<li class="wb-muted">暂无版本。</li>';
      raw.textContent = "{}";
      return;
    }
    const t = snap.task || {};
    ctxTask.innerHTML = [
      "<dt>主题</dt><dd>" + U.esc(t.topic || "—") + "</dd>",
      "<dt>任务 ID</dt><dd><code>" + U.esc(t.task_id || "—") + "</code></dd>",
      "<dt>内容形式</dt><dd>" + U.esc(t.genre || "未确认") + "</dd>",
      "<dt>语言</dt><dd>" + U.esc(t.language || "未确认") + "</dd>",
      "<dt>平台</dt><dd>" + U.esc(U.platformLabel(t.platform) || "未确认") + "</dd>",
      "<dt>受众</dt><dd>" + U.esc(t.audience || "未确认") + "</dd>",
    ].join("");

    const sources = snap.ground && snap.ground.sources ? snap.ground.sources : [];
    ctxSources.innerHTML = [
      "<dt>来源</dt><dd>" + sources.length + "</dd>",
      "<dt>证据包</dt><dd>" + U.esc((snap.ground && (snap.ground.evidence_pack_id || snap.ground.packId)) || "未回填") + "</dd>",
      "<dt>缺口</dt><dd>" + ((snap.ground && snap.ground.gaps && snap.ground.gaps.length) || 0) + "</dd>",
    ].join("");

    ctxWorkflow.innerHTML = [
      "<dt>阶段</dt><dd>" + U.esc(STAGE_LABEL[snap.workflow.stage] || snap.workflow.stage) + "</dd>",
      "<dt>状态</dt><dd>" + U.esc(snap.workflow.status || "—") + "</dd>",
      "<dt>方案版本</dt><dd>" + U.esc(snap.workflow.plan_revision != null ? "v" + snap.workflow.plan_revision : "—") + "</dd>",
      "<dt>证据状态</dt><dd>" + U.esc(snap.workflow.evidence_status || "NOT_EVALUATED") + "</dd>",
      "<dt>Gate A</dt><dd>" + gates.A.text + "</dd>",
      "<dt>Gate B</dt><dd>" + gates.B.text + "</dd>",
      "<dt>Gate C</dt><dd>" + gates.C.text + "</dd>",
    ].join("");

    const versions = [];
    if (snap.plan) versions.push("Plan v" + (snap.plan.version || 0) + " · " + U.esc(snap.plan.title || ""));
    if (snap.content) versions.push("Content v" + (snap.content.version || 1) + (snap.content.label ? " · " + U.esc(snap.content.label) : ""));
    if (snap.evaluation) versions.push("Evaluation · " + U.esc(snap.evaluation.source || "示例评价"));
    ctxVersions.innerHTML = versions.length
      ? versions.map(function (v) { return "<li>" + v + "</li>"; }).join("")
      : '<li class="wb-muted">暂无版本。</li>';

    raw.textContent = JSON.stringify(snap, null, 2).slice(0, 6000);
  }

  /* ---------------- DEFINE ---------------- */
  function bindDefine() {
    $$("#topicGrid .wb-topic").forEach(function (btn) {
      btn.addEventListener("click", function () {
        $$("#topicGrid .wb-topic").forEach(function (b) { b.classList.remove("is-picked"); });
        btn.classList.add("is-picked");
        $("#topicInput").value = btn.getAttribute("data-topic-hint");
        $("#topicInput").focus();
      });
    });
    $("#materialsInput").addEventListener("input", function () {
      const text = this.value.trim();
      const hint = $("#materialsHint");
      if (!text) { hint.textContent = "未添加材料。Ground 阶段只使用真实检索结果与这里的材料。"; return; }
      const parts = text.split(/\n\s*-{3,}\s*\n|\n{2,}/).filter(function (x) { return x.trim().length >= 8; });
      hint.textContent = "已准备 " + (parts.length || 1) + " 段材料，将在 Ground 阶段与检索结果合并。";
    });

    $("#btnStartExplore").addEventListener("click", startExplore);
    $("#topicInput").addEventListener("keydown", function (e) {
      if (e.key === "Enter") { e.preventDefault(); startExplore(); }
    });
  }

  async function startExplore() {
    const topic = $("#topicInput").value.trim();
    const materials = $("#materialsInput").value.trim();
    const errBox = $("#defineError");
    errBox.hidden = true;
    if (!topic) {
      errBox.textContent = "请先填写具体主题。";
      errBox.hidden = false;
      $("#topicInput").focus();
      return;
    }
    const btn = $("#btnStartExplore");
    U.setLoading(btn, true);
    try {
      if (APP.mode === "demo") {
        await global.WB.demo.start(topic, materials);
        APP.ui.stage = "GROUND";
      } else {
        const res = await global.WB.storyApi.createTask(topic, materials);
        if (!res.ok) {
          errBox.textContent = "创建任务失败：" + res.error.message;
          errBox.hidden = false;
          return;
        }
        APP.live.taskId = res.data.task.task_id;
        APP.live.snapshot = res.data;
        localStorage.setItem("wb.live.taskId", APP.live.taskId);
        APP.ui.stage = "GROUND";
        U.toast("任务已创建，进入 Ground");
      }
      renderShell();
      setView("GROUND");
    } finally {
      U.setLoading(btn, false);
    }
  }

  /* ---------------- GROUND ---------------- */
  function renderGround() {
    const snap = currentSnapshot();
    const srcBox = $("#groundSources");
    const sumBox = $("#groundSummary");
    const gapBox = $("#groundGaps");
    const noteBox = $("#groundNote");
    const count = $("#groundSourceCount");
    const liveGap = $("#groundLiveGap");
    const nextBtn = $("#btnGroundNext");
    const reason = $("#groundNextReason");

    if (!snap) {
      liveGap.hidden = false;
      liveGap.querySelector("#groundLiveGapText").textContent = "还没有创建任务。请先在 Define 开始探索。";
      sumBox.innerHTML = '<p class="wb-muted">尚无任务。</p>';
      gapBox.innerHTML = '<li class="wb-muted">暂无缺口信息。</li>';
      srcBox.innerHTML = '<p class="wb-muted">暂无来源。</p>';
      count.textContent = "0 条";
      nextBtn.disabled = true;
      reason.hidden = false; reason.textContent = "需要先创建任务。";
      return;
    }

    const ground = snap.ground;
    const sources = (ground && ground.sources) || [];
    if (!ground) {
      const realGaps = snap.ground_gaps || [];
      const emptyOutcome = realGaps.length > 0 || Boolean(snap.ground_note);
      liveGap.hidden = false;
      liveGap.querySelector("#groundLiveGapText").textContent = emptyOutcome
        ? "Ground 检索未产生可用证据：任务保持 GROUND，未伪造证据包。真实缺口见下方，Plan 无法开始。"
        : "后端 Story Task 尚未回填 EvidencePack：当前阶段为 " + (snap.workflow.stage || "GROUND") +
          "，证据状态 " + (snap.workflow.evidence_status || "NOT_EVALUATED") + "。这是真实缺口，不补假数据。";
      sumBox.innerHTML = emptyOutcome
        ? "<p>" + U.esc(snap.ground_note || "Ground 检索未产生可用证据。") + "</p>"
        : '<p class="wb-muted">真实 Ground 检索服务尚未接入，因此没有知识摘要。</p>';
      gapBox.innerHTML = emptyOutcome && realGaps.length
        ? realGaps.map(function (g) { return "<li>" + U.esc(g) + "</li>"; }).join("")
        : (emptyOutcome
          ? '<li>Ground 检索未产生可用证据。</li>'
          : '<li>缺少 EvidencePack 回填：Plan 阶段将无法保存方案（后端会拒绝）。</li>');
      srcBox.innerHTML = '<p class="wb-muted">没有真实来源。LIVE 模式不会用演示资料代替。</p>';
      count.textContent = "0 条";
      nextBtn.disabled = true;
      reason.hidden = false;
      reason.textContent = emptyOutcome
        ? "Ground 检索未产生可用证据：请补充主题关键词或参考资料后新建任务。"
        : "后端未回填 Ground 结果，Plan 会因缺少 Ground summary 被拒绝。";
      noteBox.textContent = emptyOutcome ? "" : "";
      return;
    }

    liveGap.hidden = true;
    sumBox.innerHTML = "<p>" + U.esc(ground.summary || ground.retrieval_note || "无摘要。") + "</p>";
    const gaps = ground.gaps || ground.evidence_gaps || [];
    gapBox.innerHTML = gaps.length
      ? gaps.map(function (g) { return "<li>" + U.esc(g) + "</li>"; }).join("")
      : '<li class="wb-muted">未报告缺口。</li>';
    noteBox.textContent = ground.note || "";
    count.textContent = sources.length + " 条";

    if (!sources.length) {
      srcBox.innerHTML = '<p class="wb-muted">Ground 未返回来源条目。</p>';
    } else {
      srcBox.innerHTML = sources.map(function (src) {
        const statusClass = { ok: "is-ok", warn: "is-warn", pending: "is-idle", failed: "is-bad" }[src.status] || "is-idle";
        const statusText = { ok: "已获得资料", warn: "需要补充资料", pending: "资料来源待确认", failed: "检索失败" }[src.status] || "待确认";
        const demoTag = src.source_type === "demo" ? '<span class="wb-tag is-warn">DEMO</span>' : "";
        return '<article class="wb-source">' +
          "<h3>" + U.esc(src.title) + "</h3>" +
          '<div class="wb-src-meta">' + demoTag +
          "<span>" + U.esc(src.institution || src.source_id || "未知机构") + "</span>" +
          '<span class="wb-tag ' + statusClass + '">' + statusText + "</span></div>" +
          "<p>" + U.esc(src.summary || "") + "</p>" +
          (src.knowledge_point ? '<div class="wb-src-meta"><span>知识点：' + U.esc(src.knowledge_point) + "</span></div>" : "") +
          (src.url || src.uri ? '<a href="' + U.esc(src.url || src.uri) + '" target="_blank" rel="noopener">' + U.esc(src.url || src.uri) + "</a>" : "") +
          "</article>";
      }).join("");
    }

    const canPlan = Boolean(APP.mode === "demo" ? ground : ground);
    nextBtn.disabled = !canPlan;
    reason.hidden = canPlan;
    if (!canPlan) reason.textContent = "Ground 结果缺失，无法进入 Plan。";
  }

  function bindGround() {
    $("#btnRefreshGround").addEventListener("click", refreshGround);
    $("#btnGroundNext").addEventListener("click", function () {
      if (APP.mode === "demo") {
        global.WB.demo.goPlan();
        renderShell();
        setView("PLAN");
      } else {
        setView("PLAN");
        U.toast("Plan 阶段需要真实 Ground 结果；当前后端尚未回填。", "bad");
      }
    });
  }

  async function refreshGround() {
    const btn = $("#btnRefreshGround");
    U.setLoading(btn, true);
    try {
      if (APP.mode === "demo") {
        await U.sleep(300);
        renderGround();
        U.toast("演示资料已刷新（本地数据，无网络请求）");
        return;
      }
      if (!APP.live.taskId) { U.toast("还没有任务", "bad"); return; }
      const res = await global.WB.storyApi.getTask(APP.live.taskId);
      if (!res.ok) { U.toast(res.error.message, "bad"); return; }
      APP.live.snapshot = res.data;
      renderShell();
      renderGround();
      U.toast("已读取后端最新状态");
    } finally {
      U.setLoading(btn, false);
    }
  }

  /* ---------------- PLAN ---------------- */
  function renderPlan() {
    const snap = currentSnapshot();
    const list = $("#planDirections");
    const preview = $("#planPreview");
    const meta = $("#planMeta");
    const chat = $("#planChat");
    const liveGap = $("#planLiveGap");
    const confirmBtn = $("#btnOpenConfirm");
    const hint = $("#confirmHint");
    const count = $("#planDirectionCount");
    const pending = $("#planPendingFlag");
    const versionBadge = $("#planVersionBadge");

    if (!snap) {
      liveGap.hidden = false;
      list.innerHTML = '<p class="wb-muted">还没有任务。</p>';
      preview.innerHTML = '<p class="wb-muted">先创建任务。</p>';
      confirmBtn.disabled = true;
      hint.textContent = "需要先创建任务并完成 Ground。";
      count.textContent = "0 个";
      versionBadge.textContent = "v0";
      return;
    }

    const isDemo = APP.mode === "demo";
    const directions = isDemo ? (snap.ground && snap.ground.directions) || getDemoDirections() : [];
    count.textContent = directions.length + " 个";

    liveGap.hidden = isDemo || Boolean(snap.plan);
    if (!isDemo && !snap.plan) {
      list.innerHTML = '<p class="wb-muted">真实故事规划服务待接入：后端没有 Plan 生成器，前端不会伪造三个方向。</p>';
    } else if (!directions.length) {
      list.innerHTML = '<p class="wb-muted">暂无方向。</p>';
    } else {
      const selectedKey = (APP.mode === "demo") ? global.WB.demo.getState().selectedDirection : null;
      list.innerHTML = directions.map(function (d) {
        const sel = selectedKey === d.key ? " is-selected" : "";
        return '<article class="wb-direction' + sel + '">' +
          '<h3><span>' + U.esc(d.title) + '</span><span class="wb-dir-key">' + U.esc(d.label || d.key) + "</span></h3>" +
          "<p>" + U.esc(d.idea) + "</p>" +
          "<dl><dt>叙事切入</dt><dd>" + U.esc(d.angle) + "</dd>" +
          "<dt>拟讲内容</dt><dd>" + U.esc(d.content) + "</dd>" +
          "<dt>受众解释</dt><dd>" + U.esc(d.audience_note) + "</dd>" +
          "<dt>关联证据</dt><dd>" + U.esc((d.evidence_ids || []).join("、") || "无") + "</dd>" +
          "<dt>证据缺口</dt><dd>" + U.esc((d.gaps || []).join("；") || "无") + "</dd></dl>" +
          '<button type="button" class="wb-secondary" data-choose="' + U.esc(d.key) + '">选择这个方向</button>' +
          "</article>";
      }).join("");
      $$("#planDirections [data-choose]").forEach(function (btn) {
        btn.addEventListener("click", function () { chooseDirection(btn.getAttribute("data-choose")); });
      });
    }

    const plan = snap.plan;
    versionBadge.textContent = "v" + (snap.workflow.plan_revision || (plan && plan.version) || 0);
    pending.hidden = !snap.plan_update_pending;
    if (!plan) {
      preview.innerHTML = '<p class="wb-muted">选择一个故事方向后显示方案。</p>';
      meta.innerHTML = "";
    } else {
      preview.innerHTML =
        "<p><strong>" + U.esc(plan.title) + "</strong></p>" +
        "<p>" + U.esc(plan.central_message || "") + "</p>" +
        "<ul>" + (plan.sections || []).map(function (s) {
          return "<li><strong>" + U.esc(s.title) + "</strong> — " + U.esc(s.purpose || "") +
            (s.fact_gaps && s.fact_gaps.length ? '<br><small class="wb-muted">缺口：' + U.esc(s.fact_gaps.join("；")) + "</small>" : "") + "</li>";
        }).join("") + "</ul>";
      meta.innerHTML =
        '<span class="wb-tag is-idle">角度：' + U.esc((plan.selected_angles || []).join("、") || "—") + "</span>" +
        '<span class="wb-tag is-idle">状态：' + U.esc(plan.planning_status || "DRAFT") + "</span>" +
        ((plan.evidence_gaps || []).length ? '<span class="wb-tag is-warn">缺口 ' + plan.evidence_gaps.length + " 项</span>" : "");
      if (!isDemo && snap.plan) {
        preview.innerHTML += '<p class="wb-help">该方案由后端存储；本页面不会替它生成内容。</p>';
      }
    }

    const fb = snap.feedback || [];
    chat.innerHTML = fb.length
      ? fb.map(function (f, i) {
        return '<div class="wb-chat-msg is-user">' + U.esc(f) + "<small>反馈 #" + (i + 1) +
          (isDemo ? " · 演示器已据此改写方案" : " · 已记录，旧方案失效，需真实规划服务产出新方案") + "</small></div>";
      }).join("")
      : '<p class="wb-muted">还没有反馈。用一句话说明你希望怎么改。</p>';

    const confirmed = isDemo
      ? (snap.gates && snap.gates.A && snap.gates.A.status === "pass")
      : Boolean(snap.joint_confirmed);
    const canConfirm = Boolean(plan) && !snap.plan_update_pending && !confirmed;
    confirmBtn.disabled = !canConfirm;
    hint.textContent = !plan
      ? (isDemo ? "先选择一个故事方向。" : "真实 Plan 待接入，暂时无法确认。")
      : snap.plan_update_pending ? "方案待重规划，不能确认。"
        : confirmed ? "本版本已确认；再次修改需要重新确认。" : "确认后锁定本次 Define 决策与 Plan 版本。";
    fillConfirmDefaults(snap);
  }

  function getDemoDirections() {
    return global.WB.demo.getState().directions;
  }

  function chooseDirection(key) {
    if (APP.mode !== "demo") { U.toast("LIVE 模式没有本地方向可选择", "bad"); return; }
    global.WB.demo.selectDirection(key);
    renderShell();
    renderPlan();
    U.toast("已选择方向 " + key + "，方案版本已更新");
  }

  function fillConfirmDefaults(snap) {
    const t = snap.task || {};
    const set = function (id, value) {
      const elx = $(id);
      if (elx && !elx.value) elx.value = value || "";
    };
    set("#confAudience", t.audience);
    set("#confGenre", t.genre);
    set("#confLanguage", t.language);
    set("#confPlatform", U.platformToUi(t.platform));
  }

  function bindPlan() {
    $("#btnDefineCheck").addEventListener("click", function () {
      const body = $("#defineCheckBody");
      const open = body.hidden;
      body.hidden = !open;
      this.setAttribute("aria-expanded", open ? "true" : "false");
    });
    $("#btnSendFeedback").addEventListener("click", sendFeedback);
    $("#btnOpenConfirm").addEventListener("click", openConfirmModal);
    $("#btnCloseConfirm").addEventListener("click", function () { toggleConfirm(false); });
    $("#btnCancelConfirm").addEventListener("click", function () { toggleConfirm(false); });
    $("#btnSubmitConfirm").addEventListener("click", submitConfirm);
    $$(".wb-modal").forEach(function (m) {
      m.addEventListener("click", function (e) { if (e.target === m) toggleConfirm(false); });
    });
  }

  async function sendFeedback() {
    const box = $("#feedbackInput");
    const text = box.value.trim();
    if (!text) { U.toast("先写一句修改意见", "bad"); box.focus(); return; }
    const btn = $("#btnSendFeedback");
    U.setLoading(btn, true);
    try {
      if (APP.mode === "demo") {
        await global.WB.demo.applyFeedback(text);
        box.value = "";
        renderShell();
        renderPlan();
        U.toast("演示方案已更新（版本号已变化）");
      } else {
        if (!APP.live.taskId) { U.toast("还没有任务", "bad"); return; }
        const res = await global.WB.storyApi.sendFeedback(APP.live.taskId, text);
        if (!res.ok) { U.toast("反馈提交失败：" + res.error.message, "bad"); return; }
        APP.live.snapshot = res.data.task || APP.live.snapshot;
        box.value = "";
        renderShell();
        renderPlan();
        U.toast("反馈已记录；旧方案已失效，等待真实规划服务生成新方案。", "bad");
      }
    } finally {
      U.setLoading(btn, false);
    }
  }

  function openConfirmModal() {
    const snap = currentSnapshot();
    if (!snap || !snap.plan) { U.toast("还没有可确认的方案", "bad"); return; }
    const conf = collectConfirmation();
    if (!conf.audience || !conf.genre || !conf.language) {
      U.toast("先在「确认传播任务设置」里填写受众、内容形式与语言", "bad");
      $("#btnDefineCheck").setAttribute("aria-expanded", "true");
      $("#defineCheckBody").hidden = false;
      return;
    }
    toggleConfirm(true);
  }

  function toggleConfirm(open, message) {
    const modal = $("#confirmModal");
    if (open) {
      const snap = currentSnapshot();
      const t = snap.task || {};
      // Show what the user just filled in, not the older snapshot values
      // (the confirmation is only persisted after the modal is submitted).
      const conf = collectConfirmation();
      $("#confirmDefineSummary").innerHTML = [
        "<dt>主题</dt><dd>" + U.esc(t.topic || "—") + "</dd>",
        "<dt>受众</dt><dd>" + U.esc(conf.audience || t.audience || "未填写") + "</dd>",
        "<dt>内容形式</dt><dd>" + U.esc(conf.genre || t.genre || "未选择") + "</dd>",
        "<dt>语言</dt><dd>" + U.esc(conf.language || t.language || "未选择") + "</dd>",
        "<dt>平台</dt><dd>" + U.esc(U.platformLabel(conf.platform || t.platform) || "未选择") + "</dd>",
      ].join("");
      const plan = snap.plan;
      $("#confirmPlanSummary").innerHTML = plan
        ? "<p><strong>" + U.esc(plan.title) + "</strong>（v" + U.esc(plan.version || 0) + "）</p><p>" +
        U.esc(plan.central_message) + "</p><ul>" +
        (plan.sections || []).map(function (s) { return "<li>" + U.esc(s.title) + "</li>"; }).join("") + "</ul>"
        : '<p class="wb-muted">没有方案。</p>';
      $("#confirmError").hidden = true;
    }
    modal.hidden = !open;
    APP.ui.modal = open;
  }

  function collectConfirmation() {
    return {
      audience: $("#confAudience").value.trim(),
      genre: $("#confGenre").value,
      language: $("#confLanguage").value,
      platform: $("#confPlatform").value || null,
      audience_knowledge: $("#confKnowledge").value || "unknown",
      user_requirements: $("#confRequirements").value.trim(),
    };
  }

  async function submitConfirm() {
    const conf = collectConfirmation();
    const errBox = $("#confirmError");
    errBox.hidden = true;
    if (!conf.audience) { errBox.textContent = "请填写目标受众。"; errBox.hidden = false; return; }
    if (!conf.genre) { errBox.textContent = "请主动选择内容形式（不会自动识别）。"; errBox.hidden = false; return; }
    if (!conf.language) { errBox.textContent = "请选择目标语言。"; errBox.hidden = false; return; }
    const btn = $("#btnSubmitConfirm");
    U.setLoading(btn, true);
    try {
      if (APP.mode === "demo") {
        try {
          await global.WB.demo.confirm(conf);
        } catch (err) {
          errBox.textContent = err.message;
          errBox.hidden = false;
          return;
        }
        toggleConfirm(false);
        renderShell();
        renderPlan();
        U.toast("Gate A 已通过（DEMO 模拟）");
      } else {
        if (!APP.live.taskId) { U.toast("还没有任务", "bad"); return; }
        const res = await global.WB.storyApi.confirm(APP.live.taskId, conf);
        if (!res.ok) {
          errBox.textContent = (res.error.gate ? "Gate " + res.error.gate + "：" : "") + res.error.message;
          errBox.hidden = false;
          return;
        }
        APP.live.snapshot = res.data;
        toggleConfirm(false);
        renderShell();
        renderPlan();
        U.toast("后端已确认 Gate A");
      }
    } finally {
      U.setLoading(btn, false);
    }
  }

  /* ---------------- CREATE ---------------- */
  function renderCreate() {
    const snap = currentSnapshot();
    const banner = $("#createGateB");
    const bannerText = $("#createGateBText");
    const planEcho = $("#createPlanEcho");
    const genBtn = $("#btnGenerate");
    const editor = $("#contentEditor");
    const badge = $("#contentVersionBadge");
    const genStatus = $("#genStatus");
    const note = $("#genAdapterNote");
    const auditBtn = $("#btnGoAudit");
    const auditReason = $("#auditNextReason");

    if (!snap) {
      banner.hidden = false;
      bannerText.textContent = "还没有任务。";
      genBtn.disabled = true;
      auditBtn.disabled = true;
      return;
    }

    const isDemo = APP.mode === "demo";
    planEcho.innerHTML = snap.plan
      ? "<p><strong>" + U.esc(snap.plan.title) + "</strong>（v" + U.esc(snap.plan.version || 0) + "）</p><p>" + U.esc(snap.plan.central_message || "") + "</p>"
      : '<p class="wb-muted">暂无已确认方案。</p>';

    if (isDemo) {
      banner.hidden = true;
      genBtn.disabled = false;
      note.textContent = "Generation Adapter：DEMO 使用本地演示器，产出的内容标注为 DEMO。";
    } else {
      const canCreate = snap.workflow.stage === "CREATE" || snap.workflow.stage === "REVISE_AUDIT" || snap.workflow.stage === "APPROVE";
      banner.hidden = canCreate;
      if (!canCreate) {
        bannerText.textContent = "当前阶段为 " + (snap.workflow.stage || "PLAN") +
          "，证据状态 " + (snap.workflow.evidence_status || "NOT_EVALUATED") +
          "。Gate A + 可信 Gate B 都满足时后端才允许进入 Create。";
      }
      genBtn.disabled = true;
      note.textContent = "Generation Adapter：LIVE 未接入真实 Skill，调用返回 NOT_CONNECTED，不生成内容。";
      auditBtn.disabled = true;
      auditReason.hidden = false;
      auditReason.textContent = "没有内容版本，无法进入审计。";
    }

    const content = isDemo ? snap.content : APP.live.content;
    if (content) {
      if (editor.value !== content.text) editor.value = content.text;
      badge.hidden = false;
      badge.textContent = "v" + content.version;
      genStatus.textContent = (content.label || "已生成") + " · 版本 v" + content.version;
      updatePreview(content.text);
      if (isDemo) { auditBtn.disabled = false; auditReason.hidden = true; }
    } else {
      badge.hidden = true;
      genStatus.textContent = APP.live.genStatus || "尚未生成";
    }
    $("#editorMeta").textContent = content && content.savedAt ? "已保存 " + U.fmtTime(content.savedAt) : "未保存";
  }

  function updatePreview(text) {
    const t = text || "";
    const tags = "#SuzhouEmbroidery #Craft";
    const box = $("#mockPreview");
    if (!t) { box.innerHTML = '<p class="wb-muted">生成后显示预览。</p>'; return; }
    box.className = "wb-mock" + (APP.ui.preview === "x" ? " is-x" : "");
    box.innerHTML = APP.ui.preview === "x"
      ? "<p><strong>ChinaStory</strong> <span class=\"wb-muted\">@chinastory</span></p><p>" + U.esc(t) + "</p><p class=\"wb-muted\">" + tags + "</p>"
      : "<p class=\"wb-muted\">chinastory_official</p><p>" + U.esc(t) + "</p><p class=\"wb-muted\">" + tags + "</p>";
  }

  function bindCreate() {
    $("#btnGenerate").addEventListener("click", generateContent);
    $("#btnSaveContent").addEventListener("click", saveContent);
    $("#btnCopyContent").addEventListener("click", copyContent);
    $("#btnGoAudit").addEventListener("click", goAudit);
    $("#btnShowBlockReason").addEventListener("click", showBlockReason);
    $$(".wb-seg-btn[data-preview]").forEach(function (b) {
      b.addEventListener("click", function () {
        APP.ui.preview = b.getAttribute("data-preview");
        $$(".wb-seg-btn[data-preview]").forEach(function (x) { x.classList.toggle("is-active", x === b); });
        const snap = currentSnapshot();
        const content = APP.mode === "demo" ? snap && snap.content : APP.live.content;
        if (content) updatePreview(content.text);
      });
    });
  }

  async function generateContent() {
    const btn = $("#btnGenerate");
    const snap = currentSnapshot();
    U.setLoading(btn, true);
    $("#genStatus").textContent = "生成中…";
    try {
      const request = {
        task_id: snap && snap.task ? snap.task.task_id : null,
        task_context: snap ? snap.task : null,
        plan: snap ? snap.plan : null,
        plan_version: snap && snap.workflow ? snap.workflow.plan_revision : 0,
        evidence_refs: snap && snap.ground && snap.ground.sources ? snap.ground.sources.map(function (s) { return s.id || s.source_id; }) : [],
        genre: snap && snap.task ? snap.task.genre : null,
        language: snap && snap.task ? snap.task.language : null,
        platform: snap && snap.task ? snap.task.platform : null,
        requirements: snap && snap.task ? snap.task.user_requirements : "",
        mode: APP.mode,
      };
      const res = await global.WB.generation.generateContent(request, APP.mode);
      if (res.status === "NOT_CONNECTED") {
        APP.live.genStatus = "NOT_CONNECTED";
        $("#genStatus").textContent = "NOT_CONNECTED · 生成 Skill 待接入";
        U.toast("真实 Generation Skill 尚未接入", "bad");
        return;
      }
      if (res.status !== "SUCCEEDED") {
        $("#genStatus").textContent = "生成失败";
        U.toast("生成失败：" + (res.error || "未知错误"), "bad");
        return;
      }
      if (APP.mode === "demo") {
        renderShell();
        renderCreate();
        U.toast("已生成 DEMO 示例内容");
      } else {
        APP.live.content = { text: res.content, version: 1, label: "真实生成", content_version_id: res.content_version_id };
        renderCreate();
        U.toast("已生成");
      }
    } finally {
      U.setLoading(btn, false);
    }
  }

  function saveContent() {
    const text = $("#contentEditor").value;
    if (APP.mode === "demo") {
      global.WB.demo.saveContent(text);
      renderShell();
      renderCreate();
    } else {
      if (!APP.live.content) { U.toast("还没有内容", "bad"); return; }
      APP.live.content = Object.assign({}, APP.live.content, { text: text, savedAt: new Date().toISOString() });
      $("#editorMeta").textContent = "已保存 " + U.fmtTime(APP.live.content.savedAt);
    }
    U.toast("已保存编辑");
  }

  async function copyContent() {
    const text = $("#contentEditor").value;
    if (!text) { U.toast("没有内容", "bad"); return; }
    try {
      await navigator.clipboard.writeText(text);
      U.toast("已复制");
    } catch (e) {
      U.toast("复制失败，请手动选择", "bad");
    }
  }

  async function showBlockReason() {
    if (APP.mode === "demo") { U.toast("DEMO 模式为示例门禁，不涉及真实 Gate B", "bad"); return; }
    if (!APP.live.taskId) { U.toast("还没有任务", "bad"); return; }
    const res = await global.WB.storyApi.enterCreate(APP.live.taskId);
    const banner = $("#createGateB");
    banner.hidden = false;
    if (res.ok) {
      APP.live.snapshot = res.data;
      renderShell();
      renderCreate();
      U.toast("后端已允许进入 Create");
    } else {
      $("#createGateBText").textContent = "后端拒绝（" + res.error.code + "）：" +
        (res.error.gate ? "Gate " + res.error.gate + " · " : "") + res.error.message;
      U.toast("后端拒绝进入 Create", "bad");
    }
  }

  async function goAudit() {
    const snap = currentSnapshot();
    if (APP.mode === "demo") {
      global.WB.demo.getState().stage = "REVISE_AUDIT";
      renderShell();
      setView("REVISE_AUDIT");
      return;
    }
    if (!APP.live.taskId || !APP.live.content) { U.toast("没有内容版本", "bad"); return; }
    setView("REVISE_AUDIT");
  }

  /* ---------------- AUDIT ---------------- */
  function renderAudit() {
    const snap = currentSnapshot();
    const contentBox = $("#auditContent");
    const claimBox = $("#claimList");
    const statusBox = $("#factStatus");
    const evalGrid = $("#evalGrid");
    const issuesBox = $("#evalIssues");
    const notConnected = $("#evalNotConnected");
    const evalSource = $("#evalSource");

    if (!snap) {
      contentBox.innerHTML = '<p class="wb-muted">还没有内容版本。</p>';
      claimBox.innerHTML = "";
      statusBox.innerHTML = '<li class="wb-muted">无核查数据。</li>';
      return;
    }
    const content = APP.mode === "demo" ? snap.content : APP.live.content;
    if (!content) {
      contentBox.innerHTML = '<p class="wb-muted">还没有内容版本。真实流程需要先通过 Gate B 进入 Create。</p>';
      claimBox.innerHTML = "";
      statusBox.innerHTML = "<li><span>Claim 提取</span><b>无内容</b></li>";
      evalGrid.innerHTML = "";
      issuesBox.innerHTML = "";
      notConnected.hidden = false;
      return;
    }
    contentBox.textContent = content.text;
    const claims = APP.mode === "demo" ? snap.claims : [];
    claimBox.innerHTML = claims.length
      ? claims.map(function (c) {
        const label = { EXTRACTED: "已提取", LOCATED: "已定位", BOUND: "已关联证据", VERIFIED: "已核验" }[c.status] || c.status;
        return '<li class="wb-claim"><div>' + U.esc(c.text) + "</div>" +
          '<div class="wb-claim-meta"><code>' + U.esc(c.id) + "</code><span>" + label + "</span>" +
          (c.evidence && c.evidence.length ? "<span>证据：" + U.esc(c.evidence.join("、")) + "</span>" : "<span>无证据引用</span>") +
          "<span>" + U.esc(c.note || "") + "</span></div></li>";
      }).join("")
      : '<li class="wb-muted">LIVE 未返回 Claim 结果（需要内容版本与提取服务）。</li>';

    const counts = claims.reduce(function (acc, c) { acc[c.status] = (acc[c.status] || 0) + 1; return acc; }, {});
    statusBox.innerHTML = [
      "<li><span>Claim 已提取</span><b>" + (counts.EXTRACTED || 0) + "</b></li>",
      "<li><span>原文已定位</span><b>" + (counts.LOCATED || 0) + "</b></li>",
      "<li><span>已关联证据</span><b>" + (counts.BOUND || 0) + "</b></li>",
      "<li><span>证据支持已核验</span><b>0</b></li>",
      "<li><span>尚未核验</span><b>" + claims.length + "</b></li>",
    ].join("");

    const evaluation = APP.mode === "demo" ? snap.evaluation : APP.live.evaluation;
    if (!evaluation) {
      notConnected.hidden = false;
      evalGrid.innerHTML = "";
      issuesBox.innerHTML = "";
      evalSource.textContent = "Evaluation Skill 待接入";
    } else {
      notConnected.hidden = false;
      evalGrid.innerHTML = evaluation.dimensions.map(function (d) {
        return '<div class="wb-eval-dim"><h4>' + U.esc(d.code) + " · " + U.esc(d.name) + "</h4>" +
          '<div class="wb-eval-score">' + U.esc(String(d.score)) + "</div><p>" + U.esc(d.reason) + "</p></div>";
      }).join("");
      issuesBox.innerHTML = (evaluation.issues || []).map(function (i) {
        return '<div class="wb-issue' + (i.level === "bad" ? " is-bad" : "") + '">' + U.esc(i.text) + "</div>";
      }).join("");
      evalSource.textContent = evaluation.source || "示例评价";
    }
  }

  function bindAudit() {
    $("#btnRevise").addEventListener("click", reviseContent);
    $("#btnRunEval").addEventListener("click", runEvaluation);
    $("#btnGoApprove").addEventListener("click", function () {
      if (APP.mode === "demo") {
        global.WB.demo.getState().stage = "APPROVE";
        renderShell();
        setView("APPROVE");
      } else {
        setView("APPROVE");
      }
    });
  }

  async function runEvaluation() {
    const snap = currentSnapshot();
    const btn = $("#btnRunEval");
    const content = APP.mode === "demo" ? snap && snap.content : APP.live.content;
    if (!content) { U.toast("没有内容版本，无法评价", "bad"); return; }
    U.setLoading(btn, true);
    try {
      const request = {
        task_id: snap && snap.task ? snap.task.task_id : null,
        content_version_id: APP.mode === "demo" ? "demo-content-v" + content.version : (content.content_version_id || null),
        content: content.text,
        task_context: snap ? snap.task : null,
        plan: snap ? snap.plan : null,
        mode: APP.mode,
      };
      const res = await global.WB.evaluation.evaluateContent(request, APP.mode);
      if (res.status === "NOT_CONNECTED") {
        if (APP.mode === "demo") { U.toast("DEMO 评价失败", "bad"); return; }
        U.toast("Evaluation Skill 待接入（NOT_CONNECTED）", "bad");
        return;
      }
      if (APP.mode === "demo") {
        renderShell();
        renderAudit();
        U.toast("已生成示例评价（DEMO，非真实 Skill）");
      } else {
        APP.live.evaluation = res;
        renderAudit();
      }
    } finally {
      U.setLoading(btn, false);
    }
  }

  async function reviseContent() {
    const instruction = $("#reviseInstruction").value.trim();
    if (!instruction) { U.toast("写一句修改说明", "bad"); return; }
    const btn = $("#btnRevise");
    U.setLoading(btn, true);
    try {
      if (APP.mode === "demo") {
        await global.WB.demo.revise(instruction);
        $("#reviseInstruction").value = "";
        renderShell();
        renderAudit();
        renderCreate();
        U.toast("已生成新版本，旧核查状态不复用");
      } else {
        U.toast("LIVE 修改需要真实版本服务，当前未接入", "bad");
      }
    } finally {
      U.setLoading(btn, false);
    }
  }

  /* ---------------- APPROVE ---------------- */
  function renderApprove() {
    const snap = currentSnapshot();
    const contentBox = $("#approveContent");
    const summary = $("#approveSummary");
    const gap = $("#approveLiveGap");
    const approveBtn = $("#btnApprove");
    const reason = $("#approveReason");
    const done = $("#approveDone");

    if (!snap) {
      contentBox.innerHTML = '<p class="wb-muted">还没有内容。</p>';
      summary.innerHTML = "<dt>状态</dt><dd>未开始</dd>";
      approveBtn.disabled = true;
      return;
    }
    const content = APP.mode === "demo" ? snap.content : APP.live.content;
    contentBox.textContent = content ? content.text : "还没有内容版本。";

    const plan = snap.plan;
    summary.innerHTML = [
      "<dt>任务</dt><dd>" + U.esc((snap.task && snap.task.topic) || "—") + "</dd>",
      "<dt>方案</dt><dd>" + U.esc(plan ? plan.title + "（v" + plan.version + "）" : "—") + "</dd>",
      "<dt>内容版本</dt><dd>" + U.esc(content ? "v" + content.version : "—") + "</dd>",
      "<dt>事实核查</dt><dd>" + (APP.mode === "demo" ? "示例：4 条 Claim，0 条已核验" : "无真实核查结果") + "</dd>",
      "<dt>内容评价</dt><dd>" + (APP.mode === "demo" ? "示例评价（非真实 Skill）" : "Evaluation Skill 待接入") + "</dd>",
      "<dt>未解决问题</dt><dd>" + (APP.mode === "demo" ? "工时说法缺一手来源；人物细节需真实访谈" : "—") + "</dd>",
      "<dt>Gate C</dt><dd>" + (snap.approved ? "已批准（DEMO）" : "未批准") + "</dd>",
    ].join("");

    if (APP.mode === "demo") {
      gap.hidden = true;
      approveBtn.disabled = !content || Boolean(snap.approved);
      reason.textContent = snap.approved ? "" : "DEMO 模式允许完成模拟审核。";
      done.hidden = !snap.approved;
      if (snap.approved) done.textContent = "DEMO 已完成：六阶段全链路已走通（演示数据）。";
    } else {
      gap.hidden = false;
      approveBtn.disabled = true;
      reason.textContent = "LIVE 不可用：需要真实内容版本、评价记录与 persisted 人工 ACCEPT 绑定。";
      done.hidden = true;
    }
  }

  function bindApprove() {
    $("#btnApprove").addEventListener("click", async function () {
      const btn = $("#btnApprove");
      U.setLoading(btn, true);
      try {
        await global.WB.demo.approve();
        renderShell();
        renderApprove();
        U.toast("已通过 Gate C（DEMO 模拟）");
      } catch (err) {
        U.toast(err.message, "bad");
      } finally {
        U.setLoading(btn, false);
      }
    });
    $("#btnReject").addEventListener("click", function () {
      if (APP.mode !== "demo") { U.toast("LIVE 拒绝需要真实审核记录", "bad"); return; }
      global.WB.demo.reject();
      renderShell();
      renderApprove();
      U.toast("已拒绝（DEMO 模拟）", "bad");
    });
    $("#btnBackRevise").addEventListener("click", function () {
      if (APP.mode === "demo") { global.WB.demo.getState().stage = "REVISE_AUDIT"; renderShell(); }
      setView("REVISE_AUDIT");
    });
  }

  /* ---------------- mode switching ---------------- */
  function syncModeButtons(mode) {
    $$(".wb-mode-btn").forEach(function (b) {
      const on = b.getAttribute("data-mode") === mode;
      b.classList.toggle("is-active", on);
      b.setAttribute("aria-pressed", on ? "true" : "false");
    });
  }

  function setMode(mode) {
    if (mode === APP.mode) return;
    if (mode === "demo") {
      const ok = window.confirm("切换到 DEMO 演示模式？\n\n演示数据与真实任务完全隔离：不会写入后端，也不会修改任何门禁状态。已进行的演示进度会保留。");
      if (!ok) return;
      APP.mode = "demo";
      if (!global.WB.demo.state) global.WB.demo.restore();
      const s = global.WB.demo.getState();
      APP.ui.stage = s.stage || "DEFINE";
    } else {
      APP.mode = "live";
      APP.ui.stage = APP.live.snapshot ? APP.live.snapshot.workflow.stage : "DEFINE";
      if (!APP.live.snapshot && APP.live.taskId) restoreLive();
    }
    try { localStorage.setItem("wb.mode", mode); } catch (e) { /* ignore */ }
    syncModeButtons(mode);
    renderShell();
    setView(APP.ui.stage);
    U.toast(mode === "demo" ? "已切换到 DEMO：演示数据，不会写入后端" : "已切换到 LIVE：读取真实接口");
  }

  async function restoreLive() {
    const id = APP.live.taskId || localStorage.getItem("wb.live.taskId");
    if (!id) return;
    APP.live.taskId = id;
    const res = await global.WB.storyApi.getTask(id);
    if (res.ok) {
      APP.live.snapshot = res.data;
      APP.ui.stage = res.data.workflow.stage;
    } else {
      APP.live.snapshot = null;
      localStorage.removeItem("wb.live.taskId");
    }
  }

  /* ---------------- boot ---------------- */
  function bindShell() {
    $$(".wb-stage-item").forEach(function (b) {
      b.addEventListener("click", function () { setView(b.getAttribute("data-stage")); });
    });
    $$(".wb-mode-btn").forEach(function (b) {
      b.addEventListener("click", function () { setMode(b.getAttribute("data-mode")); });
    });
    $("#btnContextToggle").addEventListener("click", function () {
      const shell = document.querySelector(".wb-shell");
      const btn = this;
      if (window.matchMedia("(max-width: 1280px)").matches) {
        const open = !shell.classList.contains("is-ctx-open");
        shell.classList.toggle("is-ctx-open", open);
        $("#drawerScrim").hidden = !open;
        btn.setAttribute("aria-expanded", open ? "true" : "false");
      } else {
        const collapsed = shell.classList.toggle("is-ctx-collapsed");
        btn.setAttribute("aria-expanded", collapsed ? "false" : "true");
      }
    });
    $("#drawerScrim").addEventListener("click", function () {
      document.querySelector(".wb-shell").classList.remove("is-ctx-open");
      this.hidden = true;
      $("#btnContextToggle").setAttribute("aria-expanded", "false");
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") {
        if (!$("#confirmModal").hidden) toggleConfirm(false);
        const shell = document.querySelector(".wb-shell");
        if (shell.classList.contains("is-ctx-open")) {
          shell.classList.remove("is-ctx-open");
          $("#drawerScrim").hidden = true;
        }
      }
      if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
        const stage = APP.ui.stage;
        if (stage === "DEFINE") startExplore();
        if (stage === "PLAN") sendFeedback();
      }
    });
  }

  async function boot() {
    bindShell();
    bindDefine();
    bindGround();
    bindPlan();
    bindCreate();
    bindAudit();
    bindApprove();

    const params = new URLSearchParams(location.search);
    const modeParam = params.get("mode");
    const wantDemo = modeParam === "demo";
    const wantLive = modeParam === "live";
    const fresh = params.get("fresh") === "1";
    let lastMode = "live";
    try { lastMode = localStorage.getItem("wb.mode") || "live"; } catch (e) { /* ignore */ }

    if (wantDemo) {
      // Explicit demo link. ?fresh=1 restarts the walkthrough; otherwise a
      // previous demo session is restored (mode is still clearly DEMO).
      APP.mode = "demo";
      if (fresh || !global.WB.demo.restore()) global.WB.demo.reset();
      APP.ui.stage = global.WB.demo.getState().stage || "DEFINE";
      syncModeButtons("demo");
      if (fresh) {
        // One-shot flag: drop it from the URL so a later reload resumes the
        // walkthrough instead of silently wiping it.
        try {
          const clean = new URL(location.href);
          clean.searchParams.delete("fresh");
          history.replaceState(null, "", clean);
        } catch (e) { /* ignore */ }
      }
    } else if (!wantLive && lastMode === "demo") {
      // The user was in the demo when they reloaded: come back to the same
      // demo stage instead of silently dropping their progress. This is a
      // remembered user choice, never a fallback from a failed LIVE call.
      APP.mode = "demo";
      if (!global.WB.demo.restore()) global.WB.demo.reset();
      APP.ui.stage = global.WB.demo.getState().stage || "DEFINE";
      syncModeButtons("demo");
    } else {
      await restoreLive();
    }
    renderShell();
    setView(APP.ui.stage || "DEFINE");
    renderGround();
    renderPlan();
    renderCreate();
    renderAudit();
    renderApprove();
  }

  global.WB.app = APP;
  document.addEventListener("DOMContentLoaded", boot);
})(window);
