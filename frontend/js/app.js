const API = "";

const SCENE_TIPS = {
  post: "写好主题，有资料可一并粘贴后生成",
  topics: "输入种子词，生成选题后可一键带回发帖",
  reply: "粘贴待回复评论后生成",
};

const SAMPLE_MATERIALS = `项目简介：张铁机车是一家专注定制机车改装的中国工坊。车间保留手工焊接与打磨工序，海外访客常拍摄火花飞溅的夜间加班场景。

通稿要点：2024年接待了来自欧洲与北美的体验团；强调安全培训后再允许近距离拍摄。`;

let meta = null;
let lastResult = null;
let currentScene = "post";
let evView = "cards";
let evFilter = "all";
let draftFinalized = false;

async function api(path, options = {}) {
  const res = await fetch(`${API}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || data.error || res.statusText);
  return data;
}

function $(sel) {
  return document.querySelector(sel);
}
function $all(sel) {
  return [...document.querySelectorAll(sel)];
}

function toast(msg) {
  const el = $("#toast");
  if (!el) return;
  el.textContent = msg;
  el.classList.remove("hidden");
  clearTimeout(toast._t);
  toast._t = setTimeout(() => el.classList.add("hidden"), 1800);
}

function fillSelects() {
  if (!meta) return;
  $all("select[name='country']").forEach((el) => {
    el.innerHTML = meta.countries.map((c) => `<option>${c}</option>`).join("");
  });
  $all("select[name='platform']").forEach((el) => {
    el.innerHTML = meta.platforms.map((p) => `<option>${p}</option>`).join("");
  });
  $all("select[name='identity']").forEach((el) => {
    el.innerHTML = meta.identities.map((i) => `<option value="${i}">${i}</option>`).join("");
  });
  $all("select[name='tone']").forEach((el) => {
    el.innerHTML = meta.tones.map((t) => `<option value="${t}">${t}</option>`).join("");
  });
  $all("select[name='language']").forEach((el) => {
    el.innerHTML = meta.languages.map((l) => `<option>${l}</option>`).join("");
  });
}

function renderPresetChips() {
  const wrap = $("#presetChips");
  if (!wrap || !meta?.preset_chips) return;
  wrap.innerHTML = meta.preset_chips
    .map(
      (c) =>
        `<button type="button" class="chip-preset" data-scene="${c.scene}" data-json='${JSON.stringify(c).replace(/'/g, "&#39;")}'>${c.label}</button>`
    )
    .join("");
  wrap.querySelectorAll(".chip-preset").forEach((btn) => {
    btn.addEventListener("click", () => {
      const chip = JSON.parse(btn.dataset.json);
      switchScene(chip.scene);
      if (chip.scene === "post" && chip.theme) {
        $("#themeInput").value = chip.theme;
        if (String(chip.theme).includes("张铁") || chip.label?.includes("张铁")) {
          $("#userMaterials").value = SAMPLE_MATERIALS;
          updateMaterialsHint();
        }
        $("#themeInput").focus();
      }
      if (chip.scene === "topics" && chip.seed) {
        $("#seedInput").value = chip.seed;
      }
      if (chip.scene === "reply" && chip.comment) {
        $("#commentInput").value = chip.comment;
      }
    });
  });
}

function switchScene(scene) {
  currentScene = scene;
  $all(".seg").forEach((t) => t.classList.toggle("active", t.dataset.scene === scene));
  $all(".scene-form").forEach((f) => f.classList.toggle("active", f.dataset.scene === scene));
  $("#aiTips").textContent = SCENE_TIPS[scene] || "";
  const labels = { post: "生成草稿", topics: "生成选题", reply: "生成回复" };
  $("#btnPrimaryAction").textContent = labels[scene] || "生成";
}

function formToObject(form) {
  const fd = new FormData(form);
  const obj = Object.fromEntries(fd.entries());
  if (form.querySelector("input[name='use_emoji']")) {
    obj.use_emoji = form.querySelector("input[name='use_emoji']").checked;
  }
  if (obj.max_words) obj.max_words = Number(obj.max_words);
  if (obj.n) obj.n = Number(obj.n);
  return obj;
}

function updateMaterialsHint() {
  const text = ($("#userMaterials")?.value || "").trim();
  const hint = $("#materialsHint");
  if (!hint) return;
  if (!text) {
    hint.textContent = "未添加资料";
    return;
  }
  const parts = text.split(/\n\s*-{3,}\s*\n|\n{2,}/).filter((x) => x.trim().length >= 8);
  hint.textContent = `已准备 ${parts.length || 1} 段 · 将标为「用户上传」`;
}

