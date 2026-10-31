"""FastAPI entry: thin REST wrapper over existing tool functions + static frontend."""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from uuid import uuid4
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.schemas import (  # noqa: E402
    ApprovalRequest,
    EvidenceRequest,
    PolishRequest,
    PostGenerateRequest,
    ReplyGenerateRequest,
    TopicsRequest,
    GateDecision,
    EvidencePack,
)
from api.gate_c import verify_gate_c  # noqa: E402
from api.human_review import HumanReviewStore  # noqa: E402
from api.evidence_store import EvidencePackStore, EvidenceStoreError  # noqa: E402
from api.claim_extraction import DeterministicClaimExtractor
from api.claim_store import ClaimStore, ClaimStoreError
from api.evaluation import evaluate_content_version
from api.evaluation_store import EvaluationResultStore
from api.coverage_service import (
    CoverageIntegrityError,
    inspect_canonical_coverage,
)
from api.versioning import ContentVersionStore, VersioningError  # noqa: E402
from api.workflow import workflow_state_machine, WorkflowError  # noqa: E402
from api.story_router import router as story_router  # noqa: E402
import api.story_router as story_router_module  # noqa: E402, F401  (P0-1 store binding)
from api.story_session import story_session_store  # noqa: E402

FRONTEND_DIR = ROOT / "frontend"

# --- Application-level shared stores (P0.8-B) ------------------------------
# These are the *single* shared instances for the Human Review -> Gate C
# integration path. Human Review persists decisions into ``human_review_store``;
# Gate C (the /approve endpoint) verifies from the *same* instance. Gate C never
# instantiates its own review store, and never trusts ReviewOutcome fields.
content_version_store = ContentVersionStore()
human_review_store = HumanReviewStore()
evidence_pack_store = EvidencePackStore()
claim_store = ClaimStore()
claim_extractor = DeterministicClaimExtractor()
evaluation_result_store = EvaluationResultStore()

# --- P0-1 Ground wiring -----------------------------------------------------
# The Story Task flow and the generation path must see the SAME canonical
# EvidencePack store. Binding is done here (after the stores exist) so the
# story router can persist Ground packs and StorySessionStore can verify
# evidence_pack_id existence instead of trusting bare strings.
story_router_module.bind_evidence_pack_store(evidence_pack_store)
story_session_store.bind_evidence_pack_store(evidence_pack_store)

PRESET_CHIPS = [
    {"label": "光伏羊通稿", "theme": "新闻通稿：青海塔拉滩光伏羊——牧光互补与治沙增收", "scene": "post"},
    {"label": "张铁机车+资料", "theme": "张铁机车海外社媒短帖——车间烟火气与匠人日常", "scene": "post"},
    {"label": "新疆美食", "theme": "新疆美食的多样与烟火气（大盘鸡、拉面、馕）", "scene": "post"},
    {"label": "春节非遗", "theme": "春节作为联合国教科文组织人类非物质文化遗产的当代生活意义", "scene": "post"},
    {"label": "街头美食博主", "theme": "外国YouTuber视角下的中国街头美食（如Food Ranger等）", "scene": "post"},
    {"label": "茶文化", "theme": "中国茶文化（UNESCO非遗）在当代社交与日常生活中的分享方式", "scene": "post"},
    {"label": "冬奥遗产", "theme": "北京冬奥会赛后体育文化旅游带（崇礼等场馆遗产与大众参与）", "scene": "post"},
    {"label": "Instagram选题", "seed": "讲好中国故事 Instagram账号 目标受众America", "scene": "topics"},
    {
        "label": "回复洋网红质疑",
        "comment": (
            "Foreign YouTubers who film Chinese street food are just paid propaganda. "
            "You can't trust anything they show about China."
        ),
        "scene": "reply",
    },
]

