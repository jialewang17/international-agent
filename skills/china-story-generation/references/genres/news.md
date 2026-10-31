# 体裁方法：News v3.1（报道 / 新闻稿 / 短消息 / Newsletter / Press Kit）

> **版本**：v3.1（2026-10-18 研究修订稿）  
> **替换位置**：`china-story-generation/references/genres/news.md`  
> **上游版本**：用户上传 `ChinaStory-final-skills-v2.1.zip` 中同名文件。  
> **边界**：这是 Generation 内部的新闻写作方法；Ground 负责证据来源；Plan 负责报道主题与受众策略；Evaluation Part 1 核验事实；Part 3 评价可理解性和体裁表达；人工编辑决定是否发布。  
> **来源索引**：`[N-S01]` 等标识的资料链接见末尾；逐项变化和测试编号见 v3.1 修改说明。

## 1. 确定新闻用途与来源身份 [N01]

- **适用**：`genre=news`，`format=news_article|newsletter_brief|press_kit`，包括素材支持的短消息、通讯和机构新闻通稿。
- **不适用**：`post/feature/indepth/script/faq`；不能将新闻稿自动包装成独立新闻机构的现场报道。
- 读取 `TaskContext`、`ContentPlan`、`EvidencePack` 与发稿方身份；首先识别**报道性质**：

| `editorial_mode`（内部判断，非新增必填 JSON 字段） | 如何写 | 不得声称 |
|---|---|---|
| `reported_news`（独立报道稿） | 只有在材料足够支持独立来源核查和必要观点/回应时才用；清楚列出处 | 记者亲访、采访、媒体在场，除非确有证据 |
| `institutional_release`（机构新闻稿） | 以已授权机构为发稿主体；事实依来源写，保留“该机构称/据发布材料”归属 | 冒充第三方媒体独立调查的事实结论 |
| `newsletter_summary`（简讯） | 对已证实或已明确归属的事件作摘要，并标注消息来源 | 把组织方声明自动升格为中立调查结论 |
| `press_kit`（素材包） | 按已有事实、权利和来源提供要点、新闻摘要、可选标题 | 虚构媒体评价、引语、图片版权 |

如果发布主体或报道性质影响真实性但没有给出，返回 `missing_context[]` 而不是假装独立记者。[N-S01][N-S02][N-S03]

## 2. 前置条件：事实包、时效与报道价值 [N02][N03]

1. 确认 `evidence_pack.gate=ready_to_generate`；否则只报告 `blocked` 和缺项，不补造新闻。[N-S07]
2. 从已有证据识别**真正有新闻性的可验证新信息**：发生了什么变化、在哪个时间范围、涉及谁、对谁有意义。如果仅有普遍文化背景而没有新闻事件，建议调用方转为 `post` 或 `feature`，**但本卡不得私自改动用户已确认的 genre**。[N-S04]
3. 时间分三类：`event_time`（事件发生时间）、`source_date`（来源发布时间）、`draft_time`（本次生成时间）。只按证据填前两者，不把当前日期写成事件日期；较旧来源不能无提示写成“今天/本周/最新”。[N-S02][N-S07]
4. 需要实地采访、实时确认、官方更新或争议回应而材料不足时，在 `missing_fields[] / research_gaps[] / needs_human[]` 标明；**不模拟打电话、实地探访或记者核验**。[N-S01][N-S02]
5. 对数值、名称、政策和争议结论，按 Generation `output-contracts.md` 生成 `evidence_map[]` 待 Part 1 核验；不自行裁决 Ground 未解决的来源冲突。[N-S07]

## 3. 不再把“新闻八步”设为固定全文模板 [N04]

**默认 `news_article` 使用“重要事实优先”的倒金字塔结构。** `lede`（导语）优先回答已经确知且读者最需知道的 Who、What、When、Where；Why/How 未证实就留出边界而不是补猜。

推荐写作顺序：

