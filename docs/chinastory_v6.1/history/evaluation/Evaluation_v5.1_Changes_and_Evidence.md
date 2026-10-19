# ChinaStory Evaluation v5.1｜逐项修改依据与完整证据链

**版本**：v5.1（2026-10-18）  
**基线**：本次上传的 `ChinaStory-final-skills-v4.1.zip`（压缩包原件保存于用户会话，历史文档移入本包 `docs/`）。  
**变更性质**：软件工程目录重构、可移植性增强、契约层级澄清，**不**是重新研究 D1–D6 的评分有效性。  
**证据级别**：`P` = 公开正式文档；`I` = 本项目原有约束；`D` = 基于 P/I 的工程设计决定，非官方强制；`T` = 本次实测回归。

## 1. 逐项修改对照（修改编号 V51）

| ID | v4.1 的文件/问题（修改前） | v5.1 的具体改动（修改后） | 为什么修改、依据性质 | 证明方式 |
|---|---|---|---|---|
| **V51-01** | `china-story-evaluation/` 混放专业方法和程序资产 | 保留 `SKILL.md`、`references/`、`agents/`；把 Schema/脚本/测试/研究文档迁出 Skill 文件夹 | [S1] Agent Skills 定义 `SKILL.md` 为核心、其他目录可选（P）；职责分离是工程决策（D），规范**并未强制**迁出脚本 | `T51-01` 文件结构核对 |
| **V51-02** | `references/input-contracts.md` 的定位容易被误认成能直接验证后端请求 | 保留此文件并添加“自然语言输入规范 ≠ 运行时 API 模型”的说明 | [S3] FastAPI/Pydantic 声明 API 输入类型（P）；已有 TaskContext/Audience/Part1 输入约束（I） | `T51-02` 文档检查，后端模型对照留待集成 |
| **V51-03** | `references/output-contracts.md` 与 Schema 的权威关系未明确 | 保留该文档并明确：实际部署 API/Pydantic 决定对外字段；机器 JSON Schema 应与之对齐，不一致阻断部署 | [S2] JSON Schema `required/properties`（P）；[S3] FastAPI 输出模型验证（P）；对齐流程是 D | `T51-03` 旧字段比对；真实 API 对照待执行 |
| **V51-04** | `SKILL.md` 直接引用内部 `schemas/`、`scripts/`，暗示加载 Skill 会自动运行代码 | 更新为“工程侧校验”；不再包含脆弱的内部 Schema/脚本链接 | [S1] Skill 格式和资源按需加载（P）；[S4] Python 逻辑需由程序实际调用（P）；禁止假称已经接线（D） | `T51-04` 链接检查 |
| **V51-05** | `china-story-evaluation/schemas/evaluation-result-v4.1.schema.json` 与 Skill 混存 | 迁到 `api/schemas/evaluation-result-v5.1.schema.json`；仅更新 `$id/title`、不变更字段规则 | [S2] JSON Schema 机器可检验的结构化契约（P）；在 API 层维护是 D；保留旧输出（I） | `T51-05` Schema 差异核验 + 回归测试 |
| **V51-06** | `china-story-evaluation/scripts/validate_evaluation.py` 直接访问同级 Schema 路径 | 移至 `utils/validate_evaluation.py`，修正 `SCHEMA_PATH` 到 `api/schemas/`，保持 `validate_result()` 验证逻辑 | [S4] jsonschema validator API（P）；多字段一致性是旧规范（I）；运行位置是 D | `T51-06` CLI 有效 fixture 通过 |
| **V51-07** | `china-story-evaluation/tests/` 包含可执行测试与 fixtures | 移至 `tests/evaluation/`，修正导入路径，并增加 Schema 目录存在性回归测试 | [S5] Python unittest discovery 允许独立测试目录（P）；归档方式是 D | `T51-07` 验证器旧 15 + 新 1 项；额外 7 项包结构检查 |
| **V51-08** | `china-story-evaluation/docs/` 存放旧版变更记录和计划，容易被混入每轮 Prompt | 历史归档 `docs/evaluation/history/`；新增 v5.1 变更矩阵与测试计划 | [S1] Skill 按需加载和渐进披露（P）；保留追溯是项目研究目标（I） | `T51-08` 历史文件 SHA-256 相同 |
| **V51-09** | `china-story-generation/docs/` 与体裁执行方法同在 Skill 内 | 把 Post/News v3.1 两份历史研究文档迁移 `docs/generation/`，但保留所有 Generation `SKILL.md`、`references`、平台元数据**原字节不变** | [S1] 专业 reference 与非运行证据材料可分层（P/D）；不改变创作逻辑为 I | `T51-09` Generation Runtime 文件 SHA-256 对比 |
| **V51-10** | `genre-checks.md` 用相对路径直接链接到相邻的 Generation Skill | 改成通过项目集成读取 Generation v3.1 方法，单独打包 Evaluation 时不依赖另一 Skill 文件夹 | [S1] Skill 可单独安装与解析文件（P）；双 Skill 之间是项目可选集成依赖（D） | `T51-10` 独立 Eval ZIP 内链接核对 |
| **V51-11** | `handoff-to-backend/05...` 给出的 v4.1 旧文件路径不再适用 | 在旧文档前加历史提示；新增 `06-evaluation-v5.1-integration.md`，记录新路径和不可覆盖现有项目代码等边界 | [S3] FastAPI API 模型有自身约束（P）；已有未部署声明（I），接线顺序是 D | `T51-11` 路径/命令检查 |
| **V51-12** | 用户难以区分 Skill、后端工程包与平台元数据 | 新增 README-v5.1、开发报告、单独 Skill 安装包；保留 `agents/openai.yaml`，明确其仅是特定平台 UI 元数据 | [S1] Agent Skills 最小结构（P），[S6] OpenAI 平台界面元数据定义（P）；自建 Python Loader 是否读取此文件取决于其实现（D） | `T51-12` Skill frontmatter、两个入口和 ZIP 核验 |

