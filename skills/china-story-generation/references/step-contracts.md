# Generation 步骤契约 C00–C06

> 用途：把 `SKILL.md` §2 的流程叙述，固化成**可执行、可审计、可追溯**的七步契约。
> 每一节就是一个契约单元，编号即身份；代码里的 `utils/step_audit.py` 用同一套编号记录运行态，
> 并在每次生成结果里输出 `step_audit`。
>
> 阅读顺序：本文件说明"每一步要什么、产出什么、依据什么、什么时候必须停"；
> 具体写法细节仍在 `SKILL.md` 与各体裁卡里，本文件不重复、也不改变它们。
>
> **本文档不改任何气质裁卡的表达方法**。它约束的是执行链：谁能写、写之前必须有什么、
> 写完之后必须通过什么检查、最终交给谁。

统一约定：

| 字段 | 含义 |
|---|---|
| 输入 | 该步消费的对象（必须已存在，不得在步内自行补造） |
| 产出 | 该步必须给出的东西；没有产出等于该步失败 |
| 依据 | 方法来源（本仓库内可核对的位置） |
| 停机条件 | 满足即停止后续步骤，只回报阻塞原因与补救动作 |
| 审计 status | `OK` / `SKIP` / `BLOCKED` / `FAILED` / `NOT_RUN` |

---

### C00 选择与输入契约校验

- **输入**：用户请求（主题、平台、语种、`genre`、`format`）、Define 阶段的 `TaskContext`。
- **动作**：
  1. `genre` / `format` **显式值优先**，只在显式缺省时才用关键词推断；
  2. `genre` 必须属于 `post / news / feature / indepth / script / faq`；
  3. `format` 必须已登记，且不能属于别的体裁（组合冲突即拒绝）；
  4. `format` 若只有方法定义、尚无独立输出结构（如 `thread` / `visual_story` / `caption_only`），
     报 `UNSUPPORTED_GENERATION`，**不得**用 `social_post` 的字段冒充。
- **产出**：`resolved_genre`、`resolved_format`、`routing_source`（`user_override` / `format` / `keyword`）。
- **依据**：`SKILL.md` §1 输入契约、§2.1 体裁路由；`utils/genre_contracts.py` 单一事实源。
- **停机条件**：`INVALID_GENRE` / `INVALID_FORMAT` / `GENRE_FORMAT_CONFLICT` / `UNSUPPORTED_GENERATION`
  → 在检索前就拒绝，不进入模型调用。
- **审计 detail**：`requested_genre`、`requested_format`、`resolved_genre`、`resolved_format`、`routing_source`、`output_contract`。

---

### C01 证据门禁（Gate B）

- **输入**：`EvidencePack`（canonical，唯一事实源）与检索/上传论据。
- **动作**：
  1. 用户资料 + 本地库论据合并后，必须能构成**一份** canonical `EvidencePack`；
     下游只消费由它派生的兼容投影，不允许出现第二个事实源；
  2. 证据为空 → 停；适配失败 → 停；主题与证据不对齐 → 停；
  3. 停机时**只输出阻塞原因与补救动作**（补资料 / 换主题 / 走 Gate B 例外），
     不输出任何貌似完整的成稿。
- **产出**：`evidence_used`（兼容投影）、`evidence_stats`（user/local 计数）、`_evidence_pack`、对齐判定。
- **依据**：`SKILL.md` §2.0 [G-08]；`api/evidence_adapter.py`；v2.1 架构 GROUND + Gate B。
- **停机条件**：空证据 / `canonical_evidence_invalid` / `alignment` 不通过。
- **审计 detail**：`evidence_user`、`evidence_local`、`pack_digest`、`gate_b`、`aligned`。

---

### C02 方法加载与体裁隔离

- **输入**：`resolved_genre`、`config/skills.yaml` 注册表、`always_on` 清单。
- **动作**：
  1. 严格加载该体裁的**唯一**方法卡；缺失 / 空文件 / 被禁用 / 读取失败 / 被截断 / 超总预算
     一律显式失败（不得注入 `"(no skill loaded)"` 继续裸跑）；
  2. 校验实际注入的体裁卡路径**恰好等于**契约里的那一张（防跨体裁串卡）；
  3. `always_on` 规则（立场与证据硬约束）必须随轮注入，且不参与 `max_active_skills` 预算竞争。
