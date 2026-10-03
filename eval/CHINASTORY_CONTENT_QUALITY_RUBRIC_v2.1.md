# ChinaStory Content Quality Rubric v2.1
## ChinaStory 国际传播内容质量评价标准

**文件名**：`CHINASTORY_CONTENT_QUALITY_RUBRIC_v2.1.md`  
**版本**：v2.1  
**所属模块**：Evaluation Pipeline — Part 3  
**定位**：定义 ChinaStory 自研内容评价体系的研究依据、评价对象、六个核心维度、1–5 分行为锚点、解释规则、校准方法和验证边界。  
**配套执行文档**：`CHINASTORY_EVALUATION_SKILL_SPEC_v1.1.md`

---

# 1. Rubric 的目标

本 Rubric 回答：

> **在基本事实可靠的前提下，一篇面向特定海外受众、特定体裁与平台的中国故事内容，应该从哪些维度评价？怎样才算“写得好”？**

它不负责：

- Claim–Evidence 事实核验；
- Source Traceability；
- Evidence Conflict；
- Fact Lock / Fact Drift；
- 外部 evaluator 的内部实现；
- 正文生成。

以上分别由 Evaluation Pipeline 的 Part 1、Part 2 或 Generation 模块负责。

---

# 2. 研究与设计原则

## 2.1 事实与表达质量分离

事实是否成立，与表达是否优秀，是两个不同问题。

一篇文本可以语言自然、故事性强，但包含 unsupported claim；也可以事实完全正确，但跨文化表达很差。

因此：

```text
Part 1
“事实是否可靠？”
      ↓
通过基本事实门控
      ↓
Part 3 Rubric
“作为国际传播内容，表达质量如何？”
```

## 2.2 Transcreation，而非字面翻译

ChinaStory 的目标不是只判断目标语言是否“翻译正确”，还要判断：

- 文化含义是否保留；
- 陌生概念是否得到必要解释；
- 是否为了迎合受众而造成文化失真；
- 是否根据目标受众重组信息；
- 是否符合目标体裁与平台。

## 2.3 Audience Model 基于可观察变量

Audience Fit 不使用“某国人一定喜欢什么”之类的国籍刻板印象。

评价应依据任务提供的变量，例如：

- prior knowledge
- likely unknown terms
- content environment
- genre expectation
- desired depth
- available cultural anchors
- communication goal

## 2.4 LLM Judge 评价的是内容表现，不是真实传播效果

自动 Judge 可以评价：

- 是否容易理解；
- 是否存在明显文化表达问题；
- 是否与指定 Audience Profile 匹配；
- 是否具有叙事吸引潜力。

但不能仅凭模型判断证明：

- 海外受众实际理解了多少；
- 实际兴趣有多高；
- 实际分享意愿；
- 实际信任；
- 实际文化误读率。

这些必须通过真实受众实验验证。

---

# 3. 与旧版 Content Quality Rubric v1 的关系

v2.1 不是推翻 v1，而是根据新的三部分 Evaluation Pipeline 对旧指标重新组织。

v1 已形成的研究指标包括：

- accuracy
- examples
- localization / adaptability
- source authority
- interest
- politeness
- logic
- participation
- evidence support
- naturalness

v1 的历史 ROC 权重可继续作为研究背景和比较依据，但**不直接作为 v2.1 的默认总分公式**。

原因是：新架构将不同性质的指标拆开处理。

### 3.1 指标迁移逻辑

```text
v1 指标
  │
  ├── Accuracy ───────────────→ Part 1
  ├── Evidence Support ───────→ Part 1
  ├── Source Authority ───────→ Part 1 / Source Metadata
  │
  ├── 可由成熟专项工具评价的部分 → Part 2
  │
  └── 内容表达类指标
       │
       ├── Adaptability ──────→ D1 / D3 / D5
       ├── Interest ──────────→ D4
       ├── Logic ─────────────→ D1 / D4
       ├── Participation ─────→ D4 / D5
       ├── Naturalness ───────→ D6
       ├── Examples ──────────→ D1 / D4（视任务）
       └── Politeness ────────→ D2 / D6（视语境）
```

因此，v2.1 的六维结构是对旧指标的**重构与职责归位**，不是凭空增加六个指标。

### 3.2 历史权重的使用

v1 ROC 权重保留用于：

- 说明早期评价体系的研究基础；
- 与新版架构进行方法比较；
- 后续实验分析。

在完成新一轮人工标注和校准前，不直接把旧权重强行映射到六个新维度。

