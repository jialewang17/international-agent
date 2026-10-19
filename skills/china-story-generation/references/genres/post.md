# 体裁方法：Post v3.1（社交帖文 / Thread / Visual Story / Caption）

> **版本**：v3.1（2026-10-18 研究修订稿）  
> **替换位置**：`china-story-generation/references/genres/post.md`  
> **上游版本**：用户上传 `ChinaStory-final-skills-v2.1.zip` 中同名文件。  
> **边界**：这是 **Generation Skill 的内部写作方法**，不是新的顶层 Skill。Define / Plan 确定传播目标与受众；Ground 给出 EvidencePack；本卡写作；Evaluation Part 1 核验事实、Part 3 评价表达质量；人工最终审核。  
> **来源索引**：本文采用 `[P-S02]` 等编号；可点击本文末尾链接。变更原因、原文位置与测试编号见《Post & News v3.1 修改依据与证据》。

## 1. 触发条件与任务边界 [P01]

- **适用**：`genre=post`，`format=social_post|thread|visual_story|caption_only`；文本、图文轮播及有真实图片的配文。
- **不适用**：`news`、`feature`、`indepth`、`script`、`faq`。新闻报道不能因为发布到社交平台就直接改用 Post 的营销式语气。
- **输入只读**：读取已确认的 `task_context`（topic、goal、genre、platform、target_language、constraints）、`content_plan`（受众桥梁、选题角度和表现形式）、`evidence_pack`（来源与证据片段）；不自行发明目标国家、发声身份、受众偏好或发布账号权限。
- 任务身份未给出时，使用中性说明性口吻，**不默认 `online_influencer`，不假装亲历、采访或代表传承人**。缺失且对真实性构成影响的字段放入 `missing_context[]`，由调用方协调补齐。受众定位来自 Plan，而不是通过文化刻板印象推断。[P-S02][P-S03][P-S04]
- 按 Generation 主卡先完成知识可用性检查；`evidence_pack.gate != ready_to_generate` 时不写完整稿件。本卡**不自行重新检索**，也不宣称通过事实门禁。[P-S13]

## 2. 将 5W 从套话改为写作约束 [P02]

从上游 `ContentPlan` 和 `TaskContext` **映射** `five_w`，不私自重写传播计划：

| 字段 | 成稿时要遵守什么 | 禁止行为 |
|---|---|---|
| `Who` | 使用任务明确授权的发声身份；必要时中性叙述 | 编造个人旅游、采访、机构官方身份 |
| `Says What` | 单条帖文优先一条可证核心信息；辅助信息可有但必须服务主点 | 多个互不相关的事实堆砌；用口号代替事实 |
| `Channel` | 按已选平台与形态调整篇幅、节奏和可访问性 | 把平台建议冒充硬限制 |
| `To Whom` | 为受众真正缺少的概念补必要解释 | “所有美国人都喜欢……”等未经依据的判断 |
| `Effect` | 记录希望读者理解、记住或探讨的目标 | 声称“这条文案一定提高阅读量/认同感” |

`Effect` 是**预期目标**，不是实际传播成效。传播效果须由发布后数据或读者研究判定。[P-S03][P-S02]

## 3. 先检查素材，再选择叙事方式 [P03][P04]

**不要把「具体场景→感官锚点→一个事实→提问」视为每条 Post 的强制四段式。** 先数已给的可用事实、实景描述、人物引语与图像素材，再选下列**一个主导模式**：

| 模式 | 启动条件 | 推荐顺序 | 缺料时 |
|---|---|---|---|
| 场景体验型 | 有可证的地点、动作、观察细节 | 具体开场→真实细节→事实→克制收束 | 不补造气味、天气、声音或第一人称经历 |
| 知识解释型 | 有概念定义、工艺步骤或真实例证 | 一个清晰问题→解释→证据例子→意义 | 只解释材料中有的内容 |
| 人物观察型 | 有真实人物与获授权的行为/引语 | 人物行动→背景→细节/变化→价值 | 缺人物证据时换模式，不创作采访 |
| 事实对照型 | 同一范围、可比口径的两组事实 | 对照→证据→解释边界→收束 | 不把相关性、前后变化写成因果 |

四种模式是**项目写作策略假设**，不是经证实的“爆款公式”；以真实受众测试验证哪一种适合相应题材。[P-S03]

**证据预算**：只有一个可用事实时写短帖；若需 Thread/多页轮播但没有足够彼此不同的证据点，减少页数/条数或返回 `missing_fields[]`，不靠模型常识扩写。[P-S13]

## 4. 事实、叙事与文化解释 [P04][P05]

