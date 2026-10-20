# 体裁 / format 速查（Agent 路由用）

完整说明见 `skills/README.md`。字段细则见 `content_formats.md`。

> 2026-10-19 起按 v6.1 六体裁路由，skill 路径全部指向
> `skills/china-story-generation/references/genres/`。依据
> `docs/chinastory_v6.1/history/handoff-to-backend/04-code-integration-patch.md` §1。

| 用户说法 / zip ID | genre | skill | 状态 |
|-------------------|--------|-------|------|
| 帖文 贴文 social_post thread 图文 | post | `china-story-generation/references/genres/post.md` | complete |
| 新闻通稿 通稿 消息稿 news_article press_kit newsletter | news | `.../genres/news.md` | complete |
| 特稿 非虚构 长篇特写专题稿 longform feature | feature | `.../genres/feature.md` | methods_in |
| 深度报道 解释性报道 调查报道 专题报道 in_depth_report | indepth | `.../genres/indepth.md` | methods_in |
| 短视频脚本 口播 分镜 short_video | script | `.../genres/script.md` | methods_in |
| 误解澄清 辟谣 FAQ faq_mythbust | faq | `.../genres/faq.md` | methods_in |
| 回复评论 reply | reply | intl-comm + intl_comm_reply | 已有 |
| 未指定 | post | 同上 | 默认 |

路由代码：`tools/genre_router.py`（顺序 indepth → feature → news → script → faq → post）
