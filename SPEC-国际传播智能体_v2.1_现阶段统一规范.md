# ChinaStory Agent 现阶段统一 SPEC v2.1

> **文档定位**：ChinaStory Agent 项目总规范（现阶段开发 / 研究基线）  
> **替代对象**：仓库根目录旧版 `SPEC-国际传播智能体.md`  
> **状态**：Working Baseline（仍需由用户访谈、原型测试和对照实验继续校准）  
> **原则**：立项约束项目边界；已有代码是现实起点；团队研究设想形成技术方案；老师 PRD 作为 Design Reference；用户研究发现问题；实验验证方案。

---

## 0. 为什么需要替换旧 SPEC

旧版 SPEC 形成于项目较早阶段，重点偏向“评论理解与回复”。现阶段 ChinaStory Agent 的主线已经调整为：

> **主动国际传播内容生产为主，评论理解与回应为辅。**

项目也不再以“调用大模型生成一篇英文内容”为核心，而是研究一套：

> **证据约束 + 知识组织 + 跨文化再创作 + 人机门控 + 分层评价**

的国际传播内容生产方法。

因此，本 SPEC 不再沿用早期以评论回复、单次 RAG 和单次生成为中心的流程，而以当前研究问题和 MVP 为准。

---

# 1. 项目定位

ChinaStory Agent 是一个面向中国故事国际传播任务的、**证据约束的人机协同内容生产与评价系统**。

系统目标不是代替专业人员自动发布内容，而是帮助用户完成：

1. 定义传播任务；
2. 组织用户资料与知识库证据；
3. 建立可追溯的 Claim–Evidence–Source 关系；
4. 发现关键事实缺证据与来源冲突；
5. 根据受众、文化语境和传播任务规划表达；
6. 形成中文 Content Master；
7. 完成目标语 Transcreation，而非机械翻译；
8. 对生成内容进行事实、跨语言和跨文化质量评价；
9. 在修改过程中保持已核验事实稳定；
10. 由人完成最终审核与批准。

最终目标不是证明：

> “AI 可以写中国故事。”

而是研究并验证：

> **知识图谱增强的证据检索、Claim–Evidence 可追溯、人机门控、Fact Lock、跨文化内容 Skill 与分层 Evaluation，是否能够相较 Direct LLM / 普通 Vector RAG，提高内容的事实可靠性、可追溯性、跨文化适配性和人工审核效率。**

---

# 2. 项目需求与设计依据

项目设计遵循以下层级，避免把老师 PRD 直接等同于项目任务清单。

## 2.1 立项书：最高项目约束

立项中已经承诺的议题知识管理、主动内容生产、平台适配、评论理解与回应、评价等方向构成项目边界。

这些内容不能仅因为少量访谈对象没有主动提到就直接删除。

## 2.2 已有代码与成果：现实起点

当前已有系统能力包括本地知识库、Chroma / Vector RAG、用户资料、生成流程、部分 Skill、前端和既有评价材料。

已有实现应被视为项目起点，而不是最终研究成果。

尤其需要明确：

> `JSON / Chroma / Vector RAG ≠ 已完成 Knowledge Graph / Graph RAG`

真正的 Knowledge Graph 仍需要实体、关系、来源、图查询及其参与检索/生成的闭环。

## 2.3 团队研究设想：核心技术方案来源

当前重点研究设想包括：

- Knowledge Graph / Graph RAG；
- Claim–Evidence–Source；
- Evidence Conflict Detection；
- Evidence Gate；
- Fact Lock / Fact Drift；
- Cross-cultural Planning；
- Transcreation；
- ChinaStory Evaluation；
- Human-in-the-loop Gate。

这些不能只因为“看起来合理”就宣布有效，需要通过实验验证。

## 2.4 老师 PRD：Design Reference

老师 PRD 用于帮助项目完善：

- evidence-first；
- 可追溯；
- 受众建模；
- 文化语境；
- Narrative Planning；
- Transcreation；
- 风险控制；
- Human Approval；
- Audit Trail。

项目可以吸收其中结构化思想，但不应表述为“照着 PRD 实现”。

