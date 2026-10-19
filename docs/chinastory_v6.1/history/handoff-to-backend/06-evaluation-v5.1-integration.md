# Backend Handoff 06：Evaluation Skill v5.1 工程接线清单

> 本文件属于工程交接，不是第三个 Skill；它**没有自动修改远程 GitHub 仓库**。请先在一个独立的开发分支合并，而不要覆盖已有目录。

## 1. 文件落位与职责

| 项目目标位置 | 用途 | 实际执行主体 |
|---|---|---|
| `china-story-evaluation/SKILL.md` | 评分操作与职责边界 | Skill Loader + Judge LLM |
| `china-story-evaluation/references/*.md` | Rubric 调用、跨文化、体裁、输入输出契约等 | 评测 Prompt/Loader 按需读取 |
| `api/schemas/evaluation-result-v5.1.schema.json` | 结构化结果的机器契约镜像 | Python Backend |
| `utils/validate_evaluation.py` | 六维唯一性、定位、哈希及状态校验 | Python Backend |
| `tests/evaluation/*` | 程序回归测试与固定 JSON 样本 | 开发/CI |
| `docs/evaluation/*` | 逐项变更来源与实验计划 | 开发维护人员（不属于每轮 Prompt） |
| `china-story-evaluation/agents/openai.yaml` | 某些 Skill 平台的 UI 元数据 | Skill 平台，不是 Qwen/OpenAI API 配置 |

## 2. 接线顺序（须逐项落实）

1. **先对照当前仓库** `api/`、`utils/`、`tests/` 是否已有同名模块，采用合并而不是整目录覆盖。
2. 注册 `china-story-evaluation`；加载 `SKILL.md` 和其 `references`，并从仓库加载正式的 `eval/CHINASTORY_CONTENT_QUALITY_RUBRIC_v2.1.md`（不可由 Skill 摘要替代）。
3. 请求模型按 `references/input-contracts.md` 接收已确认的任务上下文、受众、内容原文与 Part 1 状态；**API 请求模型**实际决定字段是否允许，不可把 Markdown 视为运行时代码。
4. 输出按 `references/output-contracts.md` 构造；将 v5.1 JSON Schema 与实际 Pydantic/响应模型字段、必填、空值约定作差异检查。字段冲突时阻断发布。
5. **先 Schema 后确定性校验**，失败则标记无效/可控重试或交人工，不能继续自动 Revision。`status=COMPLETED` 并非 `Gate C APPROVED`。
6. 保留正式 Rubric v2.1 的六维评分 1–5 整数，`overall_score=null`，保持 `status` 旧字段与可选新字段的映射；未更新后端前禁用可选扩展。
7. `content.text` 视为不可变定位基准；服务端 Python Unicode 码点与浏览器 UTF-16 渲染偏移要明确转换。
8. Part 1 事实核验与 Gate C 由后端处理；Judge 不可自行裁决事实或发布。模型输出与本地机器校验均不能证明内容质量正确。

## 3. 开发机验证（从交付包根目录）

```bash
python -m pip install "jsonschema>=4"
python utils/validate_evaluation.py tests/evaluation/fixtures/valid_evaluation.json --content-file tests/evaluation/fixtures/content.txt
python -m unittest discover -s tests/evaluation -p 'test_*.py' -v
```

如将 Schema 改由 Pydantic 单一生成流程维护，应保留独立逻辑验证和测试，防止两套数据契约漂移；本次未实现自动 Pydantic 同步。

## 4. 已完成与未完成

- **本次包内完成**：路径迁移、静态 Schema、逻辑脚本、回归测试、研究文档与交接说明。
- **仍未完成**：真实仓库合并、请求/响应 Pydantic 自动映射、Qwen Judge 接入、人工校准、真实模型端到端测试。不得将文档版本升级描述为部署完成。

## 5. 依据

- Agent Skills 结构规范：https://agentskills.io/specification
- JSON Schema：https://json-schema.org/understanding-json-schema/reference/object
- Python jsonschema：https://python-jsonschema.readthedocs.io/en/stable/validate/
- FastAPI response model：https://fastapi.tiangolo.com/tutorial/response-model/
- Python unittest：https://docs.python.org/3/library/unittest.html
- 项目正式 Rubric：https://github.com/jialewang17/international-agent/blob/main/eval/CHINASTORY_CONTENT_QUALITY_RUBRIC_v2.1.md
