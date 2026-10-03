# ChinaStory Agent

ChinaStory Agent 是一个以证据为基础的国际传播智能体，面向中国文化与中国故事的跨文化内容生产。项目最初基于 AnyClaw Agent 框架改造，当前已发展为面向 ChinaStory 场景的垂类 Agent。

## 1. 项目简介

系统围绕“证据组织—跨文化表达—人机审核”设计，输出人工审核草稿，不自动发布内容。当前主线是主动国际传播内容生产，评论理解与回复属于辅助能力。

## 2. 核心目标

- **Evidence-grounded generation**：让生成内容尽量建立在用户材料与本地证据之上。
- **International / cross-cultural communication**：根据受众、平台和体裁重构中国故事的表达入口。
- **Controllable revision**：为改稿、事实复核和后续 Fact Lock 建立可扩展基础。
- **Human-in-the-loop approval**：通过人工 Gate C 批准最终版本。
- **Evaluation-driven improvement**：逐步接入事实、翻译和 ChinaStory 内容质量评价。

## 3. 六阶段工作流

```text
Define
  → Ground
  → Plan
  → Create
  → Revise & Audit
  → Approve
```

- **Gate A — Task Confirmation**：确认任务对象、目标、体裁、平台和受众。
- **Gate B — Evidence Exception**：在关键证据缺失、不匹配或存在风险时阻断。
- **Gate C — Final Approval**：由人批准最终版本；系统不代表用户发布。

当前代码已提供六阶段与三 Gate 的运行态表示，以及基础 evidence 阻断和 Gate C API。完整持久化状态机仍在开发中。

## 4. 系统架构

```text
User Task
   ↓
Define / Gate A
   ↓
Ground
   ├─ User Materials
   ├─ Vector Retrieval
   ├─ Knowledge Graph / Graph Retrieval（规划中）
   └─ Evidence
   ↓
Gate B
   ↓
Plan
   ↓
Create
   ↓
Revise & Audit
   ↓
Approve / Gate C

Evaluation（持续建设中的独立子系统）
```

Knowledge Graph、Graph Retrieval、Claim Diff、Fact Drift、Fact Lock 等不应从当前架构图解读为已经完成的功能。

## 5. Evidence / Knowledge Layer

- **Evidence**：用户材料和本地知识库中的可核查论据，当前通过 `evidence_used` 进入生成流程。
- **Claim–Evidence–Source**：目标是将文章中的可核查 Claim 绑定到 EvidenceSpan 和 Source；统一绑定模型尚未完成。
- **Vector Retrieval**：当前已有本地 JSON / Chroma 适配和类别、语义检索基础。
- **Knowledge Graph / Graph Retrieval**：属于后续建设方向，不等同于当前 JSON 或 Vector RAG。

当前 Ground 能在没有可用 evidence 或主题明显不匹配时触发基础 Gate B 阻断，但尚未实现完整的 Evidence Pack、冲突检测和逐 Claim 可追溯链路。

## 6. Evaluation Framework

v2.1 采用三个评价部分与人工审核：

1. **Part 1 — Fact / Evidence Evaluation**：关注 Claim–Evidence Coverage、Evidence Entailment、Source Traceability、Evidence Conflict、Fact Drift 和 New Claim。当前仅有基础 evidence 门控，完整实现仍在开发。
2. **Part 2 — External Evaluators**：计划接入 XCOMET / xCOMET-lite 及 glossary / rule-based checks，用于检查错译、漏译、语义损失和错误新增。当前属于 P1 计划。
3. **Part 3 — ChinaStory Evaluation Skill**：关注跨文化可理解性、文化表达质量、受众适配、叙事吸引力、体裁/平台适配和自然度。规范文件已存在，程序化接入与校准仍在进行。

Evaluation → Revision → Re-evaluation 的完整 Revision Loop 尚未实现。

## 7. Dataset / Demo Strategy

当前四层案例承担不同验证任务，不是四个平行的大型文化知识库：

- **苏绣｜Engineering Baseline**：最小工程测试与 Claim–Evidence baseline，优先跑通 Source → EvidenceSpan → Claim → Retrieval → Generation → Traceability。
- **泉州｜Deep Knowledge / Graph Case**：Deep KG、Graph Retrieval、多源 Evidence 和历史事实追溯，在苏绣 baseline 跑通后进入。
- **茶文化｜International Communication Case**：Transcreation、Genre Adaptation 和 Cultural Distance。
- **Conflict Case｜Safety & Revision Case**：Gate B、Revision、New Claim Detection、Fact Drift 和 Fact Lock 的可控失败案例。

执行顺序：

```text
苏绣 baseline
→ 泉州 Deep KG
→ 茶文化 Transcreation
→ Conflict / Fact Lock stress test
```

