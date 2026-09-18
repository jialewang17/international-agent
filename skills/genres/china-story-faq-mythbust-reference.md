# 误解澄清 FAQ · 语料附录（默认不整篇注入）

> **采集 / 复核日期**：2026-09-15（本会话用 WebFetch / WebSearch 抓取正文，非凭空编造）。  
> 本附录只保留**可执行结构与语气边界**；外部文章里的统计**不得**直接当作本项目 `evidence_used`。  
> 成稿可核验事实仍须来自当次用户上传 ∪ 本地库。

---

## 〇、本会话已爬取内容清单（向用户交代）

| 状态 | 来源 | URL | 抓取结果 |
|------|------|-----|----------|
| ✅ 全文 | YenKid《16 Misconceptions…》 | https://www.yenkidinchina.com/latest-posts/china-travel-16-misconceptions-and-mistakes-all-first-time-visitors-must-know | 8 条 Misconception + Yenkid 纠正 + tip；另 8 条 Mistake |
| ✅ 全文 | China for Travelers《10 China Travel Myths… Debunked (2026)》 | https://chinafortravelers.com/guides/china-travel-myths-debunked/ | Myth + **Verdict** + 数据/workaround；文末 FAQ |
| ✅ 全文 | Tasting Table《Myth Vs Fact: 8 Things… Chinese Food》 | https://www.tastingtable.com/2217067/chinese-food-myth-vs-fact-diners-stop-believing/ | Myth vs Fact；引用具名厨师 |
| ✅ 全文 | East Asia Student《10 Popular Misconceptions About Chinese》 | https://eastasiastudent.net/china/mandarin/misconceptions-myths/ | 误解条目 + **What I am NOT saying** |
| ✅ 全文 | Medium · Andrea Kriston《Chinese myths busted…》 | https://medium.com/@andrea.kriston13/chinese-myths-busted-from-dumplings-to-daily-life-0869638a2985 | 引号 Myth → **Reality:** |
| ✅ 全文 | ChinaTalk《Five misconceptions… Social Credit》 | https://www.chinatalk.nl/five-misconceptions-about-chinas-social-credit-system/ | Misconception 1–5；强调「讲清楚不是什么」 |
| ✅ 全文 | MERICS《China’s social credit score – untangling myth from reality》 | https://merics.org/en/comment/chinas-social-credit-score-untangling-myth-reality | 纠正「全民打分」神话，同时声明系统并非无害 |
| ✅ 全文 | CGTN《China-Africa… Debunking Western myths》(2024-08-31) | https://news.cgtn.com/news/2024-08-31/China-Africa-cooperation-Debunking-Western-myths-1ww7wTbX0Iw/p.html | 点名误解→数据→正面事实；**末段抬杠为反例** |
| ✅ 全文 | CGTN《Four misconceptions… overcapacity》(2026-08-24) | https://news.cgtn.com/news/2026-08-24/Four-misconceptions-behind-the-overcapacity-debate-1PRr6j6aRnG/p.html | First–Fourth misconception；承认正当关切后再分概念 |
| ✅ 全文 | CGTN《Debunking Western misconceptions about China's economic model》 | https://news.cgtn.com/news/2026-06-26/Debunking-Western-misconceptions-about-China-s-economic-model-1OhY8eoVqg0/p.html | 先复述标签→拆前提→替代框架 |
| ✅ 全文 | 社科网《在海外讲好中国故事》 | https://www.cssn.cn/gjgc/tt/202312/t20231218_5718159.shtml | 对谁讲；允许怀疑；无须辩论取胜 |
| ✅ 全文 | 驻美使馆《美国对华认知中的谬误和事实真相》 | https://us.china-embassy.gov.cn/chn/zmgx_1/zxxx/202206/t20220619_10706095.htm | **谬误N / 事实真相** 对子结构（语气偏对抗，仅学结构） |
| ⚠️ 摘要 | 驻美使馆《疫情涉华谎言与事实真相》 | https://us.china-embassy.gov.cn/chn/zmgx_1/zxxx/202504/t20250404_11588782.htm | 搜索摘要确认「谎言N→事实真相」体；与上条同结构族 |
| ⚠️ 摘要 | Wikipedia / TNW 社会信用相关 | wikipedia.org / thenextweb.com | 佐证「全民统一分」为常见误解母题；不作本项目论据 |
| ❌ 失败 | NewsTrack 饮食刻板印象文 | english.newstrack.com/... | Cloudflare 拦截，未写入骨架 |
| ❌ 未用正文 | Gabz-FM Facebook 视频页 | facebook.com/GabzFMnews/... | 仅标题/标签，无可用正文结构 |

---

## 一、结构主样本（海外列表式）

