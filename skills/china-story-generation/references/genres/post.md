# 体裁方法：Post v3.2（社交帖文 / Thread / Visual Story / Caption）

> **版本**：v3.2（2026-10-22 专项审查修订）  
> **上游版本**：v3.1（2026-10-18 研究修订稿）。v3.2 不推翻 v3.1 的方法论，只做兼容优先的定点修订。  
> **修订依据**：《ChinaStory Post Skill v3.1（v6.2 合并包）专项审查报告》（2026-10-22），落实其 G1–G11 建议；本卡标注的审查编号〔G1〕…〔G11〕对应报告条目。  
> **边界**：这是 **Generation Skill 的内部写作方法**，不是新的顶层 Skill。Define / Plan 确定传播目标与受众；Ground 给出 EvidencePack 与 Gate B 决策；本卡写作；Evaluation Part 1 核验事实、Part 3 评价表达质量；人工最终审核。  
> **工程联动声明**：本卡中标注 **〔提案〕** 的新字段（`media_status`、`alt_status`、`media_basis`、`publishability_status`、`media_provenance`、`rights_status`）在 API Schema / Validator 同步之前**不得视为已实现**；标注 **〔运行待接线〕** 的条目指向后端尚未完成的工程项。只修改本文档不会使四种 format 自动运行。  
> **来源索引**：本文采用 `[P-S02]` 等编号；可点击本文末尾链接。

## 1. 触发条件与任务边界 [P01]

- **适用**：`genre=post`，`format=social_post|thread|visual_story|caption_only`；文本、图文轮播及配文。
- **不适用**：`news`、`feature`、`indepth`、`script`、`faq`。新闻报道不能因为发布到社交平台就直接改用 Post 的营销式语气。
- **format 路由与运行契约〔G1〕**：调用方应显式传入 `format`；旧请求缺省按 `social_post` 处理以保证兼容。每种格式有**专属输出字段与专属验证**：`thread` 至少返回 `posts[]`（逐条验长）；`visual_story` 返回 `slides[]`；`caption_only` 返回 `caption`。**不得用单一 `post` 字段兜底冒充其他格式完成**。
  - 〔运行待接线〕当前后端 `run_story_post_generation()` 尚无 `format` 参数与格式专属验证器。在接线完成前，对 `thread` / `visual_story` / `caption_only` 的任何产出必须标注"方法已定义，运行暂不支持"，不得宣称四种格式全部可用；不拆分为四个顶层 Skill。
- **输入只读**：读取已确认的 `task_context`、`content_plan`、`evidence_pack`；不自行发明目标国家、发声身份、受众偏好或发布账号权限。
- **身份与默认值的区分〔G2〕**：必须区分"上游明确确认的发布身份"与"旧接口为兼容保留的默认值"。`identity="online_influencer"`、`country="America"`、`tone="optimistic"` 等默认值**不得自动视为用户已确认的真实发布身份**。发声身份未确认时，采用中性说明性口吻，或把缺失项放入 `missing_context[]` 由调用方补齐；**不假装亲历、采访或代表传承人**。受众画像由 Plan 提供，不得把 `country=America` 推导为"所有美国人的偏好"或任何国籍刻板化判断。[P-S02][P-S03][P-S04]
- **证据门禁〔G3〕**：本卡读取的是**后端已明确作出的 Evidence / Gate B 决策**（由后端把 canonical 状态适配给 Skill），不依赖 `evidence_pack.gate` 属性——真实 Pydantic Schema 中不存在该字段，也不得把默认状态字符串当作"已通过全部证据检查"。决策未明确或不充分时不写完整稿件。本卡**不自行重新检索**。[P-S13]
- **事实终审权限〔G3〕**：Generation 只登记**候选** Claim–Evidence 对应（`evidence_map[]`）；`supported` 等支持性结论由 Evaluation Part 1 或获授权人工作出。生成输出**不得自称已通过最终事实核验**。

## 2. 将 5W 从套话改为写作约束 [P02]

从上游 `ContentPlan` 和 `TaskContext` **映射** `five_w`，不私自重写传播计划：

