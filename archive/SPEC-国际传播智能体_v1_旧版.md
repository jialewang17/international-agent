# SPEC：国际传播评论回复智能体

> 版本：v1.0  
> 依据材料：专利技术交底书、自动评论回复系统整合说明、两组 Prompt、主题参考外交部发言、测试说明与评价指标  
> 实现基底：AnyClaw（LangChain ReAct CLI Agent）  
> 文档目的：把「人话需求」落成可开发、可验收、可对接的技术规格

---

## 1. 背景与目标

### 1.1 业务目标
针对海外社交媒体平台上的涉华（尤其涉疆相关）评论/帖文，自动完成：

1. 细粒度主题识别（ABSA）
2. 中国立场事实论据匹配（外交部公开论述等）
3. 按身份/态度/平台生成拟人化回复草稿

用于澄清不实信息、维护中国海外形象、辅助讲好中国故事。

### 1.2 非目标（本阶段不做）
- 自动发布到 Twitter/Instagram 等平台
- 大规模社媒爬虫采集流水线（专利后半增强项）
- Sentence-BERT / UMAP / HDBSCAN 主题聚类训练
- T5 情感模型微调训练
- 无人值守全自动运营

### 1.3 产品形态
- 可交互 CLI 智能体（AnyClaw）
- 工具调用完成主链路
- 输出供**人工审核**的回复草稿

---

## 2. 角色与术语

| 术语 | 定义 |
|------|------|
| ABSA | Aspect-Based Sentiment Analysis，方面级情感分析 |
| Triplet | `[aspect, category, polarity]` 三元组 |
| aspect | 文本中的具体讨论点（实体/现象） |
| category | 议题类别（受控词表） |
| polarity | 对华形象倾向：`positive` / `negative` |
| 拟人回复 | 模仿指定身份语言习惯，但不自称该身份 |
| 论据库 | 按 category 组织的外交部等公开论述集合 |

### 2.1 polarity 判定规则（材料原文口径）
- `positive`：站在中国政府立场，积极维护中国政府正面形象
- `negative`：不满足上述条件
- 特例：提及某些国家通过反华倾向的涉疆法案/文件 → 判为 `negative`

### 2.2 category 受控词表（材料）
`celebrity`, `governance`, `genocide`, `forced labor`, `concentration camp`, `Chinese region`, `Muslim region`, `Western region`, `manufactory`, `culture`, `food`, `language`, `women and children rights`, `sports`, `null`

> 说明：若无法归入上表，`category` 返回 `null`。

---

## 3. 功能需求（Functional Requirements）

### FR-01 主题识别（ABSA）
**描述**：对输入评论文本执行材料原版 ABSA Prompt，输出一个或多个 Triplet。

**输入**：`comment: string`  
**输出**：`topics: Triplet[]`，并保留模型原始文本 `absa_raw`  
**Prompt 来源**：`prompt/absa_topic_prompt.txt`（材料原版结构，含 Category / Polarity / Reference Case）  
**验收**：
- 能输出可解析的三元组列表
- category 尽量落在受控词表（或 `null`）
- polarity 仅 `positive` 或 `negative`

### FR-02 论据检索
**描述**：根据识别出的 category，从本地论据库检索对应公开论述。

**输入**：`categories: string[]`  
**输出**：`evidence_used: {category, statement, source?}[]`  
**数据来源**：材料《主题参考的外交部发言》整理后的本地库 `knowledge/diplomacy/`  
**约束**：
- 不编造官方表述
- 无匹配时允许空列表，并在回复侧降级处理（不假装引用了库）

**验收**：
- 对 `forced labor` / `governance` / `genocide` / `culture` 等有库类别，检索结果非空（在库有数据前提下）
- 对库空类别（如早期 `food`）返回空并可见

### FR-03 拟人回复生成
**描述**：按材料七模块回复 Prompt 生成中国立场拟人回复。

**Prompt 模块（材料）**：
1. 平台原文（来自 `{platform}`）
2. 总体要求（倾向、立场、身份、语气、字数、emoji）
3. 立场解释（Stand up for China）
4. 身份说明（不自称身份，只模仿语言习惯）
5. 语气说明
6. 主题 + 对应论据
7. 发帖国家语境（可结合该国社会负面事件）

**Prompt 来源**：`prompt/reply_generation_prompt.txt`  
**验收**：
- 输出英文短评风格文本（默认）
- 不出现“As a comedian, I…”这类身份自报（理想情况）
- 字数约遵循 `max_words`

