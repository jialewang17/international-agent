# 多形态输出适配（China Storytelling 扩展）

本文件是 `docs/china-storytelling-skill.md` **第六节内容形式 / 第二十节输出形式** 的落地规范。

**生成前必须先走 China Storytelling 主流程**，且 **必须先调用工具 `load_story_knowledge(format=...)`**，依据返回的 framework / methodology / format_spec 再写作。  
禁止跳过读库与结构适配、直接套形态模板填空。

- `reply`：走 `intl_comm` + `intl_comm_reply`，不走本文件长文流程。  
- **默认英文海外向**（发外国社交媒体）；用户明确要求中文则中文。只出人工审核草稿。  
- 平台差异用同一 format + `platform` 参数处理。  
- 下文 `social_post` 等为形态 ID（供工具调用）；字段名保留机读键，括号内为中文含义，便于人工阅读。

---

## Tier 分层（降低路由混乱）

### Tier-1（默认，未指定形态时只在此层猜测）

| ID | 中文名称 | 说明 |
|----|----------|------|
| `social_post` | 单条贴文 | 微博 / 社媒短帖 |
| `thread` | 叙事长帖串 | 分条讲完一个小故事 |
| `news_article` | 消息 / 特稿 | 新闻通稿体 |
| `visual_story` | 图文 / 轮播 | 多页图文 |
| `short_video` | 短视频完整脚本 | 含分镜与旁白 |
| `press_kit` | 对外素材包 | 整套发布材料 |

### Tier-2（进阶，仅当用户明确要求时使用）

| ID | 中文名称 |
|----|----------|
| `explainer` | 概念解释 |
| `quote_card` | 引语 / 金句卡 |
| `reel_hook` | 前三秒钩子 |
| `caption_only` | 成片/成图配文 |
| `longform` | 深度长文 |
| `headline_pack` | 标题 + 导语组 |
| `newsletter_brief` | 简报 |
| `youtube_script` | 中长视频脚本 |
| `podcast_script` | 播客脚本 |
| `faq_mythbust` | 误解澄清 FAQ |
| `talking_points` | 发言 / 采访要点 |
| `bilingual_pair` | 中英对照 |

样例（Tier-1）：`knowledge/format_examples.md`（英文成稿样例 + 中文对照说明）

---

## 0. 共用规则

1. 内部完成一句话核心句与模块选择；**不要**把模块名写成读者可见小标题（除非用户要分析过程）。
2. 事实仅来自用户素材或明确允许的资料；不足则输出 `missing_fields`（缺失字段）+ 具体追问，或收缩结构；`press_kit` 缺料部件写 `omitted_reason`（省略原因）。
3. 输出末尾可附：`format`（形态）/ `tier`（层级）/ `platform`（平台）/ `modules_used`（所用模块）/ `methods_used`（所用方法）/ `one_liner`（一句话核心）/ `caveats`（注意）/ `knowledge_loaded: true`（已读库）。
4. 若用户一次要「整套发布」，优先 `press_kit`。
5. **未指定语种 → 英文（海外向）**；用户明确要求中文再出中文。  
   样例文件 `format_examples.md` 带中文对照，仅方便读懂结构，不成稿语种依据。
6. **软虚构禁令**：未给的精确钟点/秒数、物种名、姓名性别、职业身份、制度背景、旁支情节、百分比等一律不写（细则见 `skills/china-storytelling.md`）。
7. **同轮只调一次** `load_story_knowledge`。
8. 用户说「形态还没想好」→ 先列 Tier-1 选项询问，确认后再生成。

### 素材不足时的标准输出

```text
status: need_more_material
missing_fields: [人物姓名与身份, 可核验数据, 时间地点, ...]
can_generate_partial: true|false
questions:
  - 具体追问1
  - 具体追问2
partial_plan: 若可部分生成，说明将采用的临时结构（并标明非库内验证结构，如适用）
```

缺料回复须含上述字段头（可用 Markdown 呈现，但键名保持一致）。

---

## A. 发布向（社媒 / 轻内容）

### A1. social_post 单条贴文
**Tier-1**

| 平台 | 建议长度 |
|------|----------|
| twitter / X | ≤280 字符，或说明可扩成 thread |
| weibo（微博） | 80–140 汉字（仅用户要求中文时） |
| facebook | 80–150 词 |
| instagram | 60–120 词 + hashtag 3–8 |
| linkedin | 100–180 词，稍正式 |

结构：钩子（场景/反差/数据）→ 1 个可核验事实或行动 → 可分享收束。  
字段：`post`（正文）、可选 `alt_versions`（备选 2 条）、`hashtags`（话题标签）、`platform`（平台）。

---

### A2. thread 叙事长帖串
**Tier-1**

适用：一个完整小故事需分条讲清（微博长帖 / X / Threads）。  
默认 **6–10 条**（可 5–12）；每条控制在平台可读长度内。  
第 1 条强钩子；中间条推进行动/人物/变化；末条自然意义 + 提问式引导互动。  
字段：`tweets[]` / `posts[]`（各条正文）、`hook`（钩子）、`cta`（行动号召）、`hashtags`、`platform`。

---

### A3. explainer 概念解释帖
**Tier-2**

结构 4 拍：概念一句话 → 场景 → 1 事实锚点 → 与读者相关。120–220 词。  
字段：`concept`（概念句）、`body`（正文）、`misconception`（可选，常见误解）、`hashtags`。

---

### A4. quote_card 引语 / 金句卡
**Tier-2**

