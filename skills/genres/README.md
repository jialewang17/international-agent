# 体裁 Skill 目录与权威依据

| 体裁 ID | 文件 | 状态 | 细节依据（禁止无依据编造） |
|---------|------|------|---------------------------|
| `post` | `china-story-post.md` | **已启用** | Harold Lasswell 5W（1948）；老师 0822「贴文用 5W」；intl-comm |
| `news` | `china-story-news.md` | **已启用** | 官媒长文语料库约100篇（`docs/corpus/`）；新华/中国日报/CGTN 通稿骨架；与 post **独立** |
| `feature` | `china-story-feature.md` | 占位 | 待南方周末/深度叙事材料；老师：长模板不适短帖 |
| `script` | `china-story-script.md` | 占位 | 待短视频/讲好中国故事研究材料 |
| `reply` | （`intl_comm` + `intl_comm_reply`） | 已有 | 专利/材料两段 Prompt |

参照（不默认注入）：`china-story-news-reference.md`

路由实现：`tools/genre_router.py` → `tools/story_post_gen.py`  
- post → `prompt/story_post_prompt.txt`  
- news → `prompt/story_news_prompt.txt`
