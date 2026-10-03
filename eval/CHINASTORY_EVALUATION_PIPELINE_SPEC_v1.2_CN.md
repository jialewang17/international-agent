---
title: ChinaStory Evaluation Pipeline Spec v1.2
---

*评价流水线规范｜根据后续讨论修订版*

# 0. 文档状态与修订说明

本版替代此前把 Part 1、Part 2、Part 3 全部统称为"Evaluation
Skill"的写法。后续讨论已经明确：Evaluation Pipeline 是总流程；ChinaStory
Evaluation Skill 只属于 Part 3。

  -------------------------------------------------------------------------------------------------------------------------------
  项目                                本版定义
  ----------------------------------- -------------------------------------------------------------------------------------------
  文档职责                            定义三部分评价如何串联、各部分的输入输出、阻断/继续规则，以及最终如何进入修改与人工审核。

  Part 1                              Fact / Evidence Gate：事实与证据的客观质量控制。

  Part 2                              External Evaluators：复用已有评价工具，重点检查中→英转换中的语义保持与翻译错误。

  Part 3                              ChinaStory Evaluation Skill：自研跨文化内容质量评价，只负责已经通过前置检查的内容质量判断。

  最终责任                            自动评价不等于发布批准；最终进入 Human Review。

  阈值状态                            未通过实验验证的阈值、权重、自动放行线均标记为 TBD，不写成既定事实。
  -------------------------------------------------------------------------------------------------------------------------------

# 1. 核心原则

-   事实层不能为了叙事效果被改写；可核查主张必须能够回溯到证据与来源。

-   Hard Gate 与 Soft Score
    分离：严重事实问题不能被"有趣、自然、叙事好"等分数抵消。

-   Translation Quality ≠ International Communication
    Quality：第二部分检查"有没有转错"，第三部分检查"有没有转好"。

-   LLM-as-a-Judge 是自动评价代理，不应表述为"等同真人专家"。

-   真实传播效果必须由目标受众实验验证；自动 Judge 只能评价潜在质量。

-   Evaluation 负责发现问题和形成结构化修改指令；主要重写仍交回 Writing
    / Transcreation Skill。

# 2. 总体架构

生成内容 / 英文 Transcreation\
↓\
Part 1 Fact / Evidence Gate\
↓ PASS\
Part 2 External Evaluators\
↓\
Part 3 ChinaStory Evaluation Skill\
↓\
Evaluation Report\
↓\
Revision Instruction\
↓\
Writing / Transcreation Skill → V2\
↓\
重新评价\
↓\
Human Review / Approve

# 3. Part 1｜Fact / Evidence Gate

目标：先回答"这篇内容有没有不能接受的事实与证据问题"。这是运行顺序上的第一关，不是
Part 3 自研评价 Skill。

  ------------------------------------------------------------------------------------
  检查项                  核心问题                             处理
  ----------------------- ------------------------------------ -----------------------
  Claim--Evidence         可核查 Claim 是否有对应 Evidence？   关键 Claim 无证据 →
  Coverage                                                     BLOCK / RETURN

  Evidence Entailment     Evidence 是否真正支持 Claim          不支持/过度推断 → BLOCK
                          的强度、数字、时间、人物等？         / RETURN

  Source Traceability     能否回溯 EvidenceSpan → Source？     关键来源不可追溯 →
                                                               BLOCK

  Evidence Conflict       不同来源是否对关键事实存在冲突？     冲突未解决 →
                                                               WAIT_FOR_HUMAN

  Fact Drift / New Claim  改稿后是否新增或改变事实？           新增 Claim → 返回
                                                               Evidence Gate

  Fact Lock               已核验事实是否在改稿中被擅自改写？   违反锁定事实 → BLOCK
  ------------------------------------------------------------------------------------

Part 1
的输出至少应包含：gate_status、claims、evidence_links、unsupported_claims、conflicts、new_claims、fact_drift、required_actions。

# 4. Part 2｜External Evaluators

