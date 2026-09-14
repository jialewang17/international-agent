# Skill 评测文件说明

## 评价体系文档（文献 / 定稿表，与跑分表分开）

| 文件 | 用途 |
|------|------|
| `CONTENT_QUALITY_RUBRIC_v1.md` | **成稿符合度定稿表**（ROC 权重已锁定） |
| `DRAFT_USER_RUBRIC_v0.md` | 权重推演说明 + **材料运用轨**维度池（后续扩展） |
| `LIT_DIMENSION_BANK.md` | 文献维度库与会议五维映射 |
| `UNIFIED_SCORECARD_v1.md` | 现行工程打分卡（Shared + 体裁插件） |

后续：其他体裁评价体系、材料关联性细表，继续加在本目录并以独立 md 命名，勿与下方 CSV 跑分模板混用。

---

## 跑分 / Changelog 模板

| 文件 | 用途 |
|------|------|
| `skill_eval_template.csv` | 15 条固定测试题 + 7 维打分（用 Excel 打开） |
| `skill_changelog_template.csv` | 每轮 skill 改动记录（一次只改一处） |
| `skill_eval_summary_template.csv` | 每轮汇总均分与通过率 |

## 使用步骤

1. 复制 `skill_eval_template.csv` 为 `skill_eval_v0.1_YYYYMMDD.csv`
2. 按 T01–T15 在 CLI 跑测，把 Agent 输出粘贴到最后一列
3. 用评测 Judge Prompt（见项目文档或对话记录）打分
4. 只改 skill 一处 → 记入 `skill_changelog_template.csv`
5. 重跑全量或受影响用例 → 填 `skill_eval_summary_template.csv`
