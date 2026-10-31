# ChinaStory Post & News v3.1｜逐项修改记录、证据链与工程说明

> **版本日期**：2026-10-18  
> **基线**：用户上传的 `ChinaStory-final-skills-v2.1.zip`，具体比较对象：`china-story-generation/references/genres/post.md`（39 行）、`news.md`（33 行）。  
> **产物**：`ChinaStory_Post_v3.1.md`、`ChinaStory_News_v3.1.md`、`ChinaStory_Post_News_v3.1_Tests.md`、完整 v3.1 文件包。  
> **原则**：只调整 Generation Skill 两个体裁内部的方法，不调整两个顶层 Skill 数量，不复制 Ground/Fact Check/Evaluation 的职责；保留 v2.1 `output-contracts.md` 的字段，接口新增项列为后端候选而非直接强制变更。  
> **重要说明**：这里记录的是**外部资料支持某项设计的理由**，不是“相关研究证明 v3.1 必然胜过 v2.1”。质量提升仍须通过同样输入的 A/B 测试判定。

## A. 证据等级与适用边界

| 代号 | 材料类型 | 可以证明什么 | 不能证明什么 |
|---|---|---|---|
| P | 平台/监管/官方新闻标准 | 该机构公开规定的功能、限制、规范和责任 | 不能直接证明某种文案的曝光率更高；不能跨平台外推 |
| J | 新闻专业规范与教材 | 新闻采写、归属、引语和报道结构的成熟要求 | 不是中国法律，也不自动适用所有机构稿件 |
| R | 学术研究 / 专业共识报告 | 支持事实拆解、受众差异等设计原则 | 不保证某个具体开头或字数一定最有效 |
| I | 本项目工程推导 | 根据已有 v2.1 架构、字段和需求做出的兼容性选择 | 不是外部事实、法律要求或平台强制规定 |
| S | 经过核对的二手行业报道 | 可暂时为平台变动提供保守实施依据 | 不能冒充平台可直接访问的一手政策页面 |

**证据复核日期**：2026-10-18；平台规则实施范围、API 与账号权限应由后端在发布前再次核实。**Post 的“Instagram 5 标签”来源是 Social Media Today 2025-12 对 Instagram 声明的转引，属 S，不是本次直接验证的 Instagram 一手帮助页。**

## B. Post 的 12 项修改：每项旧规、新规、理由、证据、测试

