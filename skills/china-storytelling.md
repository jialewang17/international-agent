---
name: china-storytelling
description: |
  讲好中国故事成稿入口。先识别体裁再读对应 genres skill；
  生成前必须调用一次 load_story_knowledge。默认 post。
  Skill 不更新知识库。细则见 skills/china-storytelling-reference.md。
knowledge_dependencies:
  - knowledge/storytelling_framework.txt
  - knowledge/writing_methodology.txt
  - knowledge/content_formats.md
  - knowledge/format_examples.md
  - skills/genres/README.md
  - skills/evidence-user-materials.md
---

# 中国故事成稿（入口）

共用铁律：`intl-comm.md`。主动路由：`china-story-active.md`。长表：`china-storytelling-reference.md`（勿整篇注入）。

## 何时用

用户要主动生成中国故事内容（帖 / 通稿 / 特稿 / 脚本 / FAQ 等）。

## 步骤（必须按序）

1. **认体裁** `detect_genre` / 关键词表；未写 → 默认 **`post`**。
2. **定 format**（如 social_post / news_article / short_video）；用户说形态没想好 → 先列 Tier-1 再问，确认后写。
3. **读库一次** `load_story_knowledge(format=..., topic_hint=...)`；仅当 `gate=ready_to_generate` 才成稿。
4. **只读一本**对应体裁 skill（禁止串味）：
   - post → `genres/china-story-post.md`
   - news → `genres/china-story-news.md`
   - feature → `genres/china-story-feature.md`
   - script → `genres/china-story-script.md`（`methods_in`）
   - faq → `genres/china-story-faq-mythbust.md`（`methods_in`）
5. 有用户粘贴资料 → 遵守 `evidence-user-materials.md`。
6. 按该体裁字段输出；附 `genre` /（如需）`genre_status` / `knowledge_loaded: true`；提醒人工审核。

## 体裁 → 主输出（速查）

| genre | 主字段 |
|-------|--------|
| post | `five_w` + `post` / `hashtags` |
| news | `headline` / `dek` / `article` |
| feature | `body` / `one_liner` / `five_dimensions` |
| script | `shots[]` |
| faq | `items[]`（myth+fact） |

## 红线

- 未读库不成稿；同轮不重复调 `load_story_knowledge`
- 通稿禁 emoji/CTA；帖文禁电头长通讯；FAQ 禁无误解对立硬凑；脚本禁假精确钟点
- 材料没有的数字/姓名/职务/精确秒数 → 不写
- 不抬杠目标国受众；Skill 不改知识库

## 优先级

真实性 > 用户素材 > 知识库 > 体裁写法 > 文采
