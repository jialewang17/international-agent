# 讲好中国故事 · 主动传播路由

当用户需要选题、发帖、生成中国故事内容、标签或账号运营建议时启用。

## 体裁路由（老师 0822：不同体裁不同框架）

后端根据用户提示词中的文体关键词选择 skill（见 `tools/genre_router.py`）：

| 关键词示例 | 体裁 | Skill 文件 | 细节依据 |
|------------|------|------------|----------|
| 帖文/发帖/Instagram… | post | `genres/china-story-post.md` | **拉斯韦尔 5W**；老师：贴文用 5W |
| 新闻稿/通稿/新华体… | news | `genres/china-story-news.md` | **官媒长文语料库**；与帖文独立 |
| 深度报道/专题… | feature | `genres/china-story-feature.md` | 占位；待南方周末深度叙事 |
| 短视频脚本/口播… | script | `genres/china-story-script.md` | 占位；待研究报告 |
| 默认（主动生成工具） | post | 同上 | 先把贴文做好 |

**禁止**：用通稿骨架生成短帖；用帖文 5W/emoji/Gen Z CTA 生成通稿；无材料时编造深度结构。

## 固定流程
1. 主题不清 → `plan_china_story_topics`
2. 生成成稿 → `generate_china_story_post`（内部：体裁识别 → 用户资料规范化 + 本地检索 → 门控 → 成稿）
3. 展示 five_w / 论据要点（区分用户上传/本地库） / post / hashtags / ops_tips / skills_applied / genre
4. 提醒：人工审核后再发布

## 用户资料（v0.4）
- Skill：`skills/evidence-user-materials.md`
- 入参：`user_materials`（粘贴文本；空行/`---` 分段）
- 成稿论据 = 用户上传 + 本地库；`source_type` 必须可区分

## 硬性约束
- 必须先调用工具，禁止不调工具直接写「完整帖文包」。
- 禁止在工具结果外追加播放量、互动率、假引语、假 Evidence 编号或库外链接。
- `evidence_used` 为空或工具有 `error` 时：如实说明，不编造帖文。
- 成稿须符合 `intl-comm.md` v0.2 + **当前体裁 skill** +（有用户资料时）evidence skill。

## 默认参数（用户未指定时）
- platform: instagram
- identity: online_influencer
- tone: optimistic
- country: America
- language: English
- max_words: 80
- genre: post

## 与评论回复的区别
- 主动：议题设置（默认帖文体裁）
- 被动：别人评论后回应 → `intl_comm_reply`