1. **事实句绑定**：人物、日期、数字、专名、技艺原理、引语、原因/结果、具体现场描述，按 Generation `output-contracts.md` 记录到 `evidence_map[]`；`evidence_used[]` 对应实际 Ground 提供的来源，**不得编造网页或证据编号**。[P-S13]
2. **事实不够怎么办**：删除无支持句→缩小适用范围/时间→改成明确注明边界的解释→必要时返回 `research_gaps[]`；不得用“传统上”“据说”“众所周知”掩盖无来源断言。
3. **文化词处理**：必要时采用“原词/原名 + 一句平实的解释”，例如对于 `Suzhou embroidery (Su embroidery)` 这样的术语，具体定义仍须以本轮 EvidencePack 为准；不能用目标文化词汇作虚假等同。[P-S03][P-S04]
4. **文化主体尊重**：对社区、传承人、个人的身份、观点、照片、引语仅据授权材料表述。涉及非遗实践时，不替特定社区虚构认同或代言。[P-S04]
5. **信息性钩子**：开头应与正文事实相关。可以有趣，但不以虚假“秘密”“首次”“世界第一”、震惊式悬念或贬低他者吸引点击。
6. **语言自然**：目标语重新组织解释顺序，但 Content Master 的已核查事实、口径、因果强度和来源归属不变；遵守 `transcreation.md`。

## 5. 平台适配与可更新规则 [P06][P07][P08][P09]

以下是 **2026-10-18 的规范核对快照**，不能把它们当作永不变化的常识。发布前由 Tool / Backend 核查适用账户、API 类型和最新官方规则；Skill 只依传入的能力参数与已验证规则执行。

| 平台 | 约束级别 | 当前生成规则 | 来源/说明 |
|---|---|---|---|
| Instagram | **保守发布约束** | `hashtags` 默认 0–5 个，选主题真正相关的词；不承诺标签提高曝光。具体帖长由平台配置决定，**不强制 60–120 词**。 | 2025-12 Instagram 宣布逐步将帖子与 Reels 限制为最多五个标签；可读取公开的**二手报道转引官方声明**，并非本次直接取得的一手规则页。[P-S11][P-S02] |
| X，普通帖文 | **平台限制** | 逐条按 X 的 **weighted length** 判断是否符合典型 280 字符上限；URL、中文、emoji 不用普通 `len()` 代替正式规则。 | X Help / twitter-text。[P-S07][P-S08] |
| X，长帖 | **账户条件** | 仅当调用方明确 `long_post_enabled=true` 才可采用对应长帖能力；否则选择 Thread 或缩短。 | X Help 长帖功能与账户限制。[P-S07] |
| LinkedIn | **平台限制** | 普通帖文不超过当前官方帮助页列出的 3,000 字符；按账号/接口规则复核。 | LinkedIn Help。[P-S10] |
| 其他平台 | **未核实** | 不臆造字符、Hashtag、轮播上限；根据任务给出短版，并在 `ops_tips` 提示需要发布前检查。 | 本项目的保守实施策略，而非外部平台政策 |

- 特定长度、emoji 数量、hashtags 数量的“最佳表现”都是**待实验的编辑策略**，不能以“平台算法规定”为由强制指定。[P-S02]
- **CTA 只在确实适合时添加**：知识帖可直接收束，活动帖可有准确的参与方式，探索性内容可有自然提问；不得用强迫点赞、评论或情绪操控的互动诱饵。Meta 对 Facebook 的 engagement bait 有明确降权政策；**不把 Facebook 政策错误宣称为 Instagram 的同等处罚规则**。[P-S12]
- 若存在商业资助、赠品、雇佣或其他重要利益关系，且目标受众与司法辖区适用相关披露要求，则请调用方提供披露信息；**不得自行虚构，也不得隐瞒已给定的合作关系**。[P-S05]

## 6. 图片、轮播与无障碍 [P10]

- `alt_text` 描述的是**确实提供的图片**及其传达的信息，不是按主题想象出来的画面；真实图片每张分别编写简洁描述，避免机械重复帖文全文。[P-S06][P-S09]
- **没有图片、只有配图想法**：不得生成假装见过图片的 Alt Text；可在 `ops_tips` 里给出 `visual_brief`（待制作的画面建议）。
- **兼容旧输出接口**：若后端要求 `alt_text` 字段一定存在且为字符串，缺图时填 `""`，表示未生成图片描述；建议后端后续将此字段明确定义为可空。**不得随意新增新的必填顶层字段**。
- `visual_story` 的 `slides[]` 必须逐页表达一个清楚的信息推进；证据不足时减少页数；不得让未提供的照片“展示”某个虚构场景。