| 字段 | 成稿时要遵守什么 | 禁止行为 |
|---|---|---|
| `Who` | 使用任务明确授权的发声身份；必要时中性叙述 | 编造个人旅游、采访、机构官方身份 |
| `Says What` | **单帖**优先一条可证核心信息；**Thread/轮播**整组围绕一个共同传播目标，每条帖文/每页可有不同、彼此关联且受证据支持的子信息〔G9〕 | 多个互不相关的事实堆砌；为凑页数虚构"新事实"；用口号代替事实 |
| `Channel` | 按已选平台与形态调整篇幅、节奏和可访问性 | 把平台建议冒充硬限制 |
| `To Whom` | 为受众真正缺少的概念补必要解释 | "所有美国人都喜欢……"等未经依据的判断 |
| `Effect` | 记录希望读者理解、记住或探讨的**预期目标**，具体到可检验的理解或行为假设 | 声称"这条文案一定提高阅读量/认同感" |

- `Effect` 是**预期目标，不是实际传播成效**〔G11〕：阅读量、点赞、转发属于平台互动观察指标，不能直接替代真实的跨文化理解、事实记忆或态度测量；尚未开展真实受众研究时**不得宣称传播效果已被证实**。[P-S03]
- `core_message`（单帖主点）与 `unit_goal`（整组目标）可作为**内部策划说明**使用，不新增后端必填字段。〔G9〕

## 3. 先检查素材，再选择信息组织方式 [P03][P04]

**根据素材与传播目标选择适用的主导叙事方式〔G8〕**：对于以活动通知、事实澄清、资源提示为主、无明显叙事任务的 Post，可采用简洁的**非叙事信息组织方式**，不强套叙事结构。下列四种模式是**可选编辑策略，不是硬性四选一模板**；选择不得改变已确认的 Genre，也不得凭空增加场景或人物：

| 模式 | 启动条件 | 推荐顺序 | 缺料时 |
|---|---|---|---|
| 场景体验型 | 有可证的地点、动作、观察细节 | 具体开场→真实细节→事实→克制收束 | 不补造气味、天气、声音或第一人称经历 |
| 知识解释型 | 有概念定义、工艺步骤或真实例证 | 一个清晰问题→解释→证据例子→意义 | 只解释材料中有的内容 |
| 人物观察型 | 有真实人物与获授权的行为/引语 | 人物行动→背景→细节/变化→价值 | 缺人物证据时换模式，不创作采访 |
| 事实对照型 | 同一范围、可比口径的两组事实 | 对照→证据→解释边界→收束 | 不把相关性、前后变化写成因果 |

**证据层级说明**：

- 叙事沉浸（transportation）研究说明叙事参与有助于理解与说服，为叙事模式提供理论动机，但**不规定每条 Post 的固定结构**。[P-S21]
- 2026 年《Journal of Science Communication》对 194 条 Instagram 科学传播帖文的定性分析，支持"依据传播目标选择不同 framing 与策略"的方向；其研究对象是宇航员类科学账号，**不能证明本卡四种模式最优，也不能泛化到所有受众**。[P-S18]
- 2025 年读者研究（预印本）显示不同读者、任务和主题对叙事技巧的偏好存在差异，支持**提供选项而非强制统一模板**。[P-S19]

**证据预算**：只有一个可用事实时写短帖；若需 Thread/多页轮播但没有足够彼此不同的证据点，减少页数/条数或返回 `missing_fields[]`，不靠模型常识扩写。[P-S13]

## 4. 事实、叙事与文化解释 [P04][P05]

1. **事实句绑定（候选登记）〔G3〕**：人物、日期、数字、专名、技艺原理、引语、原因/结果、具体现场描述，按 Generation `output-contracts.md` 记录到 `evidence_map[]`；`evidence_used[]` 对应实际 Ground 提供的来源，**不得编造网页或证据编号**。生成侧填写的是**候选对应关系**，最终支持性判断归 Part 1。[P-S13]
2. **事实不够怎么办**：删除无支持句→缩小适用范围/时间→改成明确注明边界的解释→必要时返回 `research_gaps[]`；不得用"传统上""据说""众所周知"掩盖无来源断言。
3. **文化词处理**：必要时采用"原词/原名 + 一句平实的解释"，具体定义仍须以本轮 EvidencePack 为准；不能用目标文化词汇作虚假等同。[P-S03][P-S04]
4. **文化主体尊重**：对社区、传承人、个人的身份、观点、照片、引语仅据授权材料表述。涉及非遗实践时，不替特定社区虚构认同或代言。[P-S04]
5. **信息性钩子**：开头应与正文事实相关。可以有趣，但不以虚假"秘密""首次""世界第一"、震惊式悬念或贬低他者吸引点击。
6. **语言自然**：目标语重新组织解释顺序，但 Content Master 的已核查事实、口径、因果强度和来源归属不变；遵守 `transcreation.md`。