| 编号 | v2.1 所在位置 / 原规则 | v3.1 修改 | 为什么 / 外部依据及证据类型 | 测试 |
|---|---|---|---|---|
| **P01** | 第 13 行要求确认 `identity`、`audience`，未明确如何防止错误人设 | 默认中性叙述；缺少授权不得冒充博主亲历、采访者或社区发言者；优先使用 Plan 给定受众 | [E01] 美国国家科学院指出受众既有知识和需求影响沟通；[E02] UNESCO 非遗伦理强调相关社区的自主权（R/P）；v2.1 架构 Define/Plan 不归生成侧（I） | `P-T01` |
| **P02** | 第 14、18–26 行 5W 只给简要字段 | Who/Says What/Channel/To Whom/Effect 成为明确的只读规划映射；预期 Effect 与真实指标分开 | [E01] 目标决定沟通方式，传播效果必须通过评估得知（R）；[E03] Meta 将创作/互动/触达分为不同指导领域（P） | `P-T02` |
| **P03** | 第 15 行几乎固定“场景→锚点→事实→提问” | 改为场景、知识解释、人物、事实对照四种条件式写法；场景和人物必须有证据 | [E01] 受众和目标影响表达方式，并不支持唯一固定模板（R）；避免创造现场细节来自 [E04] 原子事实研究（R）；四模式本身是项目写作策略（I） | `P-T03` |
| **P04** | 第 14、28、39 行要求证据可核验，但未按事实类型讲解 | 增加数字、引语、因果、场景等 Claim→Evidence 细化，材料不足必须缩短、退回补料 | [E04] EMNLP FActScore 支持逐原子事实追溯来源（R）；复用本项目 `output-contracts.md`（I） | `P-T04` |
| **P05** | 第 25 行“目标读者可感桥梁”比较抽象 | 以文化术语最短解释为主，禁止虚假文化等同和未授权社区代言 | [E02] UNESCO 社区主体性、尊重与知情同意（P）；[E01] 受众知识差异（R） | `P-T05` |
| **P06** | 第 39 行 CTA 可选但没有边界 | CTA 区分信息收束/自然提问/准确参与，禁止诱导互动并不保证效果 | [E05] Meta **仅针对 Facebook** 公布降低 engagement bait 分发的政策（P）；v3.1 把它转化为跨平台的编辑谨慎原则（I），不外推同等惩罚 | `P-T06` |
| **P07** | 第 16、32 行使用 hashtags，但没有平台上限与证据 | Instagram 安全侧采用 0–5 个相关标签；记录规则快照与发布前再检查 | [E06] 2025-12 Social Media Today **转引 Instagram 声明** 将帖子/Reels 标签逐步限为 5（S）；[E03] Meta 官方鼓励依据数据更新创作方法（P） | `P-T07` |
| **P08** | 第 13 行只有 platform 参数，没有 X 限制验证 | 普通 X 逐帖使用加权字符计算；长帖要求上游确认账户权限 | [E07] X Help 规定典型 280、长帖权限和更高上限（P）；[E08] 官方开源 twitter-text 规定 URL、Unicode、emoji 加权实现（P） | `P-T08` |
| **P09** | 仅强调“不假装知道最佳长度”，未给已核实限制 | LinkedIn 普通帖按官方 3,000 字符上限做确定性检查 | [E09] LinkedIn Help 公开普通帖上限（P）；账号与 API 例外再核验（I） | `P-T09` |
| **P10** | 第 16、34–35 行要求 `alt_text` 但未限定图像是否存在 | 有实图才生成 Alt Text；无图时使用空字符串作为旧接口哨兵，画面建议另给 | [E10] W3C WAI 图像文本替代规范（P）；[E11] X 图片描述指南（P）；空字符串兼容是项目接口设计（I） | `P-T10` |
| **P11** | 第 30–35 行列四形态字段但缺回归兼容说明 | 保留原 `post/five_w/hashtags/platform` 等字段，不擅自重命名；补充简短行为要求 | 本地 v2.1 `output-contracts.md` 和生成主卡字段契约（I）；平台约束由 [E07][E09] 等触发 | `P-T11` |
| **P12** | 第 37–39 行红线不足以作为验收清单 | 按身份/证据/平台/无障碍/商业披露/人工审核建立前置清单 | [E12] FTC 要求面向美国消费者的有实质利益关系推荐清楚披露（P，条件适用）；[E02][E04][E10]（P/R） | `P-T12` |

**特别强调**：P03 的四种叙事模式是项目设计假设，并非“经学术研究证明最优”；P06 的 Facebook engagement bait 规范不是 Instagram 政策；P07 的限额消息已明确标识为“行业报道转引官方”，不会冒充一手验证。

## C. News 的 12 项修改：每项旧规、新规、理由、证据、测试

