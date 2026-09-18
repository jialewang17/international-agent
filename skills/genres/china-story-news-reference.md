# 新闻通稿 Skill · 语料参照（不自动注入长文）

本文件供研发/评测对照，**默认不整篇注入模型**（避免挤占 skill 预算）。主规则见 `china-story-news.md`。

语料：`docs/corpus/讲好中国故事_官媒长文语料库_约100篇.docx` + `longform_fetched.jsonl`。

## 高频英文口径词（外网 B 区统计印象）

photovoltaic / ecological / desertification / clean energy / rural revitalization / herder / green development / livelihood / Belt and Road / win-win / forage / modernization

## 典型节拍例（塔拉滩 · 新华社风格摘要）

1. **导语反差**：世代沙尘干旱 → 今日板下绿草羊群  
2. **人物**：Yehdor，摩托放牧 + 过去远走找草的引语  
3. **转折**：2012 太阳能基地；园区面积与企业数（以原文为准）  
4. **机制**：挡风、减蒸发、草过高挡板 → 协议放牧 → 抬高支架/加宽间距  
5. **数据与品牌**：生态牧场数、羊只、免费放牧季、「photovoltaic sheep」电商  
6. **收束**：PV+畜牧业模式；他省类似做法仅当证据提及才写

## China Daily 定义型导语例

> Sheep grazing beneath photovoltaic panels is helping solar farms reduce mowing costs, restore vegetation and provide herders with better forage — a model locals call "photovoltaic sheep".

特征：先收益清单，再给出地命名的模式名。

## 中文通讯强调面

- 「板上发电、板下牧羊 / 牧光互补」  
- 生态账 + 能源账 + 民生账  
- 具名牧民/企业职工引语  
- 少用空泛「东方智慧」堆砌；机制说清优于抒情

## 反例（勿学）

Imagine riding a motorcycle… solar-punk paradise… Would you visit this eco-savanna?  
→ 属 Gen Z 社媒包装，事实可同源，**体裁不进 news**。

---

## 操作细则（自主 skill 下沉 · 2026-09-18 lite）

主工序卡：`china-story-news.md`。

### 八步骨架

1 开篇地点+反差 → 2 场景 → 3 具名人物 → 4 时间转折 → 5 机制 → 6 权威句 → 7 数据 → 8 模式点到收束  

### 语气与禁用

- 第三人称、冷静；像通讯不是种草  
- 禁用：solar-punk / vibes / emoji / Imagine… / Would you visit / 抬杠对比  
- 用户要求 GenZ → 仍出通稿  

### 篇幅

- 消息约 400–700 词；通讯约 450–900 英词或 800–1500 字；材料薄则更短  

### 自检要点

无帖文钩子/emoji；数据可映射 Evidence；收束非口号墙；无离题库条目；不凑字编造  

---

## 版本补记

- v0.2 · 2026-09-18 · 主 skill 工序卡化；操作细则迁入本附录  