async function handleFilesSelected(e) {
  const files = [...(e.target.files || [])];
  if (!files.length) return;
  const chunks = [];
  for (const f of files) {
    chunks.push(`【文件:${f.name}】\n${(await f.text()).trim()}`);
  }
  const box = $("#userMaterials");
  const prev = (box.value || "").trim();
  box.value = prev ? `${prev}\n\n${chunks.join("\n\n")}` : chunks.join("\n\n");
  updateMaterialsHint();
  toast(`已导入 ${files.length} 个文件`);
  e.target.value = "";
}

function inferPipeline(data) {
  const evidence = data.evidence_used || [];
  const hasPost = Boolean((data.post || data.reply || "").trim());
  const hasError = Boolean(data.error);
  const gateReason = data.gate_reason;
  const stats = data.evidence_stats || {};
  const nUser = stats.user ?? evidence.filter((e) => e.source_type === "用户上传").length;
  const nLocal = stats.local ?? evidence.filter((e) => e.source_type !== "用户上传").length;

  const stages = Array.isArray(data.pipeline_steps) && data.pipeline_steps.length
    ? data.pipeline_steps
    : [
        { id: "DEFINE", label: "Define", status: "ok", detail: data.genre || "" },
        { id: "GROUND", label: "Ground", status: gateReason || (hasError && !hasPost) ? "stop" : evidence.length ? "ok" : "warn", detail: `U${nUser}/L${nLocal}` },
        { id: "PLAN", label: "Plan", status: evidence.length && !gateReason ? "ok" : "idle", detail: (data.skills_applied || []).slice(0, 2).join("+") },
        { id: "CREATE", label: "Create", status: hasPost ? "ok" : hasError ? "stop" : "idle", detail: "" },
        { id: "REVISE_AUDIT", label: "Revise & Audit", status: hasPost ? "warn" : "idle", detail: hasPost ? "可反馈" : "" },
        { id: "APPROVE", label: "Approve", status: draftFinalized ? "ok" : hasPost ? "warn" : "idle", detail: draftFinalized ? "已批准" : "待批准" },
      ];

  const gates = Array.isArray(data.gates) && data.gates.length
    ? data.gates
    : [
        { id: "A", label: "Task Confirmation", status: "ok", detail: "任务已确认" },
        { id: "B", label: "Evidence Exception", status: gateReason || (hasError && !hasPost) ? "stop" : "ok", detail: gateReason || "clear" },
        { id: "C", label: "Final Approval", status: draftFinalized ? "ok" : hasPost ? "warn" : "idle", detail: draftFinalized ? "已批准" : "待人工批准" },
      ];

  const normalize = (x, kind) => ({
    ...x,
    kind,
    icon: x.status === "ok" ? "✓" : x.status === "stop" ? "!" : x.status === "run" ? "…" : x.status === "warn" ? "○" : "·",
  });
  const sm = Object.fromEntries(stages.map((x) => [x.id, normalize(x, "stage")]));
  const gm = Object.fromEntries(gates.map((x) => [x.id, normalize(x, "gate")]));
  return [sm.DEFINE, gm.A, sm.GROUND, gm.B, sm.PLAN, sm.CREATE, sm.REVISE_AUDIT, sm.APPROVE, gm.C].filter(Boolean);
}

function renderPipeline(data, { running = false } = {}) {
  const el = $("#pipelineViz");
  if (!el) return;
  if (data.pipeline?.includes("topics -> template")) {
    el.classList.add("hidden");
    return;
  }
  el.classList.remove("hidden");
  let steps = inferPipeline(data);
  if (running) {
    let seenStages = 0;
    steps = steps.map((step) => {
      if (step.kind === "gate") return step;
      seenStages += 1;
      return seenStages <= 4 ? { ...step, status: "run", icon: "…" } : { ...step, status: "idle", icon: "·" };
    });
  }
  if (draftFinalized) {
    steps = steps.map((step) =>
      step.id === "APPROVE" || (step.kind === "gate" && step.id === "C")
        ? { ...step, status: "ok", icon: "✓", detail: "已人工批准" }
        : step
    );
  }
  el.innerHTML = steps
    .map(
      (s) =>
        `<div class="pipe-step ${s.status} ${s.kind || "stage"}" title="${s.detail || s.label}">` +
        `<span class="gid">${s.id || ""}</span>` +
        `<span class="icon">${s.icon}</span>${s.label}` +
        `${s.detail ? `<br><small>${s.detail}</small>` : ""}` +
        `</div>`
    )
    .join("");
}

