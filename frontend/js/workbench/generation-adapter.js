/* Generation Capability Adapter.
   Single seam the Create page talks to. Today:
     - LIVE  -> NOT_CONNECTED (no wired Generation Skill endpoint yet)
     - DEMO  -> SUCCEEDED via the local demo adapter (clearly labelled)
   When the team wires a real Skill endpoint, set GenerationAdapter.endpoint
   (or replace `invoke`), and the Create page keeps working unchanged. */
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

  const Adapter = {
    STATUS: STATUS,
    /* e.g. "/api/generation/run"; null means the real service is not wired. */
    endpoint: null,
    skillId: "generation-skill",
    skillVersion: "unwired",

    isConnected: function () { return Boolean(this.endpoint); },

    /* request: {task_id, task_context, plan, plan_version, evidence_refs,
                 genre, language, platform, requirements} */
    generateContent: async function (request, mode) {
      if (mode !== "demo") {
        if (!this.endpoint) {
          return {
            status: STATUS.NOT_CONNECTED,
            content: "",
            content_version_id: null,
            provider: "live",
            skill_id: this.skillId,
            skill_version: this.skillVersion,
            warnings: ["真实 Generation Skill 尚未接入；LIVE 不生成内容。"],
            error: "NOT_CONNECTED",
            request_echo: summarize(request),
          };
        }
        const res = await U.getJSON(this.endpoint, { method: "POST", body: request, timeout: 120000 });
        if (!res.ok) {
          const err = U.parseError(res);
          return {
            status: STATUS.FAILED, content: "", content_version_id: null, provider: "live",
            skill_id: this.skillId, skill_version: this.skillVersion,
            warnings: [], error: err.message, request_echo: summarize(request),
          };
        }
        const data = res.data && res.data.data ? res.data.data : res.data;
        return {
          status: STATUS.SUCCEEDED,
          content: data.content || data.post || "",
          content_version_id: data.content_version_id || null,
          provider: data.provider || "live",
          skill_id: data.skill_id || this.skillId,
          skill_version: data.skill_version || this.skillVersion,
          warnings: data.warnings || [],
          error: null,
          request_echo: summarize(request),
        };
      }

      // DEMO path: local only, never a real generation call.
      const s = await global.WB.demo.generate();
      return {
        status: STATUS.SUCCEEDED,
        content: s.content.text,
        content_version_id: "demo-content-v" + s.content.version,
        provider: "demo",
        skill_id: "demo-generation-stub",
        skill_version: "1.0-demo",
        warnings: ["DEMO 示例内容：不是真实模型输出，不可用于发布。"],
        error: null,
        request_echo: summarize(request),
      };
    },
  };

  function summarize(request) {
    const r = request || {};
    return {
      task_id: r.task_id || null,
      plan_version: r.plan_version || null,
      genre: r.genre || null,
      language: r.language || null,
      platform: r.platform || null,
      evidence_refs: (r.evidence_refs || []).length,
      mode: r.mode || null,
    };
  }

  global.WB.generation = Adapter;
})(window);