META = {
    "platforms": ["twitter", "instagram", "facebook", "tiktok", "youtube", "weibo"],
    "identities": [
        "online_influencer",
        "political_commentator",
        "comedian",
        "scientist",
        "rapper",
    ],
    "tones": ["optimistic", "humorous", "serious", "sarcastic", "cold"],
    "countries": ["America", "UK", "Japan"],
    "languages": ["English", "Chinese"],
    "preset_chips": PRESET_CHIPS,
    "pipeline_steps": [
        {"id": "DEFINE", "label": "Define", "hard": False},
        {"id": "GROUND", "label": "Ground", "hard": False},
        {"id": "PLAN", "label": "Plan", "hard": False},
        {"id": "CREATE", "label": "Create", "hard": False},
        {"id": "REVISE_AUDIT", "label": "Revise & Audit", "hard": False},
        {"id": "APPROVE", "label": "Approve", "hard": False},
    ],
    "gates": [
        {"id": "A", "label": "Joint Task + Plan Confirmation", "after": "PLAN", "hard": True},
        {"id": "B", "label": "Plan Evidence Check", "after": "PLAN", "hard": True, "exception_only": True},
        {"id": "C", "label": "Final Approval", "after": "APPROVE", "hard": True},
    ],
    "genres": [
        {"id": "", "label": "自动识别"},
        {"id": "post", "label": "社交帖文"},
        {"id": "news", "label": "新闻通稿"},
        {"id": "feature", "label": "新闻特稿"},
        {"id": "indepth", "label": "深度报道"},
        {"id": "script", "label": "短视频脚本"},
        {"id": "faq", "label": "误解澄清"},
    ],
    "version": "0.7.0-v6.1-six-genre",
    "skills_note": "china-story-generation(v6.1 六体裁) + china-story-evaluation(v6.1) + intl-comm + evidence-user-materials",
    "spec_doc": "SPEC-国际传播智能体_v2.1_现阶段统一规范.md",
    "lit_map_doc": "docs/PIPELINE_LIT_MAP.md",
}

app = FastAPI(
    title="AnyClaw · 讲好中国故事工作台",
    description="国际传播智能体 API：主动发帖 / 选题 / 回复 + 论据透明 + 门控可视化",
    version="0.7.0-v6.1-six-genre",
)

app.include_router(story_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"ok": True, "service": "anyclaw-api"}


@app.get("/api/meta")
def meta():
    return META


@app.post("/api/workflow/{task_id}/start")
def start_workflow(task_id: str):
    return {"ok": True, "data": workflow_state_machine.start(task_id).__dict__}


@app.post("/api/workflow/{task_id}/gate")
def decide_workflow_gate(task_id: str, decision: GateDecision):
    try:
        if story_session_store.exists(task_id) and decision.gate.upper() in {"A", "B", "C"}:
            raise WorkflowError(decision.gate, "Use story task joint confirmation / trusted evaluation / canonical approval")
        state = workflow_state_machine.decide_gate(task_id, decision)
        return {"ok": True, "data": state.__dict__}
    except (KeyError, WorkflowError) as exc:
        detail = {"gate": getattr(exc, "gate", "task"), "status": "blocked", "reason": str(exc)}
        raise HTTPException(status_code=409, detail=detail) from exc


@app.post("/api/workflow/{task_id}/advance/{target}")
def advance_workflow(task_id: str, target: str):
    try:
        state = workflow_state_machine.advance(task_id, target.upper())
        return {"ok": True, "data": state.__dict__}
    except (KeyError, WorkflowError) as exc:
        detail = {"gate": getattr(exc, "gate", "stage"), "status": "blocked", "reason": str(exc)}
        raise HTTPException(status_code=409, detail=detail) from exc