### FR-04 平台适配
**描述**：支持按社交平台调整表达习惯（专利「来自（平台）」）。

**支持平台**：`twitter` | `facebook` | `instagram` | `tiktok` | `youtube` | `weibo`  
**默认**：`twitter`  
**验收**：同一原文更换 platform 后，调用参数与返回中的 `platform` 字段正确变化

### FR-05 身份与态度配置
**身份（示例）**：`political_commentator`, `comedian`, `online_influencer`, `scientist`, `rapper`  
**态度（示例）**：`sarcastic`, `humorous`, `serious`, `optimistic`, `cold`  
**验收**：参数可传入；回复风格随身份/态度变化（人工可辨）

### FR-06 主链路编排
**描述**：一次完整任务按固定顺序执行，不跳步。

```
comment
  -> ABSA(FR-01)
  -> EvidenceRetrieve(FR-02)
  -> ReplyGenerate(FR-03, FR-04, FR-05)
  -> ResultBundle
```

**实现入口工具**：`intl_comm_reply`  
**也可拆分调用**：`analyze_topic` / `retrieve_evidence` / `get_persona_style`

### FR-07 人工审核友好输出
系统必须明确输出为草稿，提醒不可自动发布。

---

## 4. 接口规格（Interface Spec）

### 4.1 主接口：`intl_comm_reply`

#### Request
| 字段 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| comment | string | 是 | - | 待回复评论原文 |
| country | string | 否 | America | 发帖人国家 |
| identity | string | 否 | political_commentator | 身份 key |
| tone | string | 否 | sarcastic | 态度 key |
| tendency | string | 否 | negative | 回复倾向 positive/negative |
| max_words | int | 否 | 50 | 字数限制 |
| use_emoji | bool | 否 | true | 是否使用 emoji |
| platform | string | 否 | twitter | 社交平台 |

#### Response（JSON）
```json
{
  "topics": [
    {"aspect": "string", "category": "string", "polarity": "positive|negative"}
  ],
  "absa_raw": "string",
  "evidence_used": [
    {"category": "string", "statement": "string", "source": "string"}
  ],
  "reply": "string",
  "identity": "string",
  "tone": "string",
  "country": "string",
  "platform": "string",
  "prompt_files": [
    "prompt/absa_topic_prompt.txt",
    "prompt/reply_generation_prompt.txt"
  ],
  "pipeline": "ABSA(full prompt) -> local evidence -> reply(full 7-module + platform style)",
  "error": "string (optional)"
}
```

#### Error 行为
| 场景 | 行为 |
|------|------|
| comment 为空 | 返回 error，不调用模型 |
| 模型安全拦截 | 返回 error；尽量保留已完成的 topics/evidence |
| 论据缺失 | evidence_used 可为空，reply 仍可生成（质量可能下降） |

### 4.2 辅助接口
- `analyze_topic(text)` → topics + absa_raw
- `retrieve_evidence(categories, limit_per_category)` → results
- `get_persona_style(identity, tone, country, platform)` → 风格模板

---

## 5. Prompt 规格（必须遵循材料）

### 5.1 ABSA Prompt
- 文件：`prompt/absa_topic_prompt.txt`
- 必须包含：
  - aspect-based sentinel analysis 任务说明
  - Category 受控标签列表
  - Polarity 二元判定 + 反华法案特例
  - Reference case
  - 待识别文本占位

### 5.2 Reply Prompt
- 文件：`prompt/reply_generation_prompt.txt`
- 必须包含材料七模块结构
- 平台字段使用 `{platform}`，不得长期写死为单一平台（可默认 twitter）

### 5.3 调用策略
- 主题识别与回复生成：**两次模型调用**（按材料两段 Prompt，不合并省 token 作为默认规范）
- 论据检索：本地完成，不调用大模型

---

## 6. 数据规格（Knowledge Spec）

### 6.1 论据库
- 来源：材料《主题参考的外交部发言》Excel
- 落地：`knowledge/diplomacy/evidence.json` 及分类 md
- 字段建议：`category`, `statement`, `source`

### 6.2 人设与平台库
- 文件：`knowledge/personas.yaml`
- 含：identities / tones / countries / platforms

