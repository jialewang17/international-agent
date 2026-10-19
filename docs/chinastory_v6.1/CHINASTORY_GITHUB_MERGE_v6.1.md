# ChinaStory Agent — GitHub 合并与工程交接规范 v6.1

> 日期：2026-10-18。**基线**：用户上传的 `ChinaStory-final-skills-v5.1.zip` + 在线核对的 `jialewang17/international-agent` 公开 `main`。这是**可复制到本地仓库的合并候选包**，不是 GitHub 上已提交的代码，也不等于完整 E2E 已跑通。
>
> **原则**：保留两项 Skill、六份体裁参考方法（Post/News v3.1 不改动）、正式 Rubric D1–D6 1–5 分；不因文件复制而谎称 Part 1、Part 2、Part 3、Revision Loop 已完整实施。

## 0. 结论与合并策略

本次已做：调整 Skill 目录到仓库既有 `skills/` 下；Schema 避开 `api/schemas.py` 命名碰撞；修复合并时评测验证器引用路径；新增受约束的按需方法加载器；提供**默认 dry-run 的幂等合并脚本**，其中修复 News 成功响应遗漏 canonical `_evidence_pack` 的具体问题；新增 `jsonschema` 依赖；保留原始研究和规范证据；扩充离线单元测试。完整改动依据见 [V6.1 变更与来源清单](CHANGELOG_AND_EVIDENCE_v6.1.md)。

**本次没有做**：没有改 `api/schemas.py` 的 `EvaluationResult` 字段；没有把 `confidence=null` 自动伪装成浮点置信概率；没有把新 Schema 直接注册为 API；没有修改现有发布/审批权限；没有把 `faq/indepth` 假称为已完成端到端生成；没有直接向远端 GitHub 写入代码。

## 1. 合并后的目标目录

```text
international-agent/
  skills/
    china-story-generation/{SKILL.md,references/,agents/}
    china-story-evaluation/{SKILL.md,references/,agents/}
  eval/
    CHINASTORY_CONTENT_QUALITY_RUBRIC_v2.1.md    # GitHub 原文件，不覆盖
    contracts/evaluation-result-v6.1.schema.json # 从 v5.1 api/schemas 迁入
  utils/
    chinastory_skill_loader_v61.py               # 新增：按需读方法与权威 Rubric
    validate_evaluation.py                       # v5.1 逻辑校验迁移
  tests/chinastory_v61/                          # 回归测试、独立数据样本
  docs/chinastory_v6.1/                          # 本文、依据、历史档案、验收
  scripts/apply_chinastory_v6_1.py               # 默认 dry-run 的合并辅助
```

**不要**把 ZIP 中 `skills/`、`api/`、`utils/`、`docs/` 整个覆盖仓库同名目录。现有知识库、生成工具、Pydantic、Gate A/B/C、前端以及 GitHub LICENSE 保持原样。

## 2. 合并前已有的真实差异

| 部位 | 在线核查的公开 `main` | 处理 |
|---|---|---|
| `config/skills.yaml` | 旧的 `china_story_post/news/feature/script` 与 `china_story_active` 仍存在 | 注册两个新 ID 为阶段性（`keywords: []`），不删除旧项，避免突然影响旧流程；**不等于路由完成迁移** |
| `utils/skill_registry.py` | 每个 Skill 默认最多加载 3600 字符，根级 `.md` 扫描 | 新建显式 loader 从 `SKILL.md + references` 读取完整指定体裁；未接线时不自动生效 |
| `tools/genre_router.py` | 深度报道被 feature 提前匹配，`faq` 与 `indepth` 生成尚不完整 | 标为上线阻断事项，别只改路由词导致落入错误的 Post 分支 |
| `tools/story_post_gen.py` | News 分支返回 `post/article` 但遗漏 `_evidence_pack` | 合并辅助脚本添加 canonical EvidencePack 内部交接；阻塞/错误输出不持久化 |
| `api/main.py` | 成功生成时要求 `_evidence_pack`，并创建 ContentVersion；Gate C 已有绑定校验 | 只修上述交接缺口；不覆盖审批流程 |
| `api/schemas.py` | 定义 canonical `EvaluationResult`，其 `confidence: float`，`EvidenceSpan` 要求源 ID | Skill JSON 尚需显式 adapter，**禁止直接把独立 JSON 当成 API model** |
| `requirements.txt` | 未列 `jsonschema` | 添加 `jsonschema>=4`，用于离线确定性校验 |
| `eval/...Rubric_v2.1.md` | 六维评分的项目权威标准 | 不修改、不复制替代；loader 必须从当前仓库加载 |

