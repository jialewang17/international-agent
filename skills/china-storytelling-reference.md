# 入口附录（默认不整篇注入）

主工序卡：`china-storytelling.md`。本文件仅在需要对照长表时查阅。

## Tier

| Tier-1（默认可选） | Tier-2（用户明确才用） |
|--------------------|------------------------|
| social_post, thread, news_article, visual_story, short_video, press_kit | explainer, quote_card, reel_hook, caption_only, longform, headline_pack, newsletter_brief, youtube_script, podcast_script, faq_mythbust, talking_points, bilingual_pair |

字段与样例：`knowledge/content_formats.md` / `format_examples.md`（工具返回摘录）。默认英文海外向。

## 体裁 ↔ format

| 用户说法 / format | genre | 主字段 |
|-------------------|-------|--------|
| social_post / thread / visual_story / caption_only / 帖文 | post | five_w + post/hashtags |
| news_article / press_kit / newsletter_brief / 通稿 | news | headline/dek/article |
| longform / 特稿 / 深度 | feature | body/one_liner/five_dimensions |
| short_video / reel_hook / 口播分镜 | script | shots[] |
| faq_mythbust / 误解澄清 / FAQ | faq | items[] myth+fact |

## 结构适配（读 framework 后用）

| 主题 | 必选 | 优先扩展 |
|------|------|----------|
| 科技 | A+B+C | D 蜕变, F 数据 |
| 文化 | A+B+C | E 人物, D 蜕变 |
| 生态 | A+B+C | D 蜕变, F 数据 |
| 社会 | A+B+C | E 人物, D 蜕变 |
| 国际合作-项目 | A+B+C | F 数据, E 人物 |
| 国际合作-理念 | A+B+C | H 隐喻 |

先有素材再定结构；不为凑模块而虚构。

## 软虚构禁令

用户未提供则不写：精确钟点/秒数、未给姓名职务、未给年限/百分比/大额数字、未给制度旁支。  
允许：同义改写已给事实；模糊时段；缺料追问或 `omitted_reason`。

## 生成前检查（可选默念）

- 已认 genre 并读对应体裁 skill  
- 已调一次 load_story_knowledge  
- 无空壳核心、无虚构、缺料已处理  
- 未串味；有用户资料时区分 source_type  
- 无口号开篇、无空赞美、不抬杠他国  
