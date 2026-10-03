# ChinaStory Evaluation Skill Specification v1.1
## ChinaStory 自研内容评价 Skill 规范

**文件名**：`CHINASTORY_EVALUATION_SKILL_SPEC_v1.1.md`  
**版本**：v1.1  
**所属模块**：Evaluation Pipeline — Part 3  
**上位标准**：`CHINASTORY_CONTENT_QUALITY_RUBRIC_v2.1.md`  
**定位**：定义 Part 3 自研 Evaluation Skill 如何按照 Rubric 检查已经生成的内容。  
**性质**：生成后质检 Skill，不是内容生成 Skill。

---

# 1. Skill 目标

```text
已生成内容
   ↓
读取 Task Context / Audience / Genre / Platform
   ↓
加载 ChinaStory Content Quality Rubric
   ↓
执行 D1–D6 独立评价
   ↓
定位原文问题
   ↓
生成 Revision Suggestions
   ↓
结构化 Evaluation Result
```

---

# 2. 职责边界

## MUST

- 读取待评价内容和任务上下文；
- 按指定 Rubric Version 执行 D1–D6；
- 每个维度输出 score、rationale、evidence spans、problems、revision suggestion、confidence；
- 提取 priority issues；
- 支持修改后的版本重新评价；
- 记录模型、Prompt、Rubric 和 Calibration 版本。

## MUST NOT

- 从零生成正文；
- 执行 Part 1 Claim–Evidence 事实门控；
- 把 Part 2 外部 evaluator 结果冒充为自己的评分；
- 模拟真实海外受众并声称是真实用户结果；
- 使用国籍刻板印象推断 Audience Fit；
- 自动产生最终 `APPROVED`；
- 为提高评分自行增加未经验证的事实。

---

# 3. 与 Pipeline 的接口

```text
Part 1
Fact / Evidence Gate
      ↓
Part 2
External Evaluators
      ↓
Part 3
ChinaStory Evaluation Skill
      ↓
Unified Evaluation Report
```

Part 1 若为 `BLOCKED`，原则上不进入正常 Part 3 评价。

Part 2 结果可作为独立上下文保存，但不得直接决定 D1–D6 分数。

Part 3 若发现疑似事实问题：

`RETURN_TO_PART1 = true`

---

# 4. 输入契约

```json
{
  "evaluation_id": "eval_xxx",
  "task_id": "task_xxx",
  "version_id": "v2",
  "rubric_version": "CHINASTORY_CONTENT_QUALITY_RUBRIC_v2.1",
  "task_context": {
    "topic": "苏绣",
    "goal": "understanding_and_interest",
    "genre": "social_post",
    "platform": "Instagram",
    "target_language": "en-US"
  },
  "audience_profile": {
    "prior_knowledge": "low",
    "likely_unknown_terms": [],
    "desired_depth": "medium"
  },
  "content": {
    "language": "en-US",
    "text": "..."
  },
  "upstream_evaluation": {
    "part1_status": "PASS",
    "part2_results": []
  }
}
```

---

# 5. Preflight

检查：

- content 是否存在；
- Rubric Version 是否支持；
- Task Context 是否足够；
- Audience Profile 是否足够；
- Genre / Platform 是否明确；
- Part 1 状态是否允许继续。

关键上下文不足：

`status = INSUFFICIENT_CONTEXT`

不得自行猜测。

---

# 6. Evaluation Procedure

```text
PRECHECK
   ↓
LOAD_RUBRIC
   ↓
D1 Cross-cultural Comprehensibility
   ↓
D2 Cultural Expression Quality
   ↓
D3 Audience Fit
   ↓
D4 Narrative Engagement Potential
   ↓
D5 Genre & Platform Fit
   ↓
D6 Naturalness & Non-sloganeering
   ↓
PRIORITIZE_ISSUES
   ↓
BUILD_REVISION_SUGGESTIONS
   ↓
OUTPUT_RESULT
```

六个维度应独立判断，不要求必须按顺序串行实现。

---

# 7. Judge Rules

Judge MUST：

