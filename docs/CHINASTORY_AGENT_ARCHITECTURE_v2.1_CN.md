# ChinaStory Agent v2.1 完整架构（含 Evaluation 三层体系）

> **文档定位**：本文件用于统一 ChinaStory Agent
> 当前阶段的系统架构认知，并把 Evaluation
> 三层体系正式嵌入六阶段主流程。\
> **当前基线**：`Define → Ground → Plan → Create → Revise & Audit → Approve`，三个人工/异常门控为
> Gate A / B / C。\
> **重要说明**：本图是目标架构与当前开发基线的统一视图；其中部分模块仍处于开发中或规划阶段，不能据此宣称
> SPEC v2.1 已全部实现。

------------------------------------------------------------------------

## 1. 一张图看完整 Agent

``` text
ChinaStory Agent v2.1
│
├─ ① DEFINE｜定义任务
│   │
│   ├─ Topic / Goal / Genre / Platform / Audience
│   ├─ User Material
│   └─ TaskContext（任务上下文）
│          ↓
│      Gate A｜Task Confirmation
│      任务确认：做什么、给谁看、在哪个平台、有什么约束
│
├─ ② GROUND｜建立事实基础（知识图谱）
│   │
│   ├─ User Materials｜用户资料
│   ├─ Vector Retrieval / RAG｜向量检索
│   ├─ Knowledge Graph / Graph Retrieval｜知识图谱 / 图检索
│   └─ Multi-source Evidence｜多来源证据
│          ↓
│      Evidence Pack
│          ↓
│      Claim ── evidence_refs 证据引用──> EvidenceSpan证据片段 ──> Source
│          ↓
│      Sufficiency充分性审查 / Conflict 冲突性审查/ Traceability Check可追溯性审查
│          ↓
│      Gate B｜Evidence Exception
│      证据异常：缺证据、来源冲突、不可追溯、改稿新增事实等
│
├─ ③ PLAN｜跨文化表达规划
│   │
│   ├─ Audience Profile｜受众画像
│   ├─ Cultural Context / Cultural Distance｜文化语境 / 文化距离
│   ├─ Narrative Strategy｜叙事策略
│   ├─ Genre Strategy｜体裁策略
│   └─ Platform Strategy｜平台策略
│          ↓
│      Content / Narrative Plan（生成一个内容/故事计划）
│
├─ ④ CREATE｜内容生产
│   │
│   ├─ Evidence-grounded Generation｜证据约束生成
│   ├─ Chinese Content Master｜中文母稿
│   ├─ Transcreation｜跨文化再创作
│   └─ Genre / Platform Adaptation｜体裁与平台适配
│          ↓
│      ContentVersion V1 第一版生成（生成后进行评价）
│          ↓
│      ┌─────────────────────────────────────────────┐
│      │ EVALUATION｜分层评价                       │
│      │                                             │
│      │ Part 1｜Fact / Evidence Evaluation          │
│      │ 事实与证据有没有问题？                      │
│      │ - Claim–Evidence Coverage                   │
│      │ - Evidence Entailment / Sufficiency         │
│      │ - Source Traceability                       │
│      │ - Evidence Conflict                         │
│      │ - New Claim / Fact Drift / Fact Lock 检查   │
│      │                                             │
│      │                 ↓                           │
│      │                                             │
│      │ Part 2｜External Evaluators （已有skill接入）                │
│      │ 跨语言转化有没有“转错”？                    │
│      │ - XCOMET / xCOMET-lite（P1 接入）           │
│      │ - Glossary / Rule-based Checks（P1）        │
│      │ - 错译 / 漏译 / 语义损失 / 错误新增 / span  │
│      │                                             │
│      │                 ↓                           │
│      │                                             │
│      │ Part 3｜ChinaStory Evaluation Skill（自有评价skill，搭配评价维度表rubric）         │
│      │ 有没有“转好、写好”？                        │
│      │ - 跨文化可理解性                            │
│      │ - 文化表达质量                              │
│      │ - Audience Fit｜受众适配                    │
│      │ - Narrative Engagement｜叙事吸引潜力        │
│      │ - Genre / Platform Fit｜体裁/平台适配        │
│      │ - Naturalness｜自然度 / 非口号化             │
│      └─────────────────────────────────────────────┘
│          ↓
│      EvaluationResult
│          ↓
│      RevisionInstruction（如需修改）
│
├─ ⑤ REVISE & AUDIT｜修改与审计
│   │
│   ├─ V1 → Revision → V2
│   ├─ Claim Diff｜前后事实主张差异
│   ├─ New Claim Detection｜新增事实检测
│   ├─ Evidence Recheck｜证据重新核验
│   ├─ Fact Drift｜事实漂移检测
│   ├─ Fact Lock｜已核验事实锁定
│   ├─ 必要时重新进入 Gate B
│   └─ Re-evaluation｜重新评价
│          │
│          └──── 不满足要求 → Revision Loop → 新版本 → 再评价
│
└─ ⑥ APPROVE｜最终人工审核
    │
    ├─ Review State / Unresolved Warnings
    ├─ ContentVersion + Evidence + Evaluation 关联
    └─ Gate C｜Final Approval
           ↓
       APPROVED
           ↓
       Story Package / Delivery
       （Agent 不自动公开发布）
```

