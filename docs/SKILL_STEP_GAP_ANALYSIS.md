# Skill 执行步骤 / 方法依据 / 可追溯性 / 质量门 —— 差距分析

> 判据（来自任务书四项要求）：
> ① 每一步**包含什么**（输入、动作、产出、停机条件）；
> ② 每一步**有依据**（不是"我觉得应该这样写"，而是能指到具体来源）；
> ③ 每一步**可溯**（跑没跑、停在哪、产出是什么，能机器读出来）；
> ④ 每一步**有质量门**（不达标就停，不靠"看起来还行"）。
>
> 本文只记录**核实过的事实**：每条差距都给出代码/文件位置与复现方式；
> 没有核实的猜测一律标注"未验证"，不写进结论。

---

## 0. 核查方式

| 方式 | 具体做法 |
|---|---|
| 读代码 | `tools/story_post_gen.py`（生成主链路）、`api/evaluation_part3.py`（评测 Part 3）、`api/evaluation.py`（Part1→3 编排）、`api/workflow.py`（Gate 状态机）、`utils/skill_registry.py`（技能加载）、`utils/genre_contracts.py`（六体裁契约） |
| 读文档 | 两个 `SKILL.md`、`config/skills.yaml`、`eval/CHINASTORY_CONTENT_QUALITY_RUBRIC_v2.1.md`、`eval/contracts/evaluation-result-v6.1.schema.json` |
| 跑测试 | `pytest tests/ -q` 全绿基线（612 项，本次改造后 631 项） |
| 反向验证 | 对每个"文档说已实现"的点，去代码里找调用点；找不到即记为差距 |

**一个已发生的实例**：`SKILL.md` §2.0 曾写"成稿前调用 `load_story_knowledge`，仅当 `gate=ready_to_generate` 才继续"，
但 `tools/story_post_gen.py` 里根本没有这个调用——文档与代码漂移了几个月没人发现。
这正是"缺少机器可校验依据"的直接后果，也是本次要把依据做成**锚点可校验**的动机。

---

## 1. 差距清单

编号规则：`GAP-xx`。状态：**已修**（本次改造完成）/ **不修**（说明原因）/ **待人工**（需要老师/成员决策或外部条件）。

### GAP-01 生成链路没有接 Gate 状态机，Gate 状态是"画"出来的

- **现状证据**：`api/workflow.py` 提供 `WorkflowStateMachine`（A/B/C 三道门 + 阶段推进），
  `api/main.py:150` 也有 `/api/workflow/...` 控制器；但 `api/main.py:179` 调用
  `run_story_post_generation(**payload)` 时**不查任何 gate**，生成器内部的
  `_pipeline_state()`（`tools/story_post_gen.py`）自己拼了一份 `pipeline_steps` 与 `gates` 列表，
  `status` 全按本次参数算出来（例如 "Gate B: stop"）。
- **影响**：前端看到的 Gate B 状态与后端状态机可能不一致；"证据异常已阻断"只是文案，
  不是状态机裁决；无法回答"这次生成是 Gate B 批准后跑的吗"。
- **本次处置：部分已修 + 明确边界**
  - 已做：生成结果增加 `step_audit`，其中 C01 记录真实门禁依据
    （`gate_b=ready_to_generate` / `empty` / `canonical_evidence_invalid` / `alignment`，
    外加 `pack_digest` 与证据条数），使"门禁到底过没过、凭什么过"可核。
  - 未做（**不修，需架构决策**）：让 `run_story_post_generation` 直接驱动 `WorkflowStateMachine`。
    原因：状态机以 `task_id` 为键、要求按 `DEFINE→GROUND→…` 顺序 `advance`，
    而生成工具当前是**无状态函数**（可被 CLI / Agent 工具环 / API 分别调用）。
    强行接入会改变所有既有调用方语义，并牵连 `api/human_review.py`、`api/revision_loop.py`
    两处显式"不碰状态机"的约定（见 `tests/test_human_review.py:211`）。
    建议单独起一项"Gate 状态机与生成工具对接"任务，由老师在 `api/main.py` 层收口。

### GAP-02 `always_on` 只写在卡上，代码没强制（**已修**）

- **现状证据**（改造前）：
  1. `skill_ids_for(genre)` 只返回体裁卡（`utils/genre_contracts.py`），`intl_comm` 从未被注入；
  2. `evidence_user_materials` 仅在"有用户资料"时才追加（`tools/story_post_gen.py`）；
  3. `get_active_skills_for_query`（`utils/skill_registry.py`）对不可用的 `always_on`
     直接 `continue`，且 `always_on` 与其他技能一起参与 `max_total_chars` 裁剪
     —— 预算不足时会被丢掉。