引语必须来自用户素材；无引语则用事实短句并标明非直接引语。  
字段：`quote`（引语）、`attribution`（出处）、`context_line`（上下文）、`visual`（画面建议）、`caption`（配文）。

---

### A5. visual_story 图文 / 轮播
**Tier-1**

4–8 页；每页 `visual`（画面）+ `title`（标题）+ `caption`（说明）。  
字段：`slides[]`（页列表）、`cover_line`（封面句）、`cta`（行动号召）。

---

### A6. short_video 短视频脚本
**Tier-1**

默认 45–60 秒。前 3 秒钩子须具体。按秒：`t`（时间）/`shot`（镜头）/`vo`（旁白）/`on_screen`（字幕）/`broll`（空镜）/`sfx`（音效）。  
字段：`title`（标题）、`duration_sec`（时长秒）、`shots[]`（分镜）、`caption`（成片配文）、`hashtags`。  
**禁精确钟点/未给耗时**（如 7:42、Thirty seconds）；可用 morning rush / 早高峰 等模糊时段。  
**禁令**：用户未给精确钟点/秒数时，用 morning rush / a short exchange 等模糊表述；禁止自造 7:42、Thirty seconds 等。

---

### A7. reel_hook 钩子三选
**Tier-2**

3 个前 3 秒方案；选定后再升格 `short_video`。

---

### A8. caption_only 成片/成图配文
**Tier-2**

字段：`caption`（配文）、`hashtags`、`alt_text`（无障碍描述）、`cta`、`platform`。

---

## B. 媒体 / 机构向

### B1. news_article 消息 / 特稿
**Tier-1**

消息 400–700 词；特稿 900–1500 词。  
字段：`headline`（标题）、`dek`（导语）、`body`（正文）、可选 `pull_quote`（提引）、`suggested_visual`（配图建议）。  
**素材回溯（强制）**：正文每一句事实须能对应到用户素材；禁止用常识补迁徙路线、人员身份、数字化系统、未给物种、未给管理动作等。素材薄则写短消息并标明局限，或输出 `missing_fields`。

---

### B2. longform 深度长文
**Tier-2**

1500–3000 词。  
字段：`headline`、`dek`、`body`、`pull_quote`、`suggested_visuals[]`。

---

### B3. headline_pack 标题 + 导语组
**Tier-2**

`headline_main`（主标题）+ `headline_alts`（备选 3–5）+ `dek`（导语）+ 可选 `social_headline`（社媒标题）。

---

### B4. newsletter_brief 简报
**Tier-2**

300–500 词。  
字段：`subject_line`（邮件主题）、`preview_text`（预览句）、`body`（正文）、`cta`。  
**素材回溯（强制）**：同 news_article；禁止扩写志愿者构成、城市治理趋势等未给信息。

---

### B5. press_kit 对外素材包
**Tier-1**

含：`news_blurb`（短消息）、`headline_pack`（标题组）、`key_facts`（要点）、可选 `quote_card`、`visual_captions`（图说）、`faq`（问答）、`social_post`×2。  
缺料部件写 `omitted_reason`（省略原因）。

---

### B6. youtube_script 中长视频脚本
**Tier-2**

3–8 分钟，按场输出 `scenes[]`（场次）+ `description`（描述）+ `chapters[]`（章节）。

---

### B7. podcast_script 播客脚本
**Tier-2**

8–15 分钟大纲。字段：`episode_title`（集标题）、`rundown[]`（流程）、`show_notes`（节目注）。

---

## C. 互动 / 口径向

### C1. faq_mythbust 误解澄清 FAQ
**Tier-2**

5–8 组问答；可选 `retrieve_evidence`。

### C2. talking_points 发言 / 采访要点
**Tier-2**

5–7 条 + `opening`（开场）/`closing`（收束）；可选 `retrieve_evidence`。

### C3. bilingual_pair 中英对照
**Tier-2**

`format_base`（基础形态）+ `en`（英文）+ `zh`（中文）；两版事实必须等价。默认以英文海外向为主，中文作对照。  
**强制**：中英事实一一对应；情感收束句两边同有或同无，禁止中文多出「默契」等英侧没有的评价。

---

## D. 回帖（独立路径）

### reply

路由至 `intl_comm` → `intl_comm_reply`。（回帖语种规则见回帖 skill，不在此文件改写。）

---

## E. 形式路由表

| 用户说法 | format | Tier |
|----------|--------|------|
| 贴文/发帖/社媒文案 | social_post | 1 |
| 长帖/线程/连环帖 | thread | 1 |
| 图文/配图/轮播 | visual_story | 1 |
| 短视频完整脚本 | short_video | 1 |
| 新闻/消息/特稿/报道/通稿 | news_article | 1 |
| 素材包/通稿套装/press kit | press_kit | 1 |
| 解释/科普/什么是XX | explainer | 2 |
| 金句/引语卡 | quote_card | 2 |
| 只要开头钩子/前三秒 | reel_hook | 2 |
| 已有图或视频只要文案 | caption_only | 2 |
| 深度/长篇 | longform | 2 |
| 标题/导语/headline | headline_pack | 2 |
| 简报/newsletter | newsletter_brief | 2 |
| YouTube/中长视频 | youtube_script | 2 |
| 播客/音频脚本 | podcast_script | 2 |
| FAQ/辟谣/常见问题 | faq_mythbust | 2 |
| 发言提纲/采访口径 | talking_points | 2 |
| 中英对照/双语 | bilingual_pair | 2 |
| 回帖/评论回复 | reply → intl_comm | — |
| 未指定 | **仅在 Tier-1 中**询问或猜测 | 1 |
