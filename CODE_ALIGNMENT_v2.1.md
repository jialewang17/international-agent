# Code Alignment v2.1

## 本次改动

代码运行态从旧 `G1–G7` 对齐到项目总 SPEC v2.1：

`Define -> Ground -> Plan -> Create -> Revise & Audit -> Approve`

Gate 与 Stage 分离：

- Gate A — Task Confirmation
- Gate B — Evidence Exception
- Gate C — Final Approval

## 修改文件

- `AGENT.md`
- `api/main.py`
- `tools/story_post_gen.py`
- `frontend/js/app.js`
- `frontend/index.html`
- `config/tools.yaml`

## 补齐缺失工具

### `tools/load_story_knowledge.py`
仓库的 `AGENTS.md`、Skill 与 Knowledge 文档都要求生成前调用，但原 ZIP 中缺失实现。本次补齐为知识门禁工具。

### `tools/intl_comm_reply.py`
`api/main.py` 与 `config/tools.yaml` 已引用该模块/工具，但原 ZIP 中缺少文件，导致 API 导入失败。本次按旧 SPEC、现有 ABSA/Reply Prompt、本地 evidence/persona 工具补齐，同时提供：
- `analyze_topic`
- `intl_comm_reply`

`detect_content_genre` 已存在于 `tools/genre_router.py`，本次将其加入 enabled tools。

## 兼容策略

- API 响应使用 `pipeline_steps` 表示六阶段。
- API 响应使用 `gates` 单独表示 A/B/C。
- 前端 `#pipelineViz` 将 Stage 与 Gate 同时可视化，但 Gate 不再伪装成 Stage。
- 历史研究文档 `docs/PIPELINE_OUTLINE_v1.md`、`docs/PIPELINE_LIT_MAP.md` 中的 G1–G7 保留为历史材料，没有机械替换。
- `archive/` 中旧 SPEC 保留，不参与当前运行规范。

## 推送前建议

```bash
python -m compileall agent api tools utils
python -c "from utils.tool_registry import get_tool_registry; r=get_tool_registry(force_reload=True); print([x.name for x in r.enabled_tools]); print(r.module_errors)"
```

若本地已配置模型/API Key，再启动 FastAPI 和前端进行一次：
1. 主动帖文生成；
2. Evidence Gate B 阻断；
3. 改稿；
4. Gate C 人工批准；
5. 评论回复。


## 验收补充

- Gate C 已增加后端 `POST /api/posts/approve`，前端不再只靠本地变量“假批准”。
- Approval 返回 UTC 时间、内容 SHA-256、approver、status；`published=false`，明确“批准 ≠ 发布”。
- `Revise & Audit` 当前仍只能做到“改稿后标记需事实复核”，尚未实现自动 Claim Diff / Fact Drift 检测；不能把它宣称为已完成 Fact Lock。