---

# 4. 评价对象与前置上下文

Rubric 评价的对象不是脱离任务的一段孤立文本，而是：

```text
Content
  +
Task Context
  +
Audience Profile
  +
Genre
  +
Platform
  +
Communication Goal
```

至少应尽可能提供：

- topic
- communication goal
- target language
- audience prior knowledge
- likely unknown concepts
- genre
- platform
- desired depth

若关键上下文缺失，应降低 confidence；严重不足时返回：

`INSUFFICIENT_CONTEXT`

而不是自行假设受众。

---

# 5. 评分结构

采用 **1–5 分 Behaviorally Anchored Rating Scale（BARS）**。

每个维度必须输出：

- `score`
- `rationale`
- `evidence_spans`
- `problems`
- `revision_suggestion`
- `confidence`

## 5.1 分数的一般含义

- **5｜Excellent**：高度满足该维度，几乎无实质问题。
- **4｜Good**：总体表现良好，有少量可优化点。
- **3｜Adequate**：基本可用，但存在明显改善空间。
- **2｜Weak**：问题较多，已影响传播效果。
- **1｜Poor**：存在严重问题，需要实质性修改。

具体评分必须优先依据各维度自己的行为锚点，而不是只套用上述通用描述。

## 5.2 不默认计算 Overall Score

默认：

`overall_score = null`

原因：

- 六个维度性质不同；
- 总分可能掩盖关键短板；
- 当前尚未通过人工标注确定合理权重。

如实验需要聚合分数，权重必须作为实验变量明确声明。

---

# 6. D1｜Cross-cultural Comprehensibility
## 跨文化可理解性

### 核心问题

缺少相关中国背景知识的目标受众，能否理解核心人物、事件、制度、文化概念及其意义？

### 重点观察

- 陌生概念是否在需要时得到解释；
- 是否存在只在中国语境中默认成立的知识跳跃；
- 文化词是否直接音译/直译而无必要说明；
- 核心因果和逻辑是否清晰；
- 信息密度是否超出目标受众背景。

### BARS

**5**
- 核心内容无需额外背景即可理解；
- 陌生概念解释自然且不过度；
- 几乎没有文化知识跳跃；
- 信息组织帮助受众建立正确理解。

**4**
- 整体容易理解；
- 少数概念或背景可以进一步说明，但不影响主旨。

**3**
- 主要意思可以理解；
- 存在若干未解释概念、背景跳跃或信息密度问题；
- 需要受众自行推断部分语境。

**2**
- 明显依赖中国语境知识；
- 多处概念或逻辑对目标受众不透明；
- 已影响核心内容理解。

**1**
- 核心内容难以理解；
- 存在严重语境缺失或容易造成关键误解。

---

# 7. D2｜Cultural Expression Quality
## 文化表达质量

### 核心问题

内容是否准确、具体、有语境地呈现文化含义，同时避免文化失真、标签化和不恰当类比？

### 重点观察

- 是否保留关键文化意义；
- 是否过度简化；
- 是否把中国概念错误等同于目标文化概念；
- 是否使用刻板化、异国情调化或空泛价值标签；
- 是否在解释和保真之间取得平衡。

### BARS

**5**
- 文化含义准确、具体、有语境；
- 必要解释自然；
- 不依赖刻板印象或错误等同；
- 既可理解又保持文化主体性。

**4**
- 总体准确且有语境；
- 有少量简化，但未改变核心文化意义。

**3**
- 基本准确；
- 解释较薄、较概括，或存在轻微去语境化；
- 尚未造成明显误读。

**2**
- 存在明显过度简化、不恰当类比、标签化或去语境化；
- 可能导致目标受众形成偏差理解。

**1**
- 存在严重文化误读、错误等同或扭曲；
- 已改变核心文化意义。

---

# 8. D3｜Audience Fit
## 受众适配度

### 核心问题

内容是否真正根据给定 Audience Profile 调整信息选择、解释深度、语气、结构和认知入口？

### 重点观察

- prior knowledge 是否被考虑；
- likely unknown terms 是否得到处理；
- 信息深度是否合适；
- 认知入口是否贴合目标受众；
- 是否出现“换语言但不换表达策略”；
- 是否依赖国籍刻板印象。

### BARS

**5**
- 信息选择、解释深度、语气和结构均明显针对目标受众；
- 受众画像真正影响了内容设计；
- 不依赖刻板印象。

