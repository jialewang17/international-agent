# ChinaStory 基线说明（2026-11-02）

> **这个文件夹是唯一的修改基线。以后所有改动都在这里做，不要再改其他副本。**

## 一、这份基线是什么

| 项目 | 内容 |
|---|---|
| 来源 | `Desktop\大创了吗\international-agent-main\international-agent-main`（合并 PR #5 后的最新状态） |
| 对应线上 | GitHub `jialewang17/international-agent` 的 `main` 分支，merge commit `ac76d4f` |
| 建立时间 | 2026-11-02 16:30 |
| 文件数 / 体积 | 657 个文件 / 约 11 MB |
| 验证结果 | **633 项测试全部通过**（含 40 项 P0 六体裁测试、21 项步骤契约/质量门测试）；关键文件 SHA-256 与源副本逐字节一致 |
| 最近一次本地改造 | 2026-11-02 晚：步骤契约化（C00–C06 / E00–E05）+ step_audit + 确定性质量门（**尚未推送**，PR 草稿见 `docs/chinastory_v6.1/PR_步骤契约与质量门.md`） |

## 二、当前版本状态（改之前先看这里）

### 两套核心技能

| 技能 | 路径 | 作用 |
|---|---|---|
| 内容生成技能 | `skills/china-story-generation/` | 按体裁把素材写成面向海外受众的稿件（SKILL.md 13,852 B；含 C00–C06 步骤契约） |
| 质量评测技能 | `skills/china-story-evaluation/` | 按 D1–D6 六维评分并输出可执行修改指令（SKILL.md 10,572 B；含 E00–E05 步骤契约） |

### 六体裁方法卡（`skills/china-story-generation/references/genres/`）

| 体裁 | 文件 | 大小 | 版本 |
|---|---|---|---|
| 社交帖文 | `post.md` | 23,427 B | **v3.2**（2026-10-22 专项审查修订，落实 G1–G11） |
| 新闻通稿 | `news.md` | 11,535 B | v3.1 |
| 特稿 | `feature.md` | 6,833 B | 原版 |
| 深度报道 | `indepth.md` | 5,988 B | 原版 |
| 短视频脚本 | `script.md` | 1,682 B | 原版（内容偏薄，待补齐） |
| 问答澄清 | `faq.md` | 1,474 B | 原版（内容偏薄，待补齐） |

### P0 六体裁接入修复（2026-11-02）

| 文件 | 作用 |
|---|---|
| `utils/genre_contracts.py` | **六体裁契约单一事实源**：Genre ↔ Skill ID ↔ 方法卡路径 ↔ 默认/已支持 Format ↔ 输出契约 |
| `tools/genre_router.py` | 路由与选择校验：显式选择优先、`INVALID_GENRE`、`GENRE_FORMAT_CONFLICT` |
| `utils/skill_registry.py` | `load_required_skills()` 严格加载：缺失/为空/禁用/超预算即失败 |
| `tools/story_post_gen.py` | 生成主流程：体裁模板隔离、`UNSUPPORTED_GENERATION`、`OUTPUT_INVALID`、`skill_load` 诊断 |
| `tests/test_six_genre_p0.py` | 40 项 P0 回归测试 |
| `scripts/p0_acceptance_check.py` | 验收脚本（映射一致性 / 六体裁链路 / 失败路径 / Prompt 样例） |
| `docs/chinastory_v6.1/P0_六体裁接入交付说明.md` | 交付说明：改动清单、行为对照、测试结果、剩余风险 |

### 步骤契约与质量门（2026-11-02 晚，本地待推）

| 文件 | 作用 |
|---|---|
| `skills/china-story-generation/references/step-contracts.md` | 生成侧 **C00–C06** 契约（输入/动作/产出/依据/停机/审计字段） |
| `skills/china-story-evaluation/references/step-contracts.md` | 评测侧 **E00–E05** 契约 |
| `utils/step_audit.py` | 13 步契约单一事实源 + 40 个方法依据锚点 + 步骤审计记录器 + 确定性复核 |
| `tools/story_post_gen.py` | 生成结果新增 `step_audit`；`always_on` 改为硬约束 |
| `api/evaluation_part3.py` | 新增 `evaluate_part3_with_audit()` + E05 确定性校验（契约不变） |
| `scripts/step_audit_check.py` | 复核 CLI：`--evidence` / `--index` / `--require-complete` |
| `scripts/make_step_trace_samples.py` | 用真实代码路径产出 4 份脱敏追溯样例 |
| `docs/SKILL_STEP_GAP_ANALYSIS.md` | 差距报告（GAP-01–GAP-10） |
| `docs/SKILL_METHOD_EVIDENCE_MATRIX.md` | 步骤 × 方法依据矩阵 |
| `docs/SKILL_TRACEABILITY_CHANGELOG.md` | 变更记录与验证结果 |
| `docs/chinastory_v6.1/step_trace_samples/` | 4 份样例 + README |
| `tests/test_step_audit.py` | 21 项回归测试 |