@app.post("/api/posts/generate")
def generate_post(body: PostGenerateRequest):
    # SPEC §5.1 Define: topic(=theme)/goal/audience. Additive composition keeps
    # legacy theme-only clients unchanged; goal/audience flow into user_brief.
    topic = (body.topic or "").strip()
    theme = (body.theme or "").strip()
    goal = (body.goal or "").strip()
    audience = (body.audience or "").strip()
    effective_theme = topic or theme
    if not effective_theme:
        raise HTTPException(status_code=400, detail="topic 不能为空（theme 亦可）")
    try:
        from tools.story_post_gen import run_story_post_generation

        payload = body.model_dump()
        requested_task_id = str(payload.pop("task_id", "") or "").strip()
        payload.pop("topic", None)
        payload.pop("goal", None)
        payload.pop("audience", None)
        payload["theme"] = effective_theme
        brief_parts = [effective_theme]
        if goal:
            brief_parts.append(f"传播目标：{goal}")
        if audience:
            brief_parts.append(f"目标受众：{audience}")
        payload["user_brief"] = "\n".join(brief_parts) if (goal or audience) else None
        if requested_task_id and story_session_store.exists(requested_task_id):
            workflow_state_machine.assert_create_ready(requested_task_id)
            confirmed = story_session_store.get(requested_task_id).task
            if str(payload.get("genre") or "") != confirmed.genre:
                raise WorkflowError("A", "genre conflicts with the confirmed task")
            if str(payload.get("language") or "") != confirmed.language:
                raise WorkflowError("A", "language conflicts with the confirmed task")
            if str(payload.get("theme") or "").strip() != confirmed.topic.strip():
                raise WorkflowError("A", "theme conflicts with the confirmed task")
            if confirmed.platform and str(payload.get("platform") or "") != confirmed.platform:
                raise WorkflowError("A", "platform conflicts with the confirmed task")
            existing_materials = str(payload.get("user_materials") or "")
            if existing_materials and existing_materials != confirmed.user_materials:
                raise WorkflowError("A", "user materials differ from the submitted materials")
            payload["user_materials"] = confirmed.user_materials
            payload["desired_effect"] = (
                "Present confirmed information clearly and accurately without presuming "
                "a specific audience attitude or outcome."
            )
        result = run_story_post_generation(**payload)

        # Blocked/error paths never persist evidence and never create a version.
        if result.get("error"):
            result.pop("_evidence_pack", None)
            return {"ok": False, "data": result}

        canonical_content = str(result.get("post") or "").strip()
        pack_payload = result.pop("_evidence_pack", None)
        if not canonical_content:
            result["error"] = "生成结果为空，未创建 ContentVersion。"
            return {"ok": False, "data": result}
        if pack_payload is None:
            raise RuntimeError("successful generation missing canonical EvidencePack")

        # I2-B-003: a canonical pack is required before Claim snapshots.
        pack = EvidencePack.model_validate(pack_payload)

        if not pack.evidence_pack_id.strip():
            raise RuntimeError(
                "canonical EvidencePack has empty evidence_pack_id"
            )

        # Extract candidates only from the actual generated content.
        # This is sentence-level extraction, NOT fact verification.
        claim_candidates = claim_extractor.extract(canonical_content)
        claim_ids = [
            claim.claim_id
            for claim in claim_candidates
        ]

        # I2-B-003 does NOT infer semantic evidence support.
        # Extracted candidates retain evidence_ids=[].
        for candidate in claim_candidates:
            if candidate.evidence_ids:
                raise RuntimeError(
                    "candidate extraction must not auto-bind evidence_ids"
                )

        # Reject known immutable Claim collisions before the first write.
        # This reduces common partial-write failures, but is not a transaction.
        for candidate in claim_candidates:
            existing_claim = claim_store.get(
                pack.evidence_pack_id,
                candidate.claim_id,
            )

            if (
                existing_claim is not None
                and existing_claim != candidate
            ):
                raise ClaimStoreError(
                    "claim collision: "
                    f"evidence_pack_id={pack.evidence_pack_id}, "
                    f"claim_id={candidate.claim_id}"
                )

        # IMPORTANT: stores are currently independent in-memory stores.
        # Write snapshots before creating a visible ContentVersion.
        evidence_pack_store.put(pack)
        claim_store.put_many(
            pack.evidence_pack_id,
            claim_candidates,
        )

        task_id = requested_task_id or str(uuid4())

        version = content_version_store.create_initial_version(
            task_id,
            canonical_content,
            evidence_pack_id=pack.evidence_pack_id,
            claim_ids=claim_ids,
        )

        # Additive response fields; preserve all existing response fields.
        result["task_id"] = task_id
        result["evidence_pack_id"] = pack.evidence_pack_id
        result["content_version_id"] = version.content_version_id
        result["claim_ids"] = list(version.claim_ids)
        return {"ok": True, "data": result}
    except WorkflowError as e:
        raise HTTPException(status_code=409, detail={"gate": e.gate, "reason": e.reason}) from e
    except ModuleNotFoundError as e:
        raise HTTPException(
            status_code=503,
            detail=f"运行依赖未安装: {e.name}. 请先执行 pip install -r requirements.txt",
        ) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


class EvaluationRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content_version_id: str
    task_id: str = ""