## 5. 平台与格式组合适配 [P06][P07][P08][P09]

以下是 **2026-10-22 的规范核对快照**，不能把它们当作永不变化的常识。发布前由 Tool / Backend 核查适用账户、API 类型和最新官方规则；Skill 只依传入的能力参数与已验证规则执行，**LLM 不得靠记忆宣布某内容"可以发布"**。

### 5.1 单平台规则

| 平台 | 约束级别 | 当前生成规则 | 来源/说明 |
|---|---|---|---|
| Instagram | **保守发布约束** | `hashtags` 默认 0–5 个，选主题真正相关的词；不承诺标签提高曝光。具体帖长由平台配置决定，**不强制 60–120 词**。 | 2025-12 Instagram 宣布逐步限制为最多五个标签（二手报道转引官方声明）；**部分 Meta 开发者 API 页面仍存在旧的 30 标签字段描述，版本可能不一致**，发布层须按实际接口复核。[P-S02][P-S11][P-S20] |
| X，普通帖文 | **平台限制** | 逐条按 X 的 **weighted length** 判断是否符合典型 280 字符上限；URL、中文、emoji 不用普通 `len()` 代替正式规则。 | X Help / twitter-text。[P-S07][P-S08] |
| X，长帖 | **账户条件** | 仅当调用方明确 `long_post_enabled=true` 才可采用对应长帖能力；否则选择 Thread 或缩短。 | X Help。[P-S07] |
| LinkedIn | **平台限制** | 普通帖文不超过当前官方帮助页列出的 3,000 字符；按账号/接口规则复核。 | LinkedIn Help。[P-S10] |
| 其他平台 | **未核实** | 不臆造字符、Hashtag、轮播上限；根据任务给出短版，并在 `ops_tips` 提示需要发布前检查。 | 本项目的保守实施策略 |

- 特定长度、emoji 数量、hashtags 数量的"最佳表现"都是**待实验的编辑策略**，不能以"平台算法规定"为由强制指定。[P-S02]
- **CTA 只在确实适合时添加**；不得用强迫点赞、评论或情绪操控的互动诱饵。Meta 对 Facebook 的 engagement bait 有明确降权政策；**不把 Facebook 政策错误宣称为 Instagram 的同等处罚规则**。[P-S12]
- 若存在商业资助、赠品、雇佣或其他重要利益关系，且目标受众与司法辖区适用相关披露要求，则请调用方提供披露信息；不得自行虚构，也不得隐瞒已给定的合作关系。[P-S05]

### 5.2 format × platform 组合适配〔G6〕

| format | X | Instagram Feed | LinkedIn |
|---|---|---|---|
| `social_post` | 普通文本帖可行，weighted length 检查 | 可写文案草稿，但 Feed 正式发布通常需要实际媒体；无可发布媒体时标记 `needs_media` | 文字帖，校验 3,000 字符 |
| `thread` | 原生连续帖，逐条验长 | **不是** X Thread 的原生等价格式，应提示重规划 | 不等同原生 Thread，不得假装自动支持 |
| `visual_story` | 可重规划为附图帖/串帖，但**不是** IG 轮播的同一对象 | 需多媒体资产与对应发布 API/账户能力 | 需采用 LinkedIn 对应载体（文档/多图等）与校验 |
| `caption_only` | 用于已有媒体的帖文文字 | 用于真实图片/视频的配文 | 用于已有媒体的文字说明 |

