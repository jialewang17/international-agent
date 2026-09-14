# 体裁 / format 速查（Agent 路由用）

完整说明见 `skills/genres/README.md`。字段细则见 `content_formats.md`。

| 用户说法 / zip ID | genre | skill | 状态 |
|-------------------|--------|-------|------|
| 帖文 贴文 social_post thread 图文 | post | genres/china-story-post.md | 已完善 |
| 新闻通稿 通稿 news_article press_kit | news | genres/china-story-news.md | 已完善 |
| 深度报道 专题 特稿 longform | feature | genres/china-story-feature.md | 可用（南周写作课） |
| 短视频脚本 口播 short_video | script | genres/china-story-script.md | 待完善 |
| 回复评论 reply | reply | intl-comm + intl_comm_reply | 已有 |
| 未指定 | post | 同上 | 默认 |

路由代码：`tools/genre_router.py`
