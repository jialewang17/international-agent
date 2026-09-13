"""本地向量论据库：优先 Chroma；装不上时自动回退 TF-IDF（同接口）。"""

from __future__ import annotations

import json
import pickle
from pathlib import Path
from typing import Any, Dict, List, Optional

from utils.path import get_project_root

COLLECTION_NAME = "diplomacy_evidence"
DEFAULT_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
TFIDF_NAME = "tfidf_fallback.pkl"


def chroma_dir() -> Path:
    return get_project_root() / "knowledge" / "diplomacy" / "chroma_db"


def evidence_path() -> Path:
    return get_project_root() / "knowledge" / "diplomacy" / "evidence.json"


def _tfidf_path() -> Path:
    return chroma_dir() / TFIDF_NAME


def chroma_ready() -> bool:
    d = chroma_dir()
    if not d.exists():
        return False
    # Chroma sqlite or tfidf fallback
    if _tfidf_path().exists():
        return True
    return any(d.iterdir())


def _flatten_evidence(data: Dict[str, Any]) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    seen = set()
    for bucket_name in ("by_category", "topics_raw"):
        bucket = data.get(bucket_name) or {}
        if not isinstance(bucket, dict):
            continue
        for cat, items in bucket.items():
            if not isinstance(items, list):
                continue
            for it in items:
                if not isinstance(it, dict):
                    continue
                statement = (it.get("statement") or "").strip()
                source = (it.get("source") or "").strip()
                if not statement:
                    continue
                key = (source, statement)
                if key in seen:
                    continue
                seen.add(key)
                theme = (it.get("theme") or "").strip()
                quote = (it.get("quote_en") or it.get("quote_cn") or "").strip()
                eid = (it.get("id") or "").strip()
                doc_parts = [p for p in [theme, statement, quote, f"category:{cat}"] if p]
                rows.append(
                    {
                        "id": eid or f"{cat}_{len(rows)}",
                        "category": str(it.get("category") or cat),
                        "statement": statement,
                        "source": source,
                        "theme": theme,
                        "document": " | ".join(doc_parts),
                        "source_type": str(it.get("source_type") or ""),
                    }
                )
    return rows


def _build_tfidf(rows: List[Dict[str, str]]) -> Dict[str, Any]:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.preprocessing import normalize

    docs = [r["document"] for r in rows]
    vectorizer = TfidfVectorizer(max_features=8000, ngram_range=(1, 2))
    matrix = normalize(vectorizer.fit_transform(docs))
    meta = [
        {
            "category": r["category"],
            "statement": r["statement"],
            "source": r["source"],
            "theme": r["theme"],
        }
        for r in rows
    ]
    return {"vectorizer": vectorizer, "matrix": matrix, "meta": meta, "backend": "tfidf"}


def _build_chromadb(rows: List[Dict[str, str]]) -> Dict[str, Any]:
    import chromadb
    from chromadb.utils import embedding_functions

    # DefaultEmbeddingFunction：ONNX MiniLM，无需 torch / sentence-transformers
    try:
        ef = embedding_functions.DefaultEmbeddingFunction()
        model_name = "default-onnx-minilm"
    except Exception:
        ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=DEFAULT_MODEL)
        model_name = DEFAULT_MODEL

    persist = chroma_dir()
    persist.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(persist))
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass

    col = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"},
    )

    ids, documents, metadatas = [], [], []
    used = set()
    for i, row in enumerate(rows):
        rid = row["id"]
        if rid in used:
            rid = f"{rid}_{i}"
        used.add(rid)
        ids.append(rid)
        documents.append(row["document"])
        metadatas.append(
            {
                "category": row["category"],
                "statement": row["statement"][:500],
                "source": row["source"][:500],
                "theme": row["theme"][:200],
                "source_type": row["source_type"][:100],
            }
        )

    batch = 64
    for start in range(0, len(ids), batch):
        col.add(
            ids=ids[start : start + batch],
            documents=documents[start : start + batch],
            metadatas=metadatas[start : start + batch],
        )
    return {
        "ok": True,
        "count": len(ids),
        "persist_dir": str(persist),
        "model": model_name,
        "collection": COLLECTION_NAME,
        "backend": "chromadb",
    }