目标：复用成熟外部 evaluator，重点检查中文母稿经过 Transcreation
后是否发生语义损失、错译、漏译或错误新增。第一阶段优先 xCOMET-lite /
XCOMET；ReMedy 暂不作为 MVP 必选项。

  -------------------------------------------------------------------------------------------------
  对象                    检查内容                                     不负责
  ----------------------- -------------------------------------------- ----------------------------
  中文母稿 ↔ 英文版本     意义保持、漏译、错译、错误新增、可能的错误   不判断海外受众是否真正理解
                          span                                         

  术语/专名               可配合 glossary / rule 检查规范性            不替代文化解释质量评价

  外部 evaluator 输出     作为辅助证据进入总报告                       不直接决定国际传播质量总分
  -------------------------------------------------------------------------------------------------

若 Part 2 发现严重语义错误，应优先返回 Transcreation
修订；轻微问题可携带 warning 进入 Part 3。严重阈值目前为 TBD，需校准。

# 5. Part 3｜ChinaStory Evaluation Skill（自研）

目标：评价"已经基本事实可靠、语义转换无严重错误"的候选稿，是否真正符合
ChinaStory 的跨文化内容质量要求。Part 3 使用独立的 Content Quality
Rubric；Rubric 定义"评什么"，Skill Spec 定义"程序怎么评"。

  --------------------------------------------------------------------------------------------------------
  维度                                核心判断
  ----------------------------------- --------------------------------------------------------------------
  Cross-cultural Comprehensibility    低先验知识目标受众是否能理解核心概念、背景与因果关系？

  Cultural Expression Quality         是否避免文化概念降维、错误等同、去语境化和空泛文化评价？

  Audience Fit                        是否依据 prior knowledge、unknown terms、content environment
                                      等可观察变量适配，而非国籍刻板印象？

  Narrative Engagement Potential      是否有清晰认知入口、具体人物/行动/场景或问题驱动，而非仅抽象说明？

  Genre & Platform Fit                结构、长度、表达方式是否符合指定体裁与平台任务？

  Naturalness / Non-sloganeering      是否自然、具体、非口号化，避免中文宣传话语的机械外译？
  --------------------------------------------------------------------------------------------------------

每个维度应输出：score（1--5）、evidence/problem_span、reason、revision_direction、confidence。当前不建议用未经验证的固定总权重替代逐维诊断。

# 6. Part 3 输入 / 输出合同

## 6.1 最小输入

-   task_context：topic、goal、genre、platform。

-   audience_profile：language、prior_knowledge、likely_unknown_terms、available_cultural_anchors、desired_depth
    等。

-   candidate_content：待评价英文/目标语成稿。

-   source_master：中文母稿或生成前的核心内容版本，用于上下文参考。

-   rubric_version：必须记录具体版本，保证实验可复现。

-   upstream_results：Part 1 / Part 2 的状态与 warning；Part 3
    不重新承担它们的职责。

## 6.2 最小输出

