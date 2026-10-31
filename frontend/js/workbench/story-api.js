/* LIVE adapter: the only module allowed to call story-task HTTP endpoints.
   Shapes follow api/story_router.py exactly (schemas use extra="forbid"). */
(function (global) {
  "use strict";
  const U = global.WB.util;

  const BASE = "/api/story-tasks";

  async function call(method, path, body) {
    const res = await U.getJSON(BASE + path, { method: method, body: body });
    if (!res.ok) return { ok: false, error: U.parseError(res) };
    return { ok: true, data: res.data && res.data.data !== undefined ? res.data.data : res.data };
  }

  const StoryApi = {
    /* POST /api/story-tasks — body is restricted to {topic, user_materials}. */
    createTask: function (topic, userMaterials) {
      return call("POST", "", { topic: topic, user_materials: userMaterials || "" });
    },

    /* GET /api/story-tasks/{id} — returns {task, ground, plan, workflow, ...} */
    getTask: function (taskId) {
      return call("GET", "/" + encodeURIComponent(taskId));
    },

    /* POST /plan — accepts an already produced NarrativePlan; it is NOT a planner. */
    submitPlan: function (taskId, plan) {
      const payload = {
        version: Number(plan.version || 0),
        title: String(plan.title || ""),
        central_message: String(plan.central_message || ""),
        selected_angles: plan.selected_angles || [],
        excluded_angles: plan.excluded_angles || [],
        sections: (plan.sections || []).map(function (s) {
          return {
            title: String(s.title || ""),
            purpose: String(s.purpose || ""),
            evidence_ids: s.evidence_ids || [],
            fact_gaps: s.fact_gaps || [],
          };
        }),
        evidence_gaps: plan.evidence_gaps || [],
        planning_status: plan.planning_status || "DRAFT",
      };
      return call("POST", "/" + encodeURIComponent(taskId) + "/plan", payload);
    },

    /* P0-2: POST /plan/generate — real model plan candidates from the
       attached Ground EvidencePack. Draft proposals only; saving goes
       through submitPlan. */
    generatePlanCandidates: function (taskId) {
      return call("POST", "/" + encodeURIComponent(taskId) + "/plan/generate", {});
    },

    /* POST /feedback — records text and invalidates the previous plan only. */
    sendFeedback: function (taskId, instruction) {
      return call("POST", "/" + encodeURIComponent(taskId) + "/feedback", { instruction: instruction });
    },

    /* POST /confirm — Gate A joint confirmation (server validates the plan).
       The UI says "X"; the backend stores the canonical "twitter" id. */
    confirm: function (taskId, confirmation) {
      const payload = {
        audience: String(confirmation.audience || ""),
        genre: String(confirmation.genre || ""),
        language: String(confirmation.language || ""),
        audience_knowledge: confirmation.audience_knowledge || "unknown",
        platform: U.platformToBackend(confirmation.platform),
        user_requirements: String(confirmation.user_requirements || ""),
      };
      return call("POST", "/" + encodeURIComponent(taskId) + "/confirm", payload);
    },

    /* POST /enter-create — server enforces Gate A + trusted Gate B. */
    enterCreate: function (taskId) {
      return call("POST", "/" + encodeURIComponent(taskId) + "/enter-create");
    },

    /* Existing canonical Gate C endpoint is not part of story tasks; exposed for
       audit panels that already hold a real content_version_id + evaluation_id. */
    approveExisting: function (payload) {
      return U.getJSON("/api/posts/approve", { method: "POST", body: payload }).then(function (res) {
        if (!res.ok) return { ok: false, error: U.parseError(res) };
        return { ok: true, data: res.data && res.data.data };
      });
    },
  };

  global.WB.storyApi = StoryApi;
})(window);