## 2.5 用户研究：发现真实问题

用户研究用于回答：

- 谁是真实用户；
- 真实工作流程是什么；
- 哪些环节最耗时或最痛；
- AI 当前在哪里出问题；
- 哪些环节实际需要人工判断。

原则：

> **访谈发现问题，实验验证方案。**

## 2.6 对照实验：验证技术方案

Graph RAG、Narrative Strategy、Evidence Gate、Fact Lock 等是否有效，应由原型和实验决定，而不是由少量访谈者投票决定。

---

# 3. Primary User（当前假设）

现阶段暂定 Primary User：

> **高校中承担中国文化国际传播内容生产与研究任务的师生团队。**

这是当前研究假设，不写成已经验证的最终用户定义。

后续通过 5–8 次半结构访谈重点验证：

- 目标用户是否成立；
- AS-IS 工作流；
- 三个左右核心痛点；
- 人工复核节点；
- 当前工具缺口。

访谈不要求受访者评价 Knowledge Graph、Fact Lock、Gate、G1–G7 等内部技术方案。

---

# 4. Context Model

为避免把所有信息混成一个“大 Profile”，系统区分三类上下文。

## 4.1 Stable Profile

相对稳定、可跨任务复用的信息，例如：

- 用户/团队角色；
- 常用语言；
- 长期传播对象；
- 常用平台；
- 固定表达规范；
- 审核偏好。

## 4.2 Task Context

本次任务才成立的信息，例如：

- Topic；
- Goal；
- Genre；
- Platform；
- Target Audience；
- Desired Depth；
- Length / Format；
- Deadline / Campaign Context。

## 4.3 Dynamic Evidence

必须随任务检索、更新和核验的信息，例如：

- 用户上传资料；
- 本地知识库材料；
- Knowledge Graph 子图；
- 来源；
- EvidenceSpan；
- 时间敏感事实；
- 冲突信息。

系统不能因为 Stable Profile 中曾经出现过某个事实，就默认其在新任务中仍然有效。

---

# 5. ChinaStory Agent V1 主流程

当前主流程统一压缩为六个阶段：

```text
Define
  ↓
Ground
  ↓
Plan
  ↓
Create
  ↓
Revise & Audit
  ↓
Approve
```

---

## 5.1 Define｜定义任务

输入：

- Topic
- Goal
- Genre
- Platform
- Audience / Audience Profile
- 用户本次提供的材料

系统只要求确认真正影响本次任务的变量，避免重复询问稳定信息。

输出：

```text
Task Context
```

并进入 **Gate A：Task Confirmation**。

---

## 5.2 Ground｜建立事实基础

数据来源至少包括：

```text
用户资料
   +
本地知识库 / Vector RAG
   +
Knowledge Graph / Graph Retrieval
```

检索结果不能只作为 prompt context，而应尽量组织成：

```text
Claim
  ↓ supported_by
EvidenceSpan
  ↓ comes_from
Source
```

Ground 阶段主要完成：

- Entity / Relation Retrieval；
- Vector Retrieval；
- Graph Retrieval；
- Claim Extraction；
- Evidence Mapping；
- Source Traceability；
- Evidence Conflict Detection；
- Evidence Sufficiency 判断。

输出：

```text
Evidence Pack
+
Claim–Evidence–Source Map
+
Conflict / Missing Evidence Report
```

---

# 6. Knowledge Graph 与 Graph RAG

## 6.1 当前目标

项目不追求建设“全中国文化知识图谱”。

MVP 优先选择少量深案例，例如：

- 苏绣；
- 鲁菜；
- 一个冲突资料案例。

知识图谱至少表达：

```text
Entity
Relation
Attribute
Source
Time / Version（需要时）
```

候选关系可包括：

```text
CulturalElement → practiced_by → Practitioner
CulturalElement → located_in → Place
CulturalElement → uses → Material
CulturalElement → requires → Technique
Claim → supported_by → EvidenceSpan
EvidenceSpan → comes_from → Source
```

## 6.2 Graph RAG 的研究定位

Graph RAG 不是因为“知识图谱更高级”而加入。