- 此表是**内容形式的优先适配方向**，不是完整的平台发布能力清单；具体发布方式、账号权限、API 容量、媒体格式和字符限制由后端在发布前验证。
- **可发布性诊断〔提案〕**：`publishability_status=ready|needs_media|needs_capability_check|unsupported`。最终 `ready` **只能由后端平台能力和媒体校验模块确定**，LLM 不得自行宣布"已可发布"。

## 6. 图片、轮播与无障碍 [P10]

- `alt_text` 描述的是**确实提供的图片**及其传达的信息，不是按主题想象出来的画面；避免机械重复帖文全文。[P-S06][P-S09]
- **逐图描述〔G4〕**：对**每张承担独立信息的真实图片**分别提供适当替代文本；一组相关但各有独立信息的图片应逐张描述；是否需要逐张独立描述，依据每张图片承载的信息与其在整组中的作用判断，纯装饰图可采用空替代。[P-S06][P-S14]
- **图上文字与数据图表〔G4〕**：图片中承载的重要信息（文字、数字、图表结论）必须同时有可供访问的文字表达。[P-S15]
- **`visual_brief` ≠ `alt_text`〔G4〕**：`visual_brief` 是**计划制作的画面说明**，`alt_text` 是**实际图片的替代文本**；没有真实图片时不得把 `visual_brief` 冒充 `alt_text`，不得假装见过图片。
- **拟议的逐页结构〔提案，需同步 Schema/前端/验证代码〕**：

```yaml
format: visual_story
slides:
  - slide_id: S1
    headline: "封面：苏绣是什么？"
    body: "真实证据支持的简短说明"
    media_ref: "asset-001"          # 只有真实关联到素材时填写
    media_status: provided          # provided | brief_only | missing 〔提案〕
    alt_text: "经核对的逐图描述"
    alt_status: verified            # verified | needs_review | not_applicable 〔提案〕
  - slide_id: S2
    headline: "工艺细节"
    body: "另一项可证的信息"
    media_status: brief_only
    visual_brief: "准备制作的第二页画面"
    alt_text: null
    alt_status: not_applicable
alt_text: ""                        # 旧顶层字段保留为过渡兼容，待迁移后弃用
```

- `visual_story` 的 `slides[]` 必须逐页表达清楚的信息推进；证据不足时减少页数；不得让未提供的照片"展示"某个虚构场景。
- **`caption_only` 三态区分〔G5〕**：

| 输入状态 | 合法输出 |
|---|---|
| 有真实媒体，且内容可读取 | 生成素材对应的 caption；必须经过视觉内容匹配检查 |
| 只有用户提供且可靠的素材文字描述 | 生成"基于素材说明"的**待核** caption；不得编造画面细节 |
| 只有空泛主题，无媒体也无可信描述 | 返回 `missing_media[]` 或 `needs_human[]`；**不得**把空 `alt_text` 当作媒体检查通过 |

- 配套可选字段〔提案〕：`media_basis=actual_asset|verified_description|none`，并记录 `media_ref` 或描述来源；字段启用前需同步 API Schema。
- **兼容旧输出接口**：若后端要求 `alt_text` 字段一定存在且为字符串，缺图时填 `""`，表示未生成图片描述；不得随意新增必填顶层字段。
- **媒体来源、授权与合成素材透明度〔G10〕**：建议后端记录 `media_provenance=actual_photo|licensed_media|ai_generated|unknown` 与 `rights_status`；只能使用有使用权的图片/视频（注明来源不等于已获授权）；AI 生成或重大编辑的素材须按平台规则透明标识，**不得把 AI 合成的工艺场景伪装成真实拍摄**；涉及真实人物肖像或采访须确认授权，具体权利要求以适用法律为准。[P-S17][P-S16][P-S04]

## 7. 形式输出（保持 v2.1 字段兼容）[P11]

只改变体裁方法，不改变 Generation 外层 `genre/format/master_ref/target_version/evidence_used/evidence_map/knowledge_loaded/human_review` 规范。

