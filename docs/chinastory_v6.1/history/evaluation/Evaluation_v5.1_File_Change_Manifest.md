# ChinaStory v5.1｜逐文件变动清单（SHA-256 对照）

> 本表以用户上传的 v4.1 ZIP 解包为基准。`移动未改` 表示 SHA-256 相同，`修改` 表示内容变化；本表记录了所有基线文件的去向（排除 Python 自行产生的 `__pycache__`）。如工程路径移入后端，**不代表已经合并到 GitHub**。

| v4.1 相对路径 | v5.1 相对路径 | 分类 | 修改编号 | SHA-256 对照（前 12 位） |
|---|---|---|---|---|
| `README-v3.1.md` | `docs/history/README-v3.1.md` | 移动未改 | V51-08 | `641e21960933` → `641e21960933` |
| `README-v4.1.md` | `docs/history/README-v4.1.md` | 移动并修改 | V51-08 | `95bc2bac0573` → `0d7cbd95379f` |
| `china-story-evaluation/SKILL.md` | `china-story-evaluation/SKILL.md` | 内容修改 | V51-04 | `5d8d6ba4a1ed` → `9c69ec224c9a` |
| `china-story-evaluation/agents/openai.yaml` | `china-story-evaluation/agents/openai.yaml` | 保留未改 | — | `fe742494eab4` → `fe742494eab4` |
| `china-story-evaluation/docs/Evaluation_v4.1_Changes_and_Evidence.md` | `docs/evaluation/history/Evaluation_v4.1_Changes_and_Evidence.md` | 移动未改 | V51-08 | `223872bcd095` → `223872bcd095` |
| `china-story-evaluation/docs/Evaluation_v4.1_Test_Plan.md` | `docs/evaluation/history/Evaluation_v4.1_Test_Plan.md` | 移动未改 | V51-08 | `59079a365318` → `59079a365318` |
| `china-story-evaluation/references/cross-cultural-review.md` | `china-story-evaluation/references/cross-cultural-review.md` | 内容修改 | V51-12 | `83a46854a42f` → `f9879493c0cc` |
| `china-story-evaluation/references/genre-checks.md` | `china-story-evaluation/references/genre-checks.md` | 内容修改 | V51-10 | `1cef35f38369` → `d90d64a38917` |
| `china-story-evaluation/references/input-contracts.md` | `china-story-evaluation/references/input-contracts.md` | 内容修改 | V51-02 | `e726519cf90e` → `145ff73c25bc` |
| `china-story-evaluation/references/judge-reliability.md` | `china-story-evaluation/references/judge-reliability.md` | 内容修改 | V51-12 | `1cf71e49a9fe` → `ca7034c0cfb4` |
| `china-story-evaluation/references/output-contracts.md` | `china-story-evaluation/references/output-contracts.md` | 内容修改 | V51-03 | `3312d5c89a87` → `7a69f1debb33` |
| `china-story-evaluation/references/revision-feedback.md` | `china-story-evaluation/references/revision-feedback.md` | 内容修改 | V51-12 | `8f4c205d1f6b` → `1cab8580b466` |
| `china-story-evaluation/references/rubric-usage.md` | `china-story-evaluation/references/rubric-usage.md` | 内容修改 | V51-12 | `1d83ab9368bd` → `2ea74a91ba9c` |
| `china-story-evaluation/schemas/evaluation-result-v4.1.schema.json` | `api/schemas/evaluation-result-v5.1.schema.json` | 移动并修改 | V51-05 | `ad81945e27c5` → `9db69618924f` |
| `china-story-evaluation/scripts/validate_evaluation.py` | `utils/validate_evaluation.py` | 移动并修改 | V51-06 | `c48f3b4d146e` → `4dc0377685a3` |
| `china-story-evaluation/tests/fixtures/content.txt` | `tests/evaluation/fixtures/content.txt` | 移动未改 | V51-07 | `a58f03fdf722` → `a58f03fdf722` |
| `china-story-evaluation/tests/fixtures/valid_evaluation.json` | `tests/evaluation/fixtures/valid_evaluation.json` | 移动未改 | V51-07 | `b34908feed20` → `b34908feed20` |
| `china-story-evaluation/tests/test_validate_evaluation.py` | `tests/evaluation/test_validate_evaluation.py` | 移动并修改 | V51-07 | `29967e578097` → `ed884dc56de7` |
| `china-story-generation/SKILL.md` | `china-story-generation/SKILL.md` | 保留未改 | — | `d5746a33ac74` → `d5746a33ac74` |
| `china-story-generation/agents/openai.yaml` | `china-story-generation/agents/openai.yaml` | 保留未改 | — | `4c6bd41d1c71` → `4c6bd41d1c71` |
| `china-story-generation/docs/Post_News_v3.1_Changes_and_Sources.md` | `docs/generation/Post_News_v3.1_Changes_and_Sources.md` | 移动未改 | V51-09 | `5368e0a7dd22` → `5368e0a7dd22` |
| `china-story-generation/docs/Post_News_v3.1_Tests.md` | `docs/generation/Post_News_v3.1_Tests.md` | 移动未改 | V51-09 | `3ae923f6730e` → `3ae923f6730e` |
| `china-story-generation/references/genres/faq.md` | `china-story-generation/references/genres/faq.md` | 保留未改 | — | `7cba45c3d430` → `7cba45c3d430` |
| `china-story-generation/references/genres/feature.md` | `china-story-generation/references/genres/feature.md` | 保留未改 | — | `5b9a37b05f89` → `5b9a37b05f89` |
| `china-story-generation/references/genres/indepth.md` | `china-story-generation/references/genres/indepth.md` | 保留未改 | — | `695463358c7a` → `695463358c7a` |
| `china-story-generation/references/genres/news.md` | `china-story-generation/references/genres/news.md` | 保留未改 | — | `8733f7e83e8c` → `8733f7e83e8c` |
| `china-story-generation/references/genres/post.md` | `china-story-generation/references/genres/post.md` | 保留未改 | — | `3aaf51177463` → `3aaf51177463` |
| `china-story-generation/references/genres/script.md` | `china-story-generation/references/genres/script.md` | 保留未改 | — | `18bd568e246e` → `18bd568e246e` |
| `china-story-generation/references/output-contracts.md` | `china-story-generation/references/output-contracts.md` | 保留未改 | — | `db7543fb9fb5` → `db7543fb9fb5` |
| `china-story-generation/references/transcreation.md` | `china-story-generation/references/transcreation.md` | 保留未改 | — | `7459bfc532ee` → `7459bfc532ee` |
| `china-story-generation/references/writing-constraints.md` | `china-story-generation/references/writing-constraints.md` | 保留未改 | — | `1a322e06daa2` → `1a322e06daa2` |
| `handoff-to-backend/01-plan-stage-spec.md` | `handoff-to-backend/01-plan-stage-spec.md` | 保留未改 | — | `49ddeb8dfc1a` → `49ddeb8dfc1a` |
| `handoff-to-backend/02-ground-evidence-spec.md` | `handoff-to-backend/02-ground-evidence-spec.md` | 保留未改 | — | `7ed5b05e83f1` → `7ed5b05e83f1` |
| `handoff-to-backend/03-evaluation-part1-fact-check.md` | `handoff-to-backend/03-evaluation-part1-fact-check.md` | 保留未改 | — | `363fa0804f51` → `363fa0804f51` |
| `handoff-to-backend/04-code-integration-patch.md` | `handoff-to-backend/04-code-integration-patch.md` | 保留未改 | — | `df0ad26c3164` → `df0ad26c3164` |
| `handoff-to-backend/05-evaluation-v4.1-integration.md` | `handoff-to-backend/05-evaluation-v4.1-integration.md` | 内容修改 | V51-11 | `c79932dbe765` → `19d3f739055e` |