需要通过实验回答：

> 相较 Vector RAG，Graph RAG 是否改善相关证据检索、关系型信息组织、可追溯性或最终生成质量？

因此至少保留：

```text
Direct LLM
vs
Vector RAG
vs
Graph RAG
```

的对照条件。

---

# 7. Claim–Evidence–Source 与 Evidence Conflict

## 7.1 Claim–Evidence

最终生成内容中的可核查 Claim 应尽可能回溯到 Evidence 与 Source。

前端/审计层最终希望能够展示：

```text
最终文章中的一句话
        ↓
Claim
        ↓
EvidenceSpan
        ↓
Source
```

而不是只在文章末尾显示：

```text
Sources: 1, 2, 3
```

## 7.2 Evidence Conflict

用户资料与知识库材料不能简单合并后交给 LLM 自行判断。

至少检测：

- 数字冲突；
- 时间冲突；
- 人物身份/职务冲突；
- 新旧资料冲突；
- 关键事实表述冲突；
- 来源观点差异。

关键冲突应形成结构化状态：

```text
Evidence Conflict
→ 暂停
→ Human Decision
→ 记录处理结果
→ 继续
```

---

# 8. Human Gates 与自动化边界

旧方案中的 G1–G7 不再全部作为硬门。

MVP 只保留三个核心 Gate。

## Gate A｜Task Confirmation

确认：

> 为谁、为什么任务、生产什么内容。

## Gate B｜Evidence Exception

只有出现关键风险时阻断，例如：

- 关键 Claim 缺证据；
- 关键来源不可追溯；
- 来源严重冲突；
- 改稿新增未经支持的事实；
- 已核验事实发生 Fact Drift。

## Gate C｜Final Approval

任何对外最终版本必须由人批准。

其他环节默认采用：

> **系统自动执行 + 用户可查看 / 修改**

避免 Agent 变成连续确认页面。

---

# 9. Risk Policy v0.1

当前 Green / Yellow / Red 只作为工程风险策略，不宣称已经由用户研究验证。

## Green

不改变事实的低风险变化，例如：

- 格式；
- 长度；
- 措辞；
- 平台排版；
- 非事实性语气调整。

处理：

> 自动继续。

## Yellow

例如：

- 低风险歧义；
- 文化解释可能不足；
- 可改善的受众适配问题。

处理：

> 提醒 / 建议，但默认不阻断。

## Red

例如：

- 关键事实冲突；
- 无依据的重要 Claim；
- 改稿新增事实；
- Fact Lock 被破坏。

处理：

> 阻断并进入人工处理。

阈值后续通过实验和真实任务校准。

---

# 10. Plan｜跨文化表达规划

Plan 阶段暂时合并原先可能拆开的：

- Audience Brief；
- Cultural Context；
- Cultural Distance；
- Narrative Angles；
- Story Blueprint；
- Narrative Strategy。

MVP 不要求把这些全部做成独立页面或独立 Gate。

输入：

```text
Task Context
+
Audience Profile
+
Evidence Pack
```

输出：

```text
Content / Narrative Plan
```

其中 Audience Profile 尽量使用可观察变量，而不是国籍刻板印象，例如：

- language；
- prior knowledge；
- likely unknown terms；
- available cultural anchors；
- platform / content environment；
- desired depth。

Narrative Angles 是否值得作为显式模块，后续通过 ON/OFF 实验验证。

---

# 11. Create｜Content Master 与 Transcreation

当前推荐：

```text
Evidence-grounded Planning
        ↓
Chinese Content Master
        ↓
Transcreation
        ↓
Genre / Platform Adaptation
```

## 11.1 Chinese Content Master

中文母稿承担：

- 核心事实稳定；
- 证据映射；
- 文化语境完整；
- 主要叙事结构。

## 11.2 Transcreation

目标语生成不等于逐句翻译。

Transcreation 可以调整：

- 认知入口；
- 信息顺序；
- 解释方式；
- 叙事结构；
- 文化桥接；
- 平台表达。

但不能擅自改变已核验事实。

