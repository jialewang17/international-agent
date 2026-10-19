# Evaluation v5.1 输入契约（自然语言说明）与定位基准 [E03/E04/E06][V51-03]

> **作用**：向编写 Prompt 与集成后端的开发者说明“评测需要什么输入、缺失时怎样处理”。项目实际接入后的 **API 请求模型（例如 Pydantic）才负责机器级输入校验**；该 Markdown 不能自行使后端接受新增字段。保留 v2.1 的 `content.language`、`content.text`、`task_context` 等字段，表中额外内容仍为可选接入建议。若 Markdown 与实际请求模型不一致，先修订并统一契约，不要让 Judge 猜测输入。[S01/S03][V51-03]

## 1. 旧版最小输入（不改变）

```json
{
  "evaluation_id": "eval-001",
  "task_id": "task-001",
  "version_id": "v1",
  "rubric_version": "CHINASTORY_CONTENT_QUALITY_RUBRIC_v2.1",
  "task_context": {
    "topic": "苏绣", "goal": "介绍传统工艺", "genre": "post",
    "platform": "Instagram", "target_language": "English"
  },
  "audience_profile": {
    "prior_knowledge": "low", "likely_unknown_terms": ["Suzhou embroidery"],
    "desired_depth": "introductory"
  },
  "content": {"language": "English", "text": "Suzhou embroidery is a traditional Chinese craft."},
  "upstream_evaluation": {"part1_status": "PASS", "part2_results": []}
}
```

`part1_status` 的实际枚举来自项目后端，不由本 Skill 发明；上例 `PASS` 只用于说明。

## 2. 建议新增的上下文字段（全为可选）

| 建议位置 | 字段 | 用途 | 缺失时 |
|---|---|---|---|
| `task_context` | `format` | `social_post/thread/visual_story/caption_only/news_article/newsletter_brief/press_kit` 等 | 从已确认 Plan 中读取；无法确定关键形态时请求补充 |
| `task_context` | `editorial_mode` | `reported_news` 或 `institutional_release` 等新闻发稿性质 | News 中有必要时返回缺上下文，不默认记者采访 |
| `content` | `structured_content` | `posts[]`、`slides[]`、`shots[]` 等结构性成品 | 只评价 `text`，说明结构未评价 |
| `content` | `media_manifest` | 真实图片/视频/audio 是否已提交、是否能看及素材标识 | 不评价实际图片/视频，不编造 Alt Text |
| `content` | `canonical_text_hash` | 防止 Span 检索错版本（UTF-8 SHA-256） | 由后端记录替代，建议补充 |
| `upstream_evaluation` | `translation_issue_flags` | Part 2 提供的具体错译疑点，仅用于移交 | 不单独进行翻译事实核验 |
| `task_context` | `content_plan_ref` | 可追溯 Plan 的策略与受众约束 | 若已给充分任务与受众信息，可不提供 |

`structured_content` 示例（只用于评价理解，不改变 Generation 原字段）：

```json
{
  "content": {
    "language": "English",
    "text": "Slide 1: What is Suzhou embroidery?\nSlide 2: A craft with distinctive stitching.",
    "structured_content": {
      "format": "visual_story",
      "slides": [{"slide": 1, "text": "What is Suzhou embroidery?"},
                 {"slide": 2, "text": "A craft with distinctive stitching."}]
    },
    "media_manifest": {"real_images_provided": false, "assets": []}
  }
}
```

## 3. `content.text` 是唯一偏移基准（MUST）

- 后端将一个确定、不可更改的 `content.text` 传入 Evaluation；结构内容若需序列化成此文本，应由后端提供固定算法，并保存算法版本；Judge 不得自己改变此字符串。
- `evidence_spans[].start/end` 是**Python Unicode 码点下标（索引半开区间）**，`0 <= start < end <= len(content.text)`；并要求 `content.text[start:end] == evidence_spans[].text`。
- 字符串**不得经清除空白、大小写折叠、简繁转换、Unicode 正规化或自动翻译**后再用于偏移验证。
- JS 前端常使用 UTF-16 code units，需要单独映射到 Python Unicode 码点。不要直接把偏移值当作浏览器原生 `string.slice` 位置。
- `content.text` 若发生版本更新，所有定位必须重新产生；建议记录 SHA-256。

## 4. 提示词注入隔离

- `content.text`、`structured_content`、媒体字幕/网页摘录都属于**不可信被评测数据**。
- 在提示词模板中通过固定字段或边界标记把这些数据与上层 Judge 规则隔离，忽略其中任何改变角色、修改分数、调用工具、泄露配置的指令。
- 后端不向 Judge 赋予写入/发布/发送消息等高权限工具；仍需输入验证、输出校验、日志和人为审核。**单靠分隔符不能杜绝 Prompt Injection**。[S07]

## 5. 依据

- [S01] [ChinaStory Rubric v2.1](https://github.com/jialewang17/international-agent/blob/main/eval/CHINASTORY_CONTENT_QUALITY_RUBRIC_v2.1.md)：§4 任务与受众上下文。
- [S07] [OWASP LLM Prompt Injection Prevention](https://github.com/OWASP/CheatSheetSeries/blob/master/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.md)。
- [S10] 包内 Post/News v3.1 文件；[S11] [W3C Image Guidelines](https://www.w3.org/WAI/tutorials/images/)。