function setFinalizeUi(enabled) {
  const bar = $("#finalizeBar");
  const btn = $("#btnFinalize");
  const status = $("#finalizeStatus");
  if (!bar || !btn || !status) return;
  btn.disabled = !enabled;
  if (draftFinalized) {
    bar.classList.add("is-done");
    status.textContent = "已人工批准 · Gate C";
    btn.textContent = "已放行";
    btn.disabled = true;
  } else {
    bar.classList.remove("is-done");
    status.textContent = enabled ? "待人工批准 · Gate C" : "生成成功后可进入最终批准";
    btn.textContent = "定稿放行";
  }
}

function renderGateAlert(data) {
  const el = $("#gateAlert");
  if (!el) return;
  if (data.pipeline?.includes("topics -> template") || (!data.error && (data.post || data.reply))) {
    el.classList.add("hidden");
    return;
  }
  el.classList.remove("hidden");
  const reason = data.gate_reason || (data.evidence_used?.length ? "generation_blocked" : "no_evidence");
  el.innerHTML = `<strong>已拦截</strong> ${data.error || "未生成成稿。"} <small>(${reason})</small>`;
}

function renderGenreNote(data) {
  const el = $("#genreNote");
  if (!el) return;
  if (!data.genre && !data.skills_applied) {
    el.classList.add("hidden");
    return;
  }
  el.classList.remove("hidden");
  const skills = (data.skills_applied || []).join(", ");
  const st = data.evidence_stats;
  el.textContent = `体裁 ${data.genre || "post"} · ${skills || "—"}${
    st ? ` · 用户${st.user || 0}/本地${st.local || 0}` : ""
  }${data.prompt_file ? ` · ${data.prompt_file}` : ""}`;
}

function sourceTypeBadge(ev) {
  const t = ev.source_type || (ev.retrieval === "user_upload" ? "用户上传" : "本地库");
  const cls = t === "用户上传" ? "user" : "local";
  return `<span class="src-type ${cls}">${t}</span>`;
}

function filteredEvidence(items) {
  if (evFilter === "user") return items.filter((e) => e.source_type === "用户上传" || e.retrieval === "user_upload");
  if (evFilter === "local") return items.filter((e) => e.source_type !== "用户上传" && e.retrieval !== "user_upload");
  return items;
}

function renderEvidence(data, blocked = false) {
  const panel = $("#evidencePanel");
  const summary = $("#evidenceSummary");
  if (!panel || !summary) return;
  const items = data.evidence_used || [];
  const viewItems = filteredEvidence(items);
  const usedInPost = Boolean((data.post || data.reply || "").trim()) && !data.error;
  const stats = data.evidence_stats || {};
  const nUser = stats.user ?? items.filter((e) => e.source_type === "用户上传").length;
  const nLocal = stats.local ?? items.filter((e) => e.source_type !== "用户上传").length;

  panel.classList.toggle("empty", viewItems.length === 0);

  if (!items.length) {
    summary.textContent = data.error ? "无可用论据" : "0 条论据";
    panel.innerHTML = `<p>还没有论据。生成后可在此核对来源。</p>`;
    return;
  }

  summary.textContent = `${items.length} 条（用户 ${nUser} · 本地 ${nLocal}）· 筛选 ${viewItems.length} · ${
    usedInPost ? "已用于成稿" : "未采用"
  }`;

  if (!viewItems.length) {
    panel.innerHTML = `<p>当前筛选为空。</p>`;
    return;
  }

  if (evView === "list") {
    panel.innerHTML = viewItems
      .map(
        (ev, i) =>
          `<div class="ev-list-item"><strong>#${i + 1}</strong> ${sourceTypeBadge(ev)} ${ev.statement}</div>`
      )
      .join("");
    return;
  }

  if (evView === "source") {
    panel.innerHTML = viewItems
      .map(
        (ev) =>
          `<div class="ev-source-row"><div>${sourceTypeBadge(ev)}<br><span class="cat">${ev.category || "—"}</span></div><div><a href="${ev.source || "#"}" target="_blank" rel="noopener">${ev.source || "—"}</a><p>${ev.statement}</p></div></div>`
      )
      .join("");
    return;
  }

  panel.innerHTML = viewItems
    .map(
      (ev, i) => `
    <div class="ev-card ${usedInPost ? "" : "unused"}">
      <span class="cat">${ev.category || "—"}</span>
      ${sourceTypeBadge(ev)}
      <p><strong>#${i + 1}</strong> ${ev.statement}</p>
      ${ev.source ? `<a href="${ev.source}" target="_blank" rel="noopener">${ev.source}</a>` : ""}
    </div>`
    )
    .join("");
}