必要时使用 Cultural Glossary / Terminology Rules 保持术语一致。

---

# 12. Revise & Audit｜修改与事实稳定

多轮改稿是重点风险。

第一版通过事实审核后建立：

```text
Fact Lock
```

允许修改：

- 结构；
- 长度；
- 语言；
- 语气；
- 叙事方式；
- 平台风格。

不允许未经核验：

- 新增年份；
- 新增数字；
- 新增人物事实；
- 新增历史判断；
- 改变已经确认的关键事实。

若产生 New Claim：

```text
New Claim
   ↓
Evidence Retrieval
   ↓
Claim–Evidence Check
   ↓
重新进入 Evidence Gate
```

系统应保存版本差异和审计记录。

---

# 13. Evaluation Framework

Evaluation 不再采用“所有指标加权成一个总分”的单层方案。

现阶段统一为三个评价 Part + Human Review。

```text
Generated / Transcreated Content
        ↓
Part 1 Fact / Evidence Gate
        ↓
Part 2 External Evaluators
        ↓
Part 3 ChinaStory Evaluation Skill
        ↓
Evaluation Report
        ↓
Revision
        ↓
Re-evaluation
        ↓
Human Review
```

详细执行规则由独立文件：

```text
eval/CHINASTORY_EVALUATION_PIPELINE_SPEC_v1.2_CN.md
```

定义。

## 13.1 Part 1｜Fact / Evidence

回答：

> **事实和证据有没有不可接受的问题？**

包括：

- Claim–Evidence Coverage；
- Evidence Entailment；
- Source Traceability；
- Evidence Conflict；
- Fact Drift；
- New Claim；
- Fact Lock。

严重问题属于 Hard Gate，不能被“故事有趣”抵消。

## 13.2 Part 2｜External Evaluators

重点比较：

```text
Chinese Content Master
↔
Target-language Transcreation
```

回答：

> **有没有转错？**

第一阶段优先研究/接入：

- XCOMET / xCOMET-lite；
- glossary / rule-based checks。

主要检查：

- 语义损失；
- 错译；
- 漏译；
- 错误新增；
- 可疑 span。

Part 2 不负责判断跨文化传播作品是否“写得好”。

## 13.3 Part 3｜ChinaStory Evaluation Skill

回答：

> **即使没有明显事实或翻译错误，它有没有转好、写好？**

当前核心维度：

1. Cross-cultural Comprehensibility
2. Cultural Expression Quality
3. Audience Fit
4. Narrative Engagement Potential
5. Genre & Platform Fit
6. Naturalness / Non-sloganeering

Part 3 使用独立：

```text
CHINASTORY_CONTENT_QUALITY_RUBRIC_v2.x
```

定义“评什么”，并由：

```text
CHINASTORY_EVALUATION_SKILL_SPEC_v1.x
```

定义程序“怎么评”。

## 13.4 Human / Real Audience

自动 Judge 只能评价潜在内容质量。

真实传播效果必须通过目标受众验证，例如：

- 核心概念理解；
- 可信度；
- 兴趣 / 继续了解意愿；
- 理解难度 / 文化距离；
- 记忆。

最终发布批准始终由人完成。

---

# 14. Rubric 的研究与版本迭代

当前 Rubric 不是最终真理。

推荐版本链：

```text
专家 / 用户研究
   ↓
内容效度
   ↓
Rubric v2.1
   ↓
多人盲评
   ↓
评分者一致性
   ↓
Rubric v2.2
   ↓
单变量退化 / 故障注入
   ↓
诊断能力
   ↓
Rubric v2.3
   ↓
Human–AI Judge Calibration
   ↓
Evaluation Skill
   ↓
真实目标受众验证
   ↓
Rubric v3
```

旧版 ROC 权重保留为历史研究依据，但当前不以重新优化总权重为首要目标。

---

# 15. Approve｜最终人工责任

最终状态至少区分：

```text
Draft
→ Evidence Checked
→ Revising
→ Review
→ Approved
```

系统应记录：

- content_version；
- 谁批准；
- 批准时间；
- 使用的 evidence；
- evaluation result；
- 修改记录；
- unresolved warning。