- **产出**：`skill_load` 诊断块（requested / loaded / files / chars / sha256 / status）。
- **依据**：`SKILL.md` §2.0 [G-10]、§2.1 体裁表；`utils/skill_registry.py` `load_required_skills`。
- **停机条件**：`SKILL_LOAD_FAILED` / `SKILL_UNAVAILABLE` / `SKILL_CONTRACT_VIOLATION`。
- **审计 detail**：`requested_method_id`、`loaded_method_id`、`loaded_files`、`method_sha256`、`always_on_requested`、`always_on_loaded`。

---

### C03 提示构造（证据投影 + 方法注入）

- **输入**：C01 的证据投影、C02 的方法正文、人物设定与平台参数。
- **动作**：按体裁选择提示模板，把方法正文与证据清单拼成一次请求；**不新增证据**、不混入其他体裁卡、
  不把知识库通用背景当事实写进要求。
- **产出**：完整提示串（记录 `prompt_file`、`prompt_sha256`、字符数）。
- **依据**：`SKILL.md` §2.2–§2.4；`tools/story_post_gen.py` 三套 prompt builder。
- **停机条件**：无（构造失败即抛错，按 `FAILED` 记）。
- **审计 detail**：`prompt_file`、`prompt_chars`、`prompt_sha256`。

---

### C04 成稿生成（LLM）

- **输入**：C03 的提示串。
- **动作**：调用模型产出候选稿。模型在本步**只能写**，不能宣称事实已核验、不能自动发布。
- **产出**：模型原始输出（记录 `output_chars`、`output_sha256`）。
- **依据**：`SKILL.md` §5 红线（宁短勿编、不把引用链接当已验证支持）。
- **停机条件**：空输出 → `FAILED`。
- **审计 detail**：`output_chars`、`output_sha256`。

---

### C05 输出契约校验

- **输入**：C04 的原始输出。
- **动作**：
  1. 必须是可解析 JSON（含 ```json 围栏与前后散文的容错），否则 `OUTPUT_INVALID`；
  2. 必须含该体裁的必需正文（`post5w` → `post`，`wire` → `article`，`body` → `body`）；
  3. 任一不满足即拒绝返回，**不得**把整段原始文本塞进正文冒充成功。
- **产出**：解析后的结构体 + `output_contract`。
- **依据**：`SKILL.md` §4 输出契约；`utils/genre_contracts.py` 的 `OUTPUT_*` 常量。
- **停机条件**：`OUTPUT_INVALID`。
- **审计 detail**：`output_contract`、`parse_status`、`required_body`。

---

### C06 自检与人工审核移交

- **输入**：C05 通过的成稿。
- **动作**：
  1. 执行 `SKILL.md` §2.5 输出前六问自检（体裁卡唯一、门禁与 always_on 已注入、可回指、
     无自造事实、母稿与目标稿一致、声明仅供人工审核）；
  2. 写出 `human_review=PENDING`，声明"仅供人工审核，不自动发布"；
  3. 附 `step_audit`，把 C00–C05 的实际执行状态一并交出，便于复核。
- **产出**：可审核草稿 + `step_audit`（`verdict=COMPLETE` 才代表七步全部真实执行）。
- **依据**：`SKILL.md` §2.5、§4；`api/workflow.py`（Gate C 属 REVISE_AUDIT→APPROVE，不在本 Skill 内）。
- **停机条件**：无（本步不阻断，只移交）。
- **审计 detail**：`human_review`、`publishable`（恒 `false`）、`self_check`（六问逐项布尔）。

---

## 与失败状态枚举的对应

| 失败码 | 停在哪一步 | 说明 |
|---|---|---|
| `INVALID_GENRE` / `INVALID_FORMAT` / `GENRE_FORMAT_CONFLICT` | C00 | 选择本身不合法 |
| `UNSUPPORTED_GENERATION` | C00 | 格式只有方法、无输出结构 |
| `SKILL_LOAD_FAILED` / `SKILL_UNAVAILABLE` / `SKILL_CONTRACT_VIOLATION` | C02 | 方法卡或 always_on 不可用 |
| `OUTPUT_INVALID` | C05 | 输出不可解析或缺必需正文 |
| `EVIDENCE_*` / 对齐失败 | C01 | 证据门禁未通过 |

> 只有 `step_audit.verdict == "COMPLETE"` 且 `generation_status == "OK"` 时，才算"七步都执行了"。
> 其余情况下，`step_audit.not_run` 会明确列出哪些步骤根本没跑——这就是可追溯的最小证据。
