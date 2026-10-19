# ChinaStory Evaluation v5.1｜结构重构与评测验证计划

## A. 已可执行：离线静态验收

| 测试编号 | 输入 / 步骤 | 预期 | 解释 |
|---|---|---|---|
| T51-01 | 目录扫描 `SKILL.md` | 仅 Generation/Evaluation 两个入口 | `docs`、`tests` 非第三个 Skill |
| T51-02 | 检查 `input-contracts.md` | 旧字段保留、可选字段未被描述成已接入 | 不替代 API 请求模型 |
| T51-03 | 检查 `output-contracts.md` | 保留顶层旧字段与 Rubric 规则 | 不替代 API 响应模型 |
| T51-04 | 扫描 Eval 文档内部相对链接 | 本 Skill 必需 references 均存在 | 单独安装能解析 |
| T51-05 | 比较旧/新 Schema 规则 | 只允许 `$id`/title 元数据变化 | 不应发生字段层破坏 |
| T51-06 | 使用 fixture 运行 CLI | 输出 PASS | Schema + 逻辑校验 |
| T51-07 | 运行 `unittest` | 16 项测试全部通过 | 15 项旧例 + 1 项路径回归 |
| T51-08 | 比较历史证据文件字节散列 | v4.1 文件完全保留 | 研究追溯 |
| T51-09 | 比较 Generation 运行文件散列 | 与 v4.1 完全一致 | Post/News v3.1 不变 |
| T51-10 | 检查 standalone Eval ZIP | 仅一份 `SKILL.md`，无外部路径依赖 | 可独立安装 |
| T51-11 | 检查 Handoff 06 中路径和 CLI | 全部存在且执行命令有效 | 后端接线准备 |
| T51-12 | 校验 YAML frontmatter 与 ZIP CRC | 合法，且压缩包可正常解压 | 包装质量 |

运行命令（在交付包根目录）：

```bash
python -m pip install "jsonschema>=4"
python utils/validate_evaluation.py tests/evaluation/fixtures/valid_evaluation.json --content-file tests/evaluation/fixtures/content.txt
python -m unittest discover -s tests/evaluation -p 'test_*.py' -v
python -m unittest discover -s tests -p 'test_*.py' -v  # 包含目录结构与链接检查
```

## B. 必须在真实 ChinaStory Backend 上执行：集成验收

1. 同步当前项目的 API/Pydantic 请求/响应字段和本 Schema；检查 `confidence=null`、顶层可选扩展和 `human_review=PENDING`。
2. 按 `Part1 → Part3` 的工作流调用 Qwen 等 Judge，并确认加载完整正式 Rubric v2.1。
3. 对 `status=COMPLETED` 的真实模型输出做双重校验；校验失败的结果绝不能送入 Generation 自动 Revision。
4. 运行 Post/News 代表样例，检查上传/缺失视觉素材时 D5 的边界。
5. 在 V1→V2 修改之后重新走事实核验和 Part 3 评分，确认任何结果都不等于 Gate C 的人工批准。

## C. 人工/模型有效性实验（此次未完成）

继续参见历史 [Evaluation v4.1 测试计划](history/Evaluation_v4.1_Test_Plan.md) 中 T01–T20：盲评、A/B 顺序交换、模型偏差、中文英文校准、Prompt Injection 模拟、文化误读及事实返回链路。**此次重构不证明 AI Judge 评分改进。**

依据：Agent Skills https://agentskills.io/specification；JSON Schema https://json-schema.org/understanding-json-schema/reference/object；Python unittest https://docs.python.org/3/library/unittest.html；FastAPI https://fastapi.tiangolo.com/tutorial/response-model/
