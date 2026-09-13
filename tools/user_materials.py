"""用户上传/粘贴资料 → 规范化为 evidence_used 条目。

对齐老师 0822 P0：成稿论据 = 用户资料 + 本地库；须可区分来源。
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Union

RawMaterials = Union[str, List[Any], None]

SOURCE_USER = "用户上传"
SOURCE_LOCAL = "本地库"


def _split_blocks(text: str) -> List[str]:
    text = (text or "").strip()
    if not text:
        return []
    # 空行或 --- 分段
    parts = re.split(r"\n\s*-{3,}\s*\n|\n{2,}", text)
    return [p.strip() for p in parts if p and p.strip()]


def _guess_category(blob: str) -> str:
    t = (blob or "").lower()
    rules = [
        ("food", ["food", "cuisine", "dish", "美食", "大盘鸡", "拉面", "馕", "tea", "茶"]),
        ("culture", ["unesco", "heritage", "春节", "非遗", "文化", "festival", "剪纸", "京剧"]),
        ("sports", ["olympic", "冬奥", "sports", "体育", "崇礼"]),
        ("governance", ["policy", "治理", "diplomacy", "外交"]),
    ]
    for cat, kws in rules:
        if any(k.lower() in t for k in kws):
            return cat
    return "user_material"


def normalize_user_materials(
    raw: RawMaterials,
    *,
    theme: str = "",
    default_category: Optional[str] = None,
) -> List[Dict[str, str]]:
    """
    将用户粘贴/上传内容转为 evidence 结构：
    {category, statement, source, retrieval, source_type}
    """
    items: List[Dict[str, Any]] = []

    if raw is None:
        return []
    if isinstance(raw, str):
        blocks = _split_blocks(raw)
        for i, block in enumerate(blocks, 1):
            items.append({"text": block, "title": f"用户资料#{i}"})
    elif isinstance(raw, list):
        for i, x in enumerate(raw, 1):
            if isinstance(x, str) and x.strip():
                items.append({"text": x.strip(), "title": f"用户资料#{i}"})
            elif isinstance(x, dict):
                text = (
                    str(x.get("text") or x.get("statement") or x.get("content") or "")
                ).strip()
                if not text:
                    continue
                items.append(
                    {
                        "text": text,
                        "title": str(x.get("title") or x.get("name") or f"用户资料#{i}"),
                        "source": str(x.get("source") or x.get("url") or ""),
                        "category": str(x.get("category") or ""),
                    }
                )
    else:
        return []

    out: List[Dict[str, str]] = []
    seen = set()
    for it in items:
        stmt = re.sub(r"\s+", " ", it["text"]).strip()
        if len(stmt) < 8:
            continue
        # 过长截断，避免撑爆 prompt
        if len(stmt) > 1200:
            stmt = stmt[:1197] + "..."
        key = stmt[:200]
        if key in seen:
            continue
        seen.add(key)
        cat = (it.get("category") or default_category or _guess_category(stmt + " " + theme)).strip()
        src = (it.get("source") or "").strip() or f"user_paste:{it.get('title', 'material')}"
        out.append(
            {
                "category": cat or "user_material",
                "statement": stmt,
                "source": src,
                "retrieval": "user_upload",
                "source_type": SOURCE_USER,
            }
        )
    return out


def tag_local_evidence(items: List[Dict[str, str]]) -> List[Dict[str, str]]:
    tagged: List[Dict[str, str]] = []
    for ev in items or []:
        row = dict(ev)
        row.setdefault("source_type", SOURCE_LOCAL)
        if row.get("retrieval") == "user_upload":
            row["source_type"] = SOURCE_USER
        tagged.append(row)
    return tagged


def merge_evidence(
    user_items: List[Dict[str, str]],
    local_items: List[Dict[str, str]],
    *,
    prefer_user_first: bool = True,
) -> List[Dict[str, str]]:
    """双源合并；默认用户资料在前（老师：先喂资料再生成）。"""
    user_t = list(user_items or [])
    local_t = tag_local_evidence(local_items or [])
    merged = (user_t + local_t) if prefer_user_first else (local_t + user_t)
    out: List[Dict[str, str]] = []
    seen = set()
    for ev in merged:
        key = (ev.get("source_type", ""), ev.get("statement", "")[:180])
        if not ev.get("statement") or key in seen:
            continue
        seen.add(key)
        out.append(ev)
    return out
