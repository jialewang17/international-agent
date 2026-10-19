# LLM-as-a-Judge 可靠性、偏差与多语言校准 SOP（v5.1）

> 此指南用于实验和正式部署前验证，不改变原 Rubric 评分标准，也不假装模型评分等于受众传播效果。[E07/E08]

## 1. 固定实验条件

- 同一测试批次固定：`judge_model`（包括具体模型/网关版本）、运行温度和参数、Prompt 版本、Rubric 版本、校准集版本、目标语言、Genre、Audience Profile。
- 内容提交给模型前隐藏“V1/V2”、“旧版/新版”、“人工优质样本”等会造成偏差的标签。
- 相同文章至少进行复评以观察波动；采样次数属于预注册实验设计，**不能假称某个次数有普遍最优性**。
- 逐个维度报告分数分布、重测差异、Span 是否真实指向正文、与人工的分歧，不只报告整体一致率。[S04/S05/S08]

## 2. 绝对评分与成对比较不能混同

- **绝对评分**：单篇按 D1–D6 逐维 1–5 评分，不依赖比较对象。
- **成对比较**（若团队另做实验）：使用盲评，A→B 和 B→A 两种呈现顺序，检查位置偏差及冗长偏好；成对胜率仅是实验性附加指标，**不得直接替换官方 D1–D6 分数**。[S05]
- 不因文本较长自动给高分；News 也不因避免社媒 Hook 而被 D4 不合理压低。

## 3. 人工校准流程 [E08]

1. 由有目标语言能力的编辑独立按正式 Rubric 评价校准样本，含高/中/低、边界、各体裁和典型错例。
2. 保存 `human_scores`, `human_spans`, `human_rationale`, `disagreements`, `genre`, `language`、授权状态与版本。
3. Judge 依 Rubric BARS、任务、受众和**已获人工审核的同类型样例**进行评分。
4. 记录逐维误差、问题识别一致性、严重文化误读漏检与误报；必要时通过协商/第三名编辑处理较大争议。
5. 样本尚不足时将 `confidence_status` 标记为 `UNCALIBRATED`，不要输出看似精确的置信概率。[S01/S04/S08]

## 4. 多语言层化 [E08]

- 英文、中文等目标语言分别抽样评价和报告结果；如研究涉及多语言，还应覆盖实际产品支持的语言与场景。
- 不能把一个语言的人工-模型一致率直接当成另一语言的结果。研究发现多语言 Judge 的一致性可能明显偏低。[S06]
- 翻译对错仍是 Part 2；Part 3 多语言关注目标语言内容是否清楚、自然、适合受众。

## 5. 内容真实表现的外部验证

- 若要证明海外受众真正能理解、信任并愿意继续了解，需要邀请真实符合筛选条件的受众作研究；提前约定理解题、阅读困难、误解率、兴趣/信任等观测指标。
- 对真实读者的模拟、AI personas 只能用于探索性发现问题，**不能记作真实数据**。[S01/S08]
- 如果未做受众实验：`real_audience_evaluation="NOT_EVALUATED"`。

## 6. 指标和阈值的前提

- 仓库 Rubric v2.1 §19 将样本量、自动通过阈值、Human–Judge 一致率阈值、语言分组等标记为 TBD；本 SOP 保持 TBD。
- 工程团队应先定义实验计划与可接受质量标准，经人类审批后写入部署配置；模型自行给出的 `confidence` 不能直接控制是否发布。

## 7. 依据

- [S01] [ChinaStory Rubric v2.1 §16/§19](https://github.com/jialewang17/international-agent/blob/main/eval/CHINASTORY_CONTENT_QUALITY_RUBRIC_v2.1.md)。
- [S04] [G-Eval, EMNLP 2023](https://aclanthology.org/2023.emnlp-main.153/)：评价-人工一致性研究与模型偏差讨论。
- [S05] [MT-Bench LLM-as-a-Judge, 2023](https://arxiv.org/abs/2306.05685)：位置、冗长、自我增强偏差。
- [S06] [Multilingual LLM-as-a-Judge, EMNLP 2025](https://aclanthology.org/2025.findings-emnlp.587/)：跨语言一致性限制。
- [S08] [NIST AI RMF Measure](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/)：TEVV 与持续监控。
