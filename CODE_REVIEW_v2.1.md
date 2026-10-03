# ChinaStory Agent v2.1 代码验收报告

## 结论

本轮已完成逐文件 review、静态启动前检查、API/前端契约联调检查，并修复发现的 v2.1 对齐问题。

**当前状态：可作为 GitHub 候选提交版，但真实模型生成的端到端测试仍需要在安装 `requirements.txt` 且配置项目模型 API Key 的环境中执行。**

## 已通过

- Python `compileall`：PASS
- `frontend/js/app.js` Node 语法检查：PASS
- v2.1 静态契约测试：PASS
- 运行代码中的旧 G1–G7 stage ID：未发现
- 前端调用的 API 路径均有后端对应 route
- `META.pipeline_steps`：六阶段
- `META.gates`：Gate A/B/C
- `#pipelineViz`：Stage 与 Gate 分离
- Gate C：已从“仅前端本地变量”修复为后端 `/api/posts/approve` 显式人工批准
- 两个缺失工具：`load_story_knowledge.py`、`intl_comm_reply.py` 已存在
- `detect_content_genre`：复用现有 `tools/genre_router.py`，已加入 enabled tools

## 本轮发现并修复的问题

### P1 — Gate C 原先只是前端本地状态

原实现点击“定稿放行”后只修改浏览器变量，后端没有收到批准动作。这与 v2.1 的 Final Approval Gate 不一致。

已新增：

`POST /api/posts/approve`

返回：
- `approved`
- `gate=C`
- `approver`
- `approved_at`
- `content_sha256`
- `status=APPROVED`
- `published=false`

前端只有后端批准成功后才把 Approve / Gate C 显示为完成。

### P1 — FastAPI 应用版本仍显示旧 0.1.0

已与 META 对齐为：

`0.6.0-v2.1-six-stage`

## 环境限制，不属于仓库代码错误

当前执行环境没有安装 `langchain_core`。因此：
- Tool Registry 的真实 import/load 测试无法完成；
- FastAPI `TestClient` 无法真正 import `api.main`；
- 无法调用真实模型做生成测试。

仓库 `requirements.txt` 已声明 `langchain-core>=0.3.0` 等依赖，所以这是当前验收环境缺依赖，不是本轮代码语法错误。

## 仍未完成 / 不应宣称已完成

### P1 — Revise & Audit 还没有真正的 Fact Lock / Claim Diff

当前 `/api/posts/polish` 通过 prompt 要求模型“不新增事实”，前端在改稿后标记“需事实复核”。

但目前代码还没有真正实现：
- Claim extraction before/after
- New Claim detection
- Claim–Evidence recheck
- Fact Drift detection
- Fact Lock persistence

因此当前状态只能表述为：

> “Revise & Audit 流程位置和 UI 状态已对齐，自动 Fact Lock / Fact Drift 检测待实现。”

不能在 README / 答辩中写成“Fact Lock 已完成”。

### P1 — Gate B 目前仍是基础 Evidence Gate

当前 Gate B 能处理空 evidence / alignment failure 等已有异常，但尚未覆盖完整 v2.1 目标中的：
- 来源冲突自动检测
- New Claim after revision
- Fact Drift
- 完整 Claim–Evidence coverage

这些应作为下一轮 Evidence Audit 实现。

## 建议的本地真实启动验收

安装依赖：

```bash
pip install -r requirements.txt
```

配置项目已有模型环境变量后：

```bash
uvicorn api.main:app --reload
```

浏览器打开：

`http://127.0.0.1:8000`

依次测试：
1. `/api/health`
2. `/api/meta`
3. 主动内容正常生成
4. 无证据 / 不对齐案例触发 Gate B
5. 改稿后 Revise & Audit 状态
6. Gate C 人工批准
7. 评论回复
8. 前端 `#pipelineViz` 是否与 API 返回一致

## 当前推荐提交状态

可以提交本轮 v2.1 对齐代码，但提交说明应明确：

> 六阶段 + Gate A/B/C 的运行态、前端可视化和 Final Approval API 已完成；Fact Lock / Fact Drift / 完整 Evidence Conflict Detection 仍是后续实现项。
