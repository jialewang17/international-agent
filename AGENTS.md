# AGENTS.md — 国际传播智能体（Cursor）

## 项目
垂类 Agent，使命：**讲好中国故事**。只出人工审核草稿。

## 主 Skill（体裁路由版）
- 入口：`skills/china-storytelling.md`（主动路由详版：`skills/china-story-active.md`）
- 团队基线：`skills/intl-comm.md`（证据硬约束 + 语气边界）
- 体裁分册：`skills/genres/`（post / news / feature / script / faq）
- 用户资料：`skills/evidence-user-materials.md`（双源论据）
- **生成前必须**调用 `load_story_knowledge`；体裁识别用 `detect_content_genre` / `tools/genre_router.py`
- 形态字段对照：`knowledge/content_formats.md`；样例：`knowledge/format_examples.md`

## 体裁默认
未写体裁 → **`post`**。通稿与帖文互斥。feature / script / faq 可标 `methods_in`。  
主 Skill 为短工序卡；长依据见 `*-reference.md` / `docs/corpus/`（默认不整篇注入）。

## Tier-1（默认 format）
social_post / thread / news_article / visual_story / short_video / press_kit

## 硬约束
真实性优先；不虚构；未读库不成稿；体裁不串味；Skill 不更新知识库。
