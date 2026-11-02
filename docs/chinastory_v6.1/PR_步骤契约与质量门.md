# PR 草稿：Skill 步骤契约 / 方法依据 / 可追溯性 / 质量门

> 状态：**草稿，未推送**。按任务书要求不自动进 `main`，先由老师/成员 review。
> 目标仓库：`jialewang17/international-agent`；建议分支名 `feat/skill-step-contracts-audit`。

---

## PR 标题

`Skill 步骤契约化：C00–C06 / E00–E05 契约 + step_audit 可追溯 + 确定性质量门`

## PR 描述

### 背景

两个 Skill 此前只有**流程叙述**——SKILL.md 里写着 §2 的步骤，但没有「这一步跑没跑、
依据是什么、产出是什么」的机器可读证据，也没有在代码里落地的质量门。已经出现过一次后果：
`SKILL.md` §2.0 写着"成稿前调用 `load_story_knowledge`"，而生成链路根本没有这个调用，
文档与代码漂移长期无人发现。

本次把这四件事做实：**每步包含什么 / 每步有依据 / 每步可溯 / 每步有质量门**。

### 主要改动

1. **步骤契约**（新增两份 `step-contracts.md`）
   - 生成侧 C00–C06：选择与输入契约 → 证据门禁 → 方法加载与体裁隔离 → 提示构造 →
     生成 → 输出契约校验 → 自检与人工移交；
   - 评测侧 E00–E05：前置检查与 Part 1 门禁 → 资料加载 → 逐维评价 → 定位与最小修改指令 →
     输出结构与状态 → 机器校验与校准留痕；
   - 每节含：输入 / 动作 / 产出 / 依据 / 停机条件 / 审计字段。

2. **方法依据可机器校验**（新增 `utils/step_audit.py`）
   - 13 个步骤各自声明 `文件::锚点` 形式的依据，共 40 个锚点；
   - `evidence_problems()` 校验锚点是否在仓库里**真实存在**；锚点丢掉即测试红。

3. **可追溯**（`step_audit` 伴生数据）
   - 生成结果新增 `step_audit`：C00–C06 的 `status / reason / detail`，未跑的必做步骤标 `NOT_RUN`，
     终态 `COMPLETE / BLOCKED / FAILED / INCOMPLETE`；
   - 评测新增 `evaluate_part3_with_audit()` 返回 `(EvaluationResult, step_audit)`；
     `evaluate_part3()` 签名与返回值不变，`EvaluationResult` **不加字段**；
   - 4 份脱敏样例（真实代码路径产出）+ 复核 CLI `scripts/step_audit_check.py`。

4. **质量门**
   - 修 `always_on` 假常开：`resolve_always_on()` 严格判定，生成链路并入必需技能，
     不可用即 `SKILL_ALWAYS_ON_UNAVAILABLE` 硬失败；`get_active_skills_for_query`
     为 `always_on` 预留额度，不再被字符预算裁掉；
   - 评测 E05 新增 `deterministic_checks()`：六维唯一齐全、分值 1–5、跨度精确匹配、
     正文 SHA-256、状态组合自洽；
   - E03 跨度核对：`content.text[start:end] != span.text` 不再静默通过，
     转 `span-mismatch` blocking issue；
   - 模型空输出 → `OUTPUT_INVALID`。

### 明确没做（请不要按"已完成"理解）

- 生成工具未驱动 `WorkflowStateMachine`（Gate A/B/C 真裁决）——无状态函数强接会改所有调用方语义，
  建议单独立项在 `api/main.py` 收口；
- 分数阈值型质量门未做（Rubric §19 仍 TBD，不私设标准）；
- JSON Schema 校验仍在后端 CLI，不引入运行时依赖；
- `thread` / `visual_story` / `caption_only` 仍 `UNSUPPORTED_GENERATION`。

### 验证

```bash
pytest tests/ -q                                                    # 633 passed
python scripts/step_audit_check.py --evidence                       # 40 个锚点全命中
python scripts/make_step_trace_samples.py                           # 重跑样例
python scripts/step_audit_check.py docs/chinastory_v6.1/step_trace_samples/generation_ok.json --require-complete
```

### 契约影响

| 契约 | 是否变动 |
|---|---|
| `Claim` / `EvidencePack` / `Coverage` | 不变 |
| `EvaluationResult` / `EvaluationAuditMetadata` | 不变（审计走 sidecar） |
| `api/schemas.py` | 未改 |
| 生成结果 dict | **仅新增** `step_audit` 键；既有键全保留 |
| `skill_load.loaded_files` | 值变化（新增 2 张 `always_on` 卡），语义不变 |

### 风险与回滚

- 风险：`always_on` 现在是硬失败路径。若部署环境缺 `skills/intl-comm.md` 或
  `skills/evidence-user-materials.md`，生成会直接停。这是**有意的收紧**，
  但上线前必须确认这两个文件随包发布。
- 回滚：本次改动均为**新增可选能力**或**显式失败**，回滚只需 revert 本 PR；无数据迁移。

---

## 提交拆分建议（每个 commit 可独立 review）

1. `feat(skill): 新增 C00–C06 / E00–E05 步骤契约文档`
2. `feat(audit): 新增 utils/step_audit.py 步骤审计与依据锚点校验`
3. `fix(skill): always_on 从"尽力而为"改为硬约束（G-10）`
4. `feat(generation): 生成结果输出 step_audit（C00–C06）`
5. `feat(evaluation): evaluate_part3_with_audit + E05 确定性校验`
6. `test(skill): 21 项步骤契约/质量门回归`
7. `docs(skill): 差距报告、方法依据矩阵、变更记录、追溯样例`

## Review checklist（给 reviewer）

- [ ] 13 个步骤的「停机条件」和现有错误码是否一一对应（`step-contracts.md` 末尾对照表）
- [ ] `step_audit` 是否**只增不改**：抽查 `generation_ok.json`，既有字段一个不少
- [ ] `always_on` 硬失败的取舍是否同意（不同意可降级为 warn + 审计标记，但需明确记录）
- [ ] E03 把偏移不一致转成 blocking issue 的写法是否可接受
- [ ] 差距报告 §3「遗留风险」是否遗漏需要老师决策的项
