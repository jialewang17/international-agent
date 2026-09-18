# 体裁 Skill 目录（生成链路中的体裁环节）

> 来源合并：`international communication` 定稿体裁 skill + zip `content_formats`  
> + 《南方周末写作课》→ **仅** `feature`（特稿/深度）；**不**用于帖文/通稿。

主文件是短工序卡；长语料/细则在 `*-reference.md` 与 `docs/corpus/`，默认不整篇注入。

Skill 是生成过程中的**体裁插件**：共享立场与证据硬约束（`intl-comm.md` + `evidence-user-materials.md`），按用户提示词里的**文本类型**切换不同细节框架。

## 一、体裁一览（Agent 必读）

| 体裁 ID | Skill 文件 | 状态 | 细节框架（禁止串味） | 主要输出字段 |
|---------|------------|------|----------------------|--------------|
| `post` | `china-story-post.md` | **已完善** | 5W + 钩子场景骨架 | `five_w` + `post`/`hashtags`/`ops_tips` |
| `news` | `china-story-news.md` | **已完善** | 通稿八步骨架 | `headline`/`dek`/`article` |
| `feature` | `china-story-feature.md` | **可用** | 南周特稿方法（细则在 reference） | `body`/`one_liner`/`five_dimensions` |
| `script` | `china-story-script.md` | **methods_in** | Hook-Body-CTA 分镜 | `shots[]` |
| `faq` | `china-story-faq-mythbust.md` | **methods_in** | Myth→Fact | `items[]` |

参考附录：`*-reference.md`；帖文语料 `docs/corpus/post/`；脚本语料 `docs/corpus/script/`  
字段：`knowledge/content_formats.md`；路由：`tools/genre_router.py`；门禁：`load_story_knowledge`

## 二、提示词 → 体裁路由（关键词优先，先匹配先得）

规则顺序：**feature → news → script → faq → post**；都未命中 → 默认 **`post`**。

| 用户提示词出现… | 路由到 | 说明 |
|-----------------|--------|------|
| 深度报道 / 专题稿 / 特稿 / 长篇深度 / feature / longform / in-depth | `feature` | 《南方周末写作课》方法；勿用贴文 5W 硬套 |
| 新闻稿 / 新闻通稿 / 通稿 / 消息稿 / 通讯 / 新华体 / press release / news wire / Across China | `news` | 已完善；与帖文 skill **互斥** |
| 短视频脚本 / 视频脚本 / 口播 / 分镜 / reels script / tiktok script / video script / short_video | `script` | methods_in；完整分镜 + 钩子规范 |
| 误解澄清 / 辟谣 / FAQ / mythbust / misconception / myth vs fact | `faq` | 主动 Myth→Fact 清单 |
| 帖文 / 发帖 / 社交媒体 / Instagram / Twitter / 微博 / hashtag / social post / thread / 长帖 | `post` | 已完善；含单帖与 thread |
| 未写体裁 | `post` | 默认贴文 |

### zip 体裁 ID → 本仓库体裁（对照表）

| zip `content_formats` ID | 本仓库 genre | 处理 |
|--------------------------|--------------|------|
| `social_post` / `thread` / `caption_only` | `post` | 已覆盖；thread 写在 post skill |
| `visual_story` | `post`（变体） | 按图文页输出；细则见 post skill「图文变体」 |
| `news_article` / `newsletter_brief` / `press_kit` | `news` | press_kit 在 news skill 附录；未齐材料写 `omitted_reason` |
| `longform` | `feature` | 南周特稿方法 + zip 字段 |
| `short_video` / `reel_hook` / `youtube_script` | `script` | methods_in；youtube 长片仍降级/标清 |
| `faq_mythbust` | `faq` | 见 faq skill |
| Tier-2 其余（explainer 等） | 暂不单开 | 用户明确要求时再扩展；默认勿猜 |

## 三、所有体裁共享的硬约束（先于体裁细节）

1. **事实边界**：可核验事实/数字/专名/职务/金额/营收/到访人次等 **只能** 来自 `evidence_used`（用户上传 ∪ 本地库）；禁止常识偷补。
2. **用户资料优先**：有上传时双源合并；无证据则停或只写可核验角度。
3. **立场**：讲好中国故事；不抬杠、不以贬损他国衬托；成稿供人工审核。
4. **体裁隔离**：通稿禁止 GenZ/emoji/Imagine/Would you visit；帖文禁止写成电头长通讯。
5. **完善度**：`script` / `feature` / `faq` 方法已入库时可标 `genre_status: methods_in`。feature 禁止复述南周范文；faq 禁止照搬外部网页数字当 evidence；script 禁止假精确时点与无镜头注的空口播。

## 四、生成链路中的位置

```text
用户提示词
  → genre_router.detect_genre()     # 识别文本类型
  → 注入 intl_comm + 对应体裁 skill（+ 有资料时 evidence skill）
  → load_story_knowledge（本仓库知识门禁）
  → 检索/门控 evidence_used
  → 按体裁字段生成成稿
  → 人工审核
```

## 五、Prompt / 工具对应

| genre | Prompt / 工具 | 说明 |
|-------|-------------|------|
| post | `load_story_knowledge` + post skill | 5W 成稿 |
| news | `load_story_knowledge` + news skill | 通稿成稿 |
| feature / script / faq | `load_story_knowledge` + 对应 skill | 以 skill 正文约束 |

## 版本

- v0.5-genres-merge · 2026-09-14 · 合并 zip 体裁字段与路由对照；明确四类体裁完善度
- v0.6-nfzm-feature · 2026-09-14 · 《南方周末写作课》并入 feature；帖文/通稿仍禁用南周长模板
- v0.6.1-repo · 2026-09-14 · 本仓库适配：门禁工具为 `load_story_knowledge`
- v0.7-faq · 2026-09-15 · 新增 `faq`（faq_mythbust）；依据爬取澄清帖蒸馏；评测待补
- v0.7.1-faq · 2026-09-15 · 全文复核语料清单写入 reference；skill 升 v0.2（边界句 / 承认关切 / 使馆语气裁剪）
- v0.8-post-corpus · 2026-09-18 · post skill 爬取社媒/旅行/短视频文案加固；语料落盘 docs/corpus/post
- v0.9-script-methods · 2026-09-18 · script 升 methods_in；方法论+转写分镜落盘 docs/corpus/script
- v1.1 · 2026-09-18 · 主 skill 改为工序卡；体裁为 post / news / feature / script / faq
