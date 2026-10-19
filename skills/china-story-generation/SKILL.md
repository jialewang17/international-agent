---
name: china-story-generation
description: 中国故事内容生成 Skill。在既有 TaskContext、ContentPlan 与 EvidencePack 之上，执行证据约束写作、形成中文母稿、做跨文化再创作（Transcreation），并按 post/news/feature/indepth/script/faq 六类体裁与平台输出人工审核草稿；也负责依据 RevisionInstruction 产出下一版本。供 Create 阶段与 Revision 环节调用。
---

# ChinaStory Generation Skill（生成）

> 定位：**Create 阶段的内容生产 + 受控 Revision**。
> 本 Skill 不定义任务、不检索证据、不做事实核验、不做最终批准。

---

## 0. 职责边界（先读这一段）

| 本 Skill 负责 | 本 Skill **不**负责 |
|---|---|
| 依据已有 `EvidencePack` 做证据约束写作 | **Define**：不自行建立 `TaskContext`、不自行确认任务 |
| 形成中文母稿（Content Master）并保存 | **Ground**：不检索、不建立、不裁决证据来源 |
| 跨文化再创作（Transcreation） | **Plan**：不决定传播策略、受众定位与渠道规划 |
| 六类体裁与平台的表达适配 | **Part 1 事实核验**：不判定论断是否已验证 |
| 依 `RevisionInstruction` 产出下一版本 | **Gate A/B/C**：不做门禁判断与最终 `APPROVED` |
| 输出引用关系与待核清单 | 不自动公开发布 |

> **[G-01] 移除 Define 职责**
> 来源：`ChinaStory_Agent_v2.1_Skill_Architecture_Review.md` §二「本地文件与位置」第 1 行 + §五「最新 ZIP 文件」第 1 行。
> 依据：v2.1 架构中 ① DEFINE 阶段产出 `TaskContext` 并经 **Gate A｜Task Confirmation** 确认；审查报告明确建议「**改为读取已确认的任务契约**；只在独立调用 Skill 时提供缺省处理」。

> **[G-02] 移除 Ground / 证据合并职责**
> 来源：审查报告 §二 第 3 行。
> 依据：② GROUND 阶段产出统一 `EvidencePack`（`Source / EvidenceSpan / evidence_refs`），经 **Gate B｜Evidence Exception**；生成侧只消费，不生产。

> **[G-03] 移除入口内自带的独立 Review 流程**
> 来源：审查报告 §二 第 5 行 + §三。
> 依据：`review/` 属 **Evaluation Pipeline**；其中 `fact-check` 属 **Part 1**，审查报告指出「不应是 Part 3 的一部分」「不应纳入内容质量评测 Skill 的职责」。

---

## 1. 输入契约（调用方必须提供）

```yaml
task_context:      # 来自 Define 阶段，经 Gate A 确认
  topic: ""
  goal: ""
  genre: ""        # post|news|feature|indepth|script|faq
  platform: ""
  target_language: ""
  constraints: []

content_plan:      # 来自 Plan 阶段
  story_angles: []
  audience_bridge: ""
  primary_format: ""
  repurpose_formats: []
  risks: []

evidence_pack:     # 来自 Ground 阶段，经 Gate B
  sources: []
  evidence_spans: []
  gate: ready_to_generate   # 若为 blocked，见 §2.0
```

**缺省处理（仅当 Skill 被独立调用）**：若上述契约缺失，不自行编造，输出 `missing_context` 并列出需要补齐的字段。

---

## 2. 执行流程（不可跳过）

### 2.0 门禁前置（G-08）

成稿前调用一次 `load_story_knowledge(format, topic_hint)`。

- 仅当 `gate=ready_to_generate` 才继续；
- `gate=blocked` → **只输出阻塞原因与补救动作，不输出任何貌似完整的成稿**；
- 不要在同一轮重复调用。

> **[G-08] 知识库门禁失败不成稿**
> 来源：`implementation-checklist.md` P0 第 1 条。
> 依据：缺任一知识文件时 `load_story_knowledge` 返回 `gate=blocked`，「不得静默生成」。审查报告 §四 确认该修复在当前 GitHub 代码中**已经生效**，本卡只需固化调用纪律。