{\
\"status\": \"REVISE \| READY_FOR_HUMAN_REVIEW\",\
\"rubric_version\": \"\...\",\
\"dimensions\": \[\
{\
\"name\": \"\...\",\
\"score\": 1,\
\"evidence_or_problem_span\": \"\...\",\
\"reason\": \"\...\",\
\"revision_direction\": \"\...\",\
\"confidence\": \"low\|medium\|high\"\
}\
\],\
\"priority_issues\": \[\],\
\"revision_instruction\": \[\],\
\"limitations\": \[\]\
}

# 7. Revision Loop

Evaluation Skill\
↓ 发现问题\
结构化 Revision Instruction\
↓\
Writing / Transcreation Skill\
↓\
Version 2\
↓\
Part 1（检查是否新增/改变事实）\
↓\
必要时 Part 2\
↓\
Part 3 重新评价\
↓\
Human Review

-   Evaluation Skill
    可以提出修改方向，但不应自己随意重写后再给自己打分。

-   任何改稿新增事实必须重新进入 Part
    1，而不能直接沿用上一版本的事实通过状态。

-   保存 version_id、rubric_version、judge_model、修改原因和前后问题
    span，支持审计。

# 8. Rubric 版本迭代与校准要求

后续讨论已明确：Rubric
不能靠团队主观定稿，应通过实验逐版校准。建议版本链如下：

  -----------------------------------------------------------------------------------------------------------
  阶段              实验                     目的                                           建议产出
  ----------------- ------------------------ ---------------------------------------------- -----------------
  A                 内容效度                 验证维度必要性、清晰度、重复/缺失              Rubric v2.1

  B                 2--3 名评分者对 30--50   验证评分者一致性并修订 anchors                 Rubric v2.2
                    篇样本盲评                                                              

  C                 单变量退化 / 故障注入    验证各维度能否定向识别已知问题                 Rubric v2.3

  D                 Human--AI Judge 校准     比较人工与 Skill 的各维度一致性、偏差和漏检    Evaluation Skill
                                                                                            v1

  E                 小规模真实目标受众实验   验证 Rubric                                    Rubric v3
                                             高分是否对应理解、兴趣、可信度等真实结果       

  F                 V1→Evaluate→Revise→V2    验证评价闭环是否实际改善内容且不新增事实错误   Final Framework
  -----------------------------------------------------------------------------------------------------------

旧版 ROC
权重作为历史研究依据保留，但当前不把重新优化权重作为首要任务。事实类指标已经迁移到
Part 1，不能再与软质量维度通过补偿式总分相互抵消。

# 9. Real Audience / Human Review 边界

-   自动 Judge 可以输出 Narrative Engagement
    Potential，但不能声称"真实海外用户参与度"。

-   真实受众实验可测：核心概念理解、可信度、继续了解意愿/兴趣、理解难度或文化距离、记忆。

-   最终发布批准由人完成；自动系统只能给出
    READY_FOR_HUMAN_REVIEW，而不是自动公开发布。

-   人工可 Accept / Edit / Reject，并记录理由；这些数据可反过来用于后续
    Rubric 校准。

# 10. MVP 实现优先级

  -----------------------------------------------------------------------
  优先级                              必须完成
  ----------------------------------- -----------------------------------
  P0                                  Part 1：Claim--Evidence--Source
                                      跑通；至少一个
                                      unsupported/conflict/new claim
                                      阻断案例。

  P0                                  Part 3：六维结构化 Judge
                                      输出，能定位 problem
                                      span、reason、revision。

  P0                                  Revision Loop：评价 → 修改指令 →
                                      生成 V2 → 重新检查。

  P1                                  接入 xCOMET-lite / XCOMET 作为 Part
                                      2 辅助 evaluator。

  P1                                  用人工标注子集校准 Part
                                      3；完成至少一次单变量退化实验。

  P2                                  真实目标受众小规模验证；扩展更多
                                      evaluator。
  -----------------------------------------------------------------------

# 11. 当前明确不应写死的参数

-   Part 2 严重错误阈值：TBD。

-   Part 3 各维度自动通过阈值：TBD。

-   六维是否需要总分及其权重：TBD；优先报告逐维结果。

-   自动修改最大轮数：TBD。

-   Human--AI 一致性可接受阈值：TBD，需根据人工校准样本确定。

-   真实受众实验样本量与统计检验方案：根据可获得样本进一步确定。

# 12. 与仓库其他规范的关系

01 CHINASTORY_EVALUATION_PIPELINE_SPEC_v1.2\
→ 定义 Part 1 / Part 2 / Part 3 怎么串\
\
02 CHINASTORY_CONTENT_QUALITY_RUBRIC_v2.x\
→ 只定义 Part 3 "评什么"、评分 anchors、研究依据与验证方法\
\
03 CHINASTORY_EVALUATION_SKILL_SPEC_v1.x\
→ 只定义 Part 3 自研 Skill 的工程实现、Prompt/Schema/接口

# 13. 一句话定位

**ChinaStory Evaluation Pipeline 不是一个"LLM
给文章打总分"的模块，而是"事实证据 Gate → 外部跨语言 evaluator →
自研跨文化 Rubric Judge → 修改闭环 →
真人验证/人工批准"的分层评价系统。**
