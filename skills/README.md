# Skills

主 Skill = 短工序卡（何时用 / 步骤 / 输出 / 红线）。长依据、语料、版本史放 `*-reference.md` 或 `docs/corpus/`，**默认不整篇注入**。

| 文件 | skill_id | 说明 |
|------|----------|------|
| `china-storytelling.md` | `china_storytelling` | 成稿入口；必须先 `load_story_knowledge` |
| `china-storytelling-reference.md` | — | 入口长表附录（Tier/结构适配等） |
| `china-story-active.md` | `china_story_active` | 主动内容路由 |
| `intl-comm.md` | `intl_comm` | 团队铁律（证据 + 语气 + 主动成稿） |
| `evidence-user-materials.md` | `evidence_user_materials` | 双源论据硬规矩 |
| `genres/` | — | 体裁工序卡：post / news / feature / script / faq |

## 体裁目录

| genre | 主文件 | 附录（按需） | 状态 |
|-------|--------|--------------|------|
| post | `genres/china-story-post.md` | `china-story-post-reference.md` | 已完善 |
| news | `genres/china-story-news.md` | `china-story-news-reference.md` | 已完善 |
| feature | `genres/china-story-feature.md` | `china-story-feature-reference.md` | 可用 |
| script | `genres/china-story-script.md` | `china-story-script-reference.md` + `docs/corpus/script/` | methods_in |
| faq | `genres/china-story-faq-mythbust.md` | `china-story-faq-mythbust-reference.md` | methods_in |

总表：`genres/README.md`  
路由：`tools/genre_router.py`  
门禁：`tools/load_story_knowledge.py`

**默认体裁：** post  
**Tier-1 format：** social_post / thread / news_article / visual_story / short_video / press_kit
