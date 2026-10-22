# Genre 专项内容质量检查（Evaluation v5.1，归入 D5，适当辅助 D1/D4/D6）

> 本文只评价**内容表达与形式**。事实、来源、门禁由 Ground/Part 1/后端负责。平台字数和输出字段有效性是后端确定性检查，不能用 D5 高分掩盖接口不合格。[E01/E02][S01–S03]

## 1. Post v3.2 专项 [E01]

按 `format` 评价文字结构；如有真实媒体，读取后端提供的 `media_manifest`，没有则标记无法判断视觉表现。[S10]

| 形式 | D5/D4 等质量问题 | 后端硬规则 / 明确排除 |
|---|---|---|
| `social_post` | 是否围绕一条主点展开；5W 的已确认目标是否体现在读者可见文本；是否过度口号化；Hook 是否与证据吻合 | `hashtags` 个数、平台字符/字数与字段结构由代码校验；不按个人偏好机械奖励更多标签 |
| `thread` | `posts[]` 是否**逐条有独立信息进展**，顺序合理，Hook 不夸张，结尾符合传播目标 | X 每条加权字符需后端 `twitter-text` 类工具计算；Judge 不按普通字符串长度自裁硬限制 |
| `visual_story` | `slides[]` 的封面标题、逐页信息分配、逻辑推进是否清楚；画面计划与正文是否匹配 | 没有上传真实图片时不打“实际 Alt Text 准确性”分；`alt_text=""` 不是无障碍失败的自动证据 |
| `caption_only` | 已有图片时配文与图像/目标受众是否相关；不强制提问式 CTA | 无图情况下只评价可见文字与配文策略，不编造“图片里有……” |

**注意**：Post v3.2 将四种叙事模式（场景体验、知识解释、人物、事实对照）与简洁非叙事组织方式一起列为**可选编辑策略**，评测时检查所选方式是否适配**已提供证据与目标**，不要求每篇都有场景/感官或统一 CTA，也不强求四选一。[S10][S01]

**Post v3.2 新增检查点**（归入 D5，辅助 D1/D4/D6）：

- **format 专属字段完整性**：`thread` 应有逐条 `posts[]`、`visual_story` 应有逐页 `slides[]`、`caption_only` 应有 `caption`；若产出只是单一 `post` 字符串冒充其他格式完成，属于生成/接口问题，不以 D5 高分掩盖。后端 format 参数接线完成前，按"方法已定义、运行暂不支持"处理，不强行评分。
- **caption_only 素材三态**：区分"有真实媒体""只有可靠的素材描述""完全无素材"——无图时不得出现"图片里有……"式断言，待核配文应可识别。
- **visual_story 逐图描述**：有真实多图时，检查是否为承担独立信息的图片分别提供 Alt Text，而不是整组一个笼统描述；无实图时只评画面规划文字，`visual_brief` 不得冒充实际图片描述。
- **format × platform 组合适配**：如 X 上的 `thread` 是原生连续帖，Instagram Feed 上的 Thread 非原生等价格式——评测可提示重规划，平台字符/媒体硬校验仍归后端。

**平台与无障碍**：参照 Generation 的 Post v3.2 方法（在完整项目中由独立的 `china-story-generation/references/genres/post.md` 提供）时，区分官方硬限制与编辑建议；**独立安装 Evaluation Skill 不依赖另一 Skill 的相对路径**。实际图片 Alt Text 根据 W3C 的信息性/装饰性用途判断，不能要求所有实际图都必须写很长。[S10][S11][V51-10]

## 2. News v3.1 专项 [E01]

先读取上游 `editorial_mode`（如有）。如果用户/Planner 未提供且其缺失会影响新闻性质判断，应要求补充，不得自动推断稿件是独立记者报道。[S12]

| 类别 | D5/D6 专项检查 | 不越权的限制 |
|---|---|---|
| `news_article` + `reported_news` | 导语是否把关键可信事实放前；归属可读清晰；标题/导语/正文一致；风格克制 | 是否独立采访、事实正确、引语属实 → Part 1 / 人工核查 |
| `news_article` + `institutional_release` | 是否显式保留机构声明/发布来源，不伪装为媒体独立调查；发布目的清楚 | 机构合法授权/采访资格不能由 Judge 推断 |
| `newsletter_brief` | 主次清晰、已有来源标注、篇幅与用途相符 | 外部点击率、邮件打开率不可由 Judge 声称 |
| `press_kit` | 事实要点易查阅；可供人工编辑使用；省略项解释明晰 | 图片使用权、引语许可、原事实与数字 → Part 1 / 人工 |

适用全部 News 的判断：

- 不把新闻“八步”当作强制模板；导语应符合信息优先原则，场景仅在**确有资料**时加。[S12]
- 观察消息归属是否**以文字形式明确呈现**；若怀疑归属不实，只移交 Part 1。
- 避免营销 CTA、耸动形容词、第一人称虚构采访，区分机构自述与独立报道。[S12]
- 涉及真实争议、指控或负面影响：不机械制造正反五五开；仅根据资料描述回应是否提供，不捏造拒绝置评；缺回应→`needs_human`/Part 1。[S12]
- 若认为报道因未证事实可能误导，不“扣掉 D2 几分便准许发布”；改为 `return_to_part1=true`。

## 3. 其他四类体裁（保留 v2.1 专项方法，非本次改写重点）

| Genre | D5 主检查 | 关联维度与边界 |
|---|---|---|
| Feature | 素材篇幅与内容展开相称；场景与人物推进是否有叙事功能；不混入新闻通稿、营销 CTA | D4 叙事推进；材料细节真实性由 Part 1 |
| Indepth | 研究问题是否清晰；子问题有组织地回答；论证边界可见；不是用场景代替机制 | D1 解释；证据冲突或数据口径交 Part 1 |
| Script | VO、镜头、字幕关键词的对应是否明确且可执行；节奏与目标平台匹配 | 如果无真实视频，只评脚本可拍性，不能评成片效果 |
| FAQ | Myth–Fact 是否围绕真实提供的误解；回答范围清晰、没有讽刺受众 | 误解真实性/事实支持交 Part 1 |

## 4. 评测中的缺少素材/不可评分范围

- 如没有真实图片，不检查实际图片的 `alt_text` 准确性；可评价画面规划文字是否清晰。
- 如果缺少一个**决定性**的体裁上下文（比如 News 不知发稿身份），返回 `INSUFFICIENT_CONTEXT` 或明确限制，不将猜测作为 D5 评分依据。
- `post`/`news` 的确定性规则（JSON 字段、字数、X 加权字符、发布权限）由 Backend Validator 执行，Part 3 可接收执行结果供编辑建议参考，但不替代程序。

## 5. 依据

- [S01] [ChinaStory Rubric v2.1](https://github.com/jialewang17/international-agent/blob/main/eval/CHINASTORY_CONTENT_QUALITY_RUBRIC_v2.1.md) D4/D5/D6。
- [S10] 本次包 `china-story-generation/references/genres/post.md`（Post v3.2，2026-10-22 审查修订）；[W3C Images](https://www.w3.org/WAI/tutorials/images/)。
- [S11] [W3C Image Alternatives](https://www.w3.org/WAI/tutorials/images/informative/)。
- [S12] 本次包 `china-story-generation/references/genres/news.md`（News v3.1）；[AP Telling the Story](https://www.ap.org/about/news-values-and-principles/telling-the-story/)。