**4**
- 整体匹配目标受众；
- 少量内容略深、略浅或解释不足。

**3**
- 有一定适配；
- 但部分内容仍像通用稿，Audience Profile 对内容组织影响有限。

**2**
- 受众适配主要停留在语言或表面措辞；
- 信息选择和解释方式基本未针对目标受众。

**1**
- 明显不适合目标受众；
- 或大量依赖未经支持的国籍/文化刻板印象。

---

# 9. D4｜Narrative Engagement Potential
## 叙事吸引潜力

### 核心问题

文本是否具备支持目标受众持续阅读、观看或进一步了解的叙事条件？

### 重点观察

- 是否有清晰的认知入口；
- 是否有具体人物、行动、场景、问题或变化；
- 信息是否形成推进；
- 事实与故事是否自然结合；
- 是否大量堆叠抽象价值判断；
- 开头和结构是否适合任务。

### BARS

**5**
- 入口明确且具体；
- 内容有清晰推进；
- 人物/行动/场景与事实自然结合；
- 具有较强继续阅读或了解的潜力。

**4**
- 整体有较强可读性和推进感；
- 个别部分略平或信息密度略高。

**3**
- 结构完整、信息清楚；
- 但较说明化或缺乏鲜明叙事入口。

**2**
- 信息堆叠、抽象判断或口号较多；
- 叙事推进弱，明显影响阅读动力。

**1**
- 结构混乱或高度空泛；
- 缺乏基本的持续阅读动力。

> 本维度只能称为 **Engagement Potential**，不能等同于真实用户 engagement。

---

# 10. D5｜Genre & Platform Fit
## 体裁与平台适配度

### 核心问题

内容是否符合指定 Genre 与 Platform 的结构、长度、节奏、信息密度和互动方式？

### 评价必须基于 Task Contract

例如：

**Social Post**
- 认知入口清晰；
- 信息压缩合理；
- 节奏适合平台；
- 必要时具有互动或继续了解的入口。

**News Release**
- 事实优先；
- 结构清晰；
- 来源和措辞克制；
- 避免不必要的情绪化包装。

### BARS

**5**
- 高度符合指定体裁和平台；
- 结构、长度、节奏、信息组织均与任务一致。

**4**
- 整体符合；
- 少量局部不匹配但不影响使用。

**3**
- 基本可用；
- 仍有明显“通用稿”特征，需要针对平台调整。

**2**
- 多项体裁或平台要求未落实；
- 需要较大幅度修改。

**1**
- 与指定 Genre / Platform 明显不符。

---

# 11. D6｜Naturalness & Non-sloganeering
## 自然度与非口号化表达

### 核心问题

内容是否像面向真实受众的自然表达，而不是机械翻译、模板化 AI 文本、宣传腔或抽象价值判断堆叠？

### 重点观察

- 是否存在明显翻译腔；
- 是否存在 AI 模板化结构；
- 是否过度使用宏大抽象评价；
- 是否用具体事实、人物和行动代替口号；
- 语气是否符合目标体裁。

### BARS

**5**
- 自然、具体、克制；
- 表达符合目标语言和体裁习惯；
- 主要通过事实、人物和行动传递意义。

**4**
- 总体自然；
- 少量句子略书面、模板化或宣传化。

**3**
- 可读；
- 但存在可感知的翻译腔、AI 模板感或抽象评价。

**2**
- 宣传腔、机械翻译或模板化表达较明显；
- 已影响可信度和阅读体验。

**1**
- 大量空泛、口号化或不自然表达；
- 严重影响内容可用性。

---

# 12. 跨维度评分规则

## 12.1 独立评分

不得因为一篇文章“整体感觉不错”而给所有维度相近高分。

例如：

- Cultural Expression 可以是 5；
- Audience Fit 可以同时只有 2。

## 12.2 证据先于评分

Judge 应先定位支持判断的文本片段，再给出 score。

## 12.3 不重复惩罚

同一个问题可以影响多个维度，但 rationale 应说明不同影响，不应机械重复扣分。

## 12.4 区分“缺陷”与“偏好”

只有与 Task Context、Audience Profile、Genre、Platform 或 Rubric Anchor 有明确关系的问题才应扣分。

## 12.5 保留不确定性

当上下文不足、文本过短或 Judge 无法稳定判断时，应降低 confidence，而不是制造确定性。

---

# 13. 标准输出

单维度：