Agent 不能自行把 `READY_FOR_HUMAN_REVIEW` 等同于公开发布。

---

# 16. 评论理解与回复

评论理解与回应仍属于项目立项范围，但现阶段不再作为主线创新中心。

定位调整为：

> **主动内容生产主流程的辅助能力。**

可以继续保留：

- 评论语义理解；
- 风险识别；
- 基于证据的回应；
- 回复生成；
- 人工审核。

但中期优先级低于：

- Graph RAG；
- Claim–Evidence；
- Evidence Gate；
- Fact Lock；
- Transcreation；
- Evaluation；
- Human Approval。

---

# 17. 当前实现状态 vs 目标状态

为了避免 SPEC 把“计划实现”写成“已经实现”，必须区分状态。

| 能力 | 当前定位 |
|---|---|
| 本地知识库 / JSON / Chroma | 已有基础 |
| Vector RAG | 已有基础，继续整理 |
| 用户资料输入 | 已有基础 |
| 主动内容生成 | 已有基础，需重构流程 |
| 评论回复 | 已有能力，降为辅助主线 |
| Knowledge Graph Schema | 设计 / 建设中 |
| 真正 Graph Retrieval / Graph RAG | 待形成完整闭环 |
| Claim–Evidence–Source | 核心 MVP 能力，需落地 |
| Evidence Conflict | 核心 MVP 能力，需落地 |
| 三 Gate 状态机 | 需工程化 |
| Fact Lock / Fact Drift | 需实现并实验 |
| Content Master → Transcreation | 需规范化 |
| Part 2 External Evaluator | P1 接入 |
| ChinaStory Evaluation Skill | 设计 / 校准中 |
| Real Audience Validation | 后续实验 |
| 全链路 Audit Trail | 逐步实现 |

任何 README、答辩或论文描述都应遵守该边界。

---

# 18. MVP 优先级

## P0｜必须形成闭环

1. Define → Ground → Plan → Create → Revise & Audit → Approve 六阶段主流程；
2. 至少一个真实文化主题的 Evidence Pack；
3. Claim–Evidence–Source 可追溯；
4. Evidence Conflict / Unsupported Claim 阻断案例；
5. 三个核心 Gate；
6. Chinese Content Master → Transcreation；
7. Fact Lock + 改稿后的 Claim Recheck；
8. Part 1 + Part 3 基础 Evaluation；
9. Human Approval；
10. 前端可展示证据、版本、问题和审批过程。

## P1｜研究增强

1. 小型真实 Knowledge Graph；
2. Graph RAG；
3. XCOMET / xCOMET-lite；
4. Rubric 人工校准；
5. 单变量退化实验；
6. Direct LLM / Vector RAG / Graph RAG 对照。

## P2｜后续扩展

1. 真实目标受众实验；
2. 更多题材知识图谱；
3. 更多 External Evaluators；
4. 评论模块进一步整合；
5. 更完整平台适配与自动化。

---

# 19. 用户研究计划

用户研究目标不是让受访者设计 Agent。

计划：

- 明确主要用户；
- 完成约 5–8 次半结构访谈 / 任务观察；
- 提炼约 3 个核心痛点；
- 形成真实 AS-IS Workflow；
- 标记人工判断节点；
- 记录当前 AI / 工具失效案例。

访谈优先围绕：

```text
相关经历
→ 实际流程
→ 已有 / 需重查信息
→ 资料 / 事实 / AI 问题
→ 跨文化表达
→ 初稿修改与人工复核
→ 现有工具缺口
→ 核心问题优先级
```

访谈结果用于调整产品优先级和交互，而不是直接证明 Graph RAG、Fact Lock 或某个 Gate 有效。

---

# 20. 核心实验

## 20.1 Retrieval / Generation Baseline

```text
Direct LLM
vs
Vector RAG
vs
Graph RAG
```

观察：

- unsupported claims；
- evidence coverage；
- source traceability；
- retrieval relevance；
- 人工核验成本；
- 内容质量。

## 20.2 Evidence Gate Ablation

```text
No Gate
vs
Evidence Gate
```