- **影响**：`SKILL.md` §2.0 第 3 条 [G-10] 写着"任何实现不得把证据规则挤出上下文"，
  实际运行里两条常开规则**可以整条消失**，且没有任何报错。
- **处置：已修**
  - 新增 `resolve_always_on()`：按 `config/skills.yaml` 逐条判定 `not_registered / disabled /
    load_failed / empty`，返回可用列表 + 问题列表，不再静默跳过；
  - 生成链路把可用的 `always_on` **无条件并入**必需技能，`always_on` 有问题时
    以 `SKILL_ALWAYS_ON_UNAVAILABLE` **硬失败**（C02）；
  - `get_active_skills_for_query` 改为先占位、预留字符额度，`always_on` 不再被预算裁掉；
  - `skill_load` 诊断新增 `always_on_required` / `always_on_loaded` / `always_on_problems`。
- **验证**：`tests/test_step_audit.py::test_generation_missing_always_on_fails_at_c02`、
  `tests/test_six_genre_p0.py::test_skill_load_diagnostics_are_complete_and_safe`。

### GAP-03 步骤没有运行态记录，失败说不清停在哪（**已修**）

- **现状证据**（改造前）：结果里只有 `generation_status`、`pipeline`（一段人类可读字符串）、
  `skill_load`。`OUTPUT_INVALID` 只说"输出不合法"，不说"前面几步跑没跑、后面几步没跑"。
- **影响**：无法自查"这次到底走了几步"，也无法在汇报时给出证据；排查只能靠读日志。
- **处置：已修**：新增 `utils/step_audit.py`（`StepAudit`），生成 C00–C06、评测 E00–E05
  逐条记录 `status / reason / detail / contract / evidence`，导出时未跑的必做步骤补
  `NOT_RUN`（**不补成功**），并给唯一 `verdict`（`COMPLETE / BLOCKED / FAILED / INCOMPLETE`）。

### GAP-04 失败码与步骤没有映射关系（**已修**）

- **现状证据**：`INVALID_GENRE / GENRE_FORMAT_CONFLICT / UNSUPPORTED_GENERATION /
  SKILL_UNAVAILABLE / OUTPUT_INVALID` 都是孤立字符串，没有说明"停在第几步"。
- **处置：已修**：`skills/china-story-generation/references/step-contracts.md` 末尾
  给出「失败码 → 停在哪一步」对照表；运行结果里由 `step_audit.first_failed` /
  `first_blocked` / `not_run` 直接给出答案。

### GAP-05 方法依据不可机器校验（**已修**）

- **现状证据**：`SKILL.md` 里的 `[G-01]`–`[G-11]`、评测 `[E01]`–`[E10]` 都是叙述式依据，
  指向 `docs/` 里的研究报告；没有任何检查能发现"依据文件改了/删了、卡片还引着它"。
- **处置：已修**：13 个步骤各自登记 `依据锚点`（`文件::锚点字符串`），
  `utils/step_audit.evidence_problems()` 校验 40 个锚点在仓库中**真实存在**；
  `scripts/step_audit_check.py --evidence` 可作为交付前自检命令。
  测试 `test_every_evidence_anchor_exists_in_repo` 已纳入回归。

### GAP-06 评测侧没有确定性质量门（**已修**）

- **现状证据**（改造前）：`utils/validate_evaluation.py` 是**独立 CLI**，
  `evaluate_part3` 内部不做六维唯一性/分值区间/跨度匹配/状态组合校验；
  `evidence_spans` 的 `start/end` 若与 `content.text` 不符，会被**静默接受**。
- **影响**：`SKILL.md` §4 写着"由后端而不是 Skill 本体执行机器校验"，
  但后端这条路径实际上"有工具、没接线"。
- **处置：已修**
  - `evaluate_part3_with_audit` 内新增 E05 的 `deterministic_checks()`：
    六维唯一且齐全、分值 1–5、跨度精确匹配、正文 SHA-256、状态组合自洽；
  - E03 增加逐条跨度核对，不一致时**转成 blocking issue**（`issue_id=span-mismatch`），
    状态落到 `REVISION_RECOMMENDED`，不再静默通过；
  - 需要说明的边界：`eval/contracts/*.schema.json` 的 JSON Schema 结构校验仍由后端
    `utils/validate_evaluation.py` 执行（本次不引入 `jsonschema` 运行时依赖）。

