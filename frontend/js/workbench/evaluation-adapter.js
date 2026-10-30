/* Evaluation Capability Adapter.
   The real Evaluation Skill is not wired to this page yet. LIVE therefore
   returns NOT_CONNECTED and the Audit page shows "Evaluation Skill 待接入"
   instead of inventing scores. DEMO returns an explicitly labelled sample
   evaluation ("示例评价") to demonstrate the future interaction. */
(function (global) {
  "use strict";
  const U = global.WB.util;

  const STATUS = {
    READY: "READY",
    NOT_CONNECTED: "NOT_CONNECTED",
    RUNNING: "RUNNING",
    SUCCEEDED: "SUCCEEDED",
    FAILED: "FAILED",
    BLOCKED: "BLOCKED",
  };

  const DIMENSIONS = [
    { code: "D1", name: "事实可靠性" },
    { code: "D2", name: "证据充分性" },
    { code: "D3", name: "叙事结构" },
    { code: "D4", name: "受众适配" },
    { code: "D5", name: "文化准确性" },
    { code: "D6", name: "平台适配" },
  ];

  const Adapter = {
    STATUS: STATUS,
    DIMENSIONS: DIMENSIONS,
    endpoint: null,
    evaluatorName: "evaluation-skill",
    evaluatorVersion: "unwired",

    isConnected: function () { return Boolean(this.endpoint); },

    /* request: {task_id, content_version_id, content, task_context, plan, evidence} */
    evaluateContent: async function (request, mode) {
      if (mode !== "demo") {
        if (!this.endpoint) {
          return {
            status: STATUS.NOT_CONNECTED,
            dimensions: [],
            issues: [],
            evaluator: { name: this.evaluatorName, version: this.evaluatorVersion },
            error: "NOT_CONNECTED",
            note: "真实 Evaluation Skill 尚未接入，本轮不产生任何真实评分。",
            request_echo: summarize(request),
          };
        }
        const res = await U.getJSON(this.endpoint, { method: "POST", body: request, timeout: 180000 });
        if (!res.ok) {
          const err = U.parseError(res);
          return { status: STATUS.FAILED, dimensions: [], issues: [], evaluator: { name: this.evaluatorName, version: this.evaluatorVersion }, error: err.message, request_echo: summarize(request) };
        }
        const data = res.data && res.data.data ? res.data.data : res.data;
        return {
          status: STATUS.SUCCEEDED,
          dimensions: data.dimensions || [],
          issues: data.issues || [],
          evaluator: data.evaluator || { name: this.evaluatorName, version: this.evaluatorVersion },
          error: null,
          request_echo: summarize(request),
        };
      }

      const s = await global.WB.demo.evaluate();
      return {
        status: STATUS.SUCCEEDED,
        dimensions: s.evaluation.dimensions,
        issues: s.evaluation.issues,
        evaluator: { name: "demo-evaluation-stub", version: "1.0-demo" },
        sample: true,
        note: "示例评价：仅用于展示交互，不代表真实 Evaluation Skill 结论。",
        error: null,
        request_echo: summarize(request),
      };
    },
  };

  function summarize(request) {
    const r = request || {};
    return {
      task_id: r.task_id || null,
      content_version_id: r.content_version_id || null,
      content_chars: (r.content || "").length,
      mode: r.mode || null,
    };
  }

  global.WB.evaluation = Adapter;
})(window);
