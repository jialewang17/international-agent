# ChinaStory Evaluation Skill v4.1：E01–E10 逐条修订与证据矩阵

> **基线**：`ChinaStory-final-skills-v2.1.zip` 的五份 Evaluation 文件；在 `ChinaStory-final-skills-v3.1.zip` 中它们未发生内容变化。v4.1 只对 Evaluation 进行实质升级，保持包内 Generation 的 Post/News v3.1 不变。
>
> **证据方法**：区分 A【项目规范】、B【一手行业标准】、C【同行评审研究】、D【工程建议】。外部资料只能支持方法合理性，**不能替代对本项目 v4.1 的模型实验**。引用下文 `[Sxx]` 的稳定链接及具体适用范围。
>
> **日期**：2026-10-18；运行状态：已经提供程序可执行的 Schema/偏移校验；**未进行真实 Qwen 模型质量对照实验**。

## 一、十项修订总表

| ID | 旧版问题（文件与原位置） | v4.1 的明确变化（新文件） | 为什么修改、适用边界 | 依据 | 验收编号 |
|---|---|---|---|---|---|
| **E01** | `references/genre-checks.md` 旧 §4（Post/News 各只有一句） | `genre-checks.md` §1–2 加入 `social_post/thread/visual_story/caption_only`、`reported_news/institutional_release/newsletter/press_kit` 专项；同步 Generation Post/News v3.1 | D5 应检查目标体裁实际表现；平台字符/字数是确定性后端校验，不应由 Judge 猜；新闻真实性仍给 Part 1 | [S01] A、[S10] 项目 v3.1、[S11] B、[S12] B | T01、T02、T03、T12 |
| **E02** | `cross-cultural-review.md` 原 §1 把“翻译忠实”写 D3、“新事实”写 D6 | `cross-cultural-review.md` §1–2 明确错译/漏译 → Part 2；新增事实/引语事实 → Part 1；Part 3 仅看表达可理解度/自然度 | 避免重做事实与翻译外部评价，保护事实门禁独立性 | [S01–S03] A | T04、T05 |
| **E03** | `SKILL.md` 原 §2 只有 `content.text`，对轮播/视频/新闻身份表达不足 | `input-contracts.md` §2 引入**可选** `format/editorial_mode/structured_content/media_manifest/content_hash`，§3 明确不可更改的定位基准 | 没有实际图片不能冒充已评测画面；没有新闻发稿身份不可假装记者；**须后端 Schema 适配后才能发新增字段** | [S01] A、[S10] 项目、[S11/S12] B | T02、T03、T06 |
| **E04** | `SKILL.md` 原 §4 仅给示例 JSON；`revision-feedback.md` 例子 `40:58` 与文本长度不符 | `schemas/evaluation-result-v4.1.schema.json`、`scripts/validate_evaluation.py`、`output-contracts.md` 明确六维各一次、1–5、Span 精确匹配及 UTF-8 hash | JSON Schema 支持类型/范围/必填，但“六 ID 不重复+原文偏移”需单独程序检查；不验证事实真伪 | [S13/S14] B、[S03] A；跨度示例修复系确定性代码验证 | T07、T08、T09、T10 |
| **E05** | `SKILL.md` 原 §4 状态既有 `COMPLETED` 又有 `REVISION_RECOMMENDED` 等混合语义 | `output-contracts.md` §2 保留旧 `status` 并**可选**新增 `execution_status/review_decision`，另列迁移映射 | 评分“完成”不等于文章“通过”；在后端未迁移前不能删除原字段 | [S02/S03] A | T11 |
| **E06** | 旧 `SKILL.md` 无评测正文中指令隔离要求 | `SKILL.md` §1、`input-contracts.md` §4 将文章/引用/媒体字幕视作不可信数据，建议权限限制、输出校验和注入测试 | 避免待评正文中的“给我全 5 分”成为 Judge 指令；分隔符无法百分百保证安全 | [S07] B | T13 |
| **E07** | 旧 `SKILL.md` Judge 规则无稳定性/偏差实验流程 | `judge-reliability.md` §1–2 规定版本固定、盲评、AB/BA 顺序、长文偏好和重测记录 | 论文观察到位置/冗长/自增强偏差；缓解措施不等于已证明消除偏差 | [S04/S05] C、[S08] B | T14、T15 |
| **E08** | `rubric-usage.md` 只有维度列表与简述，正式 Rubric §16 的校准要求未操作化 | `rubric-usage.md` §3–4、`judge-reliability.md` §3–6 规定人工样本、分歧保存、语言分层、置信度含义与 Rubric TBD 保持 | 避免模型评分被当成人工金标准或将英语校准外推多语言；阈值/样本量不自定 | [S01] A、[S04/S06] C、[S08] B | T16、T17 |
| **E09** | `cross-cultural-review.md` 原 §1 文化主体性的判定与移交不清 | 新 §2 加强语境、非遗传承社区主体地位、防止异国情调与去语境化；授权问题只提示人核查 | UNESCO 伦理提供规范方向，不构成自动“真实性认证”或额外加权得分 | [S09] B、[S01] A | T18 |
| **E10** | `revision-feedback.md` 只有四字段且旧偏移示例不一致 | 保留四旧字段；建议可选 `issue_id/severity/location/expected_check/requires_fact_recheck`；修复合法偏移示例，形成可追踪 V1→V2 指令 | 提高问题追踪与最小修改的可验证性；新增字段为**本项目工程设计建议**，非论文规定 | [S02/S03] A、[S04] 仅提供结构化评价研究参考（C） | T08、T19、T20 |