### 重要的边界说明

1. **关于“必须移动代码”**：Agent Skills 规范明确允许 `scripts/` 留在 Skill 内，不能说这是标准强制。v5.1 的移动目的是让**ChinaStory 的 Python 后端集中执行确定性校验**；另一个工程组织方案也可能合理。
2. **关于“Schema 是唯一来源”**：现有项目可能已有 Pydantic 请求/响应模型，本包没有连接项目仓库并修改它们。只有把后端模型与本包 JSON Schema 对照、消除漂移后，才能宣称运行时契约已一致。
3. **关于“版本升级”**：v5.1 主要是目录和工程分层升级；`rubric_version` 仍是 `CHINASTORY_CONTENT_QUALITY_RUBRIC_v2.1`，`overall_score=null`，Post/News 方法仍是 v3.1。`evaluation-result-v5.1.schema.json` 的更名不代表数据字段破坏性升级。
4. **关于文件来源**：基线内容来自上传 ZIP（I），外部资料只用于支撑结构设计、类型校验、测试原则，不能据此声称生成效果或 AI Judge 正确性提高。

## 2. 证据来源索引（可点击的一手资料）

| 来源 | 网址 | 支持什么，不支持什么 |
|---|---|---|
| **[S1] Agent Skills 官方规范** | https://agentskills.io/specification | `SKILL.md` 是必要入口，`references/scripts/assets` 可选；**不强制**移动脚本到后端 |
| **[S2] JSON Schema 官方对象与 Required** | https://json-schema.org/understanding-json-schema/reference/object | 程序可检测 properties/required；不验证内容是否新闻真实 |
| **[S3] FastAPI 官方响应模型** | https://fastapi.tiangolo.com/tutorial/response-model/ | Pydantic/FastAPI 对数据序列化与响应验证的作用；不意味着项目已迁移 |
| **[S4] Python jsonschema 官方说明** | https://python-jsonschema.readthedocs.io/en/stable/validate/ | `Draft202012Validator` 等验证接口，不能替代业务逻辑检查 |
| **[S5] Python unittest 官方文档** | https://docs.python.org/3/library/unittest.html | 测试发现与用例组织方法，不强制某个仓库目录 |
| **[S6] OpenAI 平台 Skill 元数据规范** | https://developers.openai.com/plugins/deploy/submission-errors | `agents/openai.yaml` 的 UI `interface` 字段；**不是** Qwen/OpenAI API 密钥配置 |
| **[S7] OWASP Prompt Injection Prevention** | https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html | 支持边界隔离、最小权限和输出校验；**不证明**本项目已经通过真实攻击测试 |
| **[S8] ChinaStory Rubric v2.1** | https://github.com/jialewang17/international-agent/blob/main/eval/CHINASTORY_CONTENT_QUALITY_RUBRIC_v2.1.md | D1–D6 评分权威；本次未修改 |
| **[S9] 本次上传 v4.1 包** | `docs/history/README-v4.1.md`、`docs/evaluation/history/` | E01–E10 已有设计与边界；这是**项目内部基线证据**，非外部独立验证 |

## 3. 语义不变 / 有意改变的清单

**明确不改**：Generation 的 SKILL + 六体裁 references + `agents`；Evaluation 六维 `dimension_id`、1–5 分、既有 status/字段语义、`overall_score=null`、Part 1/2/3 分工、Gate C 人工审批。

**有意改变**：Evaluation Skill 主文件中工程路径描述；refs 输入输出的权威说明；项目级 Schema 的路径与版本标识；校验脚本/单元测试的导入路径；两项研究资料目录；README 与 Handoff；Genre 检查的跨 Skill 脆弱链接。

**仍待执行**：生产环境 Schema↔Pydantic 对齐、Skill Registry 配置、真实 Judge 推理与人工评分实验、自动 Revision 闭环运行。

## 4. 验收测试编号

- `T51-01`：两个 Skill，且 Evaluation 中只有 `SKILL.md`/`references`/`agents`。
- `T51-02/03`：输入输出契约文档说明机器权威层，列出未部署的可选字段。
- `T51-04/10`：Standalone Eval Skill 无跨目录 Markdown 相对引用和失效本地链接。
- `T51-05/06/07`：Schema 不改变字段/类型/条件规则；CLI fixture PASS；`unittest` 测试通过。
- `T51-08/09`：历史文档的内容散列和 Generation 运行文件对比一致。
- `T51-11`：v5.1 Handoff 的所有路径实际存在，并明确仍需人工合并后端。
- `T51-12`：两 Skill frontmatter 含 `name`/`description` 且与目录一致，ZIP 正常解压。

> **额外静态验收**：`tests/test_package_layout.py` 的 7 项检查涵盖两个入口、7 个 references、脚本与 Schema 位置、跨文件链接、历史资料完整性及 Generation 的 Post/News 文件存在性。`tests/evaluation/__init__.py` 只为 unittest 跨目录发现而加入。依据：[S5]。

## 5. 逐文件审计

全量旧→新路径、内容是否变化、文件散列对照请查看 [Evaluation_v5.1_File_Change_Manifest.md](Evaluation_v5.1_File_Change_Manifest.md)。本表中的 V51 编号与文件清单一一关联，可识别同一调整涉及的多份文件。