function renderMetaBlocks(data) {
  const wrap = $("#metaBlocks");
  if (!wrap) return;
  const parts = [];

  if (data.five_w && Object.keys(data.five_w).length) {
    const w = data.five_w;
    parts.push(`<div class="meta-block"><h4>Lasswell 5W</h4>
      <div class="fivew-grid">
        <div class="w-row"><b>Who</b><span>${w.who || "—"}</span></div>
        <div class="w-row"><b>Says</b><span>${w.says_what || "—"}</span></div>
        <div class="w-row"><b>Channel</b><span>${w.channel || "—"}</span></div>
        <div class="w-row"><b>To Whom</b><span>${w.to_whom || "—"}</span></div>
        <div class="w-row"><b>Effect</b><span>${w.effect || "—"}</span></div>
      </div></div>`);
  }
  if (data.wire_plan && Object.keys(data.wire_plan).length) {
    const wp = data.wire_plan;
    const emp = Array.isArray(wp.emphasis) ? wp.emphasis.join(" / ") : wp.emphasis || "—";
    parts.push(`<div class="meta-block"><h4>通稿策划</h4>
      <div class="fivew-grid">
        <div class="w-row"><b>Angle</b><span>${wp.angle || "—"}</span></div>
        <div class="w-row"><b>Lead</b><span>${wp.lead_type || "—"}</span></div>
        <div class="w-row"><b>Emphasis</b><span>${emp}</span></div>
        <div class="w-row"><b>Dateline</b><span>${wp.dateline || data.dateline || "—"}</span></div>
      </div></div>`);
  }
  if (data.quotes_used?.length) {
    parts.push(
      `<div class="meta-block"><h4>引语</h4><ul>${data.quotes_used.map((t) => `<li>${t}</li>`).join("")}</ul></div>`
    );
  }
  if (data.evidence_notes?.length) {
    parts.push(
      `<div class="meta-block"><h4>权威映射</h4><ul>${data.evidence_notes.map((t) => `<li>${t}</li>`).join("")}</ul></div>`
    );
  }
  if (data.hashtags?.length) {
    parts.push(`<div class="meta-block"><h4>标签</h4>${data.hashtags.join(" ")}</div>`);
  }
  if (data.ops_tips?.length) {
    parts.push(`<div class="meta-block"><h4>运营</h4><ul>${data.ops_tips.map((t) => `<li>${t}</li>`).join("")}</ul></div>`);
  }
  if (data.skills_applied?.length) {
    parts.push(`<div class="meta-block"><h4>Skills</h4><code>${data.skills_applied.join(", ")}</code></div>`);
  }
  if (data.topics?.length && data.topics[0]?.theme) {
    parts.push(
      data.topics
        .map(
          (t) => `<div class="topic-card">
        <h4>${t.theme}</h4>
        <div>${t.why || ""}</div>
        <button type="button" class="chip use-topic" data-theme="${encodeURIComponent(t.theme)}">用此选题</button>
      </div>`
        )
        .join("")
    );
  }

  wrap.innerHTML = parts.join("") || "<p class='micro'>暂无</p>";
  wrap.querySelectorAll(".use-topic").forEach((btn) => {
    btn.addEventListener("click", () => {
      switchScene("post");
      $("#themeInput").value = decodeURIComponent(btn.dataset.theme);
      $("#themeInput").focus();
      toast("已填入主题");
    });
  });
  if (parts.length) $("#metaFold")?.setAttribute("open", "");
}

function updatePreviews(text, hashtags = []) {
  const body = text || "（暂无正文）";
  const tags = (hashtags || []).join(" ");
  $("#twitterBody").textContent = body;
  $("#twitterTags").textContent = tags;
  $("#instagramCaption").textContent = body;
  $("#instagramTags").textContent = tags;
}

function openEvidence() {
  $("#evidenceSheet")?.classList.remove("hidden");
}
function closeEvidence() {
  $("#evidenceSheet")?.classList.add("hidden");
}