观察事实错误与人工审核成本。

## 20.3 Fact Lock Experiment

```text
普通改稿
vs
Fact-Locked Revision
```

观察：

- new unsupported claims；
- fact drift；
- revision quality。

## 20.4 Narrative Strategy Experiment

如 Narrative Angles 被实现：

```text
Narrative Strategy OFF
vs
ON
```

不预设其一定有效。

## 20.5 Evaluation Calibration

```text
Human Ratings
↔
ChinaStory Evaluation Skill
```

逐维比较一致性、偏差、漏检，而不是只比较总分。

## 20.6 Revision Loop

```text
V1
→ Evaluate
→ Revision Instruction
→ V2
```

匿名比较 V1 / V2，验证是否在不增加事实错误的情况下改善跨文化内容质量。

---

# 21. 前端展示原则

前端不以“做成漂亮的 AI Chat 页面”为主要目标。

优先可视化项目创新链：

```text
当前处于哪一步
↓
检索到了哪些实体 / 资料
↓
走了什么检索路径
↓
哪些 Evidence 被接受 / 拒绝
↓
哪些 Claim 对应哪些 Evidence
↓
哪里出现 Conflict / Warning
↓
修改前后发生了什么
↓
Evaluation 发现什么
↓
谁批准了最终版本
```

前端承担：

> **把研究过程和可审计性可视化。**

---

# 22. 核心数据对象

当前建议至少统一以下对象概念：

```text
UserProfile
TaskContext
AudienceProfile
Source
EvidenceSpan
Claim
Entity
Relation
EvidenceConflict
ContentPlan
ContentVersion
FactLock
AuditIssue
EvaluationResult
RevisionInstruction
Approval
StoryPackage
```

核心关系：

```text
TaskContext
  ↓
Evidence / KG
  ↓
Claim–Evidence–Source
  ↓
ContentPlan
  ↓
ContentVersion
  ↓
EvaluationResult
  ↓
Revision / Audit
  ↓
Approval
```

具体 Schema 由后续工程文件定义，本总 SPEC 不写死所有字段。

---

# 23. 当前不应写死的参数

以下参数仍为 `TBD`：

- Evidence Gate 的最终阈值；
- Yellow / Red 的完整规则；
- Graph RAG 最终图谱规模；
- Narrative Angles 是否保留为显式模块；
- Part 2 严重错误阈值；
- Part 3 自动通过阈值；
- Rubric 是否需要总分；
- Rubric 各维权重；
- 自动修改最大轮数；
- Human–AI Judge 可接受一致性阈值；
- Real Audience 实验样本量。

这些应由访谈、工程试验或实验数据决定，而不是提前写成既定事实。

---

# 24. 仓库规范文件关系

本文件是**项目总 SPEC**。

```text
SPEC-国际传播智能体_v2.1_现阶段统一规范.md
│
├── 定义项目是什么
├── 定义六阶段主流程
├── 定义研究问题 / MVP / 实验
└── 定义各子规范之间的关系
```

评价子系统另由：

```text
eval/
├── CHINASTORY_EVALUATION_PIPELINE_SPEC_v1.2_CN.md
│   └── Part 1 / Part 2 / Part 3 如何串联
│
├── CHINASTORY_CONTENT_QUALITY_RUBRIC_v2.x.md
│   └── Part 3 “评什么”
│
└── CHINASTORY_EVALUATION_SKILL_SPEC_v1.x.md
    └── Part 3 “程序怎么评”
```

因此：

> **Evaluation Pipeline Spec 不能替代本项目总 SPEC。**

它只是本总 SPEC 中 Evaluation 子系统的详细规范。

---

# 25. 一句话定位

> **ChinaStory Agent V1 是一个以证据为基础、以跨文化再创作为核心生产方式、以人机门控和分层评价保障质量的国际传播内容生产与研究系统；项目重点不是证明大模型“能写”，而是通过用户研究和对照实验验证 Graph RAG、Claim–Evidence、Evidence Gate、Fact Lock、Transcreation 与 ChinaStory Evaluation 分别带来的实际价值。**
