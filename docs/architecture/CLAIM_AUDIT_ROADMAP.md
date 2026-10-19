# ChinaStory Agent v2.1 — Claim Audit Roadmap

**Document Type:** Architecture Decision & Development Roadmap

**Decision Authority:** Project Owner

**Architecture Design:** ChatGPT

**Engineering Execution:** WorkBuddy

**Document Status:** APPROVED FOR PLANNING

**Implementation Status:** NOT IMPLEMENTED

---

## 1. Purpose

ChinaStory Agent v2.1 是一个以证据为基础、面向国际传播的人机协同 Agent 系统。

项目核心链路为：

Evidence → Claim → Evaluation → Revision → Human Approval

本规划文档记录三项正式架构发展决策：

* ADR-CS-001：Claim Extraction A → B Evolution
* ADR-CS-002：Claim Coverage Audit
* ADR-CS-003：Pre-Approval Claim Review

三项决策均已获得项目负责人批准。

本文件记录未来技术路线，不表示相关功能已经开发完成。

---

## 2. Existing Architecture Constraints

ChinaStory Agent 固定采用六阶段：

1. Define
2. Ground
3. Plan
4. Create
5. Revise & Audit
6. Approve

三个关键 Gate：

* Gate A：Task Confirmation
* Gate B：Evidence Exception
* Gate C：Final Human Approval

禁止恢复 G1–G7。

禁止通过本规划新增 Gate D。

禁止通过本规划改变现有 Gate C 的验证语义。

系统最终内容始终需要人类批准，不允许自动发布。

---

## 3. ADR-CS-001 — Claim Extraction A → B Evolution

**Decision Status:** APPROVED

### 3.1 Claim 的概念

Claim 是生成内容中可接受事实核查的现实世界主张。

Claim 的存在不意味着该主张为真。

Claim 有 Evidence 引用，也不意味着 Evidence 一定支持该主张。

Claim Extraction 负责识别待审核的文本。

Evidence Binding 负责建立引用关系。

Evidence Support Assessment 负责判断证据是否真正支持声明。

三个职责必须区分。

### 3.2 V1 —方案 A

名称：

Deterministic Sentence-Level Claim Candidate Extraction

定位：

确定性句子级声明候选提取器。

采用保守策略：

* 优先保留有实质内容的句子
* 不随意过滤潜在事实
* 保留否定和限定条件
* 不凭空增加声明
* 不翻译或改写事实
* 不制造 Evidence 引用
* 不调用 LLM
* 相同输入产生稳定结果

允许一定程度的误报。

例如：

审美评价、宣传号召或修辞文本可能被保留为候选。

这些候选不代表已经通过事实性分类。

V1 不应被描述为完整的事实识别系统。

V1 采用句子级切分，不保证一句话中的所有独立事实都得到原子化。

因此，不能仅凭 V1 有输出就认定正文事实覆盖完整。

### 3.3 Long-Term — 方案 B

名称：

Fact-Claim Identification and Atomic Decomposition

目标：

从生成内容中识别真正具有事实含义的主张，并尽可能分解为可独立核验的原子 Claim。

未来研究和开发范围：

* 事实与非事实表达的区分
* 原子事实声明识别
* 一句话多个事实的识别
* 数字与统计信息
* 时间与年份
* 主体与机构认定
* 否定与限定词
* 比较与最高级表达
* 因果关系
* 中英文及混合语言内容
* 跨语言表达差异
* Claim 与原文片段的对应关系

方案 B 的输出不能直接代表事实真实性。

必须继续接受 Evidence 和 Evaluation 审查。

### 3.4 A → B 升级规则

不得因为方案 B 具有更强的语义识别能力，就直接替换方案 A。

B 必须经过独立漏检评估。

评估必须参考人工标注的事实主张。

需要重点考察 Claim Recall。

没有可靠基准时，不得宣称 B 的事实识别已经完整。

B 上线前必须由项目负责人批准。

---

## 4. ADR-CS-002 — Claim Coverage Audit

**Decision Status:** APPROVED

**Implementation Status:** FUTURE

### 4.1 目标

Claim Coverage Audit 用于检查正文中的内容是否被适当处理，并评估事实声明是否存在漏检。

该机制不是 Claim 真伪验证器。

覆盖完整不等于事实正确。

### 4.2 Layer 1 — Source Text Coverage

未来系统应能将正文划分为可定位的文本片段。

每个片段应具有明确处理记录。

规划状态：