def build_chroma_kb(*, reset: bool = True) -> Dict[str, Any]:
    path = evidence_path()
    if not path.exists():
        raise FileNotFoundError(f"找不到论据库: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = _flatten_evidence(data)
    if not rows:
        raise ValueError("evidence.json 中没有可用论据")

    persist = chroma_dir()
    persist.mkdir(parents=True, exist_ok=True)
    if reset and _tfidf_path().exists():
        _tfidf_path().unlink()

    # 优先 Chroma
    try:
        return _build_chromadb(rows)
    except Exception as e:
        # 回退 TF-IDF，保证本机可演示
        payload = _build_tfidf(rows)
        with _tfidf_path().open("wb") as f:
            pickle.dump(payload, f)
        return {
            "ok": True,
            "count": len(rows),
            "persist_dir": str(persist),
            "model": "tfidf-sklearn",
            "collection": TFIDF_NAME,
            "backend": "tfidf",
            "chroma_error": str(e),
            "note": "chromadb 不可用，已用 TF-IDF 语义近似回退；装好 chromadb 后请重跑本脚本",
        }


def _query_tfidf(query: str, *, categories: Optional[List[str]], top_k: int) -> List[Dict[str, str]]:
    import numpy as np
    from sklearn.metrics.pairwise import cosine_similarity

    if not _tfidf_path().exists():
        return []
    with _tfidf_path().open("rb") as f:
        payload = pickle.load(f)
    vectorizer = payload["vectorizer"]
    matrix = payload["matrix"]
    meta = payload["meta"]
    qv = vectorizer.transform([query])
    sims = cosine_similarity(qv, matrix).ravel()
    order = np.argsort(-sims)

    cats = {c.strip() for c in (categories or []) if c and c.strip()}
    ranked = []
    for idx in order:
        if sims[idx] <= 0:
            continue
        m = meta[int(idx)]
        ranked.append(
            {
                "category": m["category"],
                "statement": m["statement"],
                "source": m["source"],
                "score": float(sims[idx]),
                "retrieval": "tfidf",
            }
        )

    if cats:
        same = [x for x in ranked if x["category"] in cats]
        other = [x for x in ranked if x["category"] not in cats]
        picked = same[:top_k]
        if len(picked) < top_k:
            picked.extend(other[: top_k - len(picked)])
    else:
        picked = ranked[:top_k]
    return [
        {
            "category": x["category"],
            "statement": x["statement"],
            "source": x["source"],
            "retrieval": x["retrieval"],
        }
        for x in picked
    ]


# DefaultEmbedding 下：相关评论常见 distance≈0.4，明显跑题≈0.85+
CHROMA_MAX_DISTANCE = 0.65


def _query_chromadb(query: str, *, categories: Optional[List[str]], top_k: int) -> List[Dict[str, str]]:
    import chromadb
    from chromadb.utils import embedding_functions

    try:
        ef = embedding_functions.DefaultEmbeddingFunction()
    except Exception:
        ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=DEFAULT_MODEL)

    client = chromadb.PersistentClient(path=str(chroma_dir()))
    col = client.get_collection(name=COLLECTION_NAME, embedding_function=ef)
    n = max(top_k * 3, top_k)
    raw = col.query(
        query_texts=[query],
        n_results=min(n, max(col.count(), 1)),
        include=["documents", "metadatas", "distances"],
    )
    docs = (raw.get("documents") or [[]])[0]
    metas = (raw.get("metadatas") or [[]])[0]
    dists = (raw.get("distances") or [[]])[0]

    cats = {c.strip() for c in (categories or []) if c and c.strip()}
    ranked = []
    for doc, meta, dist in zip(docs, metas, dists):
        meta = meta or {}
        # 过滤语义过远的“硬凑近邻”，避免库外主题仍塞进无关论据
        try:
            if float(dist) > CHROMA_MAX_DISTANCE:
                continue
        except (TypeError, ValueError):
            pass
        ranked.append(
            {
                "category": str(meta.get("category") or ""),
                "statement": str(meta.get("statement") or doc or ""),
                "source": str(meta.get("source") or ""),
                "retrieval": "chroma",
                "distance": float(dist) if dist is not None else None,
            }
        )
    if cats:
        same = [x for x in ranked if x["category"] in cats]
        # 指定类别时只返回同类，避免用无关类硬凑 top_k
        picked = same[:top_k]
    else:
        picked = ranked[:top_k]
    return picked


def query_chroma(
    query: str,
    *,
    categories: Optional[List[str]] = None,
    top_k: int = 4,
) -> List[Dict[str, str]]:
    q = (query or "").strip()
    if not q or not chroma_ready():
        return []

    # TF-IDF 回退优先检测文件（避免半残 Chroma 目录干扰）
    if _tfidf_path().exists():
        try:
            return _query_tfidf(q, categories=categories, top_k=top_k)
        except Exception:
            return []

    try:
        return _query_chromadb(q, categories=categories, top_k=top_k)
    except Exception:
        return []