| 编号 | v2.1 所在位置 / 原规则 | v3.1 修改 | 为什么 / 外部依据及证据类型 | 测试 |
|---|---|---|---|---|
| **N01** | 第 8 行把“新闻稿、通讯、短消息、newsletter、press kit”合称 news | 明确独立报道、机构新闻稿、新闻简讯、素材包四种来源身份，不伪造媒体角色 | [E13] AP 严禁将机构新闻稿原样作为独立报道，并要求有来源归属（J）；[E14] Reuters 强调独立性和准确性（J） | `N-T01` |
| **N02** | 第 13 行只要求“材料少缩短” | 明确事件新信息/报道价值，不能把长期文化背景伪装为今日新闻 | [E15] Purdue 倒金字塔强调最重要事实先行（J）；[E13] AP 对事实和出处的要求（J）；新闻性判断是项目应用推导（I） | `N-T02` |
| **N03** | 第 14、18–23 行只有一个“时间节点”，缺时间源区分 | `event_time`、`source_date`、`draft_time` 分开，不用系统日期替代事件时间，不凭空写电头 | [E13] AP 新闻电头与来源时间/地点的区分（J）；[E04] 来源可验证性（R） | `N-T03` |
| **N04** | 第 14 行固定八步：地点/场景/具名人物/时间/机制/权威/数据/收束 | 新闻导语事实优先，按重要性展开；人物、数据、引语、场景均可选 | [E15] Purdue 对新闻倒金字塔及 5W 的说明（J）；[E13] AP 禁止造细节（J） | `N-T04` |
| **N05** | 第 15 行绑定证据，没有讲清单一机构来源的归属 | 将“机构称/计划”与记者独立证实的事实分开；明确消息源 | [E13] AP 归属规则、机构通稿必须核查（J）；[E14] Reuters sourcing 与偏见独立（J） | `N-T05` |
| **N06** | 第 31–33 行只列“无虚构” | 不能创造匿名知情人、假记者、假现场；匿名材料和负面指控转人工编辑 | [E13] AP 对匿名来源、获批与回应义务的规定（J）；[E14] Reuters seek fair comment（J） | `N-T06` |
| **N07** | 第 15、22 行只写“数字有时间、单位、范围；引语逐字” | 加入译文原文记录，数字分母/可比口径，观察与因果区分 | [E13] AP 准确引语、翻译与归属（J）；[E04] FActScore 原子化支持判定（R） | `N-T07` |
| **N08** | 第 27 行新闻字段只有 headline/dek/article | 明确标题事实范围应与正文一致、`dek` 补充而不是放大；不填无依据的“首个/最大” | [E16] Google 标题应简洁准确是**网络展示建议**（P）；[E13][E14] 新事实须准确（J） | `N-T08` |
| **N09** | 第 15 行未独立强调匿名与利益相关主体回应 | 对争议陈述明确归属；缺另一方回应时 `needs_human`，不能生成“拒绝置评” | [E13] AP 对公平回应的明确规范（J）；[E14] Reuters fair comment（J） | `N-T09` |
| **N10** | 新闻卡仅称为人工审核稿，未具体说明生成式 AI 在新闻中的边界 | 明确 AI 只能产出草稿；编辑负责采访核实、素材、批准和必要披露 | [E17] AP **2026-07-23** AI newsroom standards（J）；不能把 AP 内规当所有国家的法律（注意适用范围） | `N-T10` |
| **N11** | 第 25–29 行固定三个 format 字段但没有兼容性说明 | 保留 `news_article/newsletter_brief/press_kit` 原字段，使用 `omitted_reason` 明示未提供的素材 | [E13] 来源和材料使用（J）；本地 v2.1 的字段契约（I） | `N-T11` |
| **N12** | 第 31–33 行主要是禁词列表 | 增加可执行清单：新闻类型、导语、时间、来源、引语、标题、人工审批 | [E13][E14][E15][E17] （J）；这是一份项目级质量自检，不等于 Part 1 已审核通过（I） | `N-T12` |

## D. 外部来源清单（每条标明用途，尽量使用一手资料）

