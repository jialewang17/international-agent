# 交接：Evaluation Part 1 —— 事实核验

> 来源文件：原 `review/fact-check.md`
> 移出原因：审查报告 §一 建议归属表第 4 行 ——「**Evaluation Part 1**，不应纳入内容质量评测 Skill 的职责」；§二 第 6 行 ——「归入 Evaluation Part 1」；§三 ——「不应另设第三个事实审核 Skill」「不应是 Part 3 的一部分」
> 依据：v2.1 架构明确 Evaluation 三层分离，Part 1 的核心问题是「**事实和证据有没有问题？**」，检查项为 `Claim–Evidence Coverage`、`Evidence Entailment / Sufficiency`、`Source Traceability`、`Evidence Conflict`、`New Claim / Fact Drift / Fact Lock 检查`。

---

## 1. Pipeline 位置

```text
Part 1  Fact / Evidence Gate   ← 本规范
   ↓  BLOCKED → 不进入 Part 3
Part 2  External Evaluators    （P1）
   ↓
Part 3  ChinaStory Evaluation Skill
```

**Part 3 若发现疑似事实问题 → `return_to_part1 = true`，交回本环节裁决。**

---

## 2. 输入

草稿、`evidence_used`、`evidence_map`、`TaskContext`、原始用户材料、可用来源记录。

## 3. 检查顺序

1. **结构**：每个事实性论断是否有 `claim_id` 和 evidence？
2. **支持**：证据是否真的支持该句，而非只与主题相关？
3. **范围**：主语、地点、时间、样本、单位、分母是否被放大？
4. **因果**：是否把并列 / 相关写成导致 / 证明？
5. **引语**：是否逐字可回到原文；译文是否标注？
6. **时效**：政策、价格、人数、职位、网页内容是否可能过时？
7. **冲突**：不同来源是否矛盾；是否诚实呈现？
8. **遗漏**：重要的 `research_gaps` / `fact_gaps` 是否被错误隐藏？

## 4. 输出

```yaml
fact_review:
  status: pass | revise | needs_human
  coverage_rate: 0.0
  findings:
    - claim_id: C7
      severity: high | medium | low
      verdict: supported | partial | unsupported | conflict | stale
      reason: ""
      action: keep | revise | delete | needs_human
  unresolved_questions: []
```

### 严重度定义

| 级别 | 含义 | 处理 |
|---|---|---|
| `high` | 无证据事实、错误数字 / 引语、错误因果、会误导受众的范围扩大 | 必须修复或交人工 |
| `medium` | 定位不完整、口径不清、时效风险 | 修复后再审 |
| `low` | 格式、术语或可读性问题（不影响事实） | 可在语言 Review 处理 |

## 5. 规则

- 不要用模型常识替换缺失证据；
- 不要为了达到覆盖率把解释性判断伪装成事实；
- 不要删除用户材料中的限制条件；
- **Review 通过只表示"在提供材料范围内可追溯"，不表示来源本身已被独立认证。**

---

## 6. 与 Fact Lock 的关系

> 来源：v2.1 架构 ⑤ REVISE & Audit。
> 依据：「**Fact Lock 不是一套独立的第四种 Evaluation，也不是'评价完成后的最后一步'**。它是 Revise & Audit 中的事实稳定机制，**同时由 Part 1 负责检查其状态**。」

本环节需检查：是否出现 `New Claim`、`Fact Drift`、已核验事实是否被改动。
