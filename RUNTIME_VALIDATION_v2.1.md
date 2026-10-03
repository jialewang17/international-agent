# ChinaStory Agent v2.1 Runtime Validation Report

## 结论

本轮已实际启动 FastAPI/Uvicorn，并完成无需外部 LLM 的 API/前端联调。

当前环境无法联网安装 `requirements.txt` 中缺失的 LangChain/Chroma 依赖，因此**真实模型生成链路尚不能在本环境完成**。这属于执行环境限制，不应被表述为“完整 E2E 已通过”。

## 实际通过的检查

- PASS — `python_compileall`：`Spreadsheet runtime warmup failed during python startup
Traceback (most recent call last):
  File "/tmp/tmp.L2TH2Y5coc/artifact_tool_v2-2.8.22/artifact_tool/patches/warm_spreadsheet_runtime_on_startup.py", line 26, in warm_spreadsheet_runtime_on_startup
  File "/tmp/tmp.L2TH2Y5coc/artifact_tool_v2-2`
- PASS — `frontend_js_syntax`
- PASS — `no_legacy_runtime_ids`
- PASS — `frontend_api_route_contract`：`[]`
- PASS — `uvicorn_startup`
- PASS — `meta_six_stages`
- PASS — `meta_three_gates`
- PASS — `http_integration`

## HTTP 联调结果

- PASS — `health`：HTTP 200（预期 200）
- PASS — `meta`：HTTP 200（预期 200）
- PASS — `frontend_index`：HTTP 200（预期 200）
- PASS — `frontend_app_js`：HTTP 200（预期 200）
- PASS — `gate_c_approve`：HTTP 200（预期 200）
- PASS — `gate_c_empty_post`：HTTP 400（预期 400）
- PASS — `generate_dependency_guard`：HTTP 503（预期 503）

## 本轮新增修复

### API 启动与可观测性

`api/main.py` 改为对 LLM / LangChain 工具进行 lazy import。

这样即使模型依赖或 API Key 暂时不可用，以下能力仍可真实启动并用于诊断：

- `/api/health`
- `/api/meta`
- `/`
- `/static/...`
- `/api/posts/approve`

生成类接口若缺运行依赖，现在返回明确的 HTTP 503，而不是在应用启动阶段直接崩溃。

### Gate C

`POST /api/posts/approve` 已实测：
- 正常人工批准：HTTP 200
- 空正文：HTTP 400
- 返回 `approved_at`、`content_sha256`、`status=APPROVED`
- 保持 `published=false`

## 当前环境限制

缺失模块：langchain_core, langgraph, chromadb

当前测试进程检测到的模型 Key 名称：无（未读取/展示任何 Key 值）

尝试创建隔离虚拟环境并执行 `pip install -r requirements.txt` 时，运行环境无法访问包索引（DNS/network unavailable），因此不能在这里补齐 LangChain / LangGraph / Chroma。

## 尚未验证

以下仍需要在一台可以安装依赖、并由项目方本地配置模型 Key 的环境中执行：

1. Tool Registry 真实加载全部工具；
2. `load_story_knowledge` 的 LangChain Tool 调用；
3. `intl_comm_reply` 的真实模型调用；
4. `plan_china_story_topics`；
5. `/api/posts/generate` 完整生成；
6. `/api/posts/polish` 模型改稿；
7. Gate B 在真实 evidence retrieval 中的阻断；
8. 完整前端点击生成 → pipelineViz → 改稿 → Gate C。

## 重要能力边界

本轮仍未实现真正的 Fact Lock / Fact Drift / Claim Diff / Evidence Conflict Detection。当前 `Revise & Audit` 是流程与 UI 对齐，不等于这些研究能力已经完成。