> **[G-10] 证据共享规则始终激活**
> 来源：`implementation-checklist.md` P0 第 7 条。
> 依据：「不要让 `max_active_skills` 或字符预算把 `evidence-user-materials` 挤掉」——写作约束与证据规则是硬约束，不参与上下文预算竞争。

### 2.1 体裁路由（内部六选一）

按 `indepth → feature → news → script → faq → post` 识别；显式 `format` 优先于模糊关键词。

**生成侧只读取一张体裁主卡**（见下表），主卡需要时再读同目录 `*-reference.md`；不并行加载多张互相竞争的体裁模板。

| genre | 主卡（references/genres/） | 默认 format | 核心问题 |
|---|---|---|---|
| `post` | `post.md` | `social_post` | 如何用一个事实点与场景让人愿意读/分享？ |
| `news` | `news.md` | `news_article` | 发生了什么、谁做了什么、依据是什么？ |
| `feature` | `feature.md` | `longform` | 这件事是什么样？ |
| `indepth` | `indepth.md` | `in_depth_report` | 为什么发生、怎么运转、边界是什么？ |
| `script` | `script.md` | `short_video` | 画面如何在有限时长内讲清一个点？ |
| `faq` | `faq.md` | `faq_mythbust` | 哪个前提不完整，证据支持什么？ |

**体裁隔离（不可串味）**：
- `feature` 不套新闻八步或 FAQ 条目；`indepth` 不用人物场景替代机制解释；
- `news` 不用社媒 CTA / emoji / Gen-Z 包装；`post` 不写成电头长通讯；
- `script` 必须有镜头，段落散文不是分镜；`faq` 无明确误解对立时不硬凑 Myth/Fact。

> **[G-05] 六类体裁降为 Skill 内部方法**
> 来源：审查报告 §六「Skill A：ChinaStory Generation」结构 + §七.1「改造 Skill Registry」。
> 依据：审查报告指出「当前 ZIP 仍有多个独立 Skill 元数据文件，GitHub 注册仍是旧结构」；目标是**只把两个顶层能力注册**为 `china_story_generation` / `china_story_evaluation`，六体裁通过 Generation 内部路由按需加载。

### 2.2 证据约束写作（中文母稿）

按 `references/writing-constraints.md` 与体裁卡执行：

1. **先数材料，再定篇幅**：feature 使用 `material_budget`（`anchor_count` / `anchor_examples` / `recommended_words` / `chosen_words` / `gate_decision`）。
2. **逐句绑定**：事实、数字、专名、引语、现场细节、因果句登记进 `evidence_map[]`，格式见 `references/output-contracts.md`。
3. **材料不足时的处理顺序**：删掉该论断 → 收缩主语/时间/范围 → 改写为明确标注的解释性判断 → 输出 `missing_fields` / `research_gaps` 请你补料。**不得用常识填空**。

> **[G-07] 中文母稿与目标稿的关联、事实锁定**
> 来源：审查报告 §五「最应该新增、但最新版尚不完整的一项能力」+ v2.1 架构「⑤ REVISE & AUDIT」。
> 依据：架构规定「**允许修改**：语言、结构、语气、叙事方式、跨文化表达。**不能未经核验修改**：年份、数字、人物事实、历史判断、关键事实关系等」。因此生成侧必须：
> - 保存中文母稿，并让目标语成稿通过 `master_ref` 指回母稿；
> - 已核验事实在后续版本中只读，任何变动必须回到 Part 1 复核。

### 2.3 跨文化再创作（Transcreation）

读取 `references/transcreation.md` 后执行。要点：保留事实与意义，允许为受众**重组结构、调整解释顺序、补充必要背景**；不新增证据外的信息，不为了"地道"加事实。

### 2.4 体裁与平台适配

按 §2.1 选中的体裁卡输出协议构造结果，并按 `platform` 调整长度、节奏、信息密度与互动方式。**体裁优先于平台**：平台适配不得改变体裁性质。

