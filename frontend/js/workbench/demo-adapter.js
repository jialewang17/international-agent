/* DEMO adapter — a fully local, isolated simulation of the six-stage flow.
   Rules enforced here:
   - no network calls at all (never touches story-task endpoints or Gate B);
   - every object carries source_type: "demo";
   - gate states are labelled DEMO and never claim real verification.
   The demo mirrors api/story_session.py semantics (plan invalidation on
   feedback, Gate A once per plan revision, Gate C only via explicit review). */
(function (global) {
  "use strict";
  const U = global.WB.util;

  const DEMO_SOURCES = [
    {
      id: "demo-src-1", title: "苏绣：针法谱系与工艺特征（示例资料）",
      institution: "DEMO · 非遗知识库样例", url: "", source_type: "demo",
      summary: "苏绣以劈丝精细、针脚平齐、色彩过渡自然著称，常见针法有平针、套针、打籽、乱针等。",
      knowledge_point: "工艺特征与针法分类", status: "ok",
    },
    {
      id: "demo-src-2", title: "双面绣的技术难点（示例资料）",
      institution: "DEMO · 工艺研究样例", url: "", source_type: "demo",
      summary: "双面绣要求正反两面图案同时成立，对劈丝细度、针脚藏线和光线控制要求极高。",
      knowledge_point: "技术难度与制作周期", status: "ok",
    },
    {
      id: "demo-src-3", title: "苏绣传承人结构的变化（示例资料）",
      institution: "DEMO · 地方志与报道摘编", url: "", source_type: "demo",
      summary: "近年出现年轻从业者通过院校、工坊和短视频渠道进入行业的趋势，但缺少系统统计。",
      knowledge_point: "传承人群结构与进入路径", status: "warn",
    },
    {
      id: "demo-src-4", title: "工坊里的学徒与教学方式（示例资料）",
      institution: "DEMO · 田野访谈样例", url: "", source_type: "demo",
      summary: "传统师徒制仍存在，但教学节奏、考核方式和作品评价标准出现变化。",
      knowledge_point: "技艺传递机制", status: "warn",
    },
    {
      id: "demo-src-5", title: "传统工艺在当代产品中的使用（示例资料）",
      institution: "DEMO · 产业观察样例", url: "", source_type: "demo",
      summary: "苏绣元素出现在时装、家居、文创与数字内容中，常见合作方式为工艺方与设计方联名。",
      knowledge_point: "当代应用场景", status: "ok",
    },
    {
      id: "demo-src-6", title: "工艺商业化中的争议（示例资料）",
      institution: "DEMO · 评论摘编", url: "", source_type: "demo",
      summary: "关于机器绣与手工绣的边界、署名方式和收益分配，存在不同看法，尚缺一手数据。",
      knowledge_point: "争议与未核实信息", status: "pending",
    },
  ];

  const DIRECTIONS = [
    {
      key: "A", label: "方向 A · 工艺技法",
      title: "一线千针：把「精细」讲成看得见的画面",
      idea: "用最具体的针法和劈丝细节，让不了解苏绣的人先感到「难」和「美」。",
      angle: "以一件双面绣作品的制作过程为主线",
      content: "从劈丝、绷面、落针到收针，展示一件作品的时间成本与技术门槛。",
      audience_note: "不需要文化背景，靠动作细节和对比数字建立理解。",
      evidence_ids: ["demo-src-1", "demo-src-2"],
      gaps: ["缺少具体作品的完成工时数据"],
      sections: [
        { title: "开场：一根丝被分成几缕", purpose: "用一个动作建立精度感", evidence_ids: ["demo-src-1"], fact_gaps: ["劈丝细度的具体数值待核"] },
        { title: "中段：双面绣为什么难", purpose: "讲清技术门槛", evidence_ids: ["demo-src-2"], fact_gaps: [] },
        { title: "收尾：一件作品的时间成本", purpose: "把工艺难度落到时间上", evidence_ids: ["demo-src-2"], fact_gaps: ["工时数据需一手来源"] },
      ],
    },
    {
      key: "B", label: "方向 B · 技艺传承",
      title: "绣架前的年轻人：一门手艺如何被接住",
      idea: "从具体的人切入，讲年轻从业者为什么回来、怎么学、遇到什么困难。",
      angle: "以一位年轻绣娘的学艺经历为主线",
      content: "进入工坊的第一年做什么、如何被评价、何时开始独立完成作品。",
      audience_note: "用个人选择和日常细节替代抽象的文化介绍。",
      evidence_ids: ["demo-src-3", "demo-src-4"],
      gaps: ["缺少可引用的人物访谈原文", "缺少年轻从业者比例的权威统计"],
      sections: [
        { title: "开场：她第一次坐到绣架前", purpose: "建立人物与场景", evidence_ids: ["demo-src-4"], fact_gaps: ["人物细节需真实访谈"] },
        { title: "中段：学徒期怎么被评价", purpose: "讲清技艺传递机制", evidence_ids: ["demo-src-4"], fact_gaps: [] },
        { title: "收尾：留下来还是离开", purpose: "呈现真实选择与压力", evidence_ids: ["demo-src-3"], fact_gaps: ["从业比例缺权威数据"] },
      ],
    },
    {
      key: "C", label: "方向 C · 当代生活",
      title: "从绣片到日常：传统工艺今天的用法",
      idea: "不把苏绣放在展柜里，而是讲它如何进入衣服、家居和联名产品。",
      angle: "以当代使用场景为主线，穿插工艺方的视角",
      content: "设计方如何提出需求、工艺方如何判断可行性、消费者如何理解手工价值。",
      audience_note: "从消费经验切入，降低文化距离感。",
      evidence_ids: ["demo-src-5", "demo-src-6"],
      gaps: ["机器绣与手工绣的边界缺少统一标准", "收益分配缺一手数据"],
      sections: [
        { title: "开场：一件外套上的绣片", purpose: "从日常物件进入", evidence_ids: ["demo-src-5"], fact_gaps: [] },
        { title: "中段：联名是怎么谈成的", purpose: "讲清协作机制", evidence_ids: ["demo-src-5"], fact_gaps: ["合作细节需一手采访"] },
        { title: "收尾：手工的价值由谁定义", purpose: "呈现争议而不下结论", evidence_ids: ["demo-src-6"], fact_gaps: ["争议数据未核实"] },
      ],
    },
  ];

  const DEMO_CONTENT_EN = [
    "On a wooden frame in Suzhou, a single silk thread is split until it is almost invisible.",
    "",
    "That is the first thing a young embroiderer learns: before you can make a picture, you have to learn how thin a thread can be. Double-sided embroidery asks for more — both faces must hold the image, and every loose end has to disappear.",
    "",
    "The craft is often described as centuries old. What is changing now is who sits at the frame. Some arrive through design schools, some through family workshops, and some find it through short videos before they ever touch a needle.",
    "",
    "What remains unchanged is time. A small piece can take weeks; the learning takes much longer.",
  ].join("\n");

  const DEMO_CLAIMS = [
    { id: "clm_demo_1", text: "On a wooden frame in Suzhou, a single silk thread is split until it is almost invisible.", status: "LOCATED", evidence: [], note: "原文已定位；未关联证据" },
    { id: "clm_demo_2", text: "Double-sided embroidery asks for more — both faces must hold the image, and every loose end has to disappear.", status: "BOUND", evidence: ["demo-src-2"], note: "已关联示例资料；证据支持未核验" },
    { id: "clm_demo_3", text: "The craft is often described as centuries old.", status: "EXTRACTED", evidence: [], note: "仅提取，未定位、未关联证据" },
    { id: "clm_demo_4", text: "A small piece can take weeks; the learning takes much longer.", status: "EXTRACTED", evidence: [], note: "工时说法缺一手来源，待核实" },
  ];

  const DEMO_EVAL = {
    source: "DEMO · 示例评价（非真实 Evaluation Skill 结果）",
    dimensions: [
      { code: "D1", name: "事实可靠性", score: 3, reason: "多处说法缺一手来源，示例评价不构成核验。" },
      { code: "D2", name: "证据充分性", score: 3, reason: "有工艺描述，缺人物与统计数据。" },
      { code: "D3", name: "叙事结构", score: 4, reason: "开场有画面，中段转折清楚。" },
      { code: "D4", name: "受众适配", score: 4, reason: "以具体动作解释陌生工艺，理解成本低。" },
      { code: "D5", name: "文化准确性", score: 3, reason: "表述谨慎，但缺术语解释与语境。" },
      { code: "D6", name: "平台适配", score: 4, reason: "长度适合 Instagram，段落可读。" },
    ],
    issues: [
      { level: "warn", text: "第二段「centuries old」缺少可引用来源，建议改为具体年代或删除。" },
      { level: "warn", text: "结尾工时说法需一手来源，否则改为定性描述。" },
      { level: "bad", text: "没有呈现传承人视角，与所选方向 B 的意图不完全一致。" },
    ],
  };

  function clone(x) { return JSON.parse(JSON.stringify(x)); }

  /* Demo state survives a page reload, but lives under its own key and carries
     mode:"demo" + schema so it can never be mistaken for, or merged into, a
     real task. A demo task id is never sent to the backend. */
  const STORAGE_KEY = "wb.demo.state";
  const SCHEMA = 1;

  const Demo = {
    state: null,
    _persistTimer: null,

    reset: function () {
      this.state = {
        mode: "demo",
        taskId: "demo-" + Math.random().toString(36).slice(2, 8),
        topic: "",
        materials: "",
        stage: "DEFINE",
        startedAt: null,
        ground: null,
        directions: clone(DIRECTIONS),
        selectedDirection: null,
        plan: null,
        planVersion: 0,
        planPending: false,
        feedback: [],
        gates: {
          A: { status: "pending", decided_by: null, detail: "未确认" },
          B: { status: "demo-simulated", detail: "演示模式：示例门禁，未调用真实 Gate B" },
          C: { status: "pending", detail: "未审核" },
        },
        content: null,
        claims: [],
        evaluation: null,
        approved: false,
      };
      return this.state;
    },

    /* Write-through on every render (debounced), so a refresh keeps the exact
       stage the user was looking at. */
    persistSoon: function () {
      const self = this;
      clearTimeout(this._persistTimer);
      this._persistTimer = setTimeout(function () { self.persistNow(); }, 120);
    },

    persistNow: function () {
      if (!this.state) return;
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify({
          schema: SCHEMA, mode: "demo", savedAt: new Date().toISOString(), state: this.state,
        }));
      } catch (e) {
        /* private mode / quota: the demo keeps working, just without reload persistence */
      }
    },

    /* Returns true only when a well-formed demo snapshot was restored. */
    restore: function () {
      try {
        const raw = localStorage.getItem(STORAGE_KEY);
        if (!raw) return false;
        const parsed = JSON.parse(raw);
        if (!parsed || parsed.schema !== SCHEMA || parsed.mode !== "demo" || !parsed.state) return false;
        const st = parsed.state;
        if (!st.taskId || String(st.taskId).indexOf("demo-") !== 0) return false; // never adopt a live id
        this.state = st;
        if (!Array.isArray(this.state.directions) || !this.state.directions.length) {
          this.state.directions = clone(DIRECTIONS);
        }
        return true;
      } catch (e) {
        return false;
      }
    },

    clear: function () {
      clearTimeout(this._persistTimer);
      try { localStorage.removeItem(STORAGE_KEY); } catch (e) { /* ignore */ }
      this.state = null;
    },

    getState: function () {
      if (!this.state) this.reset();
      return this.state;
    },

    start: async function (topic, materials) {
      const s = this.getState();
      s.topic = topic;
      s.materials = materials || "";
      s.startedAt = new Date().toISOString();
      await U.sleep(420); // visible loading, still fully local
      s.ground = {
        packId: "demo-pack-suxiu",
        summary: "示例资料围绕三条线索：针法与工艺难度、传承人群与教学方式、当代使用与争议。资料标注为 DEMO，未经过真实检索或证据核验。",
        sources: clone(DEMO_SOURCES),
        gaps: ["缺少可引用的人物访谈原文", "缺少年轻从业者比例的权威统计", "机器绣与手工绣的边界缺少统一标准"],
        note: "DEMO：这些来源是演示数据，不代表真实检索结果。",
      };
      s.stage = "GROUND";
      return s;
    },

    goPlan: function () {
      const s = this.getState();
      if (s.stage === "GROUND") s.stage = "PLAN";
      return s;
    },

    selectDirection: function (key) {
      const s = this.getState();
      const dir = s.directions.find(function (d) { return d.key === key; });
      if (!dir) return s;
      s.selectedDirection = key;
      s.planVersion += 1;
      s.plan = {
        version: s.planVersion,
        title: dir.title,
        central_message: dir.idea,
        selected_angles: [dir.angle],
        excluded_angles: s.directions.filter(function (d) { return d.key !== key; }).map(function (d) { return d.title; }),
        sections: clone(dir.sections),
        evidence_gaps: clone(dir.gaps),
        planning_status: "DRAFT",
      };
      s.planPending = false;
      s.gates.A = { status: "pending", decided_by: null, detail: "方案已更新，需重新确认" };
      return s;
    },

    applyFeedback: async function (instruction) {
      const s = this.getState();
      if (!s.plan) return s;
      await U.sleep(500);
      s.feedback.push(instruction);
      s.planPending = true;
      // A real planner is required in production; the demo performs a visible,
      // deterministic rewrite so the interaction can be evaluated.
      const wantYoung = /年轻|传承人|人物|绣娘|学徒/.test(instruction);
      const wantScene = /开头|画面|故事感|场景/.test(instruction);
      const wantShort = /短|精简|删减/.test(instruction);
      const plan = clone(s.plan);
      plan.version = s.planVersion + 1;
      s.planVersion = plan.version;

      if (wantYoung) {
        plan.title = "绣架前的年轻人：" + (s.topic || "苏绣") + "如何被接住";
        plan.central_message = "以一位年轻绣娘的学艺经历为主线，把技艺传承讲成可感知的日常选择。";
        plan.selected_angles = ["年轻传承人的学艺经历", "工坊教学与评价方式"];
        plan.sections = [
          { title: "开场：她第一次坐到绣架前", purpose: "用一个具体场景建立人物（按反馈强化画面感）", evidence_ids: ["demo-src-4"], fact_gaps: ["人物细节需真实访谈"] },
          { title: "中段：第一年只练一种针法", purpose: "呈现技艺传递的节奏", evidence_ids: ["demo-src-4"], fact_gaps: [] },
          { title: "转折：她开始独立完成作品", purpose: "展示成长与评价标准", evidence_ids: ["demo-src-3"], fact_gaps: [] },
          { title: "收尾：留下来还是离开", purpose: "呈现真实压力，不给结论", evidence_ids: ["demo-src-3"], fact_gaps: ["从业比例缺权威数据"] },
        ];
        plan.evidence_gaps = ["缺少可引用的人物访谈原文", "缺少年轻从业者比例的权威统计"];
      } else if (wantScene) {
        plan.sections[0] = { title: "开场：一盏灯下的绣架", purpose: "以场景代替概述，建立画面感", evidence_ids: plan.sections[0].evidence_ids, fact_gaps: plan.sections[0].fact_gaps };
      } else if (wantShort) {
        plan.sections = plan.sections.slice(0, 2);
      } else {
        plan.sections[0] = {
          title: plan.sections[0].title,
          purpose: plan.sections[0].purpose + "（按反馈补充：" + instruction.slice(0, 24) + "）",
          evidence_ids: plan.sections[0].evidence_ids,
          fact_gaps: plan.sections[0].fact_gaps,
        };
      }
      if (wantYoung && wantScene) {
        plan.sections[0].purpose = "以具体场景开场，突出年轻传承人";
      }
      plan.planning_status = "READY_FOR_REVIEW";
      s.plan = plan;
      s.planPending = false;
      s.gates.A = { status: "pending", decided_by: null, detail: "方案 v" + plan.version + " 待重新确认" };
      return s;
    },

    confirm: async function (conf) {
      const s = this.getState();
      await U.sleep(380);
      if (!s.plan) throw new Error("没有可确认的方案");
      if (s.planPending) throw new Error("方案待重规划，不能确认");
      if (s.gates.A.status === "pass" && s.gates.A.planVersion === s.plan.version) {
        throw new Error("这一版方案已经确认过");
      }
      s.task = Object.assign({}, s.task, conf);
      s.confirmation = conf;
      s.gates.A = { status: "pass", decided_by: "user", detail: "DEMO 联合确认 · 方案 v" + s.plan.version, planVersion: s.plan.version };
      s.gates.B = { status: "demo-simulated", detail: "DEMO 示例门禁：允许演示流程继续，不代表真实证据充分" };
      return s;
    },

    enterCreate: async function () {
      const s = this.getState();
      await U.sleep(320);
      if (s.gates.A.status !== "pass") throw new Error("缺少联合确认（Gate A）");
      s.stage = "CREATE";
      return s;
    },

    generate: async function () {
      const s = this.getState();
      await U.sleep(900);
      s.content = {
        text: DEMO_CONTENT_EN,
        version: 1,
        label: "DEMO 示例内容（非真实模型输出）",
        source: "demo",
      };
      s.claims = clone(DEMO_CLAIMS);
      s.evaluation = null;
      return s;
    },

    saveContent: function (text) {
      const s = this.getState();
      if (!s.content) return s;
      s.content = Object.assign({}, s.content, { text: text, savedAt: new Date().toISOString() });
      return s;
    },

    revise: async function (instruction) {
      const s = this.getState();
      await U.sleep(600);
      if (!s.content) throw new Error("没有可修改的内容");
      const nextVersion = s.content.version + 1;
      const trimmed = s.content.text.replace(/centuries old/g, "more than a thousand years old");
      s.content = {
        text: trimmed + "\n\n[DEMO 修订 " + nextVersion + "：" + instruction + "]",
        version: nextVersion,
        label: "DEMO 示例内容（非真实模型输出）",
        source: "demo",
      };
      // old verification cannot be reused for a new version
      s.evaluation = null;
      s.claims = s.claims.map(function (c) { return Object.assign({}, c, { note: c.note + " · 新版本待重新评价" }); });
      s.gates.C = { status: "pending", detail: "新版本待人工审核" };
      s.approved = false;
      return s;
    },

    evaluate: async function () {
      const s = this.getState();
      await U.sleep(700);
      s.evaluation = clone(DEMO_EVAL);
      return s;
    },

    approve: async function () {
      const s = this.getState();
      await U.sleep(400);
      if (!s.content) throw new Error("没有可批准的内容");
      s.gates.C = { status: "pass", decided_by: "human", detail: "DEMO 模拟人工批准" };
      s.approved = true;
      s.stage = "APPROVE";
      return s;
    },

    reject: function () {
      const s = this.getState();
      s.gates.C = { status: "rejected", decided_by: "human", detail: "DEMO 模拟拒绝" };
      s.approved = false;
      return s;
    },

    toSnapshot: function () {
      const s = this.getState();
      this.persistSoon();
      return {
        demo: true,
        task: { task_id: s.taskId, topic: s.topic, user_materials: s.materials, genre: (s.confirmation || {}).genre || null, language: (s.confirmation || {}).language || null, platform: (s.confirmation || {}).platform || null, audience: (s.confirmation || {}).audience || null },
        ground: s.ground,
        plan: s.plan,
        feedback: s.feedback,
        joint_confirmed: s.gates.A.status === "pass",
        plan_update_pending: s.planPending,
        workflow: {
          task_id: s.taskId,
          stage: s.stage,
          status: s.approved ? "approved" : "active",
          reason: "",
          plan_revision: s.planVersion,
          confirmed_plan_revision: s.gates.A.planVersion || -1,
          evidence_status: s.gates.B.status === "demo-simulated" ? "DEMO_SIMULATED" : "NOT_EVALUATED",
          gates: { A: s.gates.A, B: s.gates.B, C: s.gates.C },
        },
        content: s.content,
        claims: s.claims,
        evaluation: s.evaluation,
        approved: s.approved,
      };
    },
  };

  Demo.reset();
  global.WB.demo = Demo;
})(window);
