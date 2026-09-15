# Skill 评测文件说明

**公开原则**：仓库只放评价体系定稿与空白模板；本机训练过程（跑分输出、分轮 xlsx/csv）不推送。

## 评价体系文档（定稿，可公开）

| 文件 | 用途 |
|------|------|
| `CONTENT_QUALITY_RUBRIC_v1.md` | **成稿符合度定稿表**（ROC 权重已锁定） |
| `DRAFT_USER_RUBRIC_v0.md` | 权重推演说明 + **材料运用轨**维度池（后续扩展） |
| `LIT_DIMENSION_BANK.md` | 文献维度库与会议五维映射 |
| `UNIFIED_SCORECARD_v1.md` | 现行工程打分卡（Shared + 体裁插件） |
| `MATERIALS_FLEX_PROMPT_COMPLIANCE_RUBRIC.md` | 提示遵从 / 用料细则附录 |
| `SCORECARD_MIGRATION_v1.md` | 旧表 → 统一计分卡迁移说明 |
| `LARGE_EVAL_PLAN.md` | 大规模评测计划 |

后续：其他体裁评价体系、材料关联性细表，继续以独立 md 放本目录。

## 空白模板（可公开）

| 文件 | 用途 |
|------|------|
| `skill_eval_template.csv` | 固定测试题空白表 |
| `skill_changelog_template.csv` | skill 改动记录空白表 |
| `skill_eval_summary_template.csv` | 汇总均分空白表 |

## 仅本机保留（已加入 .gitignore，勿再 commit）

- `outputs/`、`outputs_*/`：各轮生成 JSON  
- `skill_eval_v0.*.csv` / `.xlsx`、`skill_eval_cases_v0.*.csv`：分轮填表与用例包  
- `skill_rounds_master_summary.xlsx`：轮次总表  

Agent / API / 前端文档在仓库根目录与 `docs/`、`api/`、`frontend/`，**保留公开**。

## 本地使用步骤

1. 复制 `skill_eval_template.csv` 为 `skill_eval_v0.x_YYYYMMDD.csv`（仅本机）
2. 跑测后把输出放进 `eval/outputs*/`（仅本机）
3. 只改 skill 一处 → 记入 changelog 模板副本
