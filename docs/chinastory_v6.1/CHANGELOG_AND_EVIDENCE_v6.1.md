# ChinaStory GitHub Merge v6.1：逐处修改、依据与验证

> **依据来源级别**：`U` 用户上传 v5.1 实际文件；`R` 2026-10-18 在线核对的 GitHub 公开 `main` 源代码；`S` 公认规范/官方文档；`D` 本项目的兼容性工程决策（不是外部规定）。每项列出具体位置、动机、依据及验证。**这不是声称已写入 GitHub**。

| ID | 实际修改的文件或位置 | v5.1 → v6.1 的精确改动 | 依据（区分事实与决策） | 验证 |
|---|---|---|---|---|
| M61-01 | `china-story-generation/`、`china-story-evaluation/` | 两套完整 Skill **迁入** `skills/`，文件内容保留；Post/News 文本与 v5.1 字节一致 | R-01 仓库本有 `skills/`；S-01 Agent Skills 要求每个 Skill 目录有 `SKILL.md`；D：与 repo 路径对齐 | T01/T02、哈希比对 |
| M61-02 | Evaluation `SKILL.md` | 增加 v6.1 合并限制，标注尚未与实际 Pydantic API 等价、不自动 Gate C | R-04 现有 `EvaluationResult`；R-05 Gate C；U-02 v5.1 是方法定义 | T03 文档检查 |
| M61-03 | Generation `SKILL.md` | 增加知识方法加载≠Ground Gate B、母稿须由后端持久化、六体裁功能边界与兼容键说明 | U-01 v5.1 指令与 R-05/R-06 目前 API 实际行为对照；D：纠正潜在误导 | T04 文档检查 |
| M61-04 | `api/schemas/...json` → `eval/contracts/evaluation-result-v6.1.schema.json` | 避开 repo 现有 `api/schemas.py` 相邻同名包路径；保留字段集合，仅更新 `$id`/标题/解释 | R-04 已存在 `api/schemas.py`；U-03 v5.1 同名目录；S-02 JSON Schema 规范；D：避免未来 `__init__.py` 引入同名包的导入歧义 | T05 JSON Schema diff 与 `api.schemas` 路径隔离 |
| M61-05 | `utils/validate_evaluation.py` | Schema 路径同步迁移，不改六维/原文/哈希判定算法 | U-04 v5.1 校验代码需读取原路径；M61-04 后必须同步 | T06 16 个原测试 |
| M61-06 | `tests/chinastory_v61/` | 从原 `tests/evaluation/` 迁入独立命名空间；更新路径测试；保留测试样本 | R-07 仓库已有 `tests/`；D：减少同名测试目录覆盖风险 | T06/T07 |
| M61-07 | `config/skills.yaml`（**合并脚本应用时**） | 只添加 `china_story_generation` 和 `china_story_evaluation` 注册 ID，`keywords: []`；旧条目暂不删除 | R-02 旧 Registry 的配置结构；R-03 Skill 激活依赖关键词；D：分阶段迁移防止旧工具丢失引用 | T08 dry-run/应用后 YAML 断言 |
| M61-08 | `utils/chinastory_skill_loader_v61.py` | 新增受控加载，按 `genre` 读取相应方法；评测载入仓库**正式 Rubric**；缺文件或预算不足直接报错，不截断核心规则 | R-03 配置单卡 3600 字符、旧加载截断；U-01 六体裁分册；S-01 渐进式加载；D：避免无声丢规则 | T09–T12 loader 单测 |
| M61-09 | `tools/story_post_gen.py` News 分支（**合并脚本应用时**） | 在 News 成功结果中补 `"_evidence_pack": evidence_pack.model_dump(mode="json")`；与 Post 成功分支保持一致 | R-05 `api/main.py` 成功路径强制拿 `_evidence_pack`；R-06 News 成功路径漏此字段，Post 路径有 | T13 精确代码锚点、幂等性测试；线上 E2E 待测 |
| M61-10 | `requirements.txt`（**合并脚本应用时**） | 若缺失，追加 `jsonschema>=4` | R-08 当前依赖列表没有 jsonschema；U-04 validator 使用 `Draft202012Validator`；S-02/S-03 官方文档 | T14 是否只添加一次 |
| M61-11 | `references/output-contracts.md` | 机器契约路径改至 `eval/contracts/`，明确 `version_id`、`confidence=null`、正文跨度与旧 Pydantic 差异 | R-04 `DimensionResult.confidence: float`，`EvidenceSpan` 有 `span_id/source_id`；U-02 v5.1 描述；D：失败封闭 | T03/T15 路径和字段校验 |
| M61-12 | `docs/chinastory_v6.1/` | 把旧说明、研究证据、测试计划留历史；新增合并指南、接口缺口、逐处依据和验收 | U-05 原 `docs/`/`handoff-to-backend/` 只是交接资料；D：代码与历史说明分离、避免误将草案当运行逻辑 | T16 链接/文件清单 |
| M61-13 | `scripts/apply_chinastory_v6_1.py` | 新增 dry-run、严格源码锚点匹配、拒绝覆盖非同内容文件、拒绝脏 Git 工作树、写入异常回滚；不自动提交 | R-02/R-05/R-06 是受控修改点；S-04 Git 推荐分支/PR 审查；D：降低误覆盖风险 | T13/T17–T19 集成辅助单测 |
| M61-14 | `SKILL.md` 与 Schema Rubric 控制 | 继续 D1–D6、1–5 整数、`overall_score=null`；Post/News v3.1 保留 | R-09 正式 Rubric 是权威；U-01/U-02 既定写作/评测规则；D：本次是工程集成版本而非重新定标 | T02/T05/T06 |
| M61-15 | `docs/.../INTERFACE_GAPS_v6.1.md` | 标出新旧 EvaluationResult、文字跨度、`confidence`、六体裁未对齐是**未完成**，并不偷偷加可用按钮或批准状态 | R-04、R-05、R-06；S-05 FastAPI 对 Pydantic 的契约要求 | T15 人工复核清单 |

