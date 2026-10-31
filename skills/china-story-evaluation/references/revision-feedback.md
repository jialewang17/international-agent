# Part 3 修改反馈 → Generation 的受控 Revision（v5.1）

> 评价者只**提出修改指令**，由 Generation Skill 执行 V2，由 Part 1 再核事实。任何修改都不能因提升 D1–D6 分数而放松事实门禁。[E10][S02/S03]

## 1. 基本指令：保留四个旧字段

```json
{
  "target_dimension": "cross_cultural_comprehensibility",
  "problem": "陌生文化概念首次出现时缺少必要解释",
  "instruction": "根据现有已验证材料补一句简单解释，不新增历史断言。",
  "preserve": ["verified_facts"]
}
```

**必须先找到原文问题，再提具体修改**。禁止“让文章更吸引人”“尽量提高分数”这样的空泛或目标泄漏指令。

## 2. v5.1 继续保留的推荐扩展（需更新 API Schema）[E10]

```json
{
  "target_dimension": "cross_cultural_comprehensibility",
  "problem": "首次出现的苏绣术语未给出工艺解释",
  "instruction": "在首次出现处添加一句由现有证据支持的工艺类别解释；不写新的年代、数字或引用。",
  "preserve": ["verified_facts", "quoted_text"],
  "issue_id": "E-D1-001",
  "severity": "medium",
  "location": {"text": "Suzhou embroidery", "start": 0, "end": 17},
  "expected_check": "修改后在首次出现处能识别苏绣的工艺属性，核心事实与 V1 一致。",
  "requires_fact_recheck": true
}
```

**定位示例配套的 `content.text` 为**：`Suzhou embroidery is a traditional Chinese craft.`。使用 Unicode 码点索引，`[0:17]` 恰好是 `Suzhou embroidery`，不是旧文档中不一致的 `40:58`。[E04/E10]

| 扩展字段 | 用途 | 注意 |
|---|---|---|
| `issue_id` | 将问题、指令、V2 后重新评价对应起来 | 使用唯一 ID，不将同一问题复制多条 |
| `severity` | `high/medium/low`，引导人工与修改优先级 | 不等于事实违规裁决 |
| `location` | 与本次 `content.text` 一致的原文跨度 | 不得指向另一个版本或重排文本 |
| `expected_check` | 描述可以在 V2 中判断的修复条件 | 不用“D1 必须加到 5 分”替代目标 |
| `requires_fact_recheck` | 是否包含可能影响论断的改写 | 完成 V2 后按架构仍需 Part 1 复核 |

## 3. 维度与修改类型

| 维度 | 允许修改 | 严格保护 |
|---|---|---|
| D1 | 缩短句子、解释文化术语、调整信息顺序 | 不创造新的文化起源或背景事实 |
| D2 | 去除异国情调或刻板泛化，保留文化主体性 | 不捏造受访者或社区同意 |
| D3 | 调整专业程度和读者进入点 | 不假设“某国读者天生喜好” |
| D4 | 调整 Hook、节奏、各段功能 | 不伪造场景、情绪、采访 |
| D5 | 改善 Thread 结构、新闻导语、轮播说明 | 不绕过硬性平台限制或新闻归属审核 |
| D6 | 去口号、自然化、具体化 | 不以新数字和形容词冒充证据 |

## 4. 版本闭环

`Part3(Evaluation v5.1) → revision_suggestions[] → Generation 生成 V2 → Part1 核查新增/变化论断 →（必要时 Part2）→ Part3 复评 → GateC 人工审核`。[S02]

- 比较 V1/V2 的问题修复率时必须保留原版本和 Span；不要给 Judge 贴“v4.1 一定更优”的标签。[S05]
- 对疑似事实错误的指令只写“先返回 Part 1 核查”，不要直接让 Generation 修改人物、日期、归属或因果。
- 发布批准只能由人工决定。

## 5. 来源

- [S02] [ChinaStory Evaluation Pipeline v1.2 §7](https://github.com/jialewang17/international-agent/blob/main/eval/CHINASTORY_EVALUATION_PIPELINE_SPEC_v1.2_CN.md)。
- [S03] [ChinaStory Evaluation Skill Spec v1.1](https://github.com/jialewang17/international-agent/blob/main/eval/CHINASTORY_EVALUATION_SKILL_SPEC_v1.1.md)。
- [S04] [G-Eval](https://aclanthology.org/2023.emnlp-main.153/)：结构化任务明确性可供参考，但字段为**本项目设计建议**，并非论文规定。