@app.post("/api/evaluations/run")
def run_evaluation(body: EvaluationRunRequest):
    """Explicit evaluation using canonical in-memory store snapshots."""

    version_id = body.content_version_id.strip()
    if not version_id:
        raise HTTPException(
            status_code=400,
            detail="content_version_id is required",
        )

    try:
        version = content_version_store.get_version(version_id)
    except VersioningError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    if not version.task_id.strip():
        raise HTTPException(
            status_code=409,
            detail="content version has no canonical task_id",
        )

    requested_task_id = body.task_id.strip()

    if (
        requested_task_id
        and requested_task_id != version.task_id
    ):
        raise HTTPException(
            status_code=409,
            detail="task_id does not match canonical content version",
        )

    pack_id = (version.evidence_pack_id or "").strip()

    if not pack_id:
        raise HTTPException(
            status_code=409,
            detail="content version missing evidence_pack_id",
        )

    # The caller cannot supply Claims. Resolve exact snapshots from Store.
    # Missing Claim snapshots fail closed before EvaluationResult creation.
    if version.claim_ids:
        try:
            stored_claims = claim_store.get_many(
                pack_id,
                version.claim_ids,
            )
        except ClaimStoreError as exc:
            raise HTTPException(
                status_code=409,
                detail=f"claim snapshots unavailable: {exc}",
            ) from exc
    else:
        stored_claims = []

    claims_by_id = {
        claim.claim_id: claim
        for claim in stored_claims
    }

    # Missing EvidencePack is not a PASS and not a fabricated pack.
    # Existing Part 1 handles None as a blocking condition.
    try:
        pack = evidence_pack_store.get(pack_id)
    except EvidenceStoreError:
        pack = None

    # No judge has been implemented or configured in this milestone.
    # Never provide fabricated dimension scores.
    result = evaluate_content_version(
        version.content_version_id,
        content_version_store,
        claims_by_id,
        pack,
        judge=None,
    )

    evaluation_result_store.put(result)

    # ok=True means the evaluation operation produced a result.
    # It does not imply PASS, SUPPORTED, ACCEPT or APPROVED.
    return {
        "ok": True,
        "data": result.model_dump(mode="json"),
    }


@app.get("/api/evaluations/{evaluation_id}")
def get_evaluation(
    evaluation_id: str,
    task_id: str = "",
):
    """Read a stored evaluation result without reevaluating content."""

    result = evaluation_result_store.get(evaluation_id)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="evaluation not found",
        )

    if task_id.strip() and task_id.strip() != result.task_id:
        raise HTTPException(
            status_code=409,
            detail="task_id does not match evaluation",
        )

    return {
        "ok": True,
        "data": result.model_dump(mode="json"),
    }


class CoverageInspectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content_version_id: str
    task_id: str = ""
    expected_content_sha256: str = ""


@app.post("/api/coverage/inspect")
def inspect_content_coverage(body: CoverageInspectRequest):
    """Compute a read-only Coverage view from canonical stores."""

    version_id = body.content_version_id.strip()

    if not version_id:
        raise HTTPException(
            status_code=400,
            detail="content_version_id is required",
        )

    try:
        index = inspect_canonical_coverage(
            content_version_id=version_id,
            version_store=content_version_store,
            claim_store=claim_store,
            evidence_pack_store=evidence_pack_store,
            task_id=body.task_id,
            expected_content_sha256=body.expected_content_sha256,
        )

    except VersioningError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except (
        CoverageIntegrityError,
        ClaimStoreError,
        EvidenceStoreError,
        ValueError,
        TypeError,
        RuntimeError,
    ) as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc

    # ok=True means the inspection completed, NOT audit PASS.
    return {
        "ok": True,
        "data": {
            "coverage_review_status": "NOT_EVALUATED",
            "review_required": True,
            "index": asdict(index),
        },
    }


@app.post("/api/posts/topics")
def generate_topics(body: TopicsRequest):
    try:
        from tools.story_post_gen import plan_china_story_topics
        raw = plan_china_story_topics.invoke(body.model_dump())
        data = json.loads(raw)
        return {"ok": True, "data": data}
    except ModuleNotFoundError as e:
        raise HTTPException(
            status_code=503,
            detail=f"运行依赖未安装: {e.name}. 请先执行 pip install -r requirements.txt",
        ) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/api/replies/generate")
def generate_reply(body: ReplyGenerateRequest):
    comment = (body.comment or "").strip()
    if not comment:
        raise HTTPException(status_code=400, detail="comment 不能为空")
    try:
        from tools.intl_comm_reply import intl_comm_reply
        raw = intl_comm_reply.invoke(body.model_dump())
        data = json.loads(raw)
        blocked = bool(data.get("error")) or not (data.get("reply") or "").strip()
        return {"ok": not blocked, "data": data}
    except ModuleNotFoundError as e:
        raise HTTPException(
            status_code=503,
            detail=f"运行依赖未安装: {e.name}. 请先执行 pip install -r requirements.txt",
        ) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/api/evidence")
def query_evidence(body: EvidenceRequest):
    try:
        from tools.kb_local import retrieve_evidence
        raw = retrieve_evidence.invoke(
            {
                "categories": body.categories,
                "limit_per_category": body.limit_per_category,
                "query": body.query,
            }
        )
        data = json.loads(raw)
        return {"ok": True, "data": data}
    except ModuleNotFoundError as e:
        raise HTTPException(
            status_code=503,
            detail=f"运行依赖未安装: {e.name}. 请先执行 pip install -r requirements.txt",
        ) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/api/posts/polish")