## 参考来源（可核查链接）

- **U-01**：上传 v5.1 的 `china-story-generation/SKILL.md`、`references/genres/post.md`、`news.md`；**U-02**：上传 v5.1 的 `china-story-evaluation/SKILL.md`、`references/output-contracts.md`；**U-03**：上传的 `api/schemas/evaluation-result-v5.1.schema.json`；**U-04**：上传 `utils/validate_evaluation.py` 与测试；**U-05**：原 `docs/`、`handoff-to-backend/`。
- **R-01**：[仓库目录](https://github.com/jialewang17/international-agent)。
- **R-02**：[config/skills.yaml](https://github.com/jialewang17/international-agent/blob/main/config/skills.yaml)。
- **R-03**：[utils/skill_registry.py](https://github.com/jialewang17/international-agent/blob/main/utils/skill_registry.py)。
- **R-04**：[api/schemas.py](https://github.com/jialewang17/international-agent/blob/main/api/schemas.py)。
- **R-05**：[api/main.py](https://github.com/jialewang17/international-agent/blob/main/api/main.py)。
- **R-06**：[tools/story_post_gen.py](https://github.com/jialewang17/international-agent/blob/main/tools/story_post_gen.py)。
- **R-07**：[tests/](https://github.com/jialewang17/international-agent/tree/main/tests)。
- **R-08**：[requirements.txt](https://github.com/jialewang17/international-agent/blob/main/requirements.txt)。
- **R-09**：[Rubric v2.1](https://github.com/jialewang17/international-agent/blob/main/eval/CHINASTORY_CONTENT_QUALITY_RUBRIC_v2.1.md)。
- **S-01**：[Agent Skills Specification](https://agentskills.io/specification)。
- **S-02**：[JSON Schema 2020-12](https://json-schema.org/draft/2020-12)。
- **S-03**：[python-jsonschema Draft202012Validator](https://python-jsonschema.readthedocs.io/en/stable/validate/)。
- **S-04**：[GitHub Pull Request](https://docs.github.com/en/pull-requests)。
- **S-05**：[FastAPI Response Model](https://fastapi.tiangolo.com/tutorial/response-model/)。

## 改动边界

本版本**没有直接覆盖** repo 的 `api/main.py`、`api/schemas.py`、`tools/genre_router.py`、`utils/skill_registry.py`、既有 `skills/` 内容、真实素材库和原 `eval/` 正式 Rubric。只对合并脚本明确列出的两个遗留配置/依赖文件和一个 News 响应分支作定点修改；人工审查后才能进入第二阶段工作流接线。任何未给出确定性源码或测试依据的推测性修改均留在 `INTERFACE_GAPS_v6.1.md`。
