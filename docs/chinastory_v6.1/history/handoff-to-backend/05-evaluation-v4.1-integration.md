> ⚠️ 历史资料（v4.1）：以下路径仍按旧版 Skill 内部目录记录。**v5.1 集成请以 `06-evaluation-v5.1-integration.md` 为准**，不要直接复制旧路径命令。

# Backend Handoff 05：接入 Evaluation Skill v4.1 的工程任务

> 该文件不属于第三个 Skill；它不代表项目仓库代码已经被修改。

## 1. 先确认仍只有两个顶层 Skill

- `china-story-generation` 保留六体裁 Post/News/Feature/Indepth/Script/FAQ，并使用 Post/News v3.1 方法。
- `china-story-evaluation` 是 Part 3 的唯一内容评价 Skill。Fact Check 属 Part 1、Translation External Evaluation 属 Part 2，均不成为本次新顶层 Skill。

## 2. 推荐接入顺序

1. 保留 v2.1 旧 JSON 字段。先让 Backend 能将 `content.text`、`TaskContext`、`AudienceProfile`、`part1_status` 交给 Evaluation。
2. 修改 Pydantic 请求模型：**可选**接受 `task_context.format`、`editorial_mode`、`content.structured_content`、`media_manifest` 等；保持 `content.text` 的不可变定位基准。
3. 修改 Pydantic 响应模型：如需发布新字段，**先**支持 `execution_status`、`review_decision`、`confidence_status`、`issue_id/severity/location/expected_check/requires_fact_recheck`，并保持旧 `status`、`dimension_id` 和 `revision_suggestions` 兼容。
4. 在 API 结果交付下游前执行 `scripts/validate_evaluation.py` 对应逻辑：先 JSON Schema，再六维唯一 ID/Span/hash/状态联合检查；非法结果进入重试或人工处理，不进入自动 Revision。
5. Judge 不赋予发布权限，不执行待评文章里的命令；在 Prompt 中对不可信数据做明确隔离，并限制工具权限。
6. 保存 Judge 模型、参数、Prompt、Rubric、受众上下文版本、`content.text` 哈希和时间戳；对比时使用相同条件。
7. 执行 `Part 1 → (Part 2 如果可用) → Part 3 → RevisionInstruction → Generation V2 → Part 1 核查 → Part 3 再评价 → Gate C`。

## 3. 兼容性 / 审计提醒

- 正式 Rubric 仍是 `CHINASTORY_CONTENT_QUALITY_RUBRIC_v2.1`；没有人工实验就不要编造阈值。
- `confidence=null` 可能与旧版浮点字段冲突。请在服务端明确选择 v4.1 的 nullable 扩展，**不要为了兼容而伪造 0.95**。
- `status` 不替代 `execution_status/review_decision`；后者未部署之前可只输出原状态值。
- `evidence_spans` 在服务端以 Python Unicode 码点验证，JS 前端如需显示必须转换 UTF-16 下标。
- 对缺图形/视频场景：模型只能评价文本策划，不声称已经评估了真实图片。
- Schema 文件中 `$id` 使用 `example.invalid` 占位，不应将其当成已部署端点；正式接线时用团队域名/仓库资源地址替换。

## 4. 关键文件

- `china-story-evaluation/SKILL.md`
- `china-story-evaluation/references/input-contracts.md`
- `china-story-evaluation/references/output-contracts.md`
- `china-story-evaluation/schemas/evaluation-result-v4.1.schema.json`
- `china-story-evaluation/scripts/validate_evaluation.py`
- `china-story-evaluation/docs/Evaluation_v4.1_Test_Plan.md`
