# ChinaStory v6.1：实际后端接口差异、尚未打通事项

> 本文是**阻断条件清单**；属于待进一步工程开发的真实缺口，并非已在 v6.1 ZIP 修复或已部署的功能。

## I-01 EvaluationResult 根字段

- Skill 输出要求 `version_id`（以及 `task_id`），而当前 `api/schemas.py::EvaluationResult` 必填 `content_version_id`、`part` 和 `status`；其 `scores`、`issues` 为兼容字段。
- **决策**：后端必须从存储的 ContentVersion 获取 canonical ID，`part` 明确赋 `Part3`（实际枚举需与仓库一致）；不能只给模型输出重命名就认定通过。通过 Pydantic 模型校验后才允许持久化。
- **状态**：未实现 adapter，本次不发布 P3 API。

## I-02 DimensionResult、EvidenceSpan 不同构

- Skill 示例位置 `{text,start,end}` 表示**内容正文中的字符跨度**；后端 `api.schemas.EvidenceSpan` 是**来源证据跨度**，要求 `span_id`、`source_id`。二者语义不同！不得伪造 source_id 将正文位置硬塞进证据跨度模型。
- 后端 `DimensionResult.confidence: float`，但 v5.1/v6.1 推荐未校准时 `confidence: null`。不能编造 `0.5` 过 Pydantic；需新增明确的可空字段或真实校准记录，并调整 API 测试。
- `priority_issues` 的字符串兼容类型与 Pydantic `List[EvaluationIssue]` 也不一致；须为强类型字段设计迁移方案。
- **状态**：数据语义尚未对齐，失败封闭。

## I-03 生成工作流与母稿引用

- Generation Skill 期望已确认的 TaskContext、ContentPlan、EvidencePack、中文母稿 `master_ref` 及逐条 evidence_map；当前 `api/main.py` 主要从 `post` 保存一条 ContentVersion，尚未验证母稿、目标语版本及逐 Claim 绑定完整执行。
- 不能仅因为已把 `SKILL.md` 复制进 `skills/` 就声称具备中文母稿持久化与 Fact Lock。

## I-04 六体裁范围

- 旧生成工具显式 `allowed` 只有 post/news/feature/script；`faq/indepth` 尚未按其专用结构实现。即使修改 `genre_router.py` 提前命中 `indepth`，没有专属生成/验证分支仍会落入默认 Post Prompt。
- 因此 **本次仅保证原来支持的接口继续兼容**；独立 Skill 方法涵盖六体裁不等于六体裁已在前端上线。

## I-05 Registry 与 Prompt 注入

- 公开仓库 `utils/skill_registry.py` 可截断大型主卡（配置中每卡 3600 字符），而 Post/News 方法文本超过这个上限。
- `utils/chinastory_skill_loader_v61.py` 已提供显式按需加载的基础函数，**不会自动执行或自动加入旧 Prompt**。
- 下一轮需要由 Create 调用链在任务/计划/证据校验后，显式选择体裁参考与输出契约，并在真实模型、Token 限额下测试；未测试前保持旧路径默认。

## I-06 评价门禁与审核权限

- Part1/Part2/Part3 和 Gate C 不合并成同一个 Skill；`COMPLETED` 仅代表评测完成。
- 当前 Gate C 依赖已持久化的人工审阅记录与 `(task_id, content_version_id, evaluation_id)` 绑定；新评测不得通过模型文本自行写 `APPROVED`。

## 依据

1. [api/schemas.py](https://github.com/jialewang17/international-agent/blob/main/api/schemas.py) 与当前 v5.1 `SKILL.md`、`output-contracts.md` 的数据类型对照。
2. [tools/story_post_gen.py](https://github.com/jialewang17/international-agent/blob/main/tools/story_post_gen.py)、[tools/genre_router.py](https://github.com/jialewang17/international-agent/blob/main/tools/genre_router.py) 与 v5.1 六体裁方法对照。
3. [api/main.py](https://github.com/jialewang17/international-agent/blob/main/api/main.py) 的 EvidencePack/ContentVersion/Gate C 路径。
4. [FastAPI Response Model](https://fastapi.tiangolo.com/tutorial/response-model/)：响应按声明模型验证/过滤字段，不能认为 JSON 外观相似就兼容。