* CLAIM_MAPPED
* NON_FACTUAL_WITH_REASON
* UNCERTAIN_REVIEW_REQUIRED

这些状态目前只是规划概念，不属于已经实现的生产 schema。

含义：

CLAIM_MAPPED：

片段已经关联一个或多个 Claim。

NON_FACTUAL_WITH_REASON：

系统或审核者认为该片段不包含需要事实核验的声明，并保留理由。

UNCERTAIN_REVIEW_REQUIRED：

无法确定片段是否包含事实声明，需要进一步检查。

不得静默忽略未处理的实质文本。

不得将 UNCERTAIN_REVIEW_REQUIRED 解释为已通过审核。

### 4.3 Layer 2 — Independent Omission Evaluation

仅有正文覆盖记录是不够的。

例如：

一句话包含三项事实。

系统仅识别其中一项。

即使整句话被标记为 CLAIM_MAPPED，另外两项仍可能漏检。

因此，未来必须建立独立的事实漏检评估机制。

使用人工标注基准测试集。

至少覆盖：

* 中文事实句
* 英文事实句
* 中英文混合
* 多事实复合句
* 数字和百分比
* 日期与年份
* 否定句
* 比较和最高级
* 因果表述
* 主体与机构认定
* 预测和不确定表达
* 事实与评价混合句
* 修订导致的事实变化

### 4.4 未来建议记录的指标

Text Coverage：

记录原文片段是否全部获得处理结果。

Claim Recall：

与人工标注事实主张比较，评估事实漏检情况。

Unresolved Segments：

记录未能确定是否含事实声明的片段。

Unsupported Claims：

记录没有充分证据支持的声明。

Revision Coverage：

记录修订后的内容是否重新接受覆盖检查。

这些指标目前尚未全部实现。

不得伪造测量结果。

若没有人工标注基准，Claim Recall 应标记为 NOT_EVALUATED。

不得填写未经测量的数值。

### 4.5 安全原则

不允许以下逻辑：

“所有已提取 Claim 均通过，因此整篇文章事实安全。”

完整的事实审核必须考虑：

* 提取是否遗漏
* Claim 是否正确分解
* Evidence 是否支持 Claim
* 内容修订是否引入新事实
* 是否存在未处理片段

---

## 5. ADR-CS-003 — Pre-Approval Claim Review

**Decision Status:** APPROVED

**Implementation Status:** FUTURE

### 5.1 产品目标

在 Approve 阶段，Gate C 最终批准之前，为人类审核者提供一份可以检查的事实声明清单。

名称：

Pre-Approval Claim Review

中文：

审批前声明审查清单。

目的是让审核者能够查看：

* AI 实际写了哪些重要事实
* 每个事实对应什么证据
* 证据来自哪里
* 证据是否真正支持该声明
* 哪些声明存在风险
* 哪些内容尚未完成审核
* 修订过程中哪些事实发生了变化

本能力属于人类审批辅助功能。

不新增 Gate D。

不取代 Gate C。

不自动批准任何稿件。

### 5.2 数据关联要求

未来审核清单至少需要关联：

* task_id
* content_version_id
* evaluation_id

Claim 审核项需要支持：

* claim_id
* claim.text
* 原文片段或位置
* evidence_ids
* Evidence 来源信息
* Evidence 绑定结果
* 语义支持审查结果
* 风险或异常说明
* 修订变化
* 人工处理意见

以上为未来目标数据需求。

不得将这些字段全部视为当前 Claim schema 的已有字段。

### 5.3 审核状态的概念区分

TRACEABLE：

Claim 引用的 Evidence 和 Source 可以追溯。

SUPPORTED：

经过适当的事实支持核验，证据能够支持 Claim。

UNBOUND：

Claim 尚未绑定证据。

INSUFFICIENT：

现有资料不足以确定支持关系。

CONTRADICTED：

现有核验发现证据与 Claim 冲突。

以上是未来审核清单的概念性分类。

不得擅自将它们加入现有 Evaluation enum。

不得修改现有 Binding 的返回值。

不得将 TRACEABLE 直接等同于 SUPPORTED。

如果未来尚无可靠的语义支持审查结果，界面必须准确表达“未评估”或“不确定”。

### 5.4 人类最终决定

保持已有人工审核决策方向：

* ACCEPT
* EDIT
* REJECT

不得自动执行 ACCEPT。

人类审核意见必须关联对应内容版本。

旧版本的审核结果不能无条件作为新版本的审核结果。

如果修订改变事实性内容，相关 Claim 必须重新进入适当审核。