## v5.1 新增文件

| v5.1 新文件路径 | 用途 / 修改编号 |
|---|---|
| `README-v5.1.md` | V51-12（新增） |
| `docs/Evaluation_Skill_v5.1_Architecture.md` | V51-12（新增） |
| `docs/evaluation/Evaluation_v5.1_Changes_and_Evidence.md` | V51-08（新增） |
| `docs/evaluation/Evaluation_v5.1_Test_Plan.md` | V51-08（新增） |
| `handoff-to-backend/06-evaluation-v5.1-integration.md` | V51-11（新增） |
| `tests/evaluation/__init__.py` | V51-07（新增） |
| `tests/test_package_layout.py` | V51-07（新增） |

## 文件完整性结论

- v4.1 有 **36** 个源文件；所有文件均在 v5.1 的对应路径找到，**无无说明的丢失文件**。
- Generation 的运行文件（`SKILL.md`、所有 `references`、`agents/openai.yaml`）字节完全不变；仅移动了两份旧研究文档。
- `evaluation-result-v5.1.schema.json` 与原 v4.1 相比**只有 `$id` 和 `title` 两个元数据字段变化**；字段、必填、取值范围和条件约束保持一致。
- v4.1 的 Evaluation 两份研究文档和 Generation 两份历史研究文档散列保持一致。旧 README-v4.1 的历史说明与文档链接为适应迁移而修订。
- 检查依据：本地 SHA-256 逐文件比对与结构单元测试；并不表示真实模型效果或线上部署通过。