1. **准确标题**：展示主要有据事实或变化，不夸大规模和结果。
2. **导语**：最重要的新信息；没有明确事件时间时不自造“近日”“昨晚”。
3. **支撑段**：给出关键事实、证据归属、受影响范围和必要背景。
4. **发展段**：已核实的机制、数据、引语、差异或争议；不是每篇都需要出现这四类材料。
5. **收束**：如有可核验后续步骤或未解决问题，克制说明；不要加社媒式 CTA。

**场景导语是可选的例外**：只有真实事件现场、动作、感官细节被证据支持，且不会延误读者获取核心新闻事实时才使用。人物证言、权威引用、数据、机制等是**可选材料模块**，绝不为了补齐八个槽位而捏造。新闻通讯在证据充分时可有更多场景，但不可把 News 偷换成 Feature。[N-S04][N-S02]

## 4. 归属、独立性与核实强度 [N05][N06]

- **区分事实与主张**：机构宣布的计划用“机构宣布/计划”；尚未完成的目标不能写成已经实现。宣传资料中的自我评价用“该机构表示”，不偷换成独立证实的客观结论。[N-S01][N-S02]
- **归属要具体**：可争议的事实、数据与评价明确写明“据××机构在××日期的报告/声明”；不要只写“专家认为”“资料显示”“有消息称”。网页材料需归属原始来源，不能把转载媒体和原始报告混同。[N-S02]
- **消息来源层级**：仅有单一机构声明→只能形成明确来源归属的新闻稿或审慎摘要；独立新闻报道涉及重大争议或影响他人时，应由 Ground/人工编辑获取独立来源与必要回应，不能假装已平衡核验。[N-S01][N-S02]
- **匿名来源**：不得由模型创造匿名知情人、模糊“内部人士”。确实由上游提供并获编辑授权使用时，按证据记录其身份说明和核查条件，交人工核对；无授权时不用。[N-S02]
- **公正不等于机械制造对立**：涉及实质性争议、指控或负面影响时，准确归属指控并给相关主体合理回应机会；若上游没有回应材料，标记 `needs_human[]`，不自行伪造“对方拒绝置评”。[N-S01][N-S02]
- **版权与来源**：原句和数据按授权与引用规范使用；不得整段复制第三方稿件后当原创。图片、视频和档案素材来源须单独核实，无法确认授权时不输出“可发布素材”。[N-S02]

## 5. 引语、数字、因果与标题的专项规则 [N07][N08][N09]

| 元素 | 必须遵守的写法 | 禁止 |
|---|---|---|
| 引语 | 逐字使用上游确有文本；附说话者、来源、语境和原文定位；译文保留 `translation_note`，必要时注明译自何种语言 | 把意译放进引号、臆造发言或修正其含义 |
| 数据 | 保留数值、单位、时点、统计地域、分母/样本、比较口径；缺任何关键项则缩小结论或标注缺口 | “数十”变成精确数、样本结果变全国、相关当因果 |
| 因果 | 若资料只观察到同期变化，明确区分观察与推断；不能把共现写为“促成/证明” | 因果夸大、趋势外推 |
| 标题 | 具体、精确、与导语一致，可引用有来源的动作和变化；`dek` 补充而非扩大标题 | 虚假“首个/最大/震惊/全面突破”等、与正文不符的承诺 |
| 新闻电头/署名 | 只有证据确实说明记者所在地/报道地点/发稿主体时使用；其他情况不要伪造专业外观 | 生成假的通讯社电头、记者在场或采访身份 |

AP 关于引语、译文、归属、电头、素材许可的细则可作专业参考；Google 的简洁准确标题规则属于**搜索展示指南**，不是独立的新闻伦理准则，不能以此代替 AP/Reuters。[N-S02][N-S05]

## 6. 跨语言再创作与 AI 参与 [N10]

