# Evaluation v5.1 输出契约（自然语言说明）与旧 API 兼容方案 [E04/E05/E10][V51-03]

> **契约策略**：本文件解释“每个字段代表什么、如何交给下游”；后端正式 API/Pydantic 响应模型是部署时的接口权威，交付包 `eval/contracts/evaluation-result-v6.1.schema.json` 是必须与之保持一致的独立机器校验镜像。若二者冲突，**阻断部署并对齐**，不可让 Skill 自行选择一套。保留 v2.1 字段和六维 ID；新字段为可选扩展，未更新后端前不默认输出。评分仍取正式 Rubric v2.1。[S01–S03][V51-03]

## 1. 旧版字段不改名

`evaluation_id, task_id, version_id, rubric_version, status, dimensions, priority_issues, revision_suggestions, overall_score, return_to_part1, real_audience_evaluation, human_review, audit`

- `overall_score: null`。绝不默认平均分或加权合成。
- `human_review: PENDING`。只由人工 Gate C 写最终批准结论。
- `dimensions[]` **仅在完整成功评分时**恰好六项、无重复，`score` 为 1–5 **整数**。不要输出“未通过＝0”破坏 Rubric。
- 单维度旧字段保持：`dimension_id`、`score`、`confidence`、`evidence_spans[]`、`rationale`、`problems[]`、`revision_suggestion`。
- `revision_suggestions[]` 每条保留旧的 `target_dimension`、`problem`、`instruction`、`preserve[]`。

## 2. 状态含义建议 [E05]

| 场景 | 旧 `status`（兼容） | 新可选 `execution_status` | 新可选 `review_decision` | 注释 |
|---|---|---|---|---|
| 完成评分，存在修改建议 | `COMPLETED` | `COMPLETED` | `REVISE` | 不把执行成功和稿件通过混在一个值里 |
| 完成评分，无需建议但仍需人工 | `COMPLETED` | `COMPLETED` | `READY_FOR_HUMAN_REVIEW` | 不是 `APPROVED` |
| 缺乏决定性上下文 | `INSUFFICIENT_CONTEXT` | `INSUFFICIENT_CONTEXT` | `NEEDS_HUMAN` | `dimensions[]=[]`，不是强打 1 分 |
| 疑似事实错误须暂停评分 | `RETURN_TO_PART1` | `RETURN_TO_PART1` | `RETURN_TO_PART1` | `return_to_part1=true`，不自动裁决 |

历史执行状态列表 `CREATED/PRECHECK/INSUFFICIENT_CONTEXT/SCORING/COMPLETED/REVISION_RECOMMENDED/RETURN_TO_PART1/HUMAN_REVIEW_PENDING` 可继续由后端生命周期管理。新字段**仅作为建议字段**，不得在未升级接口时直接替代旧字段。[S02/S03]

**阈值不得私设**：`READY_FOR_HUMAN_REVIEW` 应由后端政策和人工工作流确定；本 Skill 不因“六项都 ≥4”自行批准。正式 Rubric 的“自动通过阈值”是 TBD。[S01]

## 3. 定位格式与扩展（须更新后端 Schema）

例子使用同一份 `content.text`：

```text
Suzhou embroidery is a traditional Chinese craft.
```

定位：`{"text":"Suzhou embroidery", "start":0, "end":17}`。

**索引规则**：`start` 计入，`end` 不计入，单位为 Python Unicode 码点；必须满足 `content.text[start:end] == text`。含中文或 emoji 的用例也必须通过验证。[E04]

建议新增可选字段：

- 在维度对象：`confidence_status: CALIBRATED | UNCALIBRATED | NOT_APPLICABLE`；未校准时 `confidence: null`，而不是凭空报 `0.97`（旧后端若只允许浮点数，须先迁移）。
- 在 `revision_suggestions[]`：`issue_id`、`severity`、`location`（含跨度）、`expected_check`、`requires_fact_recheck`。
- 在 `audit`：`content_sha256`（对原样 `content.text` 的 UTF-8 字节计算）及 `offset_unit: unicode_code_points`。
- 在顶层：`execution_status`、`review_decision`，以及明确的 `limitations[]`；这些均**不是 v2.1 旧字段**。

## 4. 确定性校验

- 先由**工程侧**的 `eval/contracts/evaluation-result-v6.1.schema.json` 检查类型、必填、数值范围，再由 `utils/validate_evaluation.py` 校验六维唯一性、Span 精确匹配、哈希一致、状态不冲突。两份程序文件已移出 Skill 包，不可误认“加载 SKILL.md 就会自动执行 Python 验证”。
- `status=COMPLETED` 时：`dimensions[]` 必须包含六项；`return_to_part1=true` 不得同时声明 `review_decision=READY_FOR_HUMAN_REVIEW`。
- `status=INSUFFICIENT_CONTEXT` 或 `RETURN_TO_PART1` 时：不得输出一份伪装成完整成功的六维分数。
- JSON Schema 校验失败，交给后端修复/重试或人工，不得把模型输出当作有效评价直接进入 V2 改写。

## 5. 依据

- [S01] 项目 [Rubric v2.1](https://github.com/jialewang17/international-agent/blob/main/eval/CHINASTORY_CONTENT_QUALITY_RUBRIC_v2.1.md) 和 [Skill Spec v1.1](https://github.com/jialewang17/international-agent/blob/main/eval/CHINASTORY_EVALUATION_SKILL_SPEC_v1.1.md)。
- [S02] [Evaluation Pipeline v1.2](https://github.com/jialewang17/international-agent/blob/main/eval/CHINASTORY_EVALUATION_PIPELINE_SPEC_v1.2_CN.md)。
- [S13] [JSON Schema Object / Required](https://json-schema.org/understanding-json-schema/reference/object)；[S14] [JSON Schema Numeric](https://json-schema.org/understanding-json-schema/reference/numeric)。


## v6.1 合并提示（字段不变）

- 不可直接将本文件所述 `version_id` 写入后端 `EvaluationResult.content_version_id` 而不核对其 canonical version record。
- 后端已有 `DimensionResult.confidence: float`、`EvidenceSpan` 需要 `span_id/source_id`；本 Skill 的可选 `confidence=null` 与 `{text,start,end}` 定位片段不能直接强行转为后端旧数据结构。先设计并测试无损映射；映射缺失则阻断写入。
- `priority_issues[]` 可包含字符串是文档兼容策略，不等于旧 Pydantic `List[EvaluationIssue]` 接受字符串；部署前须形成单一权威数据契约。
