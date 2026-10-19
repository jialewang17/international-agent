# ChinaStory Skills + GitHub Merge Candidate v6.1

这是针对已有 `international-agent` GitHub 工程的**保守合并候选包**，以 v5.1 用户上传 ZIP 为基线。**没有替用户直接修改远端仓库**。

**最重要的文件：**

- [v6.1 GitHub 合并详细指南](docs/chinastory_v6.1/CHINASTORY_GITHUB_MERGE_v6.1.md)
- [v6.1 每处修改的依据与来源](docs/chinastory_v6.1/CHANGELOG_AND_EVIDENCE_v6.1.md)
- [仍未对齐的接口与阻断项](docs/chinastory_v6.1/INTERFACE_GAPS_v6.1.md)
- [回归与真实验收计划](docs/chinastory_v6.1/TEST_PLAN_v6.1.md)
- `scripts/apply_chinastory_v6_1.py`（默认 dry-run，指定 `--apply` 才写入）

## 关键变化

- 两项顶层 Skill 现在落到仓库原有 `skills/`；Post/News v3.1 方法及另外四个体裁方法全部保留。
- `eval/contracts/evaluation-result-v6.1.schema.json` 取代 v5.1 的 `api/schemas/` 文件夹位置；规避与已有 `api/schemas.py` 潜在的重名导入风险。业务字段没有改变。
- `utils/validate_evaluation.py` 的 Schema 地址已更新；保持 v5.1 的校验逻辑。
- 新 `utils/chinastory_skill_loader_v61.py` 只做受约束的参考文件加载；不会自动改写 Prompt 或调用模型。
- 合并脚本分阶段**注册**两项新 Skill（旧路由先保留），修复 News `_evidence_pack` 交接，按需添加 `jsonschema` 依赖。
- **未实现**新的 P3 API、完整六体裁生成、Fact Lock、校准、人工审批后的自动发布（系统本就不自动发布）。

## 默认只做检查

```bash
python scripts/apply_chinastory_v6_1.py /path/to/international-agent
```

准备提交的工程步骤与独立测试命令见合并指南。**若提示远端源码已变化或目标文件不同，必须人工 review，不要强制覆盖。**

本地离线测试：28 项通过（非真实 GitHub 工作树 / 非 LLM E2E）。
