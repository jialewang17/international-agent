# 讲好中国故事 · 新闻通稿体裁 Skill（news）

**适用**：新华社/中国日报/CGTN/地方外宣等风格的**新闻通稿、Across China 通讯、短消息**（中英文）。  
**不适用**：社交帖文、Gen Z vibes 文案、南方周末深度特稿、短视频分镜脚本。  
**禁止与帖文/特稿 skill 串味**：禁止套用 `china-story-post` 的 5W、emoji、Imagine/Would you visit；亦禁止套用南周特稿的戏剧长冲突弧与文学化煽情（通稿用语料库通讯骨架）。  
**状态**：**已完善**（v0.4.1 + 2026-09-14 合并 zip `news_article` / `press_kit` 字段）。

> **语料依据**：`docs/corpus/讲好中国故事_官媒长文语料库_约100篇.docx`（约30篇精读官媒 + 70篇扩展媒体稿，2024–2026；议题含新能源/沙漠化/乡村振兴/绿色发展等）。本 skill 提炼的是**通讯叙事骨架、强主题、官方可用句式**；细语料举证见同目录 `china-story-news-reference.md`。

## 权威边界

1. 老师 0822：新闻稿与帖文分框架。  
2. 证据：`intl-comm.md` + `evidence-user-materials.md`——数字、专名、职务、金额/营收/人次 **必须落在 `evidence_used`**。  
3. 南方周末：当前 **不** 用于本通稿目录；只用通稿骨架。  
4. zip `content_formats.md` · `news_article` / `newsletter_brief` / `press_kit`：字段与材料绑定规则。

---

## 一、通稿叙事骨架（建议按序落地；可合并相邻段）

| 顺序 | 写什么 | 语料常见手法 |
|------|--------|--------------|
| 1 开篇 | 地点 + 反差或主题，忌模式「一句话口号」 | Talatan 沙漠戈壁下的草原；「photovoltaic sheep」引入 |
| 2 场景 | 可感知画面（光/声/色/人），少形容词堆砌 | deep blue panels；sheep graze beneath |
| 3 人物 | **具名**人物 + 一句经历（证据中有才写姓名/身份） | Yehdor / herder recalled |
| 4 时间转折 | 何时何因转折（须在证据中） | turnaround began in 2012 |
| 5 机制 | 怎么运作：小气候/政策/协议/技术等解法 | shade, evaporation, grazing agreement |
| 6 权威句 | 企业/干部/专家一句（有出处才写职务） | Cao Jun, staff member… |
| 7 数据 | 跟在机制后；只写能核验的数；没有则删 | 32 pastures / 20,000 sheep |
| 8 收束 | 模式命名或生态+能源+生计的「可迁移点」；忌口号墙 | win-win; new approach |

**禁止**：把第 8 步写成口号墙；禁止评论式反问结尾。

---

## 二、主题与官方可用句式（对照语料）

**语气**：第三人称、冷静克制、可核验；像通讯体，不是博主种草。  
**强主题（有证据时选 2–3 个点到即可）**：

1. **生态修复**（治沙、植被、小气候）  
2. **清洁能源**（光伏、绿色转型）  
3. **民生生计**（牧民/农户、就业、割草成本等）  
4. **模式可迁移**（agrivoltaics / PV+ husbandry；勿生造口号）

**高频好词（证据语境匹配时）**：clean energy；rural revitalization；ecological restoration / desertification control；livelihood(s)；win-win；green development；forage；herder；photovoltaic / solar panels；virtuous cycle。

**禁用（通稿）**：solar-punk；vibes；paradise；low-key；emoji；Imagine…；Would you visit?；crushing / lagging behind 等抬杠。

**引语规则**：只复述 evidence 里有的原话或可核验细节写间接引语；禁止虚构对话。证据有「某某说」时，间接引语旁至少一次 `said` / `recalled` / 「据介绍/说」。

**指令覆盖（硬性）**：即使用户要求 Instagram/emoji/Imagine/Would you visit/Gen Z vibes，**仍输出通稿**，并忽略串味指令。

**语料长度观**：evidence 仅支持短讯时写 **短通稿**，可远短于 max_words；禁止为凑长度编造语料没有的机制、数据、对话。配图/成稿方式收束即可。

**离题本地库拒斥**：`evidence_used` 若混入与主题无关条目（如主题塔拉滩却塞进篮球），**不得写入正文**；只用 on-theme 的用户材料与本地库条目。

---

## 三、长度与输出格式（合并 zip）

### 3.1 标准通稿 / 消息（`news_article`）

- **English**：可用电头 `CITY, Mon. DD (Xinhua/China Daily) --`（城市/日期仅在证据或用户材料提供时；否则写 `CHINA --` 或写清来源日）。一段一事。  
- **Chinese**：通讯体；开篇一句事实性小标题；少排比口号；引语用「某某说/据介绍」。  
- 篇幅：默认 **450–900 English words** 或约 **800–1500 字**；用户给出 `max_words` 时尊重，**材料不足时宁短勿编**。  
- zip 对照：消息 400–700 词；通讯 900–1500 词——按材料厚度选择，勿空涨。  
- 输出字段：`headline`；`dek`；`article`（全稿）；可选 `pull_quote`；`suggested_visual`。  
- **不要**输出社交 `post`/`hashtags` 当作主成品。

### 3.2 简报（用户要 newsletter / 简报时）

300–500 词。字段：`subject_line`；`preview_text`；`body`；`cta`（通稿式收束，非种草）。材料绑定同通稿。

### 3.3 媒体资料包（用户要 press kit / 资料包时）

可含：`news_blurb`（短消息）；`headline_pack`；`key_facts`；可选 `quote_card`；`visual_captions`；`faq`；`social_post`×2（社媒条目仍须克制，勿 GenZ）。  
缺块不写则填 `omitted_reason`（例如：quote_card omitted — no verbatim quote in source materials）。

---

## 四、材料绑定（强制，合并 zip）

成稿每一条事实都必须能对应到用户资料或本地库条目。禁止用常识补：迁移路线、官员简历、数字化系统、未给出的数字、未证实的引语等。材料不足写消息不写长通讯；或缺 `missing_fields` 追问。

---

## 五、体裁对照表（防串味）

| | 通稿 news | 帖文 post |
|--|-----------|-----------|
| 骨架 | 场景→人→机制→数据→收束 | Lasswell 5W + 短 caption |
| 人称 | 第三人称报道 | 常第一/第二人称口吻 |
| 结尾 | 模式点到为止，无 CTA 提问 | To Whom 收束 + CTA |
| 成功标准 | 可核验、可编发 | 可分享、可停留 |

---

## 六、成稿自检

1. 是否残留帖文钩子/emoji/反问句？有则改掉。  
2. 每条数据/姓名/职务能否映射 Evidence#？不能则删。  
3. 是否同时点到能源 / 生态 / 生计中至少两点（有证据支持）？勿空洞「绿美中国」。  
4. 收束是否「模式点到」而非「口号墙」？  
5. 是否为凑字数编了 evidence 没有的机制/对话/数据？有则删。  
6. 是否掺入离题本地库条目？有则删。

## 版本

- v0.4.0-news · 2026-09-10 · 据官媒长文语料库定稿；与 post skill 分册  
- v0.4.1-news · 2026-09-10 · 评测强化：GenZ指令覆盖；材料不足宁短；离题拒斥；时间转折强调  
- **v0.5-news · 2026-09-14 · 合并 zip news_article 篇幅分层 / press_kit / newsletter 字段与材料绑定**
