"""FastAPI entry: thin REST wrapper over existing tool functions + static frontend."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

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
)
from api.gate_c import verify_gate_c  # noqa: E402
from api.human_review import HumanReviewStore  # noqa: E402
from api.versioning import ContentVersionStore  # noqa: E402
from api.workflow import workflow_state_machine, WorkflowError  # noqa: E402

FRONTEND_DIR = ROOT / "frontend"

# --- Application-level shared stores (P0.8-B) ------------------------------
# These are the *single* shared instances for the Human Review -> Gate C
# integration path. Human Review persists decisions into ``human_review_store``;
# Gate C (the /approve endpoint) verifies from the *same* instance. Gate C never
# instantiates its own review store, and never trusts ReviewOutcome fields.
content_version_store = ContentVersionStore()
human_review_store = HumanReviewStore()

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
        {"id": "A", "label": "Task Confirmation", "after": "DEFINE", "hard": True},
        {"id": "B", "label": "Evidence Exception", "after": "GROUND", "hard": True, "exception_only": True},
        {"id": "C", "label": "Final Approval", "after": "APPROVE", "hard": True},
    ],
    "genres": [
        {"id": "", "label": "自动识别"},
        {"id": "post", "label": "社交帖文"},
        {"id": "news", "label": "新闻通稿"},
        {"id": "feature", "label": "特稿/深度"},
        {"id": "script", "label": "短视频脚本"},
    ],
    "version": "0.6.0-v2.1-six-stage",
    "skills_note": "china-story-post/news/feature/script + evidence-user-materials",
    "spec_doc": "SPEC-国际传播智能体_v2.1_现阶段统一规范.md",
    "lit_map_doc": "docs/PIPELINE_LIT_MAP.md",
}

app = FastAPI(
    title="AnyClaw · 讲好中国故事工作台",
    description="国际传播智能体 API：主动发帖 / 选题 / 回复 + 论据透明 + 门控可视化",
    version="0.6.0-v2.1-six-stage",
)

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
    theme = (body.theme or "").strip()
    if not theme:
        raise HTTPException(status_code=400, detail="theme 不能为空")
    try:
        from tools.story_post_gen import run_story_post_generation
        result = run_story_post_generation(**body.model_dump())
        return {"ok": not bool(result.get("error")), "data": result}
    except ModuleNotFoundError as e:
        raise HTTPException(
            status_code=503,
            detail=f"运行依赖未安装: {e.name}. 请先执行 pip install -r requirements.txt",
        ) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


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
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"message": "frontend not found; build frontend/index.html"}


if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
