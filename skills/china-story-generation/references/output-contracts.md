# 输出契约（形态 · 字段 · 异常处理）

> 合并来源：
> 1. 原 `entry/china-storytelling-reference.md`（Tier-1/Tier-2 形态、format→genre 映射、缺料处理）
> 2. 原 `shared/claim-evidence-source.md` 第 3 节（`evidence_map[]` 字段表）与第 6 节（输出模板）
> 3. 原 `shared/evidence-user-materials.md` 第 4 节（`evidence_used` 最小输出）

## 变更记录

| 编号 | 改动 | 来源 | 依据 |
|---|---|---|---|
| O-01 | 原 `entry/china-storytelling-reference.md` 独立文件取消，内容并入本卡 | 审查报告 §五 表第 2 行：「并入 Generation 的格式参考」；§六 Generation 结构只列 4 份 references | 「不需要独立激活」——形态与字段是选择时按需查阅，不是常驻上下文 |
| O-02 | 证据字段表从 `shared/claim-evidence-source.md` 迁入本卡，作为输出格式定义；证据的**建立与裁决**移交后端 | 审查报告 §二 第 4 行：「生成侧保留引用规则」 | 「避免模型自己生成证据映射，又自己判定证据有效」 |
| O-03 | 形态表保留，但不再由入口卡常驻，改为按需读取 | 审查报告 §三、§六 | 渐进式加载：主卡只保留本轮必需工序 |

---

## 1. Tier-1 形态

`social_post`、`thread`、`news_article`、`visual_story`、`short_video`、`press_kit`

## 2. Tier-2 形态

`explainer`、`quote_card`、`reel_hook`、`caption_only`、`longform`、`in_depth_report`、`headline_pack`、`newsletter_brief`、`youtube_script`、`podcast_script`、`faq_mythbust`、`talking_points`、`bilingual_pair`

## 3. format → genre 映射

| format | genre |
|---|---|
| `social_post`、`thread`、`visual_story`、`caption_only` | post |
| `news_article`、`newsletter_brief`、`press_kit` | news |
| `longform` | feature |
| `in_depth_report` | indepth |
| `short_video`、`reel_hook`、`youtube_script` | script |
| `faq_mythbust` | faq |

## 4. `evidence_used[]`

```yaml
evidence_used:
  - evidence_id: U1
    source_type: 用户上传        # 用户上传 / 本地库 / 外部检索
    source_name: garden-notes.md
    locator: p.1, paragraph 2
    excerpt: "……"                # 原文摘录
    scope: "一处苏州园林的修复工程"
    time_scope: current | dated | unknown
    status: usable
```

- 只有系统**实际检索并保存 URL/标题/定位**时，才可加入 `外部检索`；不支持检索时禁止凭记忆创建 `W` 证据。
- 使用翻译时另列 `translation_note`，不得把译文冒充原文。

## 5. `evidence_map[]`（逐条论断绑定）

| 字段 | 必填 | 规则 |
|---|---:|---|
| `claim_id` | 是 | `C1, C2…`，原子化，一条只表达一个可核验命题 |
| `claim_text` | 是 | 成稿中的原句或最小连续句，不改写 |
| `claim_type` | 是 | `fact` / `quote` / `number` / `causal` / `interpretation` / `scene_detail` |
| `evidence_ids` | 是 | 对应 `evidence_used` 编号；无证据填 `—` |
| `quote_original` | 事实/引语必填 | 来源原文摘录，不要把模型改写当原文 |
| `source_type` | 是 | 用户上传 / 本地库 / 外部检索 |
| `source_name` | 是 | 文件名、机构或页面标题 |
| `locator` | 是 | 页码、段落、章节、URL + 页面日期等 |
| `scope` | 有范围时必填 | 人群、地点、样本、时间范围 |
| `support_status` | 是 | `supported` / `partial` / `unsupported` / `conflict` / `stale` |
| `action` | 是 | `keep` / `revise` / `delete` / `needs_human` |
| `notes` | 否 | 口径、翻译、矛盾或剩余风险 |

**处理规则**：

1. `unsupported` → `delete`（不能因篇幅不足而保留）
2. `partial` → `revise`（收缩主语、时间、范围或确定性）
3. `conflict` / `stale` → `needs_human`（正文不得假装只有一个确定答案）
4. 数字必须保留单位、时间、分母/样本和统计范围；"十余种"不能变成精确数字
5. 跨来源只能并列呈现，除非某条来源明确建立因果
6. 引语须原文；译文格式为 `translated_quote` + `translation_note: translated from U1`
7. 无可定位来源的"背景常识"从正文删除

**覆盖率**：

```text
factual_claim_coverage = supported_or_revised_factual_claims / total_factual_claims
```

长文硬事实目标 100%。**覆盖率不是"真实度"证明**——来源本身的真实性、时效和利益关系仍须人工审核。生成侧不得为了达到覆盖率把解释性判断伪装成事实。

---

## 5. 缺料与异常处理

| 情形 | 处理 |
|---|---|
| 缺关键事实 | 输出 `missing_fields`，先追问或输出缩小范围的版本 |
| `gate=blocked` | 只输出阻塞原因与补救动作，**不输出貌似完整的成稿** |
| 体裁不确定 | 最多提一个澄清问题；用户不答则默认 `post` 并说明假设 |
| 用户只要"修改/检查" | 不擅自重写成另一体裁，先按请求执行 Review |
| 证据冲突 / 过期 | 不自行裁决，写入 `needs_human` |

---

## 6. 输出模板（完整示例）

```yaml
evidence_map:
  - claim_id: C1
    claim_text: "The restoration kept the Taihu stones in their original positions."
    claim_type: fact
    evidence_ids: [U1]
    quote_original: "苏州一处园林修复工程保留了原有太湖石摆放位置。"
    source_type: 用户上传
    source_name: garden-notes.md
    locator: p.1, paragraph 1
    scope: "一处园林"
    support_status: supported
    action: keep
```
