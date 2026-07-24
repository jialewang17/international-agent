# Profile Layer

Agent 人格、约束与决策策略。由 `config/profile.yaml` 配置，`utils/profile_loader.py` 加载并注入 system prompt。

| 文件 | 作用 | 默认注入 |
|------|------|----------|
| `identity.md` | 角色定位与输出格式 | 是 |
| `soul.md` | 目标、立场与安全约束 | 是 |
| `agent.md` | 工具调用与任务路由 | 是 |
| `tools.md` | 工具使用原则（含 `{{tool_registry}}`） | 是 |
| `user.md` | 用户偏好占位 | 否 |
| `memory.md` | 记忆策略说明 | 否 |

修改后可在 CLI 执行 `/profile reload` 热加载。