## 7. 形式输出（保持 v2.1 字段兼容）[P11]

只改变体裁方法，不改变 Generation 外层 `genre/format/master_ref/target_version/evidence_used/evidence_map/knowledge_loaded/human_review` 规范。

| format | 保留的原有字段 | v3.1 行为要求 |
|---|---|---|
| `social_post` | `post`, `five_w`, `hashtags`, `platform` | 一条核心信息，tags 与正文分离；`ops_tips` 可选 |
| `thread` | `posts[]`, `hook`, `five_w` | 每条提供独立进展；普通 X 帖逐条验证加权长度 |
| `visual_story` | `slides[]`, `cover_line`, `alt_text` | 未提供实图则 `alt_text=""`；不凭空生成图像描述 |
| `caption_only` | `caption`, `hashtags`, `alt_text` | 配文适配真实图像；无图时 `alt_text=""` |

不得为了加入平台规则而重新命名 `posts[]`、删除 `five_w`，或改变现有母稿引用机制。调用方若新增字段，先更新 `output-contracts` 与 API Schema，再启用。

## 8. 生成前自检（本 Skill 的自检 ≠ Part 1 审核）[P12]

- [ ] 输入由 Define/Plan/Ground 提供，未凭空补设人设、目标和账号权限。
- [ ] 只保留一个核心传播主点；所选叙事结构确实有材料支持。
- [ ] 所有可核验陈述都列入 `evidence_map[]`，无自造感官场景、人物原话、数字和链接。
- [ ] 文化术语解释不歪曲本意，不替社区作未经授权的发言。
- [ ] Hashtags / X weighted length / LinkedIn 限制按对应平台条件检查；来源可能变化时显式记录待核。
- [ ] 缺少图片时 `alt_text` 不虚构图像内容；商业关系披露不遗漏。
- [ ] CTA 非机械追加；没有对真实传播效果作保证。
- [ ] 输出完整、仍为 `human_review=PENDING`；不自动发布；由 Evaluation Part 1 和 Part 3 后续检查。

## 9. 依据索引（每条修订的用途详见 v3.1 Change Log）

- **[P-S02] Meta（2024）**，Instagram 创作者官方 Best Practices，说明创建、互动、触达等指导应随表现变化：<https://about.fb.com/news/2024/10/best-practices-education-hub-creators-instagram/>。
- **[P-S03] 美国国家科学院（2017）**，《Communicating Science Effectively》，强调目标与受众先验知识/需求影响沟通：<https://nap.nationalacademies.org/read/23674/chapter/4>。
- **[P-S04] UNESCO**，《Ethical Principles for Safeguarding Intangible Cultural Heritage》，强调社区主体性、知情同意和相互尊重：<https://ich.unesco.org/en/ethics-and-ich-00866>。
- **[P-S05] FTC（2019）**，社交媒体代言与商业利益关系披露指南（**美国相关场景适用**）：<https://www.ftc.gov/business-guidance/resources/disclosures-101-social-media-influencers>。
- **[P-S06] W3C WAI**，信息性图片的文本替代应表达实际信息：<https://www.w3.org/WAI/tutorials/images/informative/>。
- **[P-S07] X Help**，普通帖/长帖与账户条件：<https://help.x.com/en/using-x/types-of-posts>。
- **[P-S08] twitter-text**，加权字符、URL 与 emoji 处理配置：<https://github.com/twitter/twitter-text/blob/master/config/README.md>。
- **[P-S09] X Help**，每张图片可以添加描述、准确且简明：<https://help.x.com/en/using-x/picture-descriptions>。
- **[P-S10] LinkedIn Help**，普通帖文字上限 3,000 字符：<https://www.linkedin.com/help/linkedin/answer/a528176>。
- **[P-S11] Social Media Today（2025-12-18）**，**二手报道引述 Instagram 官方关于渐进式实施 5 标签上限的声明**：<https://www.socialmediatoday.com/news/instagram-implements-new-limits-on-hashtag-use/808309/>。在接入正式发布 API 前应再次核实。
- **[P-S12] Meta（2017）**，Facebook 对 engagement bait 的公告（**只可用于 Facebook，不能等同于 Instagram 政策**）：<https://about.fb.com/news/2017/12/news-feed-fyi-fighting-engagement-bait-on-facebook/amp/>。
- **[P-S13] Min 等（EMNLP 2023）**，FActScore 原子事实与支持证据的研究：<https://aclanthology.org/2023.emnlp-main.741/>。
