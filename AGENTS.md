# AGENTS.md — 国际传播智能体（Cursor）

## 项目
垂类 Agent，使命：**讲好中国故事**。只出人工审核草稿。

## 主 Skill（v6.1 双 Skill + 六体裁）
- 生成：`skills/china-story-generation/SKILL.md`（Create / Revision；六体裁方法在其 `references/genres/`）
- 评测：`skills/china-story-evaluation/SKILL.md`（Part 3 表达质量；Part 1 事实核验与 Part 3 不合并）
- 团队基线：`skills/intl-comm.md`（证据硬约束 + 语气边界，`always_on`）
- 体裁卡（实际注入）：`skills/china-story-generation/references/genres/`（post / news / feature / indepth / script / faq）
- 用户资料：`skills/evidence-user-materials.md`（双源论据，`always_on`）
- 主动路由：`skills/china-story-active.md`
- **生成前必须**调用 `load_story_knowledge`；体裁识别用 `detect_content_genre` / `tools/genre_router.py`
- 形态字段对照：`knowledge/content_formats.md`；样例：`knowledge/format_examples.md`

## 体裁默认
未写体裁 → **`post`**。通稿与帖文互斥；特稿（feature，是什么样）与深度报道（indepth，为什么/怎么运转）互斥。
路由顺序：indepth → feature → news → script → faq → post。
体裁长依据在各卡的「依据索引」；六体裁统一读 `skills/china-story-generation/references/genres/`，旧 `skills/genres/` 已于 2026-10-20 移除。

## Tier-1（默认 format）
social_post / thread / news_article / visual_story / short_video / press_kit / longform / in_depth_report

## 硬约束
真实性优先；不虚构；未读库不成稿；体裁不串味；Skill 不更新知识库。