### A1 YenKid（旅行误解）
- 固定句式：`Misconception:` → `Yenkid:` 纠正 + 实用建议  
- 常承认地域差 / 部分成立（如污染「十年大降但仍有季节与区域」；现金「必须收但可能没零钱」）  
- 误解与「失误建议」分栏——本 skill 只取误解澄清栏

### A2 China for Travelers（2026 Debunked）
- 每条带 **Verdict**：`Was partially true, now has workaround` / `False` / `Overstated`  
- 强调 pre-2020 信息易过时；纠正后给 **one-tap workaround**  
- 文末另有 FAQ 折叠——主动帖可用 `items[]`，不必再叠一层百科

### A3 Tasting Table（饮食 Myth vs Fact）
- 分节标题即误解；正文 Fact 侧引用**具名厨师**（有材料才可仿）  
- 承认美式中餐改编史，非全盘否定「不存在」

### A4 East Asia Student（语言误解）
- 面向「几乎零基础读者」  
- 每条后常加 **What I am NOT saying** 防稻草人 → 对应字段 `not_claiming`

### A5 Medium · Andrea Kriston
- 引号写出谣言 → `Reality:` 短纠正 + 第一人称观感  
- 适合社交短帖语气；精确政策/数字仍须 evidence

---

## 二、复杂议题样本（学结构，慎语气）

### B1 ChinaTalk · Social Credit「Five misconceptions」
- 编号 `Misconception N`  
- 开篇声明：不急于辩护或攻击，先讲 **what it isn't**  
- 把「芝麻信用打分」与「政府社会管理/黑名单」拆开——防概念偷换

### B2 MERICS · score myth
- 纠正「全民 AI 打分」的同时写明：**纠正神话 ≠ 宣称体系无害**  
- 本项目对应：`not_claiming` 或 Fact 内边界句（见主 skill）

### B3–B5 CGTN Debunk 系列
- 可学：先点名误解 → 分条 → 数据/机制  
- **B3（中非 2024）末段**「Cold War mentality / smearing」抬杠收束 → **禁止照搬**（违反 `intl-comm.md` §C）  
- **B5（overcapacity 2026）**「legitimate concerns should not simply be dismissed」→ 允许承认正当关切后再分概念（更适海外受众）

### B6 驻美使馆「谬误 / 事实真相」
- 结构：`谬误N` + `事实真相` + 条目化论据——与 Myth/Fact 同族  
- 语气大量对美反制列举 → **海外社交澄清帖禁用该对抗腔**；仅作字段对偶参考

---

## 三、方法样本（受众与辩论边界）

### C1 社科网《在海外讲好中国故事》
- 先界定 **对谁讲**  
- 发达国家受众易疑「宣传」→ **允许怀疑、无须辩论取胜**  
- 选题找「别人想听」的共鸣点，忌硬辩赢

---

## 四、从语料蒸馏的可执行模式（主 skill 依据）

1. **显式对立**：先写 Myth/Misconception/谬误，再写 Fact/Reality/真相（A1–A5、B1、B6）。  
2. **条数**：公开帖常见 5–10 条；本仓库 zip **5–8**；材料不足宁少勿凑。  
3. **Verdict / 部分成立**：A2、A1、B5 高频是过时/夸大/概念混淆，不是「完全捏造」。  
4. **桥梁句**：A1 tip、A2 workaround——支付/出行/阅读下一手材料；非种草 CTA。  
5. **防稻草人**：A4 `not_claiming`；B2「纠正 X 不等于否认 Y」。  
6. **具名权威仅限材料有**：A3 厨师姓名；无证据不虚构引语。  
7. **过时信息门控**：A2 强调 pre-2020——无时效证据不写「截至某年免签」等。  
8. **官方 Debunk 学分条+数据，不学抬杠收束**（B3 反例；C1 + intl-comm §C）。  
9. **承认正当关切再澄清**（B5）优于「全盘抹黑对方」。

---

## 五、高频误解母题（选题提示，非默认成稿）

仅当用户主题或 `evidence_used` 覆盖时方可写入：

- 旅行：不安全 / 必须跟团 / 不会英语就不能玩 / 现金与支付 / 网络  
- 饮食：全油腻 / 全辣 / 全国一种菜 / 幸运饼干是中国传统  
- 发展：全国一律穷或一律富  
- 文化 / 语言：铁板一块；只有普通话与粤语  
- 复杂议题：社会信用「全民统一分」等——**必须有库内或用户资料**，禁止抄外网 World Bank / UNODC 数字

---

## 版本

- v0.1-corpus · 2026-09-15 · 首批源与结构蒸馏  
- v0.2-corpus · 2026-09-15 · 本会话全文复核 A1–A5、B1–B6、C1；增 ChinaTalk / MERICS / 使馆结构 / CGTN overcapacity；标明失败抓取  
- v0.3 · 2026-09-18 · 主 skill 改为工序卡；本文件为语料与细则附录  