1. 先定位文本证据，再评分；
2. 使用 Rubric 明确的 BARS；
3. 说明主要扣分原因；
4. 给出具体、最小必要的修改建议；
5. 区分“潜在传播质量”与“真实传播效果”；
6. 保留不确定性；
7. 不因一个维度表现优秀而抬高其他维度；
8. 不因 Part 2 外部工具给出高分而自动提高自身评分。

Judge SHOULD 使用相对稳定、低随机性的配置，提高重复评价的一致性。

---

# 8. 单维度输出

```json
{
  "dimension_id": "audience_fit",
  "score": 3,
  "confidence": 0.78,
  "evidence_spans": [
    {
      "text": "...",
      "start": 40,
      "end": 58
    }
  ],
  "rationale": "...",
  "problems": ["..."],
  "revision_suggestion": "..."
}
```

---

# 9. 总输出

```json
{
  "evaluation_id": "eval_xxx",
  "task_id": "task_xxx",
  "version_id": "v2",
  "rubric_version": "CHINASTORY_CONTENT_QUALITY_RUBRIC_v2.1",
  "status": "COMPLETED",
  "dimensions": [],
  "priority_issues": [],
  "revision_suggestions": [],
  "overall_score": null,
  "return_to_part1": false,
  "real_audience_evaluation": "NOT_EVALUATED",
  "human_review": "PENDING",
  "audit": {
    "judge_model": "...",
    "prompt_version": "...",
    "rubric_version": "...",
    "calibration_set_version": "...",
    "timestamp": "..."
  }
}
```

---

# 10. Priority Issues

Part 3 内部推荐优先级：

1. 严重文化误读 / 失真风险；
2. 跨文化理解障碍；
3. Audience Fit；
4. Genre / Platform Fit；
5. 叙事组织；
6. 自然度与语言润色。

疑似事实错误不由本 Skill 裁决，应返回 Part 1。

---

# 11. Revision Interface

Evaluation Skill 负责提出修改指令，不承担主要重写。

```text
Evaluation Skill
      ↓
Revision Instruction
      ↓
Generation / Transcreation Skill
      ↓
Version N+1
      ↓
重新进入 Part 1
```

示例：

```json
{
  "target_dimension": "cross_cultural_comprehensibility",
  "problem": "陌生文化概念首次出现时缺少解释",
  "instruction": "增加一句简短自然的解释，不新增事实性信息。",
  "preserve": ["verified_facts"]
}
```

---

# 12. Calibration Interface

Skill 应支持加载：

- `rubric_version`
- `calibration_set_version`
- anchor examples
- task context

正式实验中比较：

```text
ChinaStory Evaluation Skill
        vs
External / Generic Evaluator
        vs
Human Evaluators
```

用于分析自研 Skill 对 ChinaStory-specific 问题的识别能力及与人工评价的一致性。

---

# 13. 状态

推荐最小状态：

- `CREATED`
- `PRECHECK`
- `INSUFFICIENT_CONTEXT`
- `SCORING`
- `COMPLETED`
- `REVISION_RECOMMENDED`
- `RETURN_TO_PART1`
- `HUMAN_REVIEW_PENDING`

最终 `APPROVED` 由整体 Pipeline 的 Human Review 产生，不由本 Skill 产生。

---

# 14. MVP 开发优先级

## P0

- Input / Output Schema
- Rubric Loader
- D1–D6 Judge
- Evidence Span 定位
- Priority Issues
- Revision Suggestions
- Audit Metadata

## P1

- Calibration Examples
- 多次 Judge 稳定性测试
- Genre-specific 子规则
- 前端问题高亮

## P2

- Judge–Human agreement 分析接口
- 多语言 Calibration
- 实验统计导出
- Real Audience Evaluation 结果接入展示

---

# 15. 一句话定义

> **ChinaStory Evaluation Skill v1.1 是 Part 3 的自研生成后质检 Skill：它按照项目自研 Rubric 对已生成内容进行六维评价，输出可解释的问题定位与修改建议，但不负责事实门控、正文生成或最终人工批准。**