```json
{
  "dimension_id": "audience_fit",
  "score": 3,
  "confidence": 0.78,
  "evidence_spans": [
    {
      "text": "...",
      "start": 40,
      "end": 58
    }
  ],
  "rationale": "...",
  "problems": ["..."],
  "revision_suggestion": "..."
}
```

Rubric 层总输出：

```json
{
  "rubric_version": "CHINASTORY_CONTENT_QUALITY_RUBRIC_v2.1",
  "dimensions": [],
  "priority_issues": [],
  "overall_score": null,
  "real_audience_evaluation": "NOT_EVALUATED"
}
```

---

# 14. Revision Priority
## 修改优先级

Part 3 内部推荐优先顺序：

1. 严重文化误读 / 文化失真风险；
2. 跨文化理解障碍；
3. Audience Fit 明显问题；
4. Genre / Platform 不匹配；
5. 叙事组织问题；
6. 自然度与语言润色。

若 Judge 怀疑存在事实错误：

`RETURN_TO_PART1 = true`

事实问题不由 Part 3 自行裁决。

---

# 15. Real Audience Evaluation
## 真实受众外部验证

真实受众评价用于验证 Rubric 的外部效度，而不是由 LLM Judge 模拟。

建议观察：

- comprehension
- perceived clarity
- interest / curiosity
- cultural misinterpretation
- credibility / trust

如果没有真实目标受众实验：

`REAL_AUDIENCE_EVALUATION = NOT_EVALUATED`

不得写成“受众评价良好”。

---

# 16. Human Evaluation & Calibration
## 人工评价与校准

### 16.1 Calibration Set

正式实验前建立人工校准集，包括：

- 高质量样例；
- 中等样例；
- 低质量样例；
- 典型错误；
- 边界案例；
- 不同 Genre 的样例。

### 16.2 人工标注

人工 evaluator 使用同一份 Rubric 独立评分，并记录：

- score
- rationale
- problem spans
- uncertainty

必要时采用两名及以上评价者，并记录分歧。

### 16.3 Judge Calibration

自研 Skill 应依据：

```text
Rubric
+ Scoring Anchors
+ Calibration Examples
+ Task Context
```

进行评价，而不是只使用“你是一名国际传播专家”式角色 Prompt。

### 16.4 一致性验证

后续实验应比较：

```text
ChinaStory Evaluation Skill
          vs
Human Evaluators
```

观察：

- 分数一致性；
- 问题识别一致性；
- 不同维度的一致性差异；
- 典型误判。

具体统计指标在实验设计阶段确定。

---

# 17. 与 External Evaluator 的实验关系

Part 2 与 Part 3 不应混成同一评分器。

推荐实验：

```text
同一批 ChinaStory 内容
       │
       ├── Existing / Generic Evaluator
       │
       ├── ChinaStory Custom Evaluation Skill
       │
       └── Human Evaluators
```

研究问题可表述为：

> 自研 Rubric + Skill 是否比通用 evaluator 更能识别 ChinaStory-specific 的跨文化内容质量问题，并与人工评价保持更高一致性？

---

# 18. Rubric 在系统实验中的使用

Rubric 可用于比较不同内容生成方案，例如：

- Direct LLM；
- Vector RAG；
- Graph / Evidence-enhanced RAG；
- ChinaStory Agent 完整流程。

但需要注意：

- **事实正确性**主要由 Part 1 指标评价；
- **ChinaStory 内容表达质量**由本 Rubric 评价；
- 两者应分别报告，不应混成一个模糊总分。

---

# 19. 待实验确定的参数（TBD）

以下参数在 Calibration / Pilot Study 前保持 `TBD`：

- Part 3 自动通过阈值；
- 是否需要 Overall Score；
- 若聚合，各维度权重；
- Judge confidence threshold；
- 不同 Genre 的专属子指标；
- Calibration Set 最小规模；
- Human inter-rater reliability threshold；
- Judge–Human agreement threshold；
- Real Audience Evaluation 样本量；
- 是否需要不同目标语言的独立 calibration。

---

# 20. 版本管理

每次评价应记录：

- `rubric_version`
- `judge_model`
- `prompt_version`
- `calibration_set_version`
- `task_context_version`

Rubric 修改后，不应把不同版本的实验结果直接视为完全可比。

---

# 21. 一句话定义

> **ChinaStory Content Quality Rubric v2.1 是 Part 3 的研究型评价标准：它在事实基本可靠的前提下，用六个可解释、可校准的维度评价中国故事国际传播内容，并通过人工评价和真实受众实验验证其有效性。**
