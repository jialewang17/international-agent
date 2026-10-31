# ChinaStory Evaluation Skill v5.1｜执行结构、数据契约与部署分层

## 1. 这是怎样的 Skill？

Evaluation Skill 只负责 ChinaStory Evaluation Pipeline 的 **Part 3：内容质量与跨文化表达评价**。上游 Part 1 确保事实门禁；Part 2（如部署）处理翻译独立指标；后端 Gate C 才能批准发布。

实际执行：

1. **检查前置条件**：已确定主题/受众/体裁/版本，正式 Rubric 可用，Part 1 没有未解决阻断；未满足则返回 `INSUFFICIENT_CONTEXT` 或 `RETURN_TO_PART1`。
2. **加载评测方法**：`SKILL.md` + `references/rubric-usage.md`、`cross-cultural-review.md`、对应该体裁的 `genre-checks.md` 和 `revision-feedback.md`，读取仓库官方 Rubric v2.1。
3. **大模型逐维评分**：D1 跨文化可理解、D2 文化表达、D3 受众适配、D4 叙事吸引潜力、D5 体裁平台适配、D6 自然度；每项 1–5 整数并给具体原文依据。不计算总分。
4. **问题定位**：按 `content.text` 的 Python Unicode 码点 `[start,end)` 精确定位；疑似事实问题交 Part 1，不越权。
5. **构造修改建议**：`revision_suggestions[]` 包含原有字段和已经协商启用的可选定位、严重度、验收条件等。
6. **输出后端校验**：评测模型输出 JSON 后，由**实际集成的后端程序**先按 `api/schemas/evaluation-result-v5.1.schema.json` 做机器结构校验，再由 `utils/validate_evaluation.py` 做六维唯一性、Span、哈希和状态逻辑校验。失败不得送入自动 Revision。
7. **继续流程**：有效评价交由后端决定是否返回 Generation 生成 V2、是否需要事实复核或提交人工 Gate C。`COMPLETED` 不等于 `APPROVED`。

## 2. 为什么要有 input/output contracts？

- `references/input-contracts.md` 说明**从上游必须收到哪些语义上下文**，避免模型在不知道受众/体裁时盲评。
- `references/output-contracts.md` 说明**输出的字段语义与兼容约束**，避免下游误解评分和状态。
- 它们是人类和模型的规范文档，不是程序校验器；实际 API/Pydantic 与 JSON Schema/逻辑校验需要**独立代码**执行。

## 3. 什么在 Skill 内，什么在 Skill 外？

| 层 | 文件 | 是否每次模型评价要加载？ |
|---|---|---|
| Skill 核心 | `SKILL.md` | 是 |
| 专业参考 | 七份 `references/*.md` | 按 `SKILL.md` 指示按需加载 |
| 数据机器契约 | `api/schemas/*.json` | 不直接作为推理知识，后端验证时读取 |
| 逻辑验证 | `utils/validate_evaluation.py` | 后端按接口调用，Skill 不会自动运行 |
| 回归测试 | `tests/evaluation/*` | 开发/CI 执行，不是每篇稿件的评分阶段 |
| 研究证据 | `docs/evaluation/*` | 研究追溯/人工维护，不是每篇稿件的评分阶段 |
| 平台元数据 | `agents/openai.yaml` | 取决于 Skill 平台；不是 AI 模型配置 |

## 4. 运行状态

静态 Python 数据验证可在本交付包上离线完成；真实 Qwen Judge 调用、后端请求/响应模型适配、事实门禁、人工审批、模型与人类一致性评测均需在真实项目另行验证。移动文件不等于这些流程已实现。

## 5. 修改依据

逐条参见 [Evaluation v5.1 修改证据表](evaluation/Evaluation_v5.1_Changes_and_Evidence.md)，包含 V51-01–V51-12 的内部基线、官方资料、工程判断及测试项。
