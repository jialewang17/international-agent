# ChinaStory-final-skills-v5.1｜双 Skill + 工程交接分层版

**版本日期：2026-10-18**  
**基线**：用户上传的 `ChinaStory-final-skills-v4.1.zip`（已在此包中保留历史版说明）  
**变更重点**：目录分层、文件路径与契约权威、独立打包适配；**不是改变评分标准的新版本**。

## 1. 核心原则

1. **顶层只保留两个 Skill**：`china-story-generation` 与 `china-story-evaluation`。`SKILL.md` 定义模型工作方法，`references/` 由 Loader 按需加载。
2. Evaluation Part 3 **不改变六维 D1–D6、1–5 分 BARS 和 `overall_score=null`**；Part 1 事实核验、Part 2 外部翻译评价及 Gate C 不属于该 Skill。
3. **Post 与 News 保留 v3.1 的体裁规则**；Generation 的所有执行文件按 v4.1 原样保留。历史修改依据由 Skill 内移至 `docs/generation/`，不影响写作 Prompt。
4. `input-contracts.md`、`output-contracts.md` **保留在 Evaluation Skill 内**，为人类与模型解释语义；后端 API/Pydantic 才决定实际收发的数据格式。
5. Schema 与校验程序放到工程目录：`api/schemas/`、`utils/`；单元测试放到 `tests/evaluation/`；研究证据放到 `docs/evaluation/`。
6. `agents/openai.yaml` 是 Skill 平台 UI 元数据，不是 Qwen/OpenAI API Key 配置。Python 自建 Loader 可不使用，但本交付包保留以兼容需要它的平台。

## 2. v5.1 目录

```text
ChinaStory-final-skills-v5.1/
├── README-v5.1.md
├── china-story-generation/
│   ├── SKILL.md
│   ├── agents/openai.yaml
│   └── references/            # 六体裁、输出、transcreation 等；Post/News v3.1 原文保留
├── china-story-evaluation/
│   ├── SKILL.md               # v5.1 分层描述与工作流
│   ├── agents/openai.yaml
│   └── references/
│       ├── rubric-usage.md
│       ├── cross-cultural-review.md
│       ├── genre-checks.md
│       ├── input-contracts.md
│       ├── output-contracts.md
│       ├── revision-feedback.md
│       └── judge-reliability.md
├── api/schemas/evaluation-result-v5.1.schema.json
├── utils/validate_evaluation.py
├── tests/evaluation/
│   ├── test_validate_evaluation.py
│   └── fixtures/{content.txt,valid_evaluation.json}
├── docs/
│   ├── evaluation/
│   │   ├── Evaluation_v5.1_Changes_and_Evidence.md
│   │   ├── Evaluation_v5.1_Test_Plan.md
│   │   └── history/                  # v4.1 原研究证据与测试计划
│   ├── generation/                 # Post/News v3.1 原研究证据与测试计划
│   └── history/                    # v3.1 / v4.1 README
└── handoff-to-backend/
    ├── 01–04 原文
    ├── 05-evaluation-v4.1-integration.md  # 历史，保留提示
    └── 06-evaluation-v5.1-integration.md  # 本次采用
```

## 3. 为什么要分开

Skill 的 `SKILL.md` 和专业参考文档是可按需加载的**模型工作方法**；Schema、Python 校验和自动化测试是**代码执行与质量保障**；研究证据和修订历史是**工程追溯文档**。分开以后，能够独立安装 Evaluation Skill，而不假称它会自动运行后端 Python 程序。Agent Skills 规范允许脚本放在 Skill 内，**本次分离是 ChinaStory 的工程设计决定，不是规范强制**。

## 4. 使用方式

如果你**只是阅读/安装 Evaluation Skill**：使用 `china-story-evaluation/`，按 `SKILL.md` 读取七份 references，但实际评分仍依赖外部正式 Rubric 与 LLM。

如果你要**运行 v5.1 结果校验**：请从包根目录执行：

```bash
python -m pip install "jsonschema>=4"
python utils/validate_evaluation.py tests/evaluation/fixtures/valid_evaluation.json --content-file tests/evaluation/fixtures/content.txt
python -m unittest discover -s tests/evaluation -p 'test_*.py' -v
python -m unittest discover -s tests -p 'test_*.py' -v  # 包含目录结构与链接检查
```

**注意**：这份交付包是可合并到项目的参考目录；`api/`、`utils/`、`tests/` 不代表已经提交到 GitHub。合并时检查同名文件与现有 API 模型，不要直接覆盖业务代码。

## 5. 改动追溯与验收

- [逐处修改、证据类型、来源与测试](docs/evaluation/Evaluation_v5.1_Changes_and_Evidence.md)
- [逐文件 SHA-256 变动清单](docs/evaluation/Evaluation_v5.1_File_Change_Manifest.md)
- [新目录和评测的测试计划](docs/evaluation/Evaluation_v5.1_Test_Plan.md)
- [Backend 接线检查](handoff-to-backend/06-evaluation-v5.1-integration.md)
- [v4.1 原历史资料](docs/evaluation/history/Evaluation_v4.1_Changes_and_Evidence.md)

尚未进行真实 AI Judge 的运行与人工一致性实验。**程序通过测试仅证明静态数据约束满足预期，不能证明六维评分准确**。

## 6. 本次实际静态验收

2026-10-18：**23 项单元测试通过**（16 项 Evaluation validator 检查与 7 项 package 结构检查）；双 Skill frontmatter / UI metadata 校验通过，Draft 2020-12 Schema 校验通过，原有 15 项 validator 测试兼容。Post/News 方法及 Generation 执行文件与 v4.1 ZIP 字节一致。**尚未运行真实 Qwen、真实受众与人工一致性实验，也未合并远端后端代码。**
