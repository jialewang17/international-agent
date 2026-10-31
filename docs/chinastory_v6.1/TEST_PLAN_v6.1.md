# ChinaStory v6.1 本地验收与尚需完成的端到端检查

| 测试 ID | 内容 | 期望状态 |
|---|---|---|
| T01/T02 | 两个顶层 Skill 目录存在，6 体裁完整，Post/News SHA256 与 v5.1 一致 | 本地自动化 |
| T03/T04 | 主 Skill 与输出规范引用新路径，含清楚的兼容/门禁边界 | 本地自动化与人工审读 |
| T05 | v6.1 Schema 除元信息外的结构与 v5.1 相同，且不放在 `api/schemas/` | 本地自动化 |
| T06/T07 | 16 项 validator 单测 + 使用具体 `content.txt` 做哈希/Span 检查 | 本地自动化 |
| T08 | 合并脚本注册两项新 Skill，旧项保留且再次运行幂等 | 隔离测试 |
| T09–T12 | loader Post/News、未知体裁、空文件与预算不足失败、正式 Rubric 缺失失败 | 本地自动化 |
| T13 | News 真实源码标记缺 pack 时补上；同一变更重复执行不重复；变化时拒绝改写 | 隔离测试；真实 E2E 待测试 |
| T14 | `jsonschema>=4` 依赖只追加一次 | 隔离测试 |
| T15 | 与 `api.schemas.EvaluationResult` 的差异清单存在且没有自动瞎映射 | 人工集成审查 |
| T16 | 变更依据、历史资料存在并可读取 | 本地自动化 |
| T17–T19 | 合并脚本的 dry-run 不落盘、`--apply` 更新、脏工作树/重名文件冲突拒绝操作 | 隔离测试 |

## 真正合并到 GitHub 的验收门禁（不在本地包内宣称通过）

1. 在本地仓库分支运行 `python -m unittest discover -s tests/chinastory_v61 -p "test_*.py" -v` 与原项目测试。
2. `GET /api/health`、`GET /api/meta` 保持工作；至少 Post/News 各调用一次 `POST /api/posts/generate`。News 必须可创建 `content_version_id` 并关联 canonical EvidencePack。
3. 整合新版 Skill 的 Prompt 及 Evaluation P3 前，先补齐 TaskContext、ContentPlan、Part1 状态和版本 ID；不得以静态文件安装替代真实模型实验。
4. 对 `api.schemas.EvaluationResult` 新旧跨度、confidence、优先事项、状态做迁移测试；校验失败不触发 Revision 和 Gate C。
5. 任一环节缺真实事实依据、发生生成器输出解析错误、版本绑定不匹配，应按后端门禁失败处理。
6. 实测人工批准需要关联同一个 `task_id/content_version_id/evaluation_id`，不由模型自行决定 APPROVED。

**验收判定**：离线校验通过只能写“v6.1 合并文件通过本地静态检查”；真实 Qwen、人工评分一致性、六体裁 E2E 均须独立记录，未测试就标“未验证”。
