"""步骤审计：把 Skill 的每一步落成「机器可校验 + 可溯源」的记录。

为什么需要这个模块
------------------
此前两套 Skill 只有**流程叙述**（SKILL.md 里的 §2 步骤），没有「这一步到底跑没跑、
依据是什么、产出是什么」的机器可读证据。于是出现两类问题：

1. 文档说什么 ≠ 代码做什么（例如 §2.0 写了 `load_story_knowledge` 前置门禁，
   实际生成链路早已不调用它）；
2. 失败时只知道"失败了"，无法区分"跳过了""被门禁拦住了""跑错了"。

本模块只做三件事，都是纯确定性的（不调用模型、不联网、不改业务对象）：

* ``STEP_SPECS``：C00–C06 / E00–E05 每一步的编号、名称、所属阶段、必做性、
  一句话契约，以及**方法依据锚点**（`文件::锚点字符串`，可被 ``evidence_problems()``
  校验——锚点不存在即视为"依据失真"）；
* ``StepAudit``：运行期逐条记录状态，导出 ``dict`` 时补齐未记录的必做步骤为
  ``NOT_RUN``，并给出唯一终态判定 ``verdict``；
* ``check_audit()``：对一份已导出的审计 dict 做确定性复核（重复记录、乱序、
  终态与状态不自洽等），供 CI 与 ``scripts/step_audit_check.py`` 使用。

设计约束（本任务书要求）
------------------------
* 不修改 ``Claim`` / ``EvidencePack`` / ``Coverage`` / ``EvaluationResult`` 任何契约；
* 审计是**伴生数据**（sidecar），不塞进上面这些模型；
* 不允许"看起来完整"——没记录的必做步骤就是 ``NOT_RUN``，不会被补成成功。
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

# --------------------------------------------------------------------------- #
# 状态与终态（唯一枚举源，禁止在其他模块里另造同义字符串）
# --------------------------------------------------------------------------- #
STATUS_OK = "OK"
STATUS_SKIP = "SKIP"
STATUS_NOT_RUN = "NOT_RUN"
STATUS_BLOCKED = "BLOCKED"
STATUS_FAILED = "FAILED"

ALLOWED_STATUSES: Sequence[str] = (
    STATUS_OK,
    STATUS_SKIP,
    STATUS_NOT_RUN,
    STATUS_BLOCKED,
    STATUS_FAILED,
)

VERTICT_COMPLETE = "COMPLETE"
VERDICT_BLOCKED = "BLOCKED"
VERDICT_FAILED = "FAILED"
VERDICT_INCOMPLETE = "INCOMPLETE"

ALLOWED_VERDICTS: Sequence[str] = (
    VERTICT_COMPLETE,
    VERDICT_BLOCKED,
    VERDICT_FAILED,
    VERDICT_INCOMPLETE,
)

PIPELINE_GENERATION = "generation"
PIPELINE_EVALUATION = "evaluation"


# --------------------------------------------------------------------------- #
# 步骤契约（编号 = 唯一身份；顺序 = 执行顺序）
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class StepSpec:
    """一步的静态契约。

    ``evidence`` 是 ``"<仓库相对路径>::<锚点>"`` 形式：锚点必须在该文件里真实出现，
    否则 ``evidence_problems()`` 会报错。这是"每一步有依据"的可校验形式。
    """

    step_id: str
    name: str
    pipeline: str
    stage: str
    required: bool
    contract: str
    evidence: Tuple[str, ...]


GENERATION_STEPS: Tuple[StepSpec, ...] = (
    StepSpec(
        step_id="C00",
        name="选择与输入契约校验",
        pipeline=PIPELINE_GENERATION,
        stage="DEFINE",
        required=True,
        contract=(
            "解析 genre/format（显式优先），校验 TaskContext 必需字段；"
            "非法 genre / 不存在的 format / 组合冲突一律显式拒绝，不回落 post。"
        ),
        evidence=(
            "skills/china-story-generation/references/step-contracts.md::### C00",
            "skills/china-story-generation/SKILL.md::## 1. 输入契约（调用方必须提供）",
            "utils/genre_contracts.py::def check_selection(",
        ),
    ),
    StepSpec(
        step_id="C01",
        name="证据门禁（Gate B）",
        pipeline=PIPELINE_GENERATION,
        stage="GROUND",
        required=True,
        contract=(
            "从 canonical EvidencePack 与对齐结果取得可写授权；"
            "证据为空 / 适配失败 / 主题不对齐 => 只输出阻塞原因，不产出成稿。"
        ),
        evidence=(
            "skills/china-story-generation/references/step-contracts.md::### C01",
            "skills/china-story-generation/SKILL.md::[G-08] 证据门禁（事实硬门禁）",
            "api/evidence_adapter.py::def build_evidence_pack(",
        ),
    ),
    StepSpec(
        step_id="C02",
        name="方法加载与体裁隔离",
        pipeline=PIPELINE_GENERATION,
        stage="PLAN",
        required=True,
        contract=(
            "严格加载体裁方法卡 + always_on 常开规则；缺失/空/禁用/截断/超预算一律失败，"
            "且注入的体裁卡必须恰好是本体裁那一张。"
        ),
        evidence=(
            "skills/china-story-generation/references/step-contracts.md::### C02",
            "skills/china-story-generation/SKILL.md::[G-10] 证据共享规则始终激活",
            "utils/skill_registry.py::def load_required_skills(",
            "config/skills.yaml::always_on:",
        ),
    ),
    StepSpec(
        step_id="C03",
        name="提示构造（证据投影 + 方法注入）",
        pipeline=PIPELINE_GENERATION,
        stage="PLAN",
        required=True,
        contract=(
            "用同一份 EvidencePack 的兼容投影构造提示，注入方法卡正文，"
            "不引入第二事实源，不跨体裁串卡。"
        ),
        evidence=(
            "skills/china-story-generation/references/step-contracts.md::### C03",
            "tools/story_post_gen.py::def build_story_genre_prompt(",
            "skills/china-story-generation/SKILL.md::**体裁隔离（不可串味）**：",
        ),
    ),
    StepSpec(
        step_id="C04",
        name="成稿生成（LLM）",
        pipeline=PIPELINE_GENERATION,
        stage="CREATE",
        required=True,
        contract=(
            "调用模型产出候选稿；空输出即失败。模型不得新增证据外事实，"
            "不得自动发布。"
        ),
        evidence=(
            "skills/china-story-generation/references/step-contracts.md::### C04",
            "tools/story_post_gen.py::def _llm_text(",
            "skills/china-story-generation/SKILL.md::宁短勿编；不抄教材范文；",
        ),
    ),
    StepSpec(
        step_id="C05",
        name="输出契约校验",
        pipeline=PIPELINE_GENERATION,
        stage="CREATE",
        required=True,
        contract=(
            "JSON 可解析 + 该体裁必需正文存在；任一不满足即 OUTPUT_INVALID，"
            "不得把原始文本当合格成稿。"
        ),
        evidence=(
            "skills/china-story-generation/references/step-contracts.md::### C05",
            "tools/story_post_gen.py::def _validate_contract_output(",
            "utils/genre_contracts.py::OUTPUT_WIRE = \"wire\"",
        ),
    ),
    StepSpec(
        step_id="C06",
        name="自检与人工审核移交",
        pipeline=PIPELINE_GENERATION,
        stage="REVISE_AUDIT",
        required=True,
        contract=(
            "执行输出前自检，写出 human_review=PENDING 与可追溯字段，"
            "明确仅供人工审核；Gate C 不在本 Skill 内。"
        ),
        evidence=(
            "skills/china-story-generation/references/step-contracts.md::### C06",
            "skills/china-story-generation/SKILL.md::## 2.5 输出前自检（六问）",
            "api/workflow.py::GATE_STAGE = {\"A\": \"DEFINE\", \"B\": \"GROUND\", \"C\": \"REVISE_AUDIT\"}",
        ),
    ),
)


EVALUATION_STEPS: Tuple[StepSpec, ...] = (
    StepSpec(
        step_id="E00",
        name="前置检查与 Part 1 门禁",
        pipeline=PIPELINE_EVALUATION,
        stage="Part 3 / Precheck",
        required=True,
        contract=(
            "读齐 evaluation_id/task/version/rubric/受众/正文/part1_status；"
            "Part 1 未通过即 RETURN_TO_PART1，不产出六维分数。"
        ),
        evidence=(
            "skills/china-story-evaluation/references/step-contracts.md::### E00",
            "skills/china-story-evaluation/SKILL.md::## 1. 调用前置检查（MUST）",
            "api/evaluation.py::if part1.status != PART1_PASS:",
        ),
    ),
    StepSpec(
        step_id="E01",
        name="资料加载（Rubric 与专项检查）",
        pipeline=PIPELINE_EVALUATION,
        stage="Part 3 / Load",
        required=True,
        contract=(
            "加载正式 Rubric v2.1 的 D1–D6 行为锚点、跨文化检查、本体裁专项检查与"
            "修改指令规则；Rubric 不可读则停止评分。"
        ),
        evidence=(
            "skills/china-story-evaluation/references/step-contracts.md::### E01",
            "skills/china-story-evaluation/SKILL.md::## 2. 加载资料（按需读取）",
            "api/rubric_loader.py::def load_rubric(",
        ),
    ),
    StepSpec(
        step_id="E02",
        name="逐维评价（D1–D6 独立评分）",
        pipeline=PIPELINE_EVALUATION,
        stage="Part 3 / Score",
        required=True,
        contract=(
            "六维各自对照 BARS 给 1–5 整数分，维度唯一、不平均、不跨维代替；"
            "裁判输出不合法即失败，不做静默修补。"
        ),
        evidence=(
            "skills/china-story-evaluation/references/step-contracts.md::### E02",
            "skills/china-story-evaluation/SKILL.md::## 3. 逐维度评价（六维均独立，不平均）",
            "api/evaluation_part3.py::def _validate_dimensions(",
        ),
    ),
    StepSpec(
        step_id="E03",
        name="原文定位与最小修改指令",
        pipeline=PIPELINE_EVALUATION,
        stage="Part 3 / Locate",
        required=True,
        contract=(
            "evidence_spans 用码点下标且 content.text[start:end] == span.text；"
            "扣分必须转成定位明确、可复核的最小修改指令。"
        ),
        evidence=(
            "skills/china-story-evaluation/references/step-contracts.md::### E03",
            "skills/china-story-evaluation/SKILL.md::`content.text[start:end] == span.text` 必须成立",
            "utils/validate_evaluation.py::def validate_result(",
        ),
    ),
    StepSpec(
        step_id="E04",
        name="输出结构与状态",
        pipeline=PIPELINE_EVALUATION,
        stage="Part 3 / Output",
        required=True,
        contract=(
            "保留 v2.1 顶层字段；overall_score 固定 null、human_review=PENDING、"
            "永不输出 APPROVED。"
        ),
        evidence=(
            "skills/china-story-evaluation/references/step-contracts.md::### E04",
            "skills/china-story-evaluation/SKILL.md::## 4. 输出结构与状态（兼容优先）",
            "api/evaluation_part3.py::FORBIDDEN_STATUSES = frozenset({\"APPROVED\", \"PUBLISHED\"})",
        ),
    ),
    StepSpec(
        step_id="E05",
        name="机器校验与校准留痕",
        pipeline=PIPELINE_EVALUATION,
        stage="Part 3 / Audit",
        required=True,
        contract=(
            "Schema + 确定性校验（六维唯一、分值、跨度、哈希、状态组合）由后端执行；"
            "未校准须标 UNCALIBRATED，不得伪造 confidence。"
        ),
        evidence=(
            "skills/china-story-evaluation/references/step-contracts.md::### E05",
            "skills/china-story-evaluation/SKILL.md::## 5. 公正性、稳定性与校准（实验要求）",
            "utils/validate_evaluation.py::SCHEMA_PATH = PROJECT_ROOT / \"eval\" / \"contracts\" / \"evaluation-result-v6.1.schema.json\"",
        ),
    ),
)


STEP_SPECS_BY_PIPELINE: Dict[str, Tuple[StepSpec, ...]] = {
    PIPELINE_GENERATION: GENERATION_STEPS,
    PIPELINE_EVALUATION: EVALUATION_STEPS,
}

#: ``{"C00": StepSpec, ...}`` 便于按编号查契约。
STEP_SPECS: Dict[str, StepSpec] = {
    spec.step_id: spec
    for specs in STEP_SPECS_BY_PIPELINE.values()
    for spec in specs
}


def step_ids(pipeline: str) -> Tuple[str, ...]:
    return tuple(s.step_id for s in STEP_SPECS_BY_PIPELINE[pipeline])


def spec_for(step_id: str) -> StepSpec:
    return STEP_SPECS[step_id]


# --------------------------------------------------------------------------- #
# 摘要工具：让"输入/产出是什么"可以逐条对齐，而不是靠自然语言描述
# --------------------------------------------------------------------------- #
def digest(value: Any) -> str:
    """稳定摘要：字符串取原文，其他对象转稳定 JSON 后 sha256，返回前 16 位。"""
    if isinstance(value, str):
        payload = value
    else:
        payload = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def file_digest(path: Path) -> str:
    try:
        return digest(Path(path).read_text(encoding="utf-8"))
    except OSError:
        return ""


# --------------------------------------------------------------------------- #
# 运行期记录器
# --------------------------------------------------------------------------- #
class StepAuditError(ValueError):
    """审计记录本身违规（未知步骤、状态不合法、重复记录）。"""


@dataclass
class StepAudit:
    """一次运行的步骤记录器。

    用法::

        audit = StepAudit(PIPELINE_GENERATION, context={"genre": "post"})
        audit.ok("C00", resolved_genre="post", source="user_override")
        ...
        result["step_audit"] = audit.finish()

    重复记录同一步骤会抛错（防止"一步跑了两次、其中一次失败"被后一次覆盖）。
    """

    pipeline: str
    context: Dict[str, Any] = field(default_factory=dict)
    records: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.pipeline not in STEP_SPECS_BY_PIPELINE:
            raise StepAuditError(f"未知 pipeline：{self.pipeline}")

    # -- 记录 ---------------------------------------------------------------
    def record(self, step_id: str, status: str, reason: str = "", **detail: Any) -> None:
        spec = STEP_SPECS_BY_PIPELINE[self.pipeline]
        known = {s.step_id for s in spec}
        if step_id not in known:
            raise StepAuditError(f"{step_id} 不属于 {self.pipeline} 管线（可选：{sorted(known)}）")
        if status not in ALLOWED_STATUSES:
            raise StepAuditError(f"{step_id} 状态不合法：{status}")
        if step_id in self.records:
            raise StepAuditError(f"{step_id} 被重复记录")
        spec_obj = STEP_SPECS[step_id]
        self.records[step_id] = {
            "step_id": step_id,
            "name": spec_obj.name,
            "stage": spec_obj.stage,
            "required": spec_obj.required,
            "status": status,
            "reason": reason or "",
            "detail": _jsonable_detail(detail),
            "contract": spec_obj.contract,
            "evidence": list(spec_obj.evidence),
        }

    def ok(self, step_id: str, reason: str = "", **detail: Any) -> None:
        self.record(step_id, STATUS_OK, reason, **detail)

    def skip(self, step_id: str, reason: str = "", **detail: Any) -> None:
        self.record(step_id, STATUS_SKIP, reason, **detail)

    def blocked(self, step_id: str, reason: str, **detail: Any) -> None:
        self.record(step_id, STATUS_BLOCKED, reason, **detail)

    def failed(self, step_id: str, reason: str, **detail: Any) -> None:
        self.record(step_id, STATUS_FAILED, reason, **detail)

    # -- 导出 ---------------------------------------------------------------
    def marked(self, step_id: str) -> Optional[str]:
        rec = self.records.get(step_id)
        return rec["status"] if rec else None

    def verdict(self) -> str:
        statuses = [r["status"] for r in self.records.values()]
        if STATUS_FAILED in statuses:
            return VERDICT_FAILED
        if STATUS_BLOCKED in statuses:
            return VERDICT_BLOCKED
        for spec in STEP_SPECS_BY_PIPELINE[self.pipeline]:
            if not spec.required:
                continue
            rec = self.records.get(spec.step_id)
            # 必做步骤"跳过"不等于完成：SKIP 只用于说明该步由别的层承担，
            # 一旦它被跳过，本轮就不能宣称走完了整条链。
            if rec is None or rec["status"] in (STATUS_NOT_RUN, STATUS_SKIP):
                return VERDICT_INCOMPLETE
        return VERTICT_COMPLETE

    def finish(self) -> Dict[str, Any]:
        """导出审计 dict；未记录的必做步骤补为 NOT_RUN（不补成功）。"""
        steps: List[Dict[str, Any]] = []
        for spec in STEP_SPECS_BY_PIPELINE[self.pipeline]:
            rec = self.records.get(spec.step_id)
            if rec is None:
                rec = {
                    "step_id": spec.step_id,
                    "name": spec.name,
                    "stage": spec.stage,
                    "required": spec.required,
                    "status": STATUS_NOT_RUN,
                    "reason": "未执行（运行在上游步骤终止）",
                    "detail": {},
                    "contract": spec.contract,
                    "evidence": list(spec.evidence),
                }
            steps.append(rec)
        verdict = self.verdict()
        return {
            "pipeline": self.pipeline,
            "context": _jsonable_detail(self.context),
            "steps": steps,
            "verdict": verdict,
            "not_run": [s["step_id"] for s in steps if s["status"] == STATUS_NOT_RUN],
            "first_blocked": next(
                (s["step_id"] for s in steps if s["status"] == STATUS_BLOCKED), None
            ),
            "first_failed": next(
                (s["step_id"] for s in steps if s["status"] == STATUS_FAILED), None
            ),
            "completed": [s["step_id"] for s in steps if s["status"] == STATUS_OK],
        }


def _jsonable_detail(detail: Mapping[str, Any]) -> Dict[str, Any]:
    """只保留可序列化的浅层结构（审计不是转储，禁止塞模型长文本）。"""
    out: Dict[str, Any] = {}
    for key, value in (detail or {}).items():
        if isinstance(value, (str, int, float, bool)) or value is None:
            out[key] = value
        elif isinstance(value, (list, tuple)):
            out[key] = [
                v if isinstance(v, (str, int, float, bool)) or v is None else str(v)
                for v in value
            ]
        elif isinstance(value, dict):
            out[key] = {str(k): (v if isinstance(v, (str, int, float, bool)) or v is None else str(v)) for k, v in value.items()}
        else:
            out[key] = str(value)
    return out


# --------------------------------------------------------------------------- #
# 确定性复核
# --------------------------------------------------------------------------- #
def check_audit(audit: Mapping[str, Any]) -> List[str]:
    """复核一份导出的审计 dict；返回问题列表（空 = 通过）。"""
    problems: List[str] = []
    pipeline = (audit or {}).get("pipeline")
    if pipeline not in STEP_SPECS_BY_PIPELINE:
        return [f"未知 pipeline：{pipeline!r}"]
    specs = STEP_SPECS_BY_PIPELINE[pipeline]
    expected_ids = [s.step_id for s in specs]

    steps = audit.get("steps")
    if not isinstance(steps, list) or not steps:
        return ["steps 缺失或为空"]

    seen: List[str] = []
    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            problems.append(f"steps[{index}] 不是对象")
            continue
        sid = step.get("step_id")
        if sid not in expected_ids:
            problems.append(f"steps[{index}] 未知步骤编号：{sid!r}")
            continue
        seen.append(sid)
        status = step.get("status")
        if status not in ALLOWED_STATUSES:
            problems.append(f"{sid} 状态不合法：{status!r}")
        if not step.get("name"):
            problems.append(f"{sid} 缺少步骤名称")
        if not step.get("evidence"):
            problems.append(f"{sid} 缺少方法依据锚点")
        if status in (STATUS_BLOCKED, STATUS_FAILED) and not str(step.get("reason") or "").strip():
            problems.append(f"{sid} 处于 {status} 但没有 reason")

    if seen != expected_ids:
        if sorted(seen) == sorted(expected_ids):
            problems.append(f"步骤顺序与契约不一致：{seen}")
        else:
            missing = [s for s in expected_ids if s not in seen]
            dup = [s for s in set(seen) if seen.count(s) > 1]
            if missing:
                problems.append(f"缺少步骤：{missing}")
            if dup:
                problems.append(f"重复步骤：{sorted(dup)}")

    # 顺序自洽：某步已阻断/失败，却仍宣称整条链 COMPLETE —— 典型的"补成功"。
    # 注意：允许"失败但继续产出（并如实标 FAILED）"这种设计，例如 E03 偏移不一致时
    # 仍走完 E04 输出结构、由 verdict=FAILED 与 result.issues 承担后果；
    # 这里只拦"失败 + 后续 OK + 终态 COMPLETE"这种自相矛盾的组合。
    by_id = {s.get("step_id"): s for s in steps if isinstance(s, dict)}
    first_bad = next(
        (s for s in expected_ids if by_id.get(s, {}).get("status") in (STATUS_BLOCKED, STATUS_FAILED)),
        None,
    )
    if first_bad and audit.get("verdict") == VERTICT_COMPLETE:
        later_ok = [
            s for s in expected_ids[expected_ids.index(first_bad) + 1 :]
            if by_id.get(s, {}).get("status") == STATUS_OK
        ]
        if later_ok:
            problems.append(f"{first_bad} 已阻断/失败，但后续步骤仍标记成功且终态为 COMPLETE：{later_ok}")

    # 终态自洽
    verdict = audit.get("verdict")
    if verdict not in ALLOWED_VERDICTS:
        problems.append(f"verdict 不合法：{verdict!r}")
    else:
        statuses = [by_id.get(s, {}).get("status") for s in expected_ids]
        if STATUS_FAILED in statuses and verdict != VERDICT_FAILED:
            problems.append(f"存在 FAILED 步骤但 verdict={verdict}")
        elif STATUS_FAILED not in statuses and STATUS_BLOCKED in statuses and verdict != VERDICT_BLOCKED:
            problems.append(f"存在 BLOCKED 步骤但 verdict={verdict}")
        elif (
            STATUS_FAILED not in statuses
            and STATUS_BLOCKED not in statuses
            and verdict == VERTICT_COMPLETE
            and STATUS_NOT_RUN in statuses
        ):
            problems.append("存在 NOT_RUN 步骤却判定 COMPLETE")
        elif (
            STATUS_FAILED not in statuses
            and STATUS_BLOCKED not in statuses
            and verdict == VERTICT_COMPLETE
            and STATUS_SKIP in [
                by_id.get(s, {}).get("status")
                for s in expected_ids
                if by_id.get(s, {}).get("required", True)
            ]
        ):
            problems.append("存在必做步骤被 SKIP 却判定 COMPLETE")
    return problems


def evidence_problems(root: Optional[Path] = None) -> List[str]:
    """校验所有步骤的依据锚点在仓库里真实存在（"每一步有依据"的机器检查）。"""
    base = Path(root) if root else Path(__file__).resolve().parent.parent
    problems: List[str] = []
    for step_id, spec in sorted(STEP_SPECS.items()):
        for ref in spec.evidence:
            if "::" not in ref:
                problems.append(f"{step_id} 依据格式应为 路径::锚点：{ref}")
                continue
            rel, anchor = ref.split("::", 1)
            path = base / rel
            if not path.is_file():
                problems.append(f"{step_id} 依据文件不存在：{rel}")
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except OSError as exc:  # pragma: no cover - 权限等极端情况
                problems.append(f"{step_id} 依据文件不可读：{rel}（{exc}）")
                continue
            if anchor not in text:
                problems.append(f"{step_id} 锚点在 {rel} 中找不到：{anchor!r}")
    return problems


def evidence_index(root: Optional[Path] = None) -> List[Dict[str, Any]]:
    """导出「步骤 → 依据锚点」清单，供文档与测试对齐。"""
    base = Path(root) if root else Path(__file__).resolve().parent.parent
    rows: List[Dict[str, Any]] = []
    for pipeline, specs in STEP_SPECS_BY_PIPELINE.items():
        for spec in specs:
            for ref in spec.evidence:
                rel, anchor = (ref.split("::", 1) + [""])[:2]
                path = base / rel
                rows.append(
                    {
                        "pipeline": pipeline,
                        "step_id": spec.step_id,
                        "name": spec.name,
                        "file": rel,
                        "anchor": anchor,
                        "exists": path.is_file(),
                    }
                )
    return rows


def summarize(audit: Mapping[str, Any]) -> str:
    """一行摘要，便于日志：``generation COMPLETE C00,C01,... (blocked_at=-)``"""
    steps = (audit or {}).get("steps") or []
    done = [s.get("step_id") for s in steps if s.get("status") == STATUS_OK]
    return (
        f"{audit.get('pipeline')} {audit.get('verdict')} "
        f"{','.join(v for v in done if v)} "
        f"(blocked_at={audit.get('first_blocked')}, failed_at={audit.get('first_failed')})"
    )


def iter_required(pipeline: str) -> Iterable[StepSpec]:
    return (s for s in STEP_SPECS_BY_PIPELINE[pipeline] if s.required)
