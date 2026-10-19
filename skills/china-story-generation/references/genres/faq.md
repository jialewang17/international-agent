# 体裁方法：faq（误解澄清 / 辟谣 / myth vs fact）

> 来源：原 `genres/faq/china-story-faq-mythbust.md` + `genres/faq/china-story-faq-mythbust-reference.md`
> 层级变更：由「独立顶层 Skill」降为 Generation Skill 的内部方法（来源：审查报告 §六）

## 何时使用

**只有**当用户或证据**明确存在一个误解 / 不完整前提**时使用。没有明确对立前提 → 改用普通解释帖（`post` 或 `explainer`）。

## 步骤

1. 明确受众和要澄清的误解。
2. 每条 `items[]` 由 `myth` + `fact` 组成，可加 `verdict`、`not_claiming`、`evidence_refs`。
3. 优先区分：**错误 / 过时 / 夸大 / 概念混淆 / 部分成立**；不要把复杂议题压成绝对真/假。
4. 承认合理关切、说明证据范围；不使用国家攻击、羞辱和抬杠收束。

## 单条模板

```yaml
- myth: "常见说法……"
  verdict: "overstated / outdated / partially true / unsupported"
  fact: "在本材料支持的范围内……"
  not_claiming: "这不等于声称……"
  evidence_refs: [U1, K2]
```

**"纠正一个误解"不等于证明相反的宏大结论**；证据只支持局部事实 → 保留局部范围。

## 输出

`genre: faq`、`format: faq_mythbust`、`title`、`audience`、`intro`、`items[]`、`closing`、`evidence_notes`。

## 红线

材料不足宁少勿凑；每条事实有来源；**外部网页统计不能在未检索记录的情况下直接使用**。