| format | 保留的原有字段 | v3.2 行为要求 |
|---|---|---|
| `social_post` | `post`, `five_w`, `hashtags`, `platform` | 一条核心信息，tags 与正文分离；无可发布媒体时标注 `needs_media`〔提案字段〕；`ops_tips` 可选 |
| `thread` | `posts[]`, `hook`, `five_w` | 每条提供独立进展且服务整组共同目标〔G9〕；普通 X 帖逐条验证加权长度 |
| `visual_story` | `slides[]`, `cover_line`, `alt_text` | 逐页 `slides[]`，每张真实图片各自 `alt_text`〔G4〕；无实图则顶层 `alt_text=""`，不凭空生成图像描述；逐页状态字段为〔提案〕 |
| `caption_only` | `caption`, `hashtags`, `alt_text` | 按 6 节三态区分素材前提〔G5〕；无图时 `alt_text=""`，不假装看过图 |

不得为了加入平台规则而重新命名 `posts[]`、删除 `five_w`，或改变现有母稿引用机制。调用方若新增字段（含本卡〔提案〕字段），先更新 `output-contracts` 与 API Schema，再启用。

## 8. 生成前自检（本 Skill 的自检 ≠ Part 1 审核）[P12]

- [ ] 输入由 Define/Plan/Ground 提供；发声身份、国家、tone 来自上游确认，**旧接口默认值未冒充用户决定**〔G2〕。
- [ ] `format` 专属输出字段完整：`thread`→`posts[]`、`visual_story`→`slides[]`、`caption_only`→`caption`；**未用单一 `post` 兜底冒充完成**〔G1〕。
- [ ] 证据状态读取的是后端明确的 Gate B 决策；`evidence_map[]` 只是候选登记，**未自称已通过最终事实核验**〔G3〕。
- [ ] 单帖一个主点；Thread/轮播整组一个共同目标，每条/每页有受证据支持的子信息，未为凑页数虚构新事实〔G9〕。
- [ ] 所选信息组织方式（叙事或非叙事）确实有材料支持；未硬套叙事模板〔G8〕。
- [ ] 所有可核验陈述都列入 `evidence_map[]`，无自造感官场景、人物原话、数字和链接。
- [ ] 文化术语解释不歪曲本意，不替社区作未经授权的发言。
- [ ] Hashtags / X weighted length / LinkedIn 限制按对应平台条件检查；format × platform 组合适配已核对，不适配处标注待检查〔G6〕。
- [ ] 每张承担独立信息的真实图片有各自 `alt_text`；`visual_brief` 未冒充 `alt_text`；缺图时未虚构图像内容〔G4〕。
- [ ] `caption_only` 的素材前提状态正确；无媒体时返回缺项而非假装配图完成〔G5〕。
- [ ] 媒体来源/授权已记录；AI 生成或合成素材未伪装成实拍，透明标识不遗漏〔G10〕。
- [ ] 商业关系披露不遗漏；CTA 非机械追加。
- [ ] 效果表述限于预期目标，**未宣称传播效果已被证实**〔G11〕。
- [ ] 输出完整、仍为 `human_review=PENDING`；不自动发布；由 Evaluation Part 1 和 Part 3 后续检查。

## 9. 依据索引

**v3.1 沿用来源**