def polish_post(body: PolishRequest):
    post = (body.post or "").strip()
    if not post:
        raise HTTPException(status_code=400, detail="post 不能为空")
    instruction = (body.instruction or "").strip() or "Make it clearer and more engaging."
    prompt = (
        f"You are polishing a social-media draft about China stories for international audiences.\n"
        f"Language: {body.language}\n"
        f"Max words: about {body.max_words}\n"
        f"Edit instruction: {instruction}\n"
        f"Rules: do NOT invent new facts, stats, or URLs; keep the same factual claims.\n"
        f"Return ONLY the rewritten post text, no JSON.\n\n"
        f"Original post:\n{post}"
    )
    try:
        from langchain_core.messages import HumanMessage
        from model.factory import get_text_generation_model
        model = get_text_generation_model()
        result = model.invoke([HumanMessage(content=prompt)])
        text = getattr(result, "content", "") or str(result)
        if isinstance(text, list):
            text = "".join((x.get("text", "") if isinstance(x, dict) else str(x)) for x in text)
        return {"ok": True, "data": {"post": str(text).strip(), "instruction": instruction}}
    except ModuleNotFoundError as e:
        raise HTTPException(
            status_code=503,
            detail=f"运行依赖未安装: {e.name}. 请先执行 pip install -r requirements.txt",
        ) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e



@app.post("/api/posts/approve")
def approve_post(body: ApprovalRequest):
    """Gate C: verify a persisted, exact-binding human ACCEPT and record approval metadata.

    Authorization no longer comes from ``approved=True``. Gate C verifies the
    latest persisted ``HumanReviewDecision`` for the exact
    ``(task, content_version, evaluation)`` binding from the application-level
    shared ``HumanReviewStore``. ``content_sha256`` is computed from the
    canonical ``ContentVersion.content`` — never from the request body.

    Fail-closed: missing binding fields, unknown versions, no persisted review,
    a superseded review, a non-ACCEPT latest decision, or a task conflict all
    return an error and never APPROVED. This endpoint does not publish content.
    """
    if not body.approved:
        raise HTTPException(status_code=400, detail="Gate C 需要显式人工批准")

    # Legacy `approved=True` alone is not authorization: binding is required.
    if not (body.content_version_id or "").strip():
        raise HTTPException(
            status_code=400,
            detail="Gate C 需要 content_version_id 绑定（legacy approved=True 不再构成批准）",
        )
    if not (body.evaluation_id or "").strip():
        raise HTTPException(
            status_code=400,
            detail="Gate C 需要 evaluation_id 绑定（legacy approved=True 不再构成批准）",
        )

    result = verify_gate_c(
        body.content_version_id.strip(),
        body.evaluation_id.strip(),
        version_store=content_version_store,
        review_store=human_review_store,
        task_id=(body.task_id or "").strip(),
        review_id=(body.review_id or "").strip(),
    )

    if not result.passed:
        # Fail closed: no persisted exact-binding ACCEPT -> no APPROVED.
        raise HTTPException(
            status_code=403,
            detail={
                "gate": "C",
                "gate_label": "Final Approval",
                "status": result.status,
                "approved": False,
                "published": False,
                "reason": result.reason,
            },
        )

    return {
        "ok": True,
        "data": {
            "approved": True,
            "gate": "C",
            "gate_label": "Final Approval",
            # The authoritative reviewer comes from the persisted record, not
            # from the client request.
            "approver": result.reviewer or "human",
            "approved_at": (
                result.reviewed_at.isoformat()
                if result.reviewed_at is not None else None
            ),
            "content_sha256": result.content_sha256,
            "note": (body.note or "").strip(),
            "status": "APPROVED",
            "published": False,
            # P0.8-B additive audit fields.
            "review_id": result.review_id,
            "task_id": result.task_id,
            "content_version_id": result.content_version_id,
            "evaluation_id": result.evaluation_id,
        },
    }


@app.get("/")
def index():
    """Primary entry: the six-stage workbench (Define -> ... -> Approve).

    The legacy single-page tools (post / topics / replies) stay reachable at
    /tools; nothing about their behaviour changes.
    """
    workbench_path = FRONTEND_DIR / "workbench.html"
    if workbench_path.exists():
        return FileResponse(workbench_path)
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"message": "frontend not found; build frontend/index.html"}


@app.get("/tools")
def legacy_tools():
    """Legacy tool page (single-shot post / topic / reply helpers)."""
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"message": "frontend not found; build frontend/index.html"}


if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