### 5.5 前置依赖

此功能不能在缺少生产数据链时被宣称完成。

它依赖：

* Claim Extraction
* ClaimStore
* Claim-Evidence Binding
* Evaluation 生产入口
* 内容版本关联
* 人工审核记录写入
* 必要的审核结果查询能力

还需要解决当前系统缺少语义支持审查的能力边界。

不得通过伪造 Evaluation 或 Evidence 支持状态来填充审核清单。

---

## 6. Development Roadmap

### Current Milestones — I2-B

I2-B-001：

Deterministic Claim Candidate Extraction

目标：

实现方案 A 的基础候选提取能力。

I2-B-002：

ClaimStore

目标：

提供 Claim 的内存存储和安全读取能力。

I2-B-003：

Production Claim Lifecycle

目标：

将 Claim 提取、存储和后续绑定过程接入生产内容版本生命周期。

I2-B-004：

Independent Evaluation Entry

目标：

建立独立 Evaluation 生产入口。

不得自动把 Evaluation 绑定到 Generate。

### Proposed Milestone — I2-C-001

名称：

Claim Coverage Ledger

目标：

* 建立原文片段索引
* 记录 Claim 对原文片段的映射
* 标识未处理内容
* 保留不确定片段
* 为事实漏检检查提供数据基础

验收方向：

原文实质片段能够追踪处理结果。

未处理内容必须可见。

覆盖记录不得冒充事实支持证明。

### Proposed Milestone — I2-C-002

名称：

Pre-Approval Claim Review

目标：

* 展示逐条声明审核清单
* 展示证据来源
* 区分引用追溯与语义支持
* 展示未解决问题
* 关联内容版本
* 为人类最终审批提供依据

验收方向：

审核者能够逐条检查事实风险。

审核清单不能自动批准内容。

现有 Gate C 的权限边界保持不变。

### Future Research

名称：

Fact-Claim Identification and Atomic Decomposition

目标：

实现方案 B。

研究：

* 更准确的事实主张识别
* 原子 Claim 分解
* 跨语言声明处理
* 独立事实漏检评估
* 人工标注基准
* Claim Recall 测量

具体算法与评估阈值将在后续单独设计。

不得在当前规划中假设已有模型、数据集或测量结果。

### Milestone Dependency

I2-B 的 Claim 生命周期是后续审核能力的数据基础。

I2-C-001 应先提供正文覆盖和定位能力。

I2-C-002 需要实际可查询的 Claim、Evidence 和 Evaluation 数据，并支持人类审核。

方案 B 的上线需要独立漏检评估和负责人批准。

以上为规划依赖，不表示实际完成日期或开发承诺。

---

## 7. Known Technical Gaps

根据 I2-B 审计基线，尚需处理：

1. Claim 尚未接入生产生成链。
2. 当前 Part 1 存在零 Claim 空转 PASS 风险。
3. 当前 Binding 只能验证引用可追溯，不能证明语义支持。
4. 跨语言 Evidence 支持判断尚未建立。
5. 缺少 Claim 覆盖率与事实漏检记录机制。
6. Evaluation 缺少生产调用入口。
7. Evaluation 结果缺少完整的生产存储和查询机制。
8. 人工审核写入尚未形成完整 HTTP 生产链。
9. Pre-Approval Claim Review 尚未实现。
10. 方案 B 尚未实现，也没有独立的事实漏检测评基准。

这些属于既有审计指出的缺口或本次新增的规划需求。

实际实施前应重新检查仓库当前状态。

不得仅凭本文件推断这些缺口永远存在。

---

## 8. Non-Goals

本规划不包含：

* 数据库引入
* Workflow 重构
* Gate C 重写
* Gate D 新增
* Fact Lock
* RevisionExecutor 开发
* Skill 架构重构
* 自动发布
* 真实 LLM 调用
* 生产 API 开发
* Claim schema 立即扩展
* Evaluation enum 立即修改
* 自动事实真实性保证

这些事项不属于本次规划文档写入任务。

---

## 9. Governance and Acceptance

此路线图由项目负责人批准。

ChatGPT 负责将其转化为后续独立 Patch 的详细工程规格。

WorkBuddy 仅根据明确指令实施。

每个开发 Patch 均需要独立的：

* 范围说明
* 文件清单
* 接口契约
* 测试要求
* 回归检查
* 验收报告

不得因为本规划获批就自动开始后续编码。

**Planning Status: APPROVED**

**Implementation Status: NOT IMPLEMENTED**
