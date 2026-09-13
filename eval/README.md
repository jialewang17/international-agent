# Skill 评测文件说明

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
