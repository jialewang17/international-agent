"""FastAPI entry: thin REST wrapper over existing tool functions + static frontend."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from langchain_core.messages import HumanMessage

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.schemas import (  # noqa: E402
    EvidenceRequest,
    PolishRequest,
    PostGenerateRequest,
    ReplyGenerateRequest,
    TopicsRequest,
)
from model.factory import get_text_generation_model  # noqa: E402
from tools.intl_comm_reply import intl_comm_reply  # noqa: E402
from tools.kb_local import retrieve_evidence  # noqa: E402
from tools.story_post_gen import (  # noqa: E402
    plan_china_story_topics,
    run_story_post_generation,
)
from utils.env_loader import get_env_config  # noqa: E402

get_env_config()

FRONTEND_DIR = ROOT / "frontend"

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
        {"id": "theme", "label": "主题解析"},
        {"id": "user_materials", "label": "用户资料"},
        {"id": "retrieve", "label": "本地论据"},
        {"id": "gate", "label": "对齐门控"},
        {"id": "generate", "label": "成稿生成"},
    ],
    "version": "0.4.0-frontend",
    "skills_note": "china-story-post v0.3.3 + china-story-news v0.4.0 + evidence-user-materials v0.4",
}

app = FastAPI(
    title="AnyClaw · 讲好中国故事工作台",
    description="国际传播智能体 API：主动发帖 / 选题 / 回复 + 论据透明 + 门控可视化",
    version="0.1.0",
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


@app.post("/api/posts/generate")
def generate_post(body: PostGenerateRequest):
    theme = (body.theme or "").strip()
    if not theme:
        raise HTTPException(status_code=400, detail="theme 不能为空")
    try:
        result = run_story_post_generation(**body.model_dump())
        return {"ok": not bool(result.get("error")), "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/api/posts/topics")
def generate_topics(body: TopicsRequest):
    try:
        raw = plan_china_story_topics.invoke(body.model_dump())
        data = json.loads(raw)
        return {"ok": True, "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/api/replies/generate")
def generate_reply(body: ReplyGenerateRequest):
    comment = (body.comment or "").strip()
    if not comment:
        raise HTTPException(status_code=400, detail="comment 不能为空")
    try:
        raw = intl_comm_reply.invoke(body.model_dump())
        data = json.loads(raw)
        blocked = bool(data.get("error")) or not (data.get("reply") or "").strip()
        return {"ok": not blocked, "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/api/evidence")
def query_evidence(body: EvidenceRequest):
    try:
        raw = retrieve_evidence.invoke(
            {
                "categories": body.categories,
                "limit_per_category": body.limit_per_category,
                "query": body.query,
            }
        )
        data = json.loads(raw)
        return {"ok": True, "data": data}
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
        model = get_text_generation_model()
        result = model.invoke([HumanMessage(content=prompt)])
        text = getattr(result, "content", "") or str(result)
        if isinstance(text, list):
            text = "".join((x.get("text", "") if isinstance(x, dict) else str(x)) for x in text)
        return {"ok": True, "data": {"post": str(text).strip(), "instruction": instruction}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/")
def index():
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"message": "frontend not found; build frontend/index.html"}


if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
