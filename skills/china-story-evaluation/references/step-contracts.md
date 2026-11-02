# Evaluation 步骤契约 E00–E05

> 用途：把 `SKILL.md` 的 Part 3 流程固化成六步可审计契约。编号即身份，
> 与 `utils/step_audit.py` 中的 `EVALUATION_STEPS` 一一对应。
>
> 边界不变：本 Skill 只做 **Part 3（表达与跨文化传播质量）**。
> 事实裁决在 Part 1，翻译等值在 Part 2，重写在 Generation，最终批准在 Gate C。

| 字段 | 含义 |
|---|---|
| 输入 | 该步必须读到的对象 |
| 产出 | 该步必须给出的东西 |
| 依据 | 方法来源（仓库内可核对位置） |
| 停机条件 | 满足即停止常规评分，给出明确状态 |
| 审计 status | `OK` / `SKIP` / `BLOCKED` / `FAILED` / `NOT_RUN` |

---

### E00 前置检查与 Part 1 门禁

- **输入**：`evaluation_id`、`task_id`、`version_id`、`rubric_version`、`task_context`、
  `audience_profile`、`content.language`、`content.text`、`upstream_evaluation.part1_status`。
- **动作**：
  1. 逐项确认上表齐全；缺项返回 `INSUFFICIENT_CONTEXT` 并列出缺项，**不得**凭常识补受众；
  2. `part1_status` 为 `BLOCKED` / `FAIL` / 仍有未解决阻断时，返回 `RETURN_TO_PART1`，
     不产出六维结果；
  3. Part 3 不重新裁决事实，只把疑点结构化移交。
- **产出**：可评分判定（是/否）+ 缺失项清单。
- **依据**：`SKILL.md` §1 调用前置检查；`api/evaluation.py` 的 Part 1 门禁分支。
- **停机条件**：`INSUFFICIENT_CONTEXT` / `RETURN_TO_PART1`。
- **审计 detail**：`part1_status`、`missing_context`、`content_sha256`。

---

### E01 资料加载（Rubric 与专项检查）

- **输入**：E00 通过后的上下文。
- **动作**：加载正式 Rubric v2.1 的 D1–D6 行为锚点、跨文化检查表、**本体裁**专项检查、
  修改指令规则；Rubric 不可读或版本不符即停止评分。
- **产出**：已确认版本的方法集合（`rubric_version` + 实际读取的参考文件清单）。
- **依据**：`SKILL.md` §2；`api/rubric_loader.py`；`eval/CHINASTORY_CONTENT_QUALITY_RUBRIC_v2.1.md`。
- **停机条件**：Rubric 不可读 / 版本不受支持 → `INSUFFICIENT_CONTEXT`。
- **审计 detail**：`rubric_version`、`references_loaded`。

---

### E02 逐维评价（D1–D6 独立评分）

- **输入**：正文、受众画像、E01 的 BARS。
- **动作**：
  1. 六维各自找实际文本证据，再对 BARS 取 1–5 整数分；
  2. 六维必须齐全且唯一，不得平均、不得跨维代替；
  3. 裁判输出不合法（缺维、重复、非整数、越界、confidence 越界）→ 直接失败，**不做静默修补**。
- **产出**：`dimensions[]`（`score` / `rationale` / `confidence` 或 `null`）。
- **依据**：`SKILL.md` §3；`api/evaluation_part3.py` 的 `_validate_dimensions`。
- **停机条件**：`Part3Error`（裁判不可用或输出不合法），且不得退化成"给个平均分"。
- **审计 detail**：`dimensions_count`、`score_vector`、`judge`。

---

### E03 原文定位与最小修改指令

- **输入**：E02 的维度结论。
- **动作**：
  1. `evidence_spans` 使用 Python Unicode **码点**下标，`content.text[start:end] == span.text` 必须成立；
     不得捏造偏移、不得改用另一份重组文本计算；
  2. 每个扣分点转成 `priority_issues` + `revision_suggestions`（定位、目标维度、期望检查条件、不可改动的事实）；
  3. 疑似事实错误 → `return_to_part1=true` 结构化移交，不作最终裁决。
- **产出**：`evidence_spans`、`priority_issues[]`、`revision_suggestions[]`。
- **依据**：`SKILL.md` §3 第 3–6 条；`references/output-contracts.md`；`utils/validate_evaluation.py`。
- **停机条件**：跨度不可对齐 → 该结果不得被测评为"已完成"。
- **审计 detail**：`spans_count`、`span_match`、`suggestions_count`、`return_to_part1`。

---

### E04 输出结构与状态

- **输入**：E02/E03 的结果。
- **动作**：
  1. 保留 v2.1 顶层字段（`evaluation_id` / `task_id` / `version_id` / `rubric_version` /
     `status` / `dimensions` / `priority_issues` / `revision_suggestions` / `overall_score` /
     `return_to_part1` / `human_review` / `audit`）；
  2. `overall_score` 固定 `null`（Rubric §5.2 无默认聚合）；
  3. `human_review` 保持 `PENDING`；`APPROVED` / `PUBLISHED` 属禁止状态，永不输出。
- **产出**：符合契约的 `EvaluationResult`。
- **依据**：`SKILL.md` §4；`api/evaluation_part3.py` 的 `FORBIDDEN_STATUSES`。
- **停机条件**：无（字段缺失即契约违规，按失败处理）。
- **审计 detail**：`status`、`overall_score`（恒 null）、`human_review`。

---

### E05 机器校验与校准留痕

- **输入**：E04 的结果、正文原文。
- **动作**（由**后端**执行，不是由 Skill 自评）：
  1. 跑 `eval/contracts/evaluation-result-v6.1.schema.json` + `utils/validate_evaluation.py` 的
     确定性校验：六维唯一性、分值区间、跨度精确匹配、`content.text` SHA-256、状态组合自洽；
  2. 校验失败 → 重试或转人工，**不得进入自动 Revision**；
  3. 未做目标语言/体裁人工校准前，`confidence=null` + `UNCALIBRATED`，禁止伪造精确置信度；
     记录 Rubric 版本、裁判模型、Prompt 版本、校准集版本与时间。
- **产出**：审计元数据 + （可选）伴生 `step_audit`。
- **依据**：`SKILL.md` §4 末条、§5；`references/judge-reliability.md`。
- **停机条件**：校验不通过即不得宣称评分有效。
- **审计 detail**：`schema_ok`、`deterministic_checks`、`confidence_status`、`audit_fields`。

---

> 只有 E00–E05 全部 `OK` 时，才允许对外说"这篇按 Skill 走完了六步"。
> 任何一步 `BLOCKED` / `FAILED` / `NOT_RUN`，都必须在结论里明说，不允许只报六维分数。