------------------------------------------------------------------------

## 2. Evaluation 在六阶段中的准确位置

Evaluation **不是第七个独立主阶段**，而是贯穿
`Create → Revise & Audit → Approve` 的质量控制子系统。

``` text
Create
  ↓
ContentVersion V1
  ↓
Evaluation
  ├─ Part 1：事实 / 证据
  ├─ Part 2：跨语言外部评估器
  └─ Part 3：ChinaStory 内容质量评价
  ↓
EvaluationResult
  ↓
是否需要 Revision（修订）？
  ├─ 否 → Ready for Human Review
  └─ 是
       ↓
Revise & Audit
       ↓
V2
       ↓
Claim Diff / New Claim / Evidence Recheck / Fact Lock
       ↓
Re-evaluation
       ↓
Gate C / Human Review
```

### 2.1 Part 1｜Fact / Evidence Evaluation

核心问题：**"事实和证据有没有问题？"**

它与 Ground、Gate B、Revise & Audit 强关联，重点包括：

-   Claim 是否有证据支持；
-   Evidence 是否足够、是否真正蕴含 Claim；
-   Source 是否可追溯；
-   多来源是否冲突；
-   改稿后是否出现 New Claim；
-   已核验事实是否发生 Fact Drift；
-   Fact Lock 是否被破坏；
-   出现异常时是否应重新进入 Gate B。

**产品定位**：P0 核心运行能力，不只是研究阶段离线评测。

### 2.2 Part 2｜External Evaluators

核心问题：**"跨语言转化有没有转错？"**

第一阶段计划接入：

-   XCOMET / xCOMET-lite；
-   glossary / rule-based checks。

主要检查：

-   错译；
-   漏译；
-   语义损失；
-   不应出现的事实新增；
-   可疑错误 span。

**产品定位**：P1 增强项；不阻塞当前 C-P0 后端开发。

### 2.3 Part 3｜ChinaStory Evaluation Skill

核心问题：**"即使事实和翻译没错，这个内容有没有真正转好、写好？"**

评价维度包括：

-   跨文化可理解性；
-   文化表达质量；
-   受众适配；
-   叙事吸引潜力；
-   Genre / Platform Fit；
-   Naturalness / 非口号化。

**产品定位**：基础版属于 P0 Evaluation Integration；Rubric
的多人盲评、Human--AI Judge Calibration
等属于研究校准，不是每次产品生成都执行。

------------------------------------------------------------------------

## 3. Fact Lock 与 Evaluation 的关系

Fact Lock 不是一套独立的第四种
Evaluation，也不是"评价完成后的最后一步"。

它是 **Revise & Audit 中的事实稳定机制**，同时由 Part 1 负责检查其状态。

``` text
V1
 ↓
事实 / 证据核验
 ↓
建立已核验事实集合（Fact Lock）
 ↓
Revision
 ↓
V2
 ↓
Claim Diff
 ↓
New Claim？
Fact Drift？
Fact Lock 被破坏？
 ↓
Evidence Recheck
 ↓
必要时 Gate B
 ↓
重新评价
```

允许修改：语言、结构、语气、叙事方式、跨文化表达。\
不能未经核验修改：年份、数字、人物事实、历史判断、关键事实关系等。

------------------------------------------------------------------------

## 4. Knowledge Graph（KG）在架构中的位置

KG = **Knowledge Graph，知识图谱**。

它主要属于 `Ground` 的知识组织与检索层，不是 Evaluation 本身。

``` text
Source / Evidence
      ↓
Entity ── Relation ── Entity
      ↓
Knowledge Graph
      ↓
Graph Retrieval
      ↓
Evidence Pack
      ↓
Claim–Evidence–Source
      ↓
Gate B / Create / Evidence Recheck
```

与 Vector RAG 的区别：

-   Vector RAG：主要按语义相似度寻找相关文本；
-   Graph Retrieval：沿实体---关系路径组织和寻找事实；
-   两者最终都应适配为统一 Evidence Pack，供 Agent 后端消费。




中文易懂demo分工（中期之前）：

苏绣：“我说的这句话，有没有依据？”（最小工程测试 + Claim--Evidence baseline；）

泉州：“这么多人物、地点、年代、事件之间，到底是什么关系？”（Deep KG + Graph Retrieval + 多来源 Evidence +历史事实追踪；）

