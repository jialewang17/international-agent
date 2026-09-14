# 体裁 Skill 目录（生成链路中的体裁环节）

> 来源合并：`international communication` 定稿体裁 skill + zip `content_formats`  
> + 《南方周末写作课》→ **仅** `feature`（特稿/深度）；**不**用于帖文/通稿。

Skill 是生成过程中的**体裁插件**：共享立场与证据硬约束（`intl-comm.md` + `evidence-user-materials.md`），按用户提示词里的**文本类型**切换不同细节框架。

## 一、体裁一览（Agent 必读）

| 体裁 ID | Skill 文件 | 状态 | 细节框架（禁止串味） | 主要输出字段 |
|---------|------------|------|----------------------|--------------|
| `post` | `china-story-post.md` | **已完善** | Lasswell **5W**（老师 0822：贴文用 5W） | `five_w` + `post`/`hashtags`/`ops_tips`；可选 thread |
| `news` | `china-story-news.md` | **已完善** | 官媒长文语料库骨架（新华/中国日报/CGTN） | `headline`/`dek`/`article`；**不要** 5W/emoji/CTA |
| `feature` | `china-story-feature.md` | **可用** | 《南方周末写作课》特稿方法（抽象阶梯/五维度/冲突）；评测集待补 | `headline`/`dek`/`body`/`one_liner`；禁帖文腔、禁通稿电头 |
| `script` | `china-story-script.md` | **待完善** | 临时：zip `short_video` 分镜字段；研究报告未到 | `shots[]`（t/shot/vo/…）；禁 IG 文案冒充脚本 |
| `reply` | （走 `intl_comm` + `intl_comm_reply`） | 已有 | ABSA → 论据 → 拟人回复 | `topics`/`evidence_used`/`reply` |

参考附录（不默认整篇注入）：`china-story-news-reference.md`、`china-story-feature-reference.md`（《南方周末写作课》方法）
字段级对照：`knowledge/content_formats.md`、`knowledge/format_examples.md`
路由实现：`tools/genre_router.py` → `tools/story_post_gen.py`

## 二、提示词 → 体裁路由（关键词优先，先匹配先得）

规则顺序：**feature → news → script → reply → post**；都未命中 → 默认 **`post`**（老师：先把贴文做好）。

| 用户提示词出现… | 路由到 | 说明 |
|-----------------|--------|------|
| 深度报道 / 专题稿 / 特稿 / 长篇深度 / feature / longform / in-depth | `feature` | 《南方周末写作课》方法；勿用贴文 5W 硬套 |
| 新闻稿 / 新闻通稿 / 通稿 / 消息稿 / 通讯 / 新华体 / press release / news wire / Across China | `news` | 已完善；与帖文 skill **互斥** |
| 短视频脚本 / 视频脚本 / 口播 / 分镜 / reels script / tiktok script / video script / short_video | `script` | 待完善；用临时分镜骨架 |
| 回复评论 / 回复这条 / 帮我回 / reply to comment | `reply` | 走评论回复工具链 |
| 帖文 / 发帖 / 社交媒体 / Instagram / Twitter / 微博 / hashtag / social post / thread / 长帖 | `post` | 已完善；含单帖与 thread |
| 未写体裁 | `post` | 默认贴文 |

### zip 体裁 ID → 本仓库体裁（对照表）

| zip `content_formats` ID | 本仓库 genre | 处理 |
|--------------------------|--------------|------|
| `social_post` / `thread` / `caption_only` | `post` | 已覆盖；thread 写在 post skill |
| `visual_story` | `post`（变体） | 按图文页输出；细则见 post skill「图文变体」 |
| `news_article` / `newsletter_brief` / `press_kit` | `news` | press_kit 在 news skill 附录；未齐材料写 `omitted_reason` |
| `longform` | `feature` | 南周特稿方法 + zip 字段 |
| `short_video` / `reel_hook` / `youtube_script` | `script` | 待完善；临时用 short_video 字段 |
| `reply` | `reply` | intl_comm |
| Tier-2 其余（explainer 等） | 暂不单开 | 用户明确要求时再扩展；默认勿猜 |

## 三、所有体裁共享的硬约束（先于体裁细节）

1. **事实边界**：可核验事实/数字/专名/职务/金额/营收/到访人次等 **只能** 来自 `evidence_used`（用户上传 ∪ 本地库）；禁止常识偷补。
2. **用户资料优先**：有上传时双源合并；无证据则停或只写可核验角度。
3. **立场**：讲好中国故事；不抬杠、不以贬损他国衬托；成稿供人工审核。
4. **体裁隔离**：通稿禁止 GenZ/emoji/Imagine/Would you visit；帖文禁止写成电头长通讯。
5. **完善度**：`script` 仍须标明 `genre_status: incomplete`。`feature` 方法已入库，评测未齐时可标 `genre_status: methods_in`，禁止复述南周范文。

## 四、生成链路中的位置

```text
用户提示词
  → genre_router.detect_genre()     # 识别文本类型
  → 注入 intl_comm + 对应体裁 skill（+ 有资料时 evidence skill）
  → 检索/门控 evidence_used
  → 按体裁字段生成成稿
  → 人工审核
```

## 五、Prompt / 工具对应

| genre | Prompt 文件 | 说明 |
|-------|-------------|------|
| post | `prompt/story_post_prompt.txt` | 5W 成稿 |
| news | `prompt/story_news_prompt.txt` | 通稿成稿 |
| feature / script | 暂复用生成入口，以 skill 正文约束 | 后续单独 prompt |

## 版本

- v0.5-genres-merge · 2026-09-14 · 合并 zip 体裁字段与路由对照；明确四类体裁完善度
- v0.6-nfzm-feature · 2026-09-14 · 《南方周末写作课》并入 feature；帖文/通稿仍禁用南周长模板