function showResult(data, blocked = false) {
  lastResult = data;
  draftFinalized = false;
  renderPipeline(data);
  renderGateAlert(data);
  renderGenreNote(data);
  renderEvidence(data, blocked);
  const text = data.post || data.reply || "";
  $("#editorPost").value = text;
  updatePreviews(text, data.hashtags);
  renderMetaBlocks(data);
  $("#rawJson").textContent = JSON.stringify(data, null, 2);
  setFinalizeUi(Boolean(text) && !blocked);
  if (data.error && !text) openEvidence();
}

async function runPrimaryAction() {
  const btn = $("#btnPrimaryAction");
  btn.classList.add("loading");
  try {
    if (currentScene === "post") {
      const form = $("#formPost");
      const body = formToObject(form);
      if (!String(body.theme || "").trim()) {
        toast("先写主题");
        $("#themeInput").focus();
        return;
      }
      if (!body.genre) delete body.genre;
      renderPipeline({ genre: body.genre || "auto", skills_applied: [] }, { running: true });
      const res = await api("/api/posts/generate", { method: "POST", body: JSON.stringify(body) });
      showResult(res.data, !res.ok);
      toast(res.ok ? "已生成" : "已拦截");
    } else if (currentScene === "topics") {
      const body = formToObject($("#formTopics"));
      const res = await api("/api/posts/topics", { method: "POST", body: JSON.stringify(body) });
      const data = res.data;
      data.topics = data.topics || [];
      showResult({ ...data, post: "", evidence_used: [], pipeline: "topics -> template" });
      toast("选题已出");
    } else {
      const body = formToObject($("#formReply"));
      if (!String(body.comment || "").trim()) {
        toast("先粘贴评论");
        return;
      }
      const res = await api("/api/replies/generate", { method: "POST", body: JSON.stringify(body) });
      showResult(res.data, !res.ok);
      toast(res.ok ? "回复已生成" : "已拦截");
    }
  } catch (err) {
    toast(err.message || "失败");
  } finally {
    btn.classList.remove("loading");
  }
}

async function polishPost(instruction) {
  const post = $("#editorPost").value.trim();
  if (!post) {
    toast("还没有正文");
    return;
  }
  try {
    const res = await api("/api/posts/polish", {
      method: "POST",
      body: JSON.stringify({ post, instruction, language: "English", max_words: 120 }),
    });
    $("#editorPost").value = res.data.post;
    updatePreviews(res.data.post, lastResult?.hashtags);
    draftFinalized = false;
    if (lastResult) {
      lastResult.post = res.data.post;
      if (Array.isArray(lastResult.pipeline_steps)) {
        lastResult.pipeline_steps = lastResult.pipeline_steps.map((step) =>
          step.id === "REVISE_AUDIT" ? { ...step, status: "ok", detail: "已改稿，需事实复核" } : step
        );
      }
      if (Array.isArray(lastResult.gates)) {
        lastResult.gates = lastResult.gates.map((g) =>
          g.id === "C" ? { ...g, status: "warn", detail: "待人工批准" } : g
        );
      }
      renderPipeline(lastResult);
    }
    setFinalizeUi(true);
    toast("已改稿 · Revise & Audit");
  } catch (err) {
    toast(err.message);
  }
}

