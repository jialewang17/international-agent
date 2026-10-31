> **历史记录（v4.1）**：本文保留旧版目录示意与旧命令以供追溯。请使用包根目录的 `README-v5.1.md` 和 `handoff-to-backend/06-evaluation-v5.1-integration.md` 获取当前路径。

# ChinaStory-final-skills-v4.1｜双 Skill 完整文件包

**版本**：v4.1（2026-10-18，研究修订及程序级静态校验版本）  
**基线**：v3.1 文件包（Generation 的 Post、News v3.1；Evaluation 与 v2.1 相同）。  
**本次实质升级**：Evaluation Skill 的 `SKILL.md`、四份旧 references，以及新增执行参考、JSON Schema、验证脚本、测试和工程交接。**Generation Skill 的全部文件按 v3.1 原样保留**。

## 1. 仍然只有两个顶层 Skill

- **`china-story-generation`**：Create/受控 Revision；六种体裁 Post/News/Feature/Indepth/Script/FAQ；其中 Post、News 保留 v3.1 专项写作规范。
- **`china-story-evaluation`**：Evaluation Pipeline Part 3；依唯一官方 Rubric v2.1 的 D1–D6 六维评价，识别跨文化内容质量问题，生成可执行修改建议；**不做 Part 1、Part 2、正文重写或 Gate C 批准**。

`handoff-to-backend` 是后端接线文档，**不是第三个 Skill**。

## 2. 本包主要新增内容

```text
ChinaStory-final-skills-v4.1/
├── README-v4.1.md
├── README-v3.1.md                         # 上版历史说明
├── china-story-generation/                # 与 v3.1 完全相同
│   ├── SKILL.md
│   ├── agents/openai.yaml
│   ├── references/genres/post.md          # v3.1
│   ├── references/genres/news.md          # v3.1
│   └── ...                                # 其余体裁和原研究文档保留
├── china-story-evaluation/                # v4.1 升级
│   ├── SKILL.md
│   ├── agents/openai.yaml
│   ├── references/
│   │   ├── rubric-usage.md
│   │   ├── cross-cultural-review.md
│   │   ├── genre-checks.md
│   │   ├── revision-feedback.md
│   │   ├── input-contracts.md            # 新增
│   │   ├── output-contracts.md           # 新增
│   │   └── judge-reliability.md          # 新增
│   ├── schemas/evaluation-result-v4.1.schema.json
│   ├── scripts/validate_evaluation.py
│   ├── tests/
│   │   ├── fixtures/
│   │   └── test_validate_evaluation.py
│   └── docs/
│       ├── Evaluation_v4.1_Changes_and_Evidence.md
│       └── Evaluation_v4.1_Test_Plan.md
└── handoff-to-backend/
    ├── 01-... 至 04-...                  # 与 v3.1 相同
    └── 05-evaluation-v4.1-integration.md # 新增
```

## 3. 每一处修改都有证据

[E01–E10 修改与来源矩阵](../evaluation/history/Evaluation_v4.1_Changes_and_Evidence.md) 逐条记录**旧版问题、对应文件、v4.1 修改、依据来源、证据性质及验收测试 ID**。来源涵盖项目正式规范、G-Eval、MT-Bench、Findings EMNLP 2025、OWASP、NIST、UNESCO、W3C、AP 和 JSON Schema 官方文档。

**约束**：外部研究支持采取某种方法的合理性，不证明 v4.1 在真实任务中已显著优于 v2.1；只有运行模型和人工实验才能证明。

## 4. 使用与验证

该版本的标准化 Skill 结构用于**文档与运行指令组织**；它**没有自动改写你们的 GitHub Python Backend**。必须由后端完成 Skill 注册、Prompt 加载、Fact/Part2/Part3 接线、Schema 兼容迁移、日志和人工审批。

静态测试：

```bash
python -m pip install "jsonschema>=4"
cd china-story-evaluation
python scripts/validate_evaluation.py tests/fixtures/valid_evaluation.json --content-file tests/fixtures/content.txt
python -m unittest discover -s tests -p 'test_*.py' -v
```

这些检查**不验证** AI Judge 的事实判断、分数有效性、文化表达质量或 Prompt Injection 真正拦截率；上述问题需要 [测试与实验计划](../evaluation/history/Evaluation_v4.1_Test_Plan.md) 的实测。

## 5. 系统 API 兼容原则

- 旧输出字段 `status`、`dimensions`、`revision_suggestions` 等保留，`overall_score=null` 不变。
- 新字段如 `execution_status`、`review_decision`、`confidence_status`、`issue_id` 为**可选建议扩展**，必须先升级 Backend Schema 再通过 API 输出。
- 官方权威 Rubric 继续为 `eval/CHINASTORY_CONTENT_QUALITY_RUBRIC_v2.1.md`，不得用本地摘要替代。
- v4.1 只代表当前交付包版本，**不**代表项目仓库 Python 工作流已经完成部署。