### 2.5 输出前自检（六问）

1. 是否读取了正确且唯一的一张体裁卡？
2. 是否调用了 `load_story_knowledge` 且 `gate=ready_to_generate`？
3. 每条事实能否回指 `evidence_pack` 中的具体片段？
4. 有无自造引语、链接、数据或专家判断？
5. 母稿与目标稿的事实是否一致？已核验事实有无改动？
6. 是否明确"仅供人工审核，不自动发布"？

---

## 3. 修订模式（Revision）

输入：`RevisionInstruction { target_dimension, problem, instruction, preserve }`

执行顺序：

1. **先读 `preserve`**：列出的内容（如 `verified_facts`）在本轮视为**只读**。
2. **只在允许范围内改动**：语言、结构、语气、叙事方式、跨文化表达。
3. **禁止未经核验修改**：年份、数字、人物事实、历史判断、关键事实关系。
4. **输出新版本**：`version_id` 递增，并保留 `parent_version` 指针。
5. **改完必须回到 Part 1 复核**：本 Skill 不宣布事实仍然成立。

---

## 4. 输出契约

顶层必须输出：

```yaml
genre: ""            # post|news|feature|indepth|script|faq
format: ""
genre_status: methods_in
master_ref: ""       # 中文母稿引用（G-07）
target_version:
  language: ""
  text: ""
evidence_used: []
evidence_map: []     # 见 references/output-contracts.md
knowledge_loaded: true
human_review: PENDING
```

按需输出：`needs_human[]`、`research_gaps[]`、`fact_gaps[]`、`missing_fields[]`、`missing_context[]`。

**固定附言**：仅供人工审核，不自动发布。

---

## 5. 最高优先级与红线

优先级顺序（冲突时按此取舍）：

```text
真实性 > 证据范围 > 用户明确格式 > 受众可理解性 > 体裁文采
```

红线：

- 宁短勿编；不抄教材范文；
- 不把知识库中的通用背景自动写入正文；
- 不把"写得像特稿"当作事实核验；
- 不把引用链接当作已验证支持；
- 不更新知识库（知识库由独立研究流程维护）；
- 不自动发布。

---

## 6. 知识库（动态读取，每次执行都要读）

- `knowledge/storytelling_framework.txt` —— 叙事结构规律，用于 §2.1 的结构匹配
- `knowledge/writing_methodology.txt` —— 新闻写作方法，用于 §2.2

> **[G-09] 知识库是动态知识，不复制进本卡**
> 来源：用户上一版 SKILL.md 既定原则 + 审查报告 §四 细节 1。
> 依据：审查报告明确警告「**不要直接用 ZIP 里的 `knowledge/` 覆盖 GitHub 的知识库**」——本地包中的短版本应作为 Generation 的方法摘要，完整知识文件仍由仓库 `knowledge/` 保存管理。


## v6.1 仓库合并注意事项（不修改六体裁方法）

1. **知识方法加载与事实门禁分开**：`load_story_knowledge` 用于提供叙事/体裁方法；它的 `gate` 不能替代 canonical `EvidencePack` 的 Gate B。以仓库后端的真实 EvidencePack 与任务状态为准，两项检查不可相互冒充。
2. **持久化由后端负责**：本 Skill 输出中文母稿及 `master_ref` 候选，不能声称自己把母稿写进 ContentVersionStore。现有 `api/main.py` 只保存 canonical `post` 字段；未扩展 ContentVersion 之前不得声称实现了完整母稿追踪。
3. **只启用已真正接线的体裁**：当前 `run_story_post_generation` 的显式支持集是 `post/news/feature/script`，且后两者仍复用 Post Prompt；`indepth/faq` 目前属于规则已定义、执行未完整接通。后端没有对应 Schema/分支前不要对外宣称六体裁全部已可执行。
4. **保留兼容键**：旧 Post 工具的 `post/five_w/hashtags` 和 News 的 `headline/article/post` 是现有前端兼容接口；新的 `target_version/master_ref/evidence_map` 先作为 v6.1 目标契约，须完成后端适配才默认返回。
