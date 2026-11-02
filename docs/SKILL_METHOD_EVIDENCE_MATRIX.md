# 步骤 × 方法依据矩阵（Generation C00–C06 / Evaluation E00–E05）

> 这张表回答一个问题：**每一步凭什么这么设计？**
> 「依据」列全部是仓库内的可核对位置，格式为 `文件::锚点`；
> 锚点由 `utils/step_audit.py` 声明、由 `scripts/step_audit_check.py --evidence` 逐条校验
> （当前 13 步 / 40 个锚点全部命中），因此**依据不会随文档改写而悄悄失效**。
>
> 「启发」列只写该来源对**这一步**的具体约束，不重复 SKILL.md 的方法内容。

---

## 一、Generation（生成）

| 步骤 | 依据来源（文件::锚点） | 该来源对本步的启发 | 代码落点 | 质量门 / 断言 |
|---|---|---|---|---|
| **C00** 选择与输入契约校验 | `skills/china-story-generation/SKILL.md::## 1. 输入契约（调用方必须提供）` | 生成侧只消费 Define 阶段确认过的 `TaskContext`，不自建任务；缺字段应报缺项而不是猜 | `run_story_post_generation` 入参 → `resolve_selection` | 非法 genre/format 在**检索之前**拒绝；不落回 `post` |
| | `utils/genre_contracts.py::def check_selection(` | 六体裁→skill_id→方法卡→format 必须来自**单一事实源**，否则"路由说 A、注入 B" | `utils/genre_contracts.py`、`tools/genre_router.py` | 与 `config/skills.yaml` 一致性由 `consistency_report()` 强制 |
| | `skills/china-story-generation/references/step-contracts.md::### C00` | 本步的完整契约（输入/产出/停机/审计字段） | — | `step_audit` 记 `resolved_genre/resolved_format/routing_source` |
| **C01** 证据门禁（Gate B） | `skills/china-story-generation/SKILL.md::[G-08] 证据门禁（事实硬门禁）` | 门禁未过**只输出阻塞原因**，不产出貌似完整的成稿；不在同一轮重复请求门禁 | 生成主流程的 3 个早退分支 | 空证据 / 适配失败 / 未对齐 → `step_audit.C01=BLOCKED` |
| | `api/evidence_adapter.py::def build_evidence_pack(` | 只允许**一份** canonical EvidencePack；下游用兼容投影 | `_legacy_evidence_projection` | 投影后不得成为第二事实源（`pack_digest` 入审计） |
| | `skills/.../step-contracts.md::### C01` | 停机的三种情形与补救动作 | — | `gate_b` 取值枚举化 |
| **C02** 方法加载与体裁隔离 | `skills/china-story-generation/SKILL.md::[G-10] 证据共享规则始终激活` | 立场与证据规则必须每轮注入，**不参与预算竞争** | `resolve_always_on()` + 生成链路并集 | 缺卡 → `SKILL_ALWAYS_ON_UNAVAILABLE` 硬失败 |
| | `utils/skill_registry.py::def load_required_skills(` | 缺失/空/禁用/截断/超预算一律**显式失败**，不得注入占位串继续裸跑 | `load_required_skills(*skill_ids, …)` | `loaded_method_id` 必须来自真实读到的文件 |
| | `config/skills.yaml::always_on:` | 常开清单的权威位置（`intl_comm` / `evidence_user_materials`） | 注册表配置 | `always_on_required == always_on_loaded` |
| | `skills/.../step-contracts.md::### C02` | 体裁卡必须**恰好一张** | 主流程 `genre_cards != [contract.method_path]` | 串卡 → `SKILL_CONTRACT_VIOLATION` |
| **C03** 提示构造 | `tools/story_post_gen.py::def build_story_genre_prompt(` | 六体裁共用同一套证据投影，结构交给体裁卡 | 三套 builder（post/news/genre） | 审计记 `prompt_file / prompt_chars / prompt_sha256` |
| | `skills/china-story-generation/SKILL.md::**体裁隔离（不可串味）**：` | 不并行加载互相竞争的体裁模板 | 单卡加载 + 单 builder 分支 | 断言 prompt 中只出现本体裁卡 |
| | `skills/.../step-contracts.md::### C03` | 不新增证据、不混入其他体裁 | — | — |
| **C04** 成稿生成 | `tools/story_post_gen.py::def _llm_text(` | 模型调用是**唯一**生成入口，便于替换与审计 | `_llm_text(prompt)` | 空输出 → `FAILED` |
| | `skills/china-story-generation/SKILL.md::宁短勿编；不抄教材范文；` | 模型只写不核验；不把引用链接当已验证支持 | prompt 红线段 | 审计记 `output_chars / output_sha256` |
| | `skills/.../step-contracts.md::### C04` | 本步不做事实核验 | — | 事实判定留给 Part 1 |
| **C05** 输出契约校验 | `tools/story_post_gen.py::def _validate_contract_output(` | 缺必需正文即 `OUTPUT_INVALID`，**不得**把原文当合格成稿 | `_parse_json_output` + `_validate_contract_output` | 解析失败/缺正文 → `FAILED` |
| | `utils/genre_contracts.py::OUTPUT_WIRE = "wire"` | 三种输出契约（`post5w`/`wire`/`body`）按体裁绑定 | `contract.output_contract` | 契约与体裁不匹配即失败 |
| | `skills/.../step-contracts.md::### C05` | 容错仅限代码围栏与前后散文 | `_parse_json_output` 正则 | 审计记 `top_level_keys` |
| **C06** 自检与人工移交 | `skills/china-story-generation/SKILL.md::## 2.5 输出前自检（六问）` | 六问要逐项回答，不能一句"已自检" | `_finish_success_audit` 的 `self_check` | 机器判不了的项标 `PENDING_HUMAN`，不写 PASS |
| | `api/workflow.py::GATE_STAGE = {"A": "DEFINE", "B": "GROUND", "C": "REVISE_AUDIT"}` | Gate C 属 REVISE_AUDIT→APPROVE，**不在生成 Skill 内** | 结果只给 `human_review=PENDING` | `publishable=False` 写死进审计 |
| | `skills/.../step-contracts.md::### C06` | 移交时才导出完整审计 | `audit.finish()` | `verdict=COMPLETE` 才算七步全跑 |