| ID | 出处（原始链接） | 证据类型 | 本项目引用的准确范围 |
|---|---|---|---|
| E01 | [National Academies 2017: Communicating Science Effectively](https://nap.nationalacademies.org/read/23674/chapter/4) | R | 传播策略依目标与受众差异调整；**不证明某套帖文模板最优** |
| E02 | [UNESCO: Ethics and Intangible Cultural Heritage](https://ich.unesco.org/en/ethics-and-ich-00866) | P | 尊重社区表达和参与权、获取同意；并非所有文化描述的唯一标准 |
| E03 | [Meta: Instagram Best Practices 2024](https://about.fb.com/news/2024/10/best-practices-education-hub-creators-instagram/) | P | 官方区分内容创作、互动、触达等建议，并会更新 |
| E04 | [Min et al., FActScore, EMNLP 2023](https://aclanthology.org/2023.emnlp-main.741/) | R | 逐个原子事实核对支持性证据；不能由此证明来源本身可信 |
| E05 | [Meta 2017: Fighting Engagement Bait **on Facebook**](https://about.fb.com/news/2017/12/news-feed-fyi-fighting-engagement-bait-on-facebook/amp/) | P | **只说明 Facebook 平台的该政策**，对 IG 为创作规范类推，不作硬处罚宣称 |
| E06 | [Social Media Today 2025-12-18: Instagram five hashtags](https://www.socialmediatoday.com/news/instagram-implements-new-limits-on-hashtag-use/808309/) | S | **转引 Instagram 原话**：逐步将帖子/Reels 限为不超过 5 标签；未获取一手官方帮助页 |
| E07 | [X Help: About different types of Posts](https://help.x.com/en/using-x/types-of-posts) | P | 普通帖典型 280 字符、长帖账号权限与条件 |
| E08 | [twitter-text config README](https://github.com/twitter/twitter-text/blob/master/config/README.md) | P | X 加权计数、链接与 emoji 规则，实际应接确定性实现 |
| E09 | [LinkedIn Help: Post and share updates](https://www.linkedin.com/help/linkedin/answer/a528176) | P | 普通帖 3,000 字符上限，账户或 API 不同需复核 |
| E10 | [W3C WAI Informative Images](https://www.w3.org/WAI/tutorials/images/informative/) | P | 描述已存在信息性图片传达的信息，不应构造不存在的画面 |
| E11 | [X Help: Picture Descriptions](https://help.x.com/en/using-x/picture-descriptions) | P | 对真实图片提供简洁有意义的独立图片描述 |
| E12 | [FTC: Disclosures 101](https://www.ftc.gov/business-guidance/resources/disclosures-101-social-media-influencers) | P | 商业推荐者在相关美国消费者场景中披露实质性关系；**非全球统一法律** |
| E13 | [AP: Telling the Story](https://www.ap.org/about/news-values-and-principles/telling-the-story/) | J | 采访、新闻来源、匿名消息、归属、准确引语、资料使用、电头与更正 |
| E14 | [Reuters: Standards and Values](https://reutersagency.com/about/standards-values/) | J | 来源诚实、准确优先、独立、公平回应、透明纠错 |
| E15 | [Purdue OWL: Inverted Pyramid](https://owl.purdue.edu/owl/subject_specific_writing/journalism_and_journalistic_writing/the_inverted_pyramid.html) | J | 最重要事实前置、以 5W 写导语、随后按重要性展开 |
| E16 | [Google Search Central: Title Links](https://developers.google.com/search/docs/appearance/title-link) | P | 搜索结果标题需准确、简明；不是新闻道德规范 |
| E17 | [AP 2026: AI newsroom standards](https://www.ap.org/the-definitive-source/announcements/ap-updates-newsroom-standards-for-artificial-intelligence/) | J | AI 可辅助写作任务，但记者对编辑判断、验证、问责与出版负责 |

## E. 与 v2.1 架构、Skill 和 Python 后端的衔接

**这一次没有改写**以下文件的现有字段与行为：

- `china-story-generation/SKILL.md` 的主流程：Define/Ground/Plan 输入，中文母稿，Transcreation，六体裁，Fact Lock，人工审核。
- `china-story-generation/references/output-contracts.md`：原有格式到体裁映射、evidence_used 和 evidence_map。
- `china-story-evaluation/SKILL.md` 及其 D1–D6 评价规则。
- 四份 `handoff-to-backend` 和四个非 Post/News 的体裁参考文件。

**工程上需要额外联动，但本次不假设已经实现：**

1. `post.md` 的 X 字数校验应由 Python 使用 twitter-text 兼容算法，而不是要求 LLM 自己数。
2. `post.md` 的 Instagram 限额、LinkedIn 限额由平台配置/发布接口复核，发布前规则更新不能靠永远不变的 Markdown。
3. Post 缺图片时 `alt_text=""` 兼容当前文件中的文本输出约定，但建议后端定义清晰的空值 Schema；如需要 `visual_brief` 必须先确认接线。
4. News 的 `editorial_mode` 与 `event_time` 属内部说明，尚**未新增**为顶层 JSON 必填字段；正式开发需变更 TaskContext/Schema。
5. Evaluation Part 3 的 D5 可参考这两篇 v3.1 方法做体裁适配检查，但 D1–D6 评分标准和 Part 1 事实核验仍以原架构为准。
6. 本次仅完成 Markdown 方法升级和静态校验，不代表已经调用真实大模型进行质量对照实验。

## F. 建议的 A/B 评测设计

- **对照**：同一组苏绣/非遗/文化活动素材、同一用户目标、同一 EvidencePack、同一模型参数，分别运行 v2.1 和 v3.1。
- **硬检查**：Post 账号身份与事实边界、X weighted length、Instagram hashtags、图像 Alt Text；News 事件时间与来源归属、引语一致性、机构稿身份透明度。
- **软检查**：调用现有 Evaluation Skill 的 D1–D6 量表；D5 加入本轮 Post/News 体裁检查，不创建第二套加权总分。
- **人工评审**：盲评不少于两个评价者的样本，必要时包含目标语编辑；记录分歧。**传播效果**需在合适且合规的真实发布和读者反馈之后评价，不能由模拟文本直接推断。
- **失败回退**：v3.1 在任何硬检查中出现新增违规，不应凭软分更高就判定升级成功。

> **研究结论**：现有外部资料主要支持更可靠的来源约束、平台合规与新闻写作职责边界；而叙事模式、CTA 形式、帖文长度等表现性优化仍是需要通过真实受众测试验证的编辑假设。