茶文化：“事实都对，但怎么讲外国人才容易理解？”（国际传播 + Transcreation + Genre + Cultural Distance；）

Conflict Case:“文章改了以后，原来正确的事实有没有被改坏？”(Gate B + Revision + New Claim + Fact Drift + Fact Lock。)

------------------------------------------------------------------------

## 5. 用户访谈如何反哺 Agent

用户访谈不是用来"证明 KG 或 Fact Lock
一定正确"，而是用来校正真实用户工作流和人工介入点。

``` text
访谈发现
  ↓
真实任务流程 / 痛点 / 人工审核节点
  ↓
Agent 设计调整
  ├─ Define / Gate A：用户实际需要确认什么？
  ├─ Ground / Gate B：什么事实风险最值得阻断？
  ├─ Plan：真实用户怎样考虑受众、平台和文化距离？
  ├─ Revise & Audit：用户最常改什么、最怕改坏什么？
  ├─ Evaluation：用户认为哪些质量问题最重要？
  └─ Approve / Gate C：哪些内容必须人工最终确认？
```

原则：**访谈发现问题，实验验证方案。**

------------------------------------------------------------------------

## 6. B 与 C 的系统边界

### B｜Knowledge / Evidence Layer

主要负责：

-   数据集与语料；
-   Source / Evidence；
-   Vector Retrieval；
-   Knowledge Graph；
-   Graph Retrieval；
-   多来源 Evidence；
-   Evidence Conflict / Sufficiency 等知识层信号。

### C｜Agent / Backend / Evaluation Integration

主要负责：

-   六阶段 Agent Workflow；
-   Gate A / B / C；
-   核心 Schema 与状态；
-   Claim--Evidence--Source 的后端消费契约；
-   ContentVersion；
-   Claim Diff / New Claim / Evidence Recheck；
-   Fact Drift / Fact Lock；
-   Evaluation Integration；
-   Revision Loop；
-   Human Review / Audit API。

### B/C 汇合接口

``` text
B：Knowledge / Retrieval
        ↓
统一 EvidencePack / Source / EvidenceSpan
        ↓
C：Agent Backend
        ↓
Claim Binding / Gate B / Create / Recheck / Evaluation
```

------------------------------------------------------------------------

## 7. 当前实现状态与目标状态

### 已完成 / 已验证的基线

-   v2.1 六阶段名称与基础流程对齐；
-   Gate A / B / C 基线；
-   FastAPI 服务可启动；
-   Tool Registry 可加载；
-   基础 evidence 消费；
-   Gate C approval API；
-   v2.1 静态契约测试；
-   GitHub v2.1 baseline 已建立。

### C 侧仍需开发

-   统一核心 Schema / 状态；
-   可执行、可持久化的 Gate 状态机；
-   完整 Claim--Evidence--Source binding；
-   ContentVersion / Revision state；
-   Claim Diff；
-   New Claim Detection；
-   Evidence Recheck；
-   Fact Drift；
-   Fact Lock；
-   Part 1 / Part 3 Evaluation Integration；（评价集成）
-   Revision Loop；
-   Human Review / Audit Trail。

### B / 共同后续

-   稳定 Evidence Pack 接口；
-   Chroma / Vector Retrieval 数据链；
-   泉州 Deep KG / Graph Retrieval；
-   多来源证据与冲突状态；
-   C 侧 Evidence Recheck 的统一检索适配层。

------------------------------------------------------------------------

## 8. 推荐的工程实现顺序

``` text
v2.1 Baseline
   ↓
C-P0.1 统一核心 Schema
   ↓
C-P0.2 六阶段 + Gate 状态机
   ↓
C-P0.3 Claim–Evidence–Source Binding
   ↓
C-P0.4 Revision / ContentVersion
   ↓
C-P0.5 Fact Safety
   ├─ Claim Diff
   ├─ New Claim Detection
   ├─ Evidence Recheck
   ├─ Fact Drift
   └─ Fact Lock
   ↓
C-P0.6 Evaluation Integration
   ├─ Part 1 Fact / Evidence
   └─ Part 3 ChinaStory Evaluation Skill
   ↓
C-P0.7 Revision Loop
   ↓
C-P0.8 Gate C / Human Review / Audit
   ↓
P1
   └─ Part 2 External Evaluators
      ├─ XCOMET / xCOMET-lite
      └─ Glossary / Rule-based Checks
```

------------------------------------------------------------------------

## 9. 一句话版本

> **ChinaStory Agent v2.1 = 任务定义 + 证据/KG Grounding + 跨文化规划 +
> Content Master/Transcreation + 三层 Evaluation + Revision & Fact
> Safety + 人工最终批准。**

其中 Evaluation 严格保持：

> **Part 1：事实和证据有没有问题；Part 2：有没有转错；Part
> 3：有没有转好、写好。**