## 三、目录导航

| 目录 | 内容 |
|---|---|
| `skills/` | 两套技能：生成（含六体裁卡）与评测（含 7 个参考文件） |
| `tools/` | 工具层：`genre_router.py`、`story_post_gen.py` 等 |
| `utils/` | 通用层：`genre_contracts.py`、`skill_registry.py`、`validate_evaluation.py` 等 |
| `api/` | FastAPI 接口与 Schema |
| `prompt/` | 三套 Prompt 模板（post / news / genre） |
| `config/` | `skills.yaml` 技能注册表、`model.yaml` 模型配置 |
| `eval/` | 评测流水线规范 v1.2、内容质量 Rubric v2.1、结果 Schema |
| `tests/` | 633 项测试（`test_six_genre_p0.py` P0 六体裁 40 项、`test_step_audit.py` 步骤契约 21 项） |
| `docs/` | 项目文档、交付说明、Prompt 样例（`docs/chinastory_v6.1/`） |
| `knowledge/` | 写作方法知识库（外媒编码、南周写作课等） |
| `frontend/`、`cli/`、`agent/` | 前端、命令行与 Agent 层 |

## 四、未收录的内容（不影响运行）

| 排除项 | 原因 | 需要时怎么办 |
|---|---|---|
| `venv/`（302 MB） | Python 虚拟环境，体积大且可重建 | 见下方“如何运行” |
| `__pycache__/`、`*.pyc`、`.pytest_cache/` | 编译与测试缓存 | 自动重建 |
| `project-tree.txt`、`skills-tree.txt` | 自动生成的目录清单 | 用 `find`/`dir` 重新生成 |

> `.env` 已随快照一并复制（内含当前已失效的千问 Key，见“已知问题”第 1 条）；`archive/` 里的 v1 旧版规范也保留了，仅作归档参考，不参与运行。

## 五、如何运行与测试

虚拟环境没有复制过来，两种方式都能跑：

**方式 A：借用原副本的环境（最快，不占空间）**

```bash
cd "C:/Users/xy/Desktop/大创了吗/ChinaStory-基线_2026-11-02"
"C:/Users/xy/Desktop/大创了吗/international-agent-main/international-agent-main/venv/Scripts/python.exe" -m pytest tests/ -q
```

**方式 B：在本文件夹自建环境**

```bash
cd "C:/Users/xy/Desktop/大创了吗/ChinaStory-基线_2026-11-02"
python -m venv venv
venv/Scripts/python.exe -m pip install -r requirements.txt
venv/Scripts/python.exe -m pytest tests/ -q
```

## 六、已知问题（改之前要知道）

1. **`.env` 里的千问 API Key 已失效**（平台侧吊销，返回 401）——真实大模型生成需要去 platform.qianwenai.com 重新生成 key 后替换；纯测试与路由验证不依赖 key。
2. **`post` 体裁的 `thread` / `visual_story` / `caption_only` 三种 Format 尚未接线**，当前明确返回 `UNSUPPORTED_GENERATION`（不会伪装成功）。
3. **`feature` / `indepth` / `script` / `faq` 四张卡偏薄**（1.5–6.8 KB），是下一阶段要补齐的重点。
4. **评测侧后端接线（I-01~I-06）**仍未实现，属于待办（步骤契约 E00–E05 已就位，不影响该待办）。
5. **生成工具仍未驱动 Gate 状态机**（`api/workflow.py` 的 A/B/C 真裁决）：`step_audit` 只记录本次门禁依据，不等于状态机裁决。详见差距报告 GAP-01。
6. **分数阈值型质量门未做**：Rubric §19 阈值仍是 TBD，现有质量门只拦结构性与自洽性错误。

### 交付前自检三条命令

```bash
PY="C:/Users/xy/Desktop/大创了吗/international-agent-main/international-agent-main/venv/Scripts/python.exe"
"$PY" -m pytest tests/ -q                                        # 633 passed
"$PY" scripts/step_audit_check.py --evidence                     # 40 个依据锚点全命中
"$PY" scripts/step_audit_check.py docs/chinastory_v6.1/step_trace_samples/generation_ok.json --require-complete
```

## 七、修改后如何同步到 GitHub

本文件夹**不是 git 仓库**（是快照副本），提交需要走 GitHub 接口：

- 向 `main` 直接提交：适合小改动、文档修订
- 建分支 + PR：适合代码改动（规范做法，便于审查与回溯）

两种方式我都可以代为执行，改完说一声即可。

---

**最后再强调一次：以后改代码、改文档、改技能卡，只改这个文件夹里的文件。其余副本（`international-agent-main`、`最新skill/` 下的旧包）都视为历史备份，不再修改。**
