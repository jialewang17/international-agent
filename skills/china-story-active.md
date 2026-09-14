# 讲好中国故事 · 主动内容路由

当用户需要选题、主动发布讲好中国故事内容、标签、账号运营建议时启用。

## 体裁路由（老师 0822：不同体裁不同框架）

后端根据用户提示词中的**文本类型关键词**选择 skill（实现：`tools/genre_router.py`；总表：`skills/genres/README.md`）。

| 关键词示例 | 体裁 | Skill 文件 | 完善度 | 细节依据 |
|------------|------|------------|--------|----------|
| 帖文/贴文/发帖/Instagram/thread/图文… | `post` | `genres/china-story-post.md` | **已完善** | Lasswell **5W**；zip social_post/thread 字段 |
| 新闻稿/通稿/新华体/press release… | `news` | `genres/china-story-news.md` | **已完善** | 官媒长文语料库；与帖文**互斥** |
| 深度报道/专题/特稿/longform… | `feature` | `genres/china-story-feature.md` | **可用** | 《南方周末写作课》特稿方法；评测待补 |
| 短视频脚本/口播/分镜… | `script` | `genres/china-story-script.md` | **待完善** | 临时 short_video 分镜；待研究报告 |
| 回复评论/帮我回… | `reply` | `intl-comm.md` + `intl_comm_reply` | 已有 | ABSA→论据→拟人回复 |
| 默认（主动生成未写体裁） | `post` | 同上 | — | 老师：先把贴文做好 |

**也可显式指定**：`format=social_post` / `news_article` / `longform` / `short_video` 等（zip ID），由 `resolve_format_alias` 映射到上表。

**禁止**：把通稿骨架拿去写短帖；把帖文 5W/emoji/Gen Z CTA 塞进通稿；无材料时假装深度或分镜已定稿。

## 固定流程

1. 选题不够 → `plan_china_story_topics`  
2. 生成成稿 → `generate_china_story_post`（内部：体裁识别 → 用户资料规范化 + 本地检索 → 门控 → 成稿）  
3. 展示：论据要点（区分用户上传/本地库） / 成稿字段（随体裁变化） / `skills_applied` / `genre` /（若待完善）`genre_status`  
4. 提醒：人工审核后再发布  

### 成稿字段随体裁变化

| genre | 主展示 |
|-------|--------|
| post | `five_w` / `post` / `hashtags` / `ops_tips` |
| news | `headline` / `dek` / `article`（不要当帖文打分） |
| feature | `headline` / `dek` / `body` / `one_liner` / `five_dimensions`（可标 `genre_status: methods_in`） |
| script | `shots[]` / `caption` + `genre_status: incomplete` |

## 用户资料（v0.4）

- Skill：`skills/evidence-user-materials.md`  
- 入参：`user_materials`（粘贴文本；多段用 `---` 分段）  
- 成稿论据 = 用户上传 + 本地库；`source_type` 必须可区分  

## 硬性约束

- 必须先调用工具；禁止跳过检索直接写「看起来很像」的中国故事。  
- 禁止在工具结果外硬编数字、职务、营收、到访人次、假精确钟点。  
- `evidence_used` 为空或工具报 `error` 时：如实说明，不要假装成功。  
- 成稿须符合 `intl-comm.md` v0.2+ + **当前体裁 skill** +（有用户资料时）evidence skill。  

## 默认参数（用户未指定时）

- platform: instagram  
- identity: online_influencer  
- tone: optimistic  
- country: America  
- language: English  
- max_words: 80  
- genre: post  

## 与评论回复的分工

- 主动：议题设置（默认帖文体裁）  
- 被动：海外评论回应 → `intl_comm_reply`  

## 版本

- v0.5-active · 2026-09-14 · 与 genres 合并版路由表对齐；标明四类完善度