详见 [Dataset / Demo Strategy](docs/CHINASTORY_DATASET_DEMO_STRATEGY_v1.md)。

## 8. 当前开发状态

### Already available / validated

- v2.1 六阶段 metadata / workflow baseline；
- Gate A / B / C 的基础流程定义；
- FastAPI 服务启动；
- Tool Registry 与 8 个 enabled tools；
- 基础 evidence consumption；
- Gate C 人工批准 API；
- v2.1 contract / static validation；
- `load_story_knowledge`、`detect_content_genre`、`intl_comm_reply` 等工具。

### Still under development

- 统一 backend core schema / state；
- 可执行且持久化的 Gate state machine；
- 完整 Claim–Evidence–Source binding；
- ContentVersion；
- Claim Diff；
- New Claim Detection；
- Evidence Recheck；
- Fact Drift；
- Fact Lock；
- Evaluation Integration；
- Revision Loop；
- 完整 Human Review / Audit state；
- 更深的 Knowledge Graph integration；
- 尚未验证的 full model E2E。

因此，项目当前不能表述为“SPEC v2.1 已完整实现”。

## 9. 项目结构

```text
api/          FastAPI 入口、请求 schema、REST routes
agent/        ReAct Agent 与工具调用封装
tools/        内容生成、知识加载、体裁识别、回复和 evidence 工具
utils/        Tool/Skill registry、路径、会话与配置辅助
config/       tools、skills、model 等配置
model/        模型工厂
prompt/       生成与回复 prompt 模板
skills/       ChinaStory 主 Skill 与体裁分册
knowledge/    写作知识、样例、本地 evidence 与知识材料
eval/         Evaluation Pipeline、Rubric 与 Skill 规范
frontend/     当前 Web 工作台
docs/         项目规范、运行验收、数据集策略和研究文档
tests/        v2.1 契约测试
scripts/      Chroma 构建和其他运行脚本
archive/      历史规范与归档材料
```

## 10. 快速开始

### 创建环境并安装依赖

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### 配置模型

模型配置位于 [config/model.yaml](config/model.yaml)。按该文件指定的环境变量名称，在本地创建 `.env` 并填入合法模型配置。不要把真实 API Key、token 或 secret 写入 README、代码或 Git。

当前没有模型配置时，仍可启动健康检查、元数据和部分不依赖模型的接口；生成、回复和润色的完整 E2E 需要合法模型配置。

### 启动 API

```powershell
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

检查：

```powershell
Invoke-WebRequest http://127.0.0.1:8000/api/health
Invoke-WebRequest http://127.0.0.1:8000/api/meta
```

本地 evidence / Chroma 构建说明见 [knowledge/diplomacy/CHROMA.md](knowledge/diplomacy/CHROMA.md)。

## 11. 关键文档

- [项目总 SPEC v2.1](SPEC-国际传播智能体_v2.1_现阶段统一规范.md)
- [AGENT.md](AGENT.md)
- [Dataset / Demo Strategy](docs/CHINASTORY_DATASET_DEMO_STRATEGY_v1.md)
- [Code Alignment v2.1](CODE_ALIGNMENT_v2.1.md)
- [Code Review v2.1](CODE_REVIEW_v2.1.md)
- [Runtime Validation v2.1](RUNTIME_VALIDATION_v2.1.md)
- [Evaluation Pipeline Spec](eval/CHINASTORY_EVALUATION_PIPELINE_SPEC_v1.2_CN.md)
- [Content Quality Rubric](eval/CHINASTORY_CONTENT_QUALITY_RUBRIC_v2.1.md)
- [Evaluation Skill Spec](eval/CHINASTORY_EVALUATION_SKILL_SPEC_v1.1.md)

## 12. Roadmap

- **Done**：六阶段与 Gate A/B/C 基础运行态、FastAPI 启动、Tool Registry、基础 evidence 消费、Gate C API、v2.1 契约验证。
- **In Progress**：苏绣 Evidence baseline、统一后端状态契约、Evidence Pack、Claim–Evidence–Source 绑定、完整 Gate 行为、真实模型 E2E。
- **Planned**：泉州 Deep KG、Graph Retrieval、茶文化 Transcreation 与 Genre Adaptation、Conflict / Fact Lock stress test、Evaluation Integration、Revision Loop 和更完整 Audit Trail。

## 13. 项目来源与致谢

ChinaStory Agent 是在 AnyClaw Agent 框架基础上进行领域化改造和扩展的项目。AnyClaw 提供了 Agent、工具注册、模型接入和 CLI 等基础框架能力；ChinaStory 的 evidence-grounded workflow、国际传播 Skill、内容门控与评价方向属于本项目的领域化建设。

许可证与署名要求以 [LICENSE.txt](LICENSE.txt) 为准。本次 README 重写未修改许可证文件。
