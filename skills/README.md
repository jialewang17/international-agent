# Skills

**v6.1（2026-10-19）起，技能由两套主 Skill + 两张常开基线卡构成**，六体裁方法收在生成 Skill 的 `references/genres/`。

| 文件 | skill_id | 说明 |
|------|----------|------|
| `china-story-generation/SKILL.md` | `china_story_generation` | 生成主卡：Create / Revision；六体裁 reference 在此目录下 |
| `china-story-evaluation/SKILL.md` | `china_story_evaluation` | 评测主卡：Part 3 表达质量与修订反馈 |
| `china-story-active.md` | `china_story_active` | 主动内容路由 |
| `intl-comm.md` | `intl_comm` | 团队铁律（证据 + 语气 + 主动成稿）——**always_on** |
| `evidence-user-materials.md` | `evidence_user_materials` | 双源论据硬规矩——**always_on** |
| `planning.md` / `coding.md` / `research.md` / `data-analysis.md` | 同名 | 通用技能，均在 `manual_activation.disabled` 中，默认不激活 |

## 体裁目录

| genre | 生效文件（v6.1） | 状态 |
|-------|------------------|------|
| post | `china-story-generation/references/genres/post.md` | complete |
| news | `.../genres/news.md` | complete |
| feature | `.../genres/feature.md` | methods_in |
| indepth | `.../genres/indepth.md` | methods_in |
| script | `.../genres/script.md` | methods_in |
| faq | `.../genres/faq.md` | methods_in |

字符预算：单卡上限 12000、总上限 24000（`config/skills.yaml`）；`discover_files` 已关闭，未注册的根级 md 不会被当成技能加载。

总表：本文件  
路由：`tools/genre_router.py`  
门禁：`tools/load_story_knowledge.py`

**默认体裁：** post  
**Tier-1 format：** social_post / thread / news_article / visual_story / short_video / press_kit