对应源文件直接链接：
- [config/skills.yaml](https://github.com/jialewang17/international-agent/blob/main/config/skills.yaml)
- [utils/skill_registry.py](https://github.com/jialewang17/international-agent/blob/main/utils/skill_registry.py)
- [tools/genre_router.py](https://github.com/jialewang17/international-agent/blob/main/tools/genre_router.py)
- [tools/story_post_gen.py](https://github.com/jialewang17/international-agent/blob/main/tools/story_post_gen.py)
- [api/main.py](https://github.com/jialewang17/international-agent/blob/main/api/main.py)
- [api/schemas.py](https://github.com/jialewang17/international-agent/blob/main/api/schemas.py)
- [正式 Rubric](https://github.com/jialewang17/international-agent/blob/main/eval/CHINASTORY_CONTENT_QUALITY_RUBRIC_v2.1.md)

## 3. 如何在本地 GitHub 工作树合并（Windows Cursor）

1. 将本 v6.1 ZIP 解压到仓库**旁边**的一个文件夹，例如 `ChinaStory-GitHub-v6.1/`，进入你的 `international-agent/` Git 工作树。
2. 检查分支与现状：`git status`；`git pull --ff-only`；`git switch -c feat/chinastory-skills-v6.1`。
3. **先预演**（不会写入）：
   ```powershell
   python ..\ChinaStory-GitHub-v6.1\scripts\apply_chinastory_v6_1.py .
   ```
4. 查看预演清单，无冲突才执行：
   ```powershell
   python ..\ChinaStory-GitHub-v6.1\scripts\apply_chinastory_v6_1.py . --apply
   ```
   实施脚本要求仓库工作树干净，预检查所有文件冲突；如果仓库结构与本次公开源码不一致会拒绝操作，而非盲目覆盖。**不会自动 commit/push**。
5. 安装测试依赖、验证：
   ```powershell
   python -m pip install -r requirements.txt
   python -m unittest discover -s tests/chinastory_v61 -p "test_*.py" -v
   python utils/validate_evaluation.py tests/chinastory_v61/fixtures/valid_evaluation.json --content-file tests/chinastory_v61/fixtures/content.txt
   git diff --check
   git diff --stat
   git status
   ```
6. 若已有测试框架与环境可用，再运行仓库已有测试。核对 [接口差异与阻断项](INTERFACE_GAPS_v6.1.md)，通过前**不要**对外宣称新评测已上线。
7. 人工审查代码后再 `git add`、`git commit -m "feat: stage ChinaStory skills v6.1 integration"`、`git push -u origin feat/chinastory-skills-v6.1`，并发起 Pull Request。这里仅提供步骤，未代表你提交。

## 4. Skill 的真实执行关系

```text
旧前端 /api/posts/generate ---> legacy tools/story_post_gen.py --> canonical EvidencePack
                                       |                     |
                                       |                     +--> ContentVersionStore
                           默认仍走旧 Prompt（兼容）

新登记的两个 Skill + 严格方法加载器（本次可运行、未自动接入原生成接口）
  Create/Revision: skills/china-story-generation/SKILL.md + 专属 genre.md
  Evaluation P3 : skills/china-story-evaluation/SKILL.md + 仓库正式 Rubric
                --> LLM Judge（待真正接线）--> v6.1 JSON validator
                --> canonical Pydantic 适配（待做）--> Revision / Gate C（待端到端验证）
```

新方法加载器只是**准备、验证并返回 Prompt 静态规则**，不自行调用 Qwen，不替代事实门禁，不能标记批准。当前不自动插入旧版 `story_post_gen.py`，避免任务计划/母稿引用还未适配时造成回归。

## 5. 进入下一轮工程合并前必须确认

- 使用同一条 `ContentVersion` 存储链，确保 `evaluation_id`、`content_version_id`、`task_id` 一致，不用模型输出替代 canonical ID。
- 完成 JSON Schema ↔ Pydantic 的字段映射（见 [接口差异与阻断项](INTERFACE_GAPS_v6.1.md)），且未校准评分不产生假精度。
- 至少用一个 Post 和一个 News 案例验证 **资料 → evidence → 草稿 → Part1 → Part3 → 合法 JSON → Revision → 人工**；失败不能自动 Gate C。
- 仍未完成的六体裁差异和视觉素材输入应当显式对外标为不可用或待验证，不应偷偷复用 Post 结果。
- 提交前运行仓库的安全/保密检查，确保 `.env`、密钥、用户上传的原始敏感素材未进入提交。

## 6. 验证口径

本交付能证明：离线 Skill 文档结构、方法加载、JSON 输出契约、修改脚本的保守行为可静态测试。由于当前工具环境无法克隆公有 GitHub 仓库到本地，**未对真实远端工作树运行安装或完整业务 E2E**；线上情况以你在 Cursor 的分支和 CI 结果为准。评测质量还需要真实模型与人工对照，不可从 Python 单测通过推断。


## 7. 本地离线验证（2026-10-18）

- 本交付包 **28 项离线 unittest 通过**：16 项评价 JSON 测试 + 12 项合并与加载测试；测试不依赖实际模型。
- 两项顶层 Skill 的 YAML frontmatter/name 与目录一致；六份体裁正文 SHA-256 未变化；JSON Schema 除元信息外与 v5.1 字段完全一致。
- 本包新规范文档及运行 Skill Markdown 的相对链接已检查。
- 合并辅助脚本在**模拟旧仓库**上验证了 dry-run、应用、幂等和异常拒绝操作；**没有拿到真实仓库完整源码副本，不能把此结果当作真实仓库测试通过**。