- 遵循 Generation 的“中文母稿 → Transcreation → 目标语成稿”流程；国际传播目标语可以重排背景解释顺序、为陌生文化概念加最短说明，但**不能改变事实、引语归属、因果强度和消息源身份**。[N-S02]
- 特定文化传统、传承人和社区不得被写成单一同质化群体；涉及社区观点仅在材料可证并适当授权时使用。[N-S06]
- AI 生成的新闻文本是**草稿**。来源真实性、关键事件核实、公平性、图片使用和是否发布由人类编辑负责；若 AI 在最终内容中起实质作用，相关公开披露遵守机构政策和适用要求。[N-S03]
- 不自动出稿为 `APPROVED`、不自动发布；需要更新或纠错时，应通过后端 ContentVersion、Part 1、Fact Lock 与人工审批流程，**不能通过偷偷改写旧文掩盖错误**。[N-S01][N-S03]

## 7. 与 v2.1 输出契约完全兼容 [N11]

**顶层输出仍由 Generation SKILL.md 控制**：`genre=news`、`format`、`master_ref`、`target_version`、`evidence_used[]`、`evidence_map[]`、`human_review=PENDING` 等字段保留。

| `format` | 保留原字段 | 说明 |
|---|---|---|
| `news_article` | `headline`, `dek`, `article`, `evidence_used` | 如果必要事实不足，返回缺料字段/阻塞状态，不捏造导语 |
| `newsletter_brief` | `subject_line`, `preview_text`, `body` | 来源可见、重点准确；CTA 仅在明确的机构信息用途和用户要求下使用 |
| `press_kit` | `news_blurb`, `headline_pack`, `key_facts`, `omitted_reason` | `key_facts` 只能来自证据；没有支撑的引语/图片段落标明省略原因 |

**不新增必须由旧版 API 消费的顶层字段。** `editorial_mode`、`event_time` 等用作内部检查或由调用方的 `TaskContext`/`ops_tips`、`needs_human[]` 承载；若团队准备正式写入 Schema，应由 Backend 同步调整。

## 8. 执行检查表（不是 Part 1 的替代品）[N12]

- [ ] 新闻性质明确，不把机构新闻稿伪装为独立采访报道。
- [ ] 导语包含已核实的最重要事实，不被必须执行的八段模板拖慢。
- [ ] 事件时间、来源时间、文本生成时间没有混淆。
- [ ] 事实归属足够具体；单一来源、匿名消息和争议回应风险已标注。
- [ ] 所有引语、数字、因果和专有名词都在 `evidence_map[]` 记录待核查信息。
- [ ] 没有自造电头、记者身份、现场细节、资料来源、摄影素材或使用权。
- [ ] 标题与正文一致，译文忠实，文化概念解释不过度扩写事实。
- [ ] 原定 `format` 字段结构不变，`human_review=PENDING`，交由 Part 1/Part 3 和人工审核。

## 9. 依据索引

- **[N-S01] Reuters**，News Standards and Values；来源、准确性、独立性、公平回应与纠错：<https://reutersagency.com/about/standards-values/>。
- **[N-S02] Associated Press**，Telling the Story；归属、引语、匿名来源、材料使用、电头及媒体伦理规范：<https://www.ap.org/about/news-values-and-principles/telling-the-story/>。
- **[N-S03] Associated Press（2026-07-23）**，更新的 AI 新闻编辑规范：AI 可辅助翻译、标题和摘要，但核实、编辑判断、出版责任仍由人承担：<https://www.ap.org/the-definitive-source/announcements/ap-updates-newsroom-standards-for-artificial-intelligence/>。
- **[N-S04] Purdue OWL**，Inverted Pyramid；最重要的 5W 新闻事实优先，细节依重要性后置：<https://owl.purdue.edu/owl/subject_specific_writing/journalism_and_journalistic_writing/the_inverted_pyramid.html>。
- **[N-S05] Google Search Central**，标题应准确、简洁、避免关键词堆砌（**网络标题展示参考**，非新闻行业强制规范）：<https://developers.google.com/search/docs/appearance/title-link>。
- **[N-S06] UNESCO**，非遗伦理与社区主体性：<https://ich.unesco.org/en/ethics-and-ich-00866>。
- **[N-S07] Min et al.（EMNLP 2023）**，FActScore 原子事实及证据支持研究：<https://aclanthology.org/2023.emnlp-main.741/>。
