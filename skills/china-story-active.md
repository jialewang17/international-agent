# 主动内容路由

用户要**选题 / 发帖 / 标签 / 账号运营**等主动内容时用。

## 步骤

1. 主题不清 → 先问清或列方向（不编事实）
2. `detect_genre` → 读对应 `china-story-generation/references/genres/*.md`（默认 **post**）
3. 成稿前 **一次** `load_story_knowledge`
4. 有粘贴资料 → `evidence-user-materials.md`
5. 展示：论据要点（区分来源）+ 成稿字段 + `genre` /（如需）`genre_status`
6. 提醒人工审核后再发

## 分流速查

| 用户说法含… | genre | 打开 |
|-------------|-------|------|
| 帖文/Instagram/thread… | post | `china-story-generation/references/genres/post.md` |
| 通稿/新闻稿/新华体… | news | `.../genres/news.md` |
| 特稿/非虚构/longform… | feature | `.../genres/feature.md` |
| 深度报道/解释性报道/调查报道… | indepth | `.../genres/indepth.md` |
| 短视频脚本/口播/分镜… | script | `.../genres/script.md` |
| 误解澄清/辟谣/FAQ… | faq | `.../genres/faq.md` |
| 未写 | post | 同上 |

总表：`genres/README.md`。也可指定 `format=social_post` / `in_depth_report` 等 zip ID。

## 默认（用户未指定）

platform=instagram · identity=online_influencer · tone=optimistic · country=America · language=English · genre=post

## 红线

- 必须先调工具；`evidence_used` 空/报错 → 如实说明，不假装成功
- 禁止串味；禁止工具结果外编数字/职务/假钟点
- 遵守 `intl-comm.md` + 当前体裁 skill