### GAP-07 评测没有步骤留痕（**已修，且不破坏契约**）

- **现状证据**：`EvaluationResult` 只有 `audit` 元数据（评测器/模型/Rubric 版本/时间），
  没有步骤级状态。
- **处置：已修**：新增 `evaluate_part3_with_audit()` 返回 `(result, step_audit)`；
  `evaluate_part3()` 签名与返回值**完全不变**，`EvaluationResult` 一个字段都没加。
  审计作为**伴生数据**由调用方持久化 —— 这是为了不动与前端共用的契约。

### GAP-08 质量门阈值仍是 TBD（**待人工，不私设**）

- **现状**：`eval/CHINASTORY_CONTENT_QUALITY_RUBRIC_v2.1.md` §19 的自动通过/人工复核阈值、
  校准误差上限仍标 TBD；`overall_score` 固定 `null`（无默认聚合）。
- **处置**：本次只做**结构性质量门**（该有的字段有没有、偏移对不对、状态自不自洽），
  **不设任何分数阈值**，也不产出总分。分数阈值必须由老师结合评测实验定，写进 Rubric 后再接门。

### GAP-09 Gate C / 人工批准未纳入本次范围（**不修**）

- **现状**：`_pipeline_state` 里 APPROVE 阶段状态恒为 `warn`（"待人工批准"）；
  `api/human_review.py` 明确只管人工审核记录，不碰 Gate C。
- **处置**：不修。步骤契约 C06 只到"移交人工审核（`human_review=PENDING`，`publishable=false`）"，
  与现有边界一致。

### GAP-10 体裁卡内部结构没有后置校验（**部分不修**）

- **现状**：`post.md` v3.2 定义了 `thread` / `visual_story` / `caption_only` 的独立输出结构，
  后端只有 `social_post` 的结构与验证器；`thread` 等已在 C00 以 `UNSUPPORTED_GENERATION` 明确拒绝。
  但 `social_post` 内部的细节（`hashtags` 数量区间、逐图 `alt`、`media_status`）
  目前**只靠卡片约束模型**，代码不校验。
- **处置**：不修（需要先定 Schema）。已在 `SKILL.md` 与交付说明里标注"方法已定义、运行暂不支持"，
  并写进步骤契约 C05 的"待办"边界，避免被理解成已实现。

---

## 2. 本次交付与差距的对应

| 差距 | 交付物 | 位置 |
|---|---|---|
| GAP-02 | `resolve_always_on()` + 生成链路硬约束 | `utils/skill_registry.py`、`tools/story_post_gen.py` |
| GAP-03 / GAP-04 | 步骤审计 + 状态枚举 + 终态判定 | `utils/step_audit.py` |
| GAP-05 | 40 个方法依据锚点 + 校验器 + CLI | `utils/step_audit.py`、`scripts/step_audit_check.py` |
| GAP-06 | E05 确定性校验 + E03 跨度核对 | `api/evaluation_part3.py` |
| GAP-07 | `evaluate_part3_with_audit()`（sidecar） | `api/evaluation_part3.py` |
| 步骤契约 | C00–C06 / E00–E05 | `skills/*/references/step-contracts.md` |
| 可溯样例 | 真实代码产出的 4 份审计 | `docs/chinastory_v6.1/step_trace_samples/` |
| 回归 | 21 项新测试（总 631 项全绿） | `tests/test_step_audit.py` |

---

## 3. 遗留风险（如实列出）

1. **真实模型未跑通**：本地 `qwen` API key 已被平台吊销（401），端到端真实生成/评测仍不可跑；
   本次所有样例用的是替身（`_llm_text` 固定输出、`StubJudge`），已在样例文件里 `_note` 注明。
2. **Gate 状态机未收口**（GAP-01）：生成工具仍是无状态函数，Gate A/B/C 的真实裁决在
   `api/main.py` 层尚未串起来。这是本次**没有**解决的架构问题，不应对外宣称已打通。
3. **阈值缺失**（GAP-08）：没有阈值就没有"自动通过/自动拒绝"，现在的质量门只能拦
   "结构与自洽性错误"，拦不住"内容质量不够"。
4. **评测侧 I-01–I-06 接线项**仍未完成（上一阶段遗留），与本次步骤契约不冲突，但会影响
   评测链路的端到端完整性。
