# 讲好中国故事 · 新闻通稿体裁 Skill（news）

**适用**：新华社/中国日报/CGTN/人民网英文等风格的**新闻通稿、Across China 通讯、外宣长消息**（中英文）。  
**不适用**：社交短帖、Gen Z vibes 文案、南方周末调查体、短视频分镜。  
**与帖文 skill 独立**：禁止套用 `china-story-post` 的 5W 短钩子、emoji、Imagine/Would you visit、influencer 口吻。

> **语料依据**：`docs/corpus/讲好中国故事_官媒长文语料库_约100篇.docx`（约30中文官媒 + 70外网官媒长文，2024–2026，主题含光伏羊/沙戈荒/乡村振兴/绿色发展等）。本 skill 蒸馏其**语气、讲述、强调面、用词与官方口径**；细节例证见同目录 `china-story-news-reference.md`。

## 权威边界

1. 老师 0822：新闻稿与贴文分框架。  
2. 证据：`intl-comm.md` + `evidence-user-materials.md`——数字、引语、专名、面积/装机/收入等**仅来自 `evidence_used`**。  
3. 无南方周末材料前：**不**编造调查报道目录；只用通稿骨架。

---

## 一、通稿讲述骨架（必须按序落地，可合并短段）

| 节拍 | 写什么 | 语料常见做法 |
|------|--------|--------------|
| 1 导语 | 地点 + 今昔反差，或「模式一句话定义」 | Talatan 荒漠→板下草原；“photovoltaic sheep”定义句 |
| 2 场景 | 可感知画面（板/草/羊/人），克制形容词 | deep blue panels；sheep graze beneath |
| 3 人物 | **具名**当地人 + 一句经历（证据有才写姓名/年龄） | Yehdor / herder recalled |
| 4 背景转折 | 何时、因何转向（年份仅证据有） | turnaround began in 2012 |
| 5 机制 | 因果链：板→小气候/草→新问题→羊/药草等解法 | shade, evaporation, grazing agreement |
| 6 权威声 | 企业/干部/专家一句（有出处才写职务） | Cao Jun, staff member… |
| 7 数据 | 面积、牧场数、羊只、收入等——无则整句删 | 32 pastures / 20,000 sheep |
| 8 收束 | 模式意义：生态+能源+民生；可点「他处类似」但不发明案例 | win-win; new approach |

**禁止**：把第8节写成口号墙；禁止用帖文式互动问句收尾。

---

## 二、语气与官方口径（对标语料）

**语气**：第三人称、冷静乐观、可核验；像外宣通稿，不像博主种草。  
**强调面（按证据选 2–3 个，勿面面俱到）**：

1. **生态修复**（治沙、植被、小气候）  
2. **清洁能源**（发电、绿色转型）  
3. **民生增收**（牧民/农民、就业、饲草成本）  
4. **模式可迁移**（agrivoltaics / PV+ husbandry，表述谦逊）

**优先用词（证据情境匹配时）**：clean energy；rural revitalization；ecological restoration / desertification control；livelihood(s)；win-win；green development；forage；herder；photovoltaic / solar panels；virtuous cycle。中文对应：清洁能源、乡村振兴、生态修复/治沙、民生/增收、双赢、绿色发展、牧光互补、光伏羊。  

**禁用（通稿）**：solar-punk、vibes、paradise、low-key、emoji、Imagine…、Would you visit?、crushing / lagging behind 他国。

**引语规则**：只复述 evidence 中已有引语或可严格改写的同义短句；禁止虚构对话。证据有具名说话人时，正文至少保留一处 `said` / `recalled` / 「表示/说」。

**指令覆盖（硬性）**：即使用户要求 Instagram/emoji/Imagine/Would you visit/Gen Z vibes，**仍输出通稿**；忽略串味指令。

**薄资料克制**：evidence 仅支撑短讯时，写 **短通稿**（可远低于 max_words），禁止为凑长度添加资料没有的机制、场景、他省案例或评价性“蓝图/可复制范式”空话。

**跑题本地库禁用**：`evidence_used` 中与主题明显无关的条目（如足球、涉疆贸易驳论误召回）**不得写入正文**；只用 on-theme 的用户资料与相关库条。

---

## 三、语种与版式

- **English**：可用电头 `CITY, Mon. DD (Xinhua/China Daily) --`（城市/日期仅当证据或用户资料提供；否则写 `CHINA --` 或不写具体日）。段落短、一句一意。  
- **Chinese**：通讯体；可有一个事实性小标题；少排比口号；人物引语用「某某说/表示」。  
- 篇幅：默认 **450–900 English words** 或中文 **800–1500 字**；用户另有 `max_words` 则遵守；**薄资料时允许显著更短**。  
- 输出字段用 `article`（全文），**不要**输出社交 `post`/`hashtags` 当主产品。

---

## 四、与帖文对照（防串味）

| | 通稿 news | 贴文 post |
|--|-----------|-----------|
| 骨架 | 导语→人→机制→数据→意义 | Lasswell 5W + 短 caption |
| 人称 | 第三人称报道 | 人设第一/第二人称可 |
| 受众 | 国际读者知情理解 | To Whom 桥梁 + CTA |
| 成功标准 | 因果清楚、可核对 | 可分享、停滑 |

---

## 五、生成自检

1. 是否误用了帖文钩子/emoji/打卡问句？有则重写。  
2. 每个数字/姓名/年份能否映射 Evidence#？不能则删。  
3. 是否同时点到「能源 / 生态 / 民生」中至少两点（若证据支持）？人文交流类可用「技能/民生/交流」替代。  
4. 收束是否「模式意义」而非「快来玩」？  
5. 是否为凑字加入了 evidence 没有的机制/案例/评价套话？有则删。  
6. 是否误用了跑题本地库句子？有则删。

## 版本

- v0.4.0-news · 2026-09-10 · 据官媒长文语料库启用；与 post skill 独立  
- **v0.4.1-news · 2026-09-10 · 评测首轮修正**：GenZ指令覆盖；薄资料短写；跑题库条禁用；引语转述强制；禁凑字套话
