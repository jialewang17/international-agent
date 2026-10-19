# Rubric 调用与人工校准实施指南（Evaluation v5.1）

> **权威文件**：项目仓库 `eval/CHINASTORY_CONTENT_QUALITY_RUBRIC_v2.1.md`。本文件只提供执行说明，不复制、不改写正式行为锚点；如果找不到正式 Rubric，返回 `INSUFFICIENT_CONTEXT`，不以本文简述代替完整评分。 [E08][S01]

## 1. 六个维度及原输出 ID（保持不变）

| 维度 | 规范 `dimension_id` | 检查重点 |
|---|---|---|
| D1 | `cross_cultural_comprehensibility` | 文化知识门槛、术语解释、逻辑通达 |
| D2 | `cultural_expression_quality` | 文化语境、尊重主体、避免误导类比 |
| D3 | `audience_fit` | 对具体 Audience Profile 的适配程度 |
| D4 | `narrative_engagement_potential` | 叙事吸引潜力，不等于实际传播表现 |
| D5 | `genre_platform_fit` | Genre、Format、Platform 匹配及表现 |
| D6 | `naturalness_non_sloganeering` | 自然、具体、少口号、少模板腔 |

六维均采用原 Rubric 的 **1–5 整数 BARS**；默认为 `overall_score: null`。判定时逐维援引其专属锚点，而不是用“字数越多越好”等启发式替代。[S01]

## 2. 每次真实评分的操作

1. 校验 `rubric_version` 与已加载 Rubric 相同；记录 Rubric 的路径与哈希（如果后端支持）。
2. 检查本轮任务的 `topic/goal/genre/platform/target_language`、受众画像、内容版本。若缺失的是决定性信息，停止评分。
3. 对 D1–D6 分别阅读 5、4、3、2、1 的完整锚点，**先找证据再选相应分数**。每维输出 `score, rationale, evidence_spans, problems, revision_suggestion, confidence`。
4. 对仅需 Part 1/Part 2 裁决的问题作移交说明，不在 D1–D6 内给出事实真实性结论。
5. 不计算六维平均或任意加权结果；不得写“自动通过”阈值，除非后端有经过人工校准与审批的明确配置。

## 3. 校准集的真实使用方式 [E08]

正式的项目 Rubric §16 已经要求建立 Calibration Set，包含高、中、低质量、典型错误、边界和不同 Genre。此处把要求转成操作步骤，不发明新量表：[S01]

- 收集可授权使用、版本固定且有任务上下文的案例；记录每篇的语言、体裁、来源及 `content_version_id`。
- 安排至少两位有相应语言/编辑能力的人员**独立**使用同一版 Rubric 评分（人数与样本量需由项目实验方案确定，不把建议值当作公认最佳阈值）。
- 每维记录人工分数、原文位置、文字理由和不确定性；对分歧进行讨论或第三方复核，保留原始分歧数据。
- 只选取经过人工确认、任务相近的锚点样例作为 Judge 的参考。**不能把 LLM 自己评出的五分例子当成人工基准。**
- 固定 Judge 模型、Prompt、Rubric、语言、体裁和模型配置，评价同一批样本；比较逐维分数差异、错误定位的一致性和严重漏检。
- 如评价结果差异过大，标记“不满足当前校准目标”，提交人工复核；没有经实验确定的阈值时，不编造自动停用阈值。

## 4. 非英语与真实受众验证 [E08]

- 对英文、中文及其他目标语言**分层报告**一致性；英语表现不能自动外推到其他语言。[S06]
- 自动评价 D4 只能称 **Engagement Potential**。真实理解、兴趣、信任和误读率须使用真实目标受众实验；未开展时 `real_audience_evaluation: NOT_EVALUATED`。[S01]
- 数值 `confidence` 只有经过相应人类样本校准后，才有条件用于量化解释；未校准用 `null` 并注明不确定性（需 API 兼容）。**不称其为真实正确概率。**[S04/S08]

## 5. 资料来源

- [S01] [ChinaStory Content Quality Rubric v2.1](https://github.com/jialewang17/international-agent/blob/main/eval/CHINASTORY_CONTENT_QUALITY_RUBRIC_v2.1.md)：§5、§15、§16、§19–20。
- [S04] [G-Eval, EMNLP 2023](https://aclanthology.org/2023.emnlp-main.153/)：明晰评价方法、与人类判断进行对比的实证参考（不能直接证明本项目校准成功）。
- [S06] [Fu & Liu, Findings EMNLP 2025](https://aclanthology.org/2025.findings-emnlp.587/)：多语言 Judge 评分一致性差异。
- [S08] [NIST AI RMF Measure](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/)：测试评估、量化与定性监控、独立验证。