---

## 二、Evaluation（评测 Part 3）

| 步骤 | 依据来源（文件::锚点） | 该来源对本步的启发 | 代码落点 | 质量门 / 断言 |
|---|---|---|---|---|
| **E00** 前置检查与 Part 1 门禁 | `skills/china-story-evaluation/SKILL.md::## 1. 调用前置检查（MUST）` | 缺上下文返回 `INSUFFICIENT_CONTEXT` 并列缺项；**不得**凭国籍/主题补受众 | `evaluate_part3_with_audit` 前两支 | 空正文 → `E00=BLOCKED` |
| | `api/evaluation.py::if part1.status != PART1_PASS:` | Part 1 未过不进常规 Part 3，返回 `RETURN_TO_PART1` | `evaluate_content_version` | 不允许"带着阻断打分" |
| | `skills/china-story-evaluation/references/step-contracts.md::### E00` | 缺项清单是产出的一部分 | — | 审计记 `part1_status / content_sha256` |
| **E01** 资料加载 | `skills/china-story-evaluation/SKILL.md::## 2. 加载资料（按需读取）` | 必读 Rubric/跨文化/本体裁专项/修改指令；单装 Skill 不含代码 | 参考文件清单 | Rubric 版本进审计 |
| | `api/rubric_loader.py::def load_rubric(` | 唯一定义评分准则来自 `eval/…RUBRIC_v2.1.md`，Skill 不自造权重 | `load_rubric()` | 版本不受支持即停止 |
| | `skills/.../step-contracts.md::### E01` | 加载结果要能说清"读了哪些" | — | `dimensions_expected=6` |
| **E02** 逐维评价 | `skills/china-story-evaluation/SKILL.md::## 3. 逐维度评价（六维均独立，不平均）` | 六维独立、1–5 整数、不跨维代替、无总分 | `_validate_dimensions` | 缺维/重复/非整数/越界 → 抛错，不修补 |
| | `api/evaluation_part3.py::def _validate_dimensions(` | 不合法输出必须失败（fail-closed），不能用启发式补分 | 同上 | `Part3Error` + 审计 `E02=FAILED` |
| | `skills/.../step-contracts.md::### E02` | 裁判未配置时就是 `BLOCKED`，不给假分 | `judge is None` 分支 | `E02=BLOCKED(judge_unconfigured)` |
| **E03** 定位与最小修改指令 | `skills/china-story-evaluation/SKILL.md::`content.text[start:end] == span.text` 必须成立` | 偏移用码点下标、逐字符精确匹配；不得捏造偏移 | `_span_check` | 不匹配 → 转 blocking issue |
| | `utils/validate_evaluation.py::def validate_result(` | 跨度与哈希是后端确定性校验的一部分 | `deterministic_checks` | `spans_exact` 作为 E05 检查项 |
| | `skills/.../step-contracts.md::### E03` | 扣分必须变成可执行的修改指令 | `_collect_issues` | 审计记 `spans_checked / suggestions_count` |
| **E04** 输出结构与状态 | `skills/china-story-evaluation/SKILL.md::## 4. 输出结构与状态（兼容优先）` | 保留 v2.1 顶层字段；`overall_score` 恒 `null`；`human_review` 恒 `PENDING` | 结果构造 | `status_combo_consistent` |
| | `api/evaluation_part3.py::FORBIDDEN_STATUSES = frozenset({"APPROVED", "PUBLISHED"})` | 评测永不授予批准 | 同上 | 禁止状态一出现即判定失败 |
| | `skills/.../step-contracts.md::### E04` | 新字段只能"可选 + 兼容映射" | sidecar 审计 | 不改 `EvaluationResult` 契约 |
| **E05** 机器校验与校准留痕 | `skills/china-story-evaluation/SKILL.md::## 5. 公正性、稳定性与校准（实验要求）` | 未校准必须 `UNCALIBRATED`，**禁止伪造 confidence** | `confidence` 由裁判给，Skill 不自造 | 审计记 `deterministic_checks` 结果 |
| | `utils/validate_evaluation.py::SCHEMA_PATH = PROJECT_ROOT / "eval" / "contracts" / "evaluation-result-v6.1.schema.json"` | Schema 校验由后端跑，Skill 不自评 | `deterministic_checks()` + 后端 CLI | 五项检查全绿才算 E05 OK |
| | `skills/.../step-contracts.md::### E05` | 校验不过 → 重试或转人工，**不得**进入自动 Revision | `audit.failed("E05", …)` | `verdict=FAILED` |

---

## 三、这张表怎么用

1. **改步骤前先看依据**：想动 C01 的停机条件，先读 `[G-08]` 与 `step-contracts.md` 的 C01 节；
   要改就得同时改契约、锚点与测试，否则 `--evidence` 会报错——这不是形式主义，是防止再次出现
   "文档说调用 A、代码调用 B"。
2. **汇报时直接引这一列**：「依据」列即"这个设计来自哪里"，可当场翻到具体文件行。
3. **加新步骤时**：在 `utils/step_audit.py` 增 `StepSpec`（含 ≥1 个真实锚点）→ 在
   `step-contracts.md` 写契约 → 补测试。三步缺一不可，否则 `tests/test_step_audit.py` 会红。

> 说明：本表**不含**任何未核实的来源。`docs/evaluation/history/` 里的 E01–E10 研究报告作为
> 评测能力的**历史修改来源**，已在 `SKILL.md` §7 声明，且明确"不参与每篇文章的推理加载"，
> 因此不进入本矩阵的运行时依据列。