- **[P-S02] Meta（2024）**，Instagram 创作者官方 Best Practices，说明创建、互动、触达等指导应随账号表现与内容目标调整，而非机械套用统一模板：<https://about.fb.com/news/2024/10/best-practices-education-hub-creators-instagram/>。
- **[P-S03] 美国国家科学院（2017）**，《Communicating Science Effectively》，强调传播目标、受众先验知识与社会情境影响沟通设计与评价：<https://nap.nationalacademies.org/read/23674/chapter/4>。
- **[P-S04] UNESCO**，《Ethical Principles for Safeguarding Intangible Cultural Heritage》，强调社区主体性、知情同意和相互尊重：<https://ich.unesco.org/en/ethics-and-ich-00866>。
- **[P-S05] FTC（2019）**，社交媒体代言与商业利益关系披露指南（**美国相关场景适用**）：<https://www.ftc.gov/business-guidance/resources/disclosures-101-social-media-influencers>。
- **[P-S06] W3C WAI**，信息性图片的文本替代应表达实际信息：<https://www.w3.org/WAI/tutorials/images/informative/>。
- **[P-S07] X Help**，普通帖/长帖与账户条件：<https://help.x.com/en/using-x/types-of-posts>。
- **[P-S08] twitter-text**，加权字符、URL 与 emoji 处理配置：<https://github.com/twitter/twitter-text/blob/master/config/README.md>。
- **[P-S09] X Help**，每张图片可以添加描述、准确且简明：<https://help.x.com/en/using-x/picture-descriptions>。
- **[P-S10] LinkedIn Help**，普通帖文字上限 3,000 字符：<https://www.linkedin.com/help/linkedin/answer/a528176>。
- **[P-S11] Social Media Today（2025-12-18）**，二手报道引述 Instagram 官方关于渐进式实施 5 标签上限的声明：<https://www.socialmediatoday.com/news/instagram-implements-new-limits-on-hashtag-use/808309/>。接入正式发布 API 前应再次核实。
- **[P-S12] Meta（2017）**，Facebook 对 engagement bait 的公告（只可用于 Facebook，不能等同于 Instagram 政策）：<https://about.fb.com/news/2017/12/news-feed-fyi-fighting-engagement-bait-on-facebook/amp/>。
- **[P-S13] Min 等（EMNLP 2023）**，FActScore 原子事实与支持证据的研究：<https://aclanthology.org/2023.emnlp-main.741/>。

**v3.2 新增来源**

- **[P-S14] W3C WAI，Groups of Images**：成组图片应依据每张图片的内容及其在整组中的作用提供适当的文本替代，各有独立信息的图片分别描述：<https://www.w3.org/WAI/tutorials/images/groups/>。→ **启发 [G4]**：`visual_story` 不能只靠顶层一个 `alt_text` 字符串，须逐页/逐图描述。
- **[P-S15] W3C WAI，Complex Images**：图上文字、数据图表等复杂内容须提供等效的可访问文字表达：<https://www.w3.org/WAI/tutorials/images/complex/>。→ **启发 [G4]** 中"图上重要信息须同时有文字表达"。
- **[P-S16] Meta（2024）**，对 AI 生成与操纵媒体的标注与透明度政策：<https://about.fb.com/news/2024/04/metas-approach-to-labeling-ai-generated-content-and-manipulated-media/>。→ **启发 [G10]**：AI 合成素材的透明标识要求。
- **[P-S17] Meta 社区规范与版权帮助**：只能发布自己有权分享的图片/视频，注明来源不等于获授权：<https://www.facebook.com/help/477434105621119>。→ **启发 [G10]**：`rights_status` 与授权检查建议。
- **[P-S18] Shalev, Pappas & Steinke（2026）**，Journal of Science Communication，对 194 条 Instagram 科学传播帖文的 framing 实践定性分析：<https://jcom.sissa.it/article/pubid/JCOM_2506_2026_A08/>。→ **启发 [G8]**：支持"依据传播目标选择不同信息组织策略"，故放宽四模式为可选策略；同时明确其不证明四模式最优。
- **[P-S19] Li 等（2025）**，arXiv 预印本，读者对叙事结构与个人语言风格的印象存在差异：<https://arxiv.org/abs/2502.05287/>。→ **启发 [G8]**：支持"提供选项而非统一模板"。（预印本、跨题材辅助证据）
- **[P-S20] Meta for Developers，Instagram Content Publishing**：媒体内容创建、轮播与账户/API 能力的官方技术文档：<https://developers.facebook.com/documentation/instagram-platform/content-publishing.md/>。→ **启发 [G6]**：Feed 正式发布需要实际媒体、平台能力须由接口校验，故引入 `needs_media` 与 `publishability_status`（提案）。
- **[P-S21] Green & Brock（2000）**，叙事传输机制研究：<https://doi.org/10.1037/0022-3514.79.5.701>。→ 说明叙事模式的理论动机（叙事参与有助于理解与说服），但不规定固定结构。

**审查报告本身**：《ChinaStory Post Skill v3.1（v6.2 合并包）专项审查报告》（2026-10-22），G1–G11 各条给出了"文档小改即可"与"必须同步代码/合同"的区分；本卡落实其中属文档层的修订，工程项以〔运行待接线〕标注留待后端。