function bindEvents() {
  $all(".seg").forEach((tab) => tab.addEventListener("click", () => switchScene(tab.dataset.scene)));
  $("#btnPrimaryAction").addEventListener("click", runPrimaryAction);

  $("#userMaterials")?.addEventListener("input", updateMaterialsHint);
  $("#fileMaterials")?.addEventListener("change", handleFilesSelected);
  $("#btnClearMaterials")?.addEventListener("click", () => {
    $("#userMaterials").value = "";
    updateMaterialsHint();
  });
  $("#btnSampleMaterials")?.addEventListener("click", () => {
    $("#userMaterials").value = SAMPLE_MATERIALS;
    if (!$("#themeInput").value.trim()) {
      $("#themeInput").value = "张铁机车海外社媒短帖——车间烟火气与匠人日常";
    }
    updateMaterialsHint();
  });
  $("#btnTogglePresets")?.addEventListener("click", () => {
    $("#presetChips")?.classList.toggle("hidden");
  });
  $("#btnToggleMore")?.addEventListener("click", () => {
    $("#moreParams")?.classList.toggle("hidden");
  });

  $all("#previewTabs .seg-mini-btn").forEach((tab) => {
    tab.addEventListener("click", () => {
      $all("#previewTabs .seg-mini-btn").forEach((t) => t.classList.toggle("active", t === tab));
      $all(".preview-pane").forEach((p) => p.classList.remove("active"));
      const map = { composer: "#previewComposer", twitter: "#previewTwitter", instagram: "#previewInstagram" };
      $(map[tab.dataset.preview])?.classList.add("active");
    });
  });

  $all("[data-evview]").forEach((tab) => {
    tab.addEventListener("click", () => {
      evView = tab.dataset.evview;
      $all("[data-evview]").forEach((t) => t.classList.toggle("active", t === tab));
      if (lastResult) renderEvidence(lastResult, Boolean(lastResult.error));
    });
  });
  $all("[data-evfilter]").forEach((tab) => {
    tab.addEventListener("click", () => {
      evFilter = tab.dataset.evfilter;
      $all("[data-evfilter]").forEach((t) => t.classList.toggle("active", t.dataset.evfilter === evFilter));
      if (lastResult) renderEvidence(lastResult, Boolean(lastResult.error));
    });
  });

  $all("[data-polish]").forEach((btn) => {
    btn.addEventListener("click", () => polishPost(btn.dataset.polish));
  });
  $("#btnFeedbackPolish")?.addEventListener("click", () => {
    const fb = ($("#feedbackBox")?.value || "").trim();
    if (!fb) {
      toast("写一句要改什么");
      return;
    }
    polishPost(fb);
  });
  $("#feedbackBox")?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      $("#btnFeedbackPolish")?.click();
    }
  });

  $("#btnFinalize")?.addEventListener("click", async () => {
    const text = ($("#editorPost")?.value || "").trim();
    if (!text) {
      toast("没有可定稿的正文");
      return;
    }
    try {
      const res = await api("/api/posts/approve", {
        method: "POST",
        body: JSON.stringify({ post: text, approved: true, approver: "human" }),
      });
      draftFinalized = Boolean(res?.data?.approved);
      if (!draftFinalized) throw new Error("Gate C 未完成");
      if (lastResult && Array.isArray(lastResult.gates)) {
        lastResult.gates = lastResult.gates.map((g) =>
          g.id === "C" ? { ...g, status: "ok", detail: "已人工批准" } : g
        );
        if (Array.isArray(lastResult.pipeline_steps)) {
          lastResult.pipeline_steps = lastResult.pipeline_steps.map((step) =>
            step.id === "APPROVE" ? { ...step, status: "ok", detail: "已人工批准" } : step
          );
        }
        lastResult.finalized = true;
        lastResult.approval = res.data;
        renderPipeline(lastResult);
      }
      setFinalizeUi(true);
      toast("Gate C · 已人工批准");
    } catch (err) {
      draftFinalized = false;
      setFinalizeUi(true);
      toast(err.message || "Gate C 批准失败");
    }
  });

  $("#btnCopy")?.addEventListener("click", async () => {
    const text = $("#editorPost").value;
    if (!text) return;
    await navigator.clipboard.writeText(text);
    toast("已复制");
  });
  $("#btnOpenEvidence")?.addEventListener("click", openEvidence);
  $("#btnCloseEvidence")?.addEventListener("click", closeEvidence);
  $("#sheetScrim")?.addEventListener("click", closeEvidence);

  $("#editorPost")?.addEventListener("input", (e) => {
    updatePreviews(e.target.value, lastResult?.hashtags);
    if (draftFinalized) {
      draftFinalized = false;
      setFinalizeUi(Boolean(e.target.value.trim()));
      if (lastResult) renderPipeline(lastResult);
    }
  });

  document.addEventListener("keydown", (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      runPrimaryAction();
    }
    if (e.key === "Escape") closeEvidence();
  });
}

async function init() {
  bindEvents();
  switchScene("post");
  updateMaterialsHint();
  setFinalizeUi(false);
  try {
    await api("/api/health");
    meta = await api("/api/meta");
    $("#apiDot")?.classList.add("ok");
  } catch {
    $("#apiDot")?.classList.add("err");
    meta = {
      platforms: ["twitter", "instagram", "tiktok"],
      identities: ["online_influencer", "scientist"],
      tones: ["optimistic", "humorous", "serious"],
      countries: ["America", "UK", "Japan"],
      languages: ["English", "Chinese"],
      preset_chips: [],
    };
  }
  fillSelects();
  renderPresetChips();
}

init();
