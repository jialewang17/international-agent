# 变更记录：Skill 步骤契约 / 方法依据 / 可追溯性 / 质量门

> 本轮改造的唯一目标：让「每一步包含什么、有依据、可溯、有质量门」变成**可执行、可复核**的东西，
> 而不是文档里的一句承诺。
>
> 约束（全部遵守）：不破坏 `Claim` / `EvidencePack` / `Coverage` / `EvaluationResult` 契约；
> 不自动推 `main`；不造假测试、不造假评分；没有核实的事情不写进结论。

---

## 1. 新增文件

| 文件 | 作用 |
|---|---|
| `utils/step_audit.py` | 步骤契约单一事实源（13 步 / 40 个依据锚点）+ 运行期记录器 + 确定性复核 |
| `skills/china-story-generation/references/step-contracts.md` | 生成侧 C00–C06 契约（输入/动作/产出/依据/停机/审计字段） |
| `skills/china-story-evaluation/references/step-contracts.md` | 评测侧 E00–E05 契约 |
| `scripts/step_audit_check.py` | 复核 CLI：`--evidence` / `--index` / `--require-complete` |
| `scripts/make_step_trace_samples.py` | 用真实代码路径产出 4 份脱敏追溯样例 |
| `tests/test_step_audit.py` | 21 项回归测试（契约 + 两条链路真实接线） |
| `docs/SKILL_STEP_GAP_ANALYSIS.md` | 差距报告（GAP-01–GAP-10，含证据与处置） |
| `docs/SKILL_METHOD_EVIDENCE_MATRIX.md` | 步骤 × 方法依据矩阵（含"该来源对本步的启发"） |
| `docs/chinastory_v6.1/step_trace_samples/` | 4 份样例 + README（说明哪些是替身） |
| `docs/chinastory_v6.1/PR_步骤契约与质量门.md` | PR 草稿（未推送） |

## 2. 修改文件

| 文件 | 变更 | 为什么改 |
|---|---|---|
| `tools/story_post_gen.py` | 新增 `step_audit` 输出（所有返回分支）；C00–C06 逐点记录；`always_on` 并入必需技能并硬校验；空模型输出显式失败 | GAP-02/03/04：步骤没有运行态、常开规则可被静默丢掉 |
| `utils/skill_registry.py` | 新增 `resolve_always_on()`；`get_active_skills_for_query` 为 `always_on` 预留额度，不再被预算裁掉 | GAP-02：`always_on` 此前可整条消失且无报错 |
| `api/evaluation_part3.py` | 新增 `evaluate_part3_with_audit()`（返回结果 + E00–E05 审计）与 `deterministic_checks()`；E03 增加跨度核对，不一致转 blocking issue | GAP-06/07：评测侧有校验工具但没接线，偏移不一致会被静默接受 |
| `skills/china-story-generation/SKILL.md` | §2 增加步骤契约指引（C00–C06 与 `step_audit`） | 让卡片与代码指向同一套编号 |
| `skills/china-story-evaluation/SKILL.md` | 开头增加步骤契约指引（E00–E05） | 同上；并声明 `EvaluationResult` 不新增字段 |
| `tests/test_six_genre_p0.py` | `test_skill_load_diagnostics_are_complete_and_safe` 断言改为"体裁卡第一张 + always_on 全部加载" | 行为按 GAP-02 有意改变，旧断言已不成立（不是放宽，是改对） |
| `README_基线说明.md` | 版本状态表增加本轮条目与复核命令 | 保持基线说明与实际一致 |

## 3. 行为变化（会被外部观察到的）

1. **生成结果多一个 `step_audit` 字段**（新增键，不删不改既有键）。
2. **生成提示多两张常开卡**（`intl_comm` + `evidence_user_materials`），
   因此 `skill_load.loaded_files` 由 1 项变成 3 项；`skill_chars` 相应变大（仍在预算内：post 约 1.6 万字符 < 2.4 万）。
3. **`always_on` 不可用时生成直接失败**：`generation_status = SKILL_ALWAYS_ON_UNAVAILABLE`。
   这是有意的收紧 —— 少一张证据卡继续写，比停下来更危险。
4. **模型空输出**从"当作空成稿返回"改为 `OUTPUT_INVALID`。
5. **评测 `evidence_spans` 偏移不一致**不再静默通过，会生成 `span-mismatch` blocking issue
   并把状态落到 `REVISION_RECOMMENDED`；审计终态 `FAILED`。

## 4. 明确**没有**做的事（避免误读为已实现）

| 项 | 状态 | 原因 |
|---|---|---|
| 生成工具驱动 `WorkflowStateMachine`（Gate A/B/C 真裁决） | **未做** | 生成工具是无状态函数，被 CLI / Agent 工具环 / API 共用；强接会改所有调用方语义，并触碰 `human_review` / `revision_loop` 的"不碰状态机"约定。建议单独立项，在 `api/main.py` 层收口（GAP-01） |
| 分数阈值型质量门（自动通过/自动拒绝） | **未做** | Rubric §19 阈值仍是 TBD，私设阈值等于编造标准（GAP-08） |
| JSON Schema 结构校验接线到运行时 | **未做** | 仍由后端 `utils/validate_evaluation.py` 执行，本次不引入 `jsonschema` 运行时依赖 |
| `thread` / `visual_story` / `caption_only` 输出结构 | **未做** | 已有方法定义，无 Schema/验证器；已在 C00 以 `UNSUPPORTED_GENERATION` 明确拒绝（GAP-10） |
| Gate C / 人工批准 | **不做** | 属现有边界，`api/human_review.py` 明确不碰 |

## 5. 验证记录

| 验证 | 命令 | 结果 |
|---|---|---|
| 全量回归 | `pytest tests/ -q` | **633 passed**（本轮前 612，新增 21） |
| 依据锚点 | `python scripts/step_audit_check.py --evidence` | 通过：2 条管线 / 40 个锚点 |
| 样例自洽 | `python scripts/step_audit_check.py docs/…/step_trace_samples/*.json` | 4/4 通过（退出码 0） |
| 严格模式 | `… generation_ok.json --require-complete` | 通过（`verdict=COMPLETE`） |
| 卡片预算 | 单卡 ≤ 16000 字符 | generation SKILL 8032 / evaluation SKILL 6089 / post.md 12881，均未截断 |

## 6. 已知失败与限制（如实记）

- `qwen` API key 被平台吊销（401），真实模型生成与端到端评测**仍不可跑**；
  本轮所有样例均为替身，已在样例 `_note` 与差距报告 §3 标注。
- 评测侧 I-01–I-06 接线项仍未完成（上一阶段遗留），与本轮步骤契约不冲突。
