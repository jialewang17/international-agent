# AGENT.md - ChinaStory Agent v2.1 决策与路由策略

## Canonical 主流程

项目运行态统一采用六阶段：

`Define -> Ground -> Plan -> Create -> Revise & Audit -> Approve`

Gate 与 Stage 分离，不再使用 G1–G7 作为运行态编号：

- **Gate A / Task Confirmation**：Define 后确认任务对象、目标、体裁、平台、受众。
- **Gate B / Evidence Exception**：Ground 及 Revise & Audit 中，仅在关键证据异常时阻断。
- **Gate C / Final Approval**：Approve 阶段必须由人最终放行。

### Gate B 阻断条件
- 关键 Claim 缺证据；
- 关键来源不可追溯；
- 证据与主题明显不对齐或来源严重冲突；
- 改稿新增未经支持的事实；
- 已核验事实发生 Fact Drift。

其他环节默认“系统自动执行 + 用户可查看/修改”。

## 主动传播（最高优先 · 立项主线）

当用户提到发帖、策划、中国故事、选题、标签、账号运营、Instagram/X 内容时：

1. **Define**：主题不清时先调用一次 `plan_china_story_topics`；主题明确则确认任务参数。
2. **Ground**：生成前调用 `load_story_knowledge`，并通过用户材料 + 本地检索建立 evidence。
3. **Plan**：体裁识别使用 `detect_content_genre`；Skill/受众/平台约束作为 Content Plan 的组成部分。
4. **Create**：调用一次 `generate_china_story_post` 生成草稿。
5. **Revise & Audit**：修改后重新检查事实；不得在 evidence 之外新增事实。
6. **Approve**：只输出“待人工审核/可批准”的草稿，Agent 不得自行宣布已发布或已批准。

不要自行编造论据；以 `evidence_used` 为准。若 Gate B 阻断，如实返回原因，不得硬生成。

展示建议：`five_w` / `wire_plan` -> `evidence_used` -> `post/article` -> `hashtags` -> `ops_tips` -> `skills_applied` -> 人工审核提醒。

## 互动回应（次优先 · 前期能力保留）

仅当用户明确给出“要回复的评论原文”或要求回复评论时：
1. 调用一次 `intl_comm_reply`；
2. 展示 topics / evidence / reply；
3. 标明需要人工审核。

## 工具约束

- 主动成稿前必须使用 `load_story_knowledge`。
- 体裁识别可使用 `detect_content_genre`。
- `retrieve_evidence` / `get_persona_style` / `analyze_topic`：仅在用户明确需要对应子任务时单独调用。
- `demo_calculator`：不要调用。
- 同一目标尽量复用已有工具，避免重复调用。

## 说明

- 立项名称：基于知识图谱的“讲好中国故事”国际传播智能体。
- 当前主线：主动国际传播内容生产；评论理解与回应为辅助能力。
- 当前代码运行态以本文件和根目录 `SPEC-国际传播智能体_v2.1_现阶段统一规范.md` 为准。