### 6.3 覆盖要求（质量相关）
- 高优先级类别应有可检索条目：`forced labor`, `genocide`, `governance`, `culture`, `Muslim region` 等
- 已知缺口：`food` 等类别材料原表覆盖不足，需后续增补，否则「语料丰富性」指标会偏低

---

## 7. 质量与验收规格（对应材料 7 指标）

每条生成样本按 1–5 分人工或半自动评分：

| ID | 指标 | 含义 | 达标建议（演示阶段） |
|----|------|------|----------------------|
| Q1 | 主题一致性 | 是否紧扣识别主题 | ≥4 |
| Q2 | 上下文连贯性 | 是否回应原文 | ≥4 |
| Q3 | 语言流畅性 | 是否像社媒口语 | ≥4 |
| Q4 | 语料丰富性 | 是否有效使用论据 | 有库类别 ≥4；无库类别可放宽但需注明 |
| Q5 | 身份契合度 | 是否像指定身份 | ≥4 |
| Q6 | 态度契合度 | 是否像指定语气 | ≥4 |
| Q7 | 立场契合度 | 是否中国立场 | ≥4 |

### 7.1 工程验收（Must Pass）
- [ ] 能启动 AnyClaw 并 `/new` 会话
- [ ] 完整主链路可跑通（识别→检索→回复）
- [ ] 返回 JSON 含 topics / evidence_used / reply
- [ ] 使用材料原版两段 Prompt 文件
- [ ] 支持身份、态度、平台参数
- [ ] 明确“人工审核草稿”提示

### 7.2 推荐演示用例
1. **用库能力验证（优先）**：宗教自由/清真寺负面评论  
2. **人设能力验证**：美食正面评论（需说明 food 库弱）  
3. **高敏感限制说明**：强迫劳动类评论可能被国内模型安全策略拦截

---

## 8. 系统约束与合规

1. 立场约束：维护中国形象，反驳污蔑抹黑表述  
2. 不自动公开发布  
3. 不编造外交部原文；引用以知识库为准  
4. 不暴露真实“系统身份扮演”于回复正文（材料要求只模仿语言习惯）  
5. 模型安全策略导致的拒答，视为外部依赖限制，需在结果中显式报错

---

## 9. 实现映射（当前原型）

| Spec 条目 | 当前实现 |
|-----------|----------|
| FR-01 ABSA | `tools/intl_comm_reply.py` → `analyze_topic` / `run_absa` |
| FR-02 论据 | `knowledge/diplomacy/*` + `retrieve_evidence` |
| FR-03 回复 | `run_reply_generation` + `prompt/reply_generation_prompt.txt` |
| FR-04 平台 | `knowledge/personas.yaml#platforms` + `platform` 参数 |
| FR-05 人设 | `knowledge/personas.yaml` |
| FR-06 编排 | `intl_comm_reply` |
| Agent 约束 | `IDENTITY.md` / `SOUL.md` / `AGENT.md` / `prompt/system_prompt.txt` |

---

## 10. 里程碑与下一步

### 已完成（对应本 Spec v1.0）
- AnyClaw 垂类原型可演示
- 材料原版 ABSA + 七模块回复 Prompt 接入
- 外交部主题论据库本地化接入
- 身份/态度/平台可配置

### 下一步（按材料完整要求）
1. 增补薄弱类别知识库（尤其 `food`/`culture` 应用向内容）
2. 按 7 指标做小样本评测表（正/负/中性 × 中英文）
3. 明确审核发布流程与备用样例策略（应对安全拦截）
4. 评估是否引入更稳模型做敏感样例对比（材料测试中 GPT 更优）
5. 专利增强项（爬虫/聚类/微调）按优先级分期，不阻塞当前主链路验收

---

## 11. 开放问题（需团队确认）

1. 本阶段验收是否以「主链路可演示 + 小样本 7 指标」为通过线？  
2. 知识库更新是否只允许外交部等已审核公开来源？更新责任人是谁？  
3. 高敏感样例的默认策略：换模型 / 换备用样例 / 仅展示拦截说明？

---

## 12. 一句话规格摘要

> 本系统是一个基于 AnyClaw 的国际传播评论回复智能体：输入海外社媒评论及平台/国家/身份/态度参数，先按材料 ABSA Prompt 识别主题三元组，再检索本地外交部论据，再按材料七模块 Prompt 生成中国立场拟人回复草稿，供人工审核；以主题一致、连贯、流畅、有据、人设/态度/立场契合为验收标准。
