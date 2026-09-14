# 讲好中国故事 · 社交帖文体裁 Skill（post）

**适用**：海外社交帖文（X / Instagram / TikTok 文案等）、长帖 thread、图文页 caption。  
**不适用**：新闻通稿、深度报道/特稿（南方周末长模板）、短视频分镜脚本、评论回复。  
**状态**：**已完善**（v0.3.3 + 2026-09-14 合并 zip 平台长度/字段）。

> 老师 0822：**南方周末长模板不适合作短帖**——需要深度/特稿时走 `china-story-feature.md`，不要用本 skill 硬拉长。

> **训练重点**：不要只会写口号。一条可发帖必须让 **5W 可核对、受众可感知、权威可追溯**；选题/选题门控是上一阶段，本 skill 负责成稿。

## 权威依据（禁止凭空编造）

1. **Lasswell 5W**（Harold D. Lasswell, 1948）：Who / Says What / In Which Channel / To Whom / With What Effect——传播研究经典；与老师 0822「贴文要有 5W」的共同骨架。  
2. **老师 0822**：先把贴文做好；不同体裁不同框架；南方周末长模板不适合作短帖。  
3. **证据中介与系统硬约束**：`intl-comm.md` + `evidence-user-materials.md`——可核验事实必须落入 `evidence_used`；证据未写的职务/金额/营收/到访人次等 **禁止编造**。  
4. **zip `content_formats.md` · social_post / thread / visual_story / caption_only**：平台长度、输出字段、示例结构（见 `knowledge/content_formats.md`、`knowledge/format_examples.md`）。

---

## 一、5W 可执行标准（策划字段 + 正文表达同时满足）

最终 JSON 的 `five_w` **不可空壳**；且 **正文 `post` 必须能被对照回 5W**（读者盲测：不看标签也能感到受众与渠道）。

| 5W | 策划字段写什么 | 正文里要看见什么 | 不合格（常见） |
|----|----------------|------------------|----------------|
| **Who** | 明确发声者角色（与 identity 一致） | 语气匹配：博主感 ≠ 学者腔 ≠ 发言人口吻 | 自称 influencer 却写外交部/新闻通稿口吻 |
| **Says What** | **一句**可核验主点（场景/变化/可感知细节） | 正文围绕该点展开；事实能在 evidence 找到 | 只有「多元文化/美食」等空词，无场景无锚点 |
| **Channel** | 写明平台 | X：短、少 emoji；IG：可读+视觉感；TikTok：口播感/钩子靠前 | IG 帖写成新华社通讯或机关简报 |
| **To Whom** | 写明目标国/语境 | 至少一句**当地可感**（不必一国一典，但勿全球空话） | 参数写 America，正文却堆中国内部黑话 |
| **Effect** | 期望用户侧效果（停留/评论/愿去了解等） | 句尾有可分享意图或轻提问；忌空赞美口号 | 「Let us appreciate culture!」式空赞 |

**强制对齐**：`five_w.says_what` 的主点 = 正文核心；`five_w.to_whom` 的国家 = 用户指定国家；`five_w.channel` = 用户指定平台。

---

## 二、平台长度与变体（合并 zip）

### 2.1 单帖 `social_post`（默认）

| 平台 | 建议长度 |
|------|----------|
| twitter / X | ≤280 字符；更长请改用 thread |
| weibo（微博） | 80–140 汉字（除非用户要求更长） |
| facebook | 80–150 词 |
| instagram | 60–120 词 + hashtag 3–8 |
| linkedin | 100–180 词，稍正式 |
| tiktok | 偏口播短句；钩子靠前；hashtag 适量 |

结构：钩子（场景/反差/好奇）→ 1 个可核验事实或判断 → 可分享收束。  
字段：`post`（正文）；可选 `alt_versions`（另选 2 条）；`hashtags`；`platform`；`ops_tips`；`five_w`。

### 2.2 `thread` 长帖串（用户要长帖/推文串/thread 时）

默认 **6–10 条**（可 5–12）；每条独立可读。  
第 1 条强钩子；中间条展开判断/场景/变化；末条自然收束 + 轻提问。  
字段：`tweets[]` 或 `posts[]`；`hook`；`cta`；`hashtags`；`platform`；仍要填 `five_w`。

### 2.3 图文变体 `visual_story`（用户要图文/画册时）

4–8 页；每页 `visual` + `title` + `caption`。  
字段：`slides[]`；`cover_line`；`cta`。事实仍须落在 `evidence_used`。

### 2.4 `caption_only`（用户只要配图文案时）

字段：`caption`；`hashtags`；`alt_text`；`cta`；`platform`。

---

## 三、目标国语境（To Whom 相关）

| 国家提示 | 可写的当地可感（择一即可，勿堆砌） | 禁止 |
|----------|--------------------------------------|------|
| America | 日常通勤/周末中价/周末去打卡式具体画面；或证据中有的第三方视角 | 假装懂美国政治黑话硬凑 |
| UK | 偏社交礼貌、周末短途、克制默认 | 乱写英式刻板+圣物 |
| Japan | 季节感、物哀细节、观察式细写 | 空喊「日本人也爱说」 |
| 未指定 | 按默认 America 写清 to_whom | 伪装「全球通用中国故事」 |

**自检**：删掉国家名后，全文是否仍对「该读者」成立？若变成全球宣传腔 → **To Whom 失败**。

---

## 四、权威感怎么进正文（不是只堆引用）

1. `evidence_used` 若含 **UNESCO / 官方 / 可核验事实**：在文化 `evidence_notes` 点到即可，禁止堆砌口号/金句。  
2. `evidence_notes` 须能回答：「正文靠哪条 Evidence#」——能映射，不能只有 notes 没字段。  
3. 用户资料与本地库并存时：优先场景来自用户；权威来自本地库权威源。  
4. 无权威源时：只写 modest 场景，**不要装**成官方定论/世界第一。

---

## 五、用户提示词很短时

多数用户只说「主题：xxx」。须自行识别：主点、国家、平台、身份、态度、期望效果。  
**缺省**：platform=instagram，country=America，tone=optimistic，identity=online_influencer。  
**禁**：提示词很短却空填 5W；或提示词要求全 To Whom / Effect 却省略。

---

## 六、成稿自检（写入 JSON 前）

1. 每个 W 是否有实质内容（不是 "audience" / "platform" 占位词）？  
2. 盲测能否感到 Says What 与 To Whom？  
3. 可核验专名/数字是否都能在 `evidence_used` 找到？**证据没有职务/金额/人次等原文支撑则必须删除**。  
4. 是否在蹭目标国禁忌？或对他国抬杠？  
5. 效果期望是否落成可分享收束，而非空赞口号式 Says What？

## 版本

- v0.3-post · 体裁分册（Lasswell + 老师 0822）  
- v0.3.1-post · sarcastic 不得出口转内销  
- v0.3.2-post · 5W 可执行表 + 目标国表 + 权威进正文  
- v0.3.3-post · 2026-09-07 · 明确：事实边界为系统硬约束  
- **v0.5-post · 2026-09-14 · 合并 zip 平台长度 / thread / visual_story / caption_only**