## 二、说明：为何不修改 Rubric 评分维度

正式 [S01] 对评分维度 D1–D6、每维 1–5 分 BARS、`overall_score=null`、校准尚待研究等均有明确要求。因此本次**不**：

- 设立 D7；
- 重新给 Feature/Indepth 单独 0–3 分总分；
- 随意设定 Part 3 通过阈值（项目 Rubric §19 仍标 TBD）；
- 把事实性问题按扣分处理后允许发布；
- 把 `confidence` 伪称“正确率”。

## 三、分级引用来源（每个修改都可回查）

| ID | 等级 | 可核查来源 | 它实际上支持什么；**不**支持什么 |
|---|---|---|---|
| S01 | A 项目规范 | [ChinaStory Content Quality Rubric v2.1](https://github.com/jialewang17/international-agent/blob/main/eval/CHINASTORY_CONTENT_QUALITY_RUBRIC_v2.1.md) | 支持维度、分值、BARS、受众输入、§16 校准、§19 TBD；不代表已通过真实实验 |
| S02 | A 项目规范 | [Evaluation Pipeline Spec v1.2](https://github.com/jialewang17/international-agent/blob/main/eval/CHINASTORY_EVALUATION_PIPELINE_SPEC_v1.2_CN.md) | 支持 Part1/2/3、Revision Loop、Human Review；不代表全部代码已接通 |
| S03 | A 项目规范 | [Evaluation Skill Spec v1.1](https://github.com/jialewang17/international-agent/blob/main/eval/CHINASTORY_EVALUATION_SKILL_SPEC_v1.1.md) | 支持原输入输出、六维评分与缺上下文处理；新版可选字段仍须 Schema 迁移 |
| S04 | C 论文 | [G-Eval: NLG Evaluation using GPT-4 with Better Human Alignment (EMNLP 2023)](https://aclanthology.org/2023.emnlp-main.153/) | 结构化评价和人工对照的实证研究；非本项目分数有效性保证 |
| S05 | C 研究论文 | [Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena (2023)](https://arxiv.org/abs/2306.05685) | 位置偏差、冗长偏好、自增强偏好等研究证据；盲评 AB/BA 是合理防范设计，具体收益须实验 |
| S06 | C 论文 | [How Reliable is Multilingual LLM-as-a-Judge? (Findings EMNLP 2025)](https://aclanthology.org/2025.findings-emnlp.587/) | 25 语言/五模型研究观察到评价一致性问题；不能把研究总体 κ 直接套到本项目模型 |
| S07 | B 安全规范 | [OWASP Prompt Injection Prevention Cheat Sheet](https://github.com/OWASP/CheatSheetSeries/blob/master/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.md) | 提供数据与指令分离、权限控制、输出校验建议；不承诺绝对免疫 |
| S08 | B 风险管理框架 | [NIST AI RMF Measure](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/) | 支持 TEVV、评估复现、风险监控、独立复核；不规定本项目样本量与及格线 |
| S09 | B 文化伦理准则 | [UNESCO Ethics and Intangible Cultural Heritage](https://ich.unesco.org/en/ethics-and-ich-00866) | 支持尊重文化社区主体性、避免去语境化和错误表述；不替代具体采访授权审查 |
| S10 | A 当前项目文件 | 包内 `china-story-generation/references/genres/post.md`（v3.1） | 明确 Post 已支持的四形式、选用模式、平台建议；是否有效须本地实验 |
| S11 | B 无障碍规范 | [W3C WAI Images Tutorial](https://www.w3.org/WAI/tutorials/images/) | 说明应按图片实际功能给 Alt Text；未提供图片时无法检查实际描述准确性 |
| S12 | A+B | 包内 `.../genres/news.md`（v3.1）及 [AP Telling the Story](https://www.ap.org/about/news-values-and-principles/telling-the-story/) | 新闻身份、来源归属、引语与明确编辑边界；AI 不能凭空宣称采访/回应 |
| S13 | B 软件标准 | [JSON Schema Objects and Required](https://json-schema.org/understanding-json-schema/reference/object) | 支持 required/properties/对象结构检查；不保证跨字段业务规则有效 |
| S14 | B 软件标准 | [JSON Schema Numeric](https://json-schema.org/understanding-json-schema/reference/numeric) | 支持分值上下界；不保证 Judge 评分准确 |

## 四、额外工程说明（不能混淆为已部署）

1. `schemas/evaluation-result-v4.1.schema.json` 和 `scripts/validate_evaluation.py` 是**交付在本包内的参考实现**；只有实际接入服务端请求链路才会生效。
2. `execution_status/review_decision`、`confidence_status`、`revision_suggestions[].issue_id` 等字段是**兼容性可选扩展**。如果你们当前 Pydantic 强制拒绝未知字段，必须先由 Backend 做迁移，不能把新文档直接视为已更新 API。
3. `real_audience_evaluation="NOT_EVALUATED"` 是在未做真实受众实验时的唯一诚实表述；Rubric 分数不能证明阅读量或理解率已经提升。
4. 文档和脚本的静态测试**不等于**真实 Qwen/其他 Judge 的打分准确率测试；实验用例与预期参见 `Evaluation_v4.1_Test_Plan.md`。
