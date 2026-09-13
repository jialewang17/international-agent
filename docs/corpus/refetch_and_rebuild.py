# -*- coding: utf-8 -*-
import json
import time
import importlib.util
from pathlib import Path

import requests
import trafilatura
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

ROOT = Path(r"D:\大创\anyclaw\docs\corpus")
CATALOG = ROOT / "longform_catalog.json"
JSONL = ROOT / "longform_fetched.jsonl"
OUT = ROOT / "讲好中国故事_官媒长文语料库_约100篇.docx"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36"
}

items = json.loads(CATALOG.read_text(encoding="utf-8"))
for it in items:
    if it["id"] == "A24":
        it["url"] = (
            "http://www.zj.xinhuanet.com/20250328/"
            "5d88775fca7840f18a087898c18c1977/c.html"
        )
CATALOG.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")

rows = {}
for line in JSONL.read_text(encoding="utf-8").splitlines():
    if line.strip():
        r = json.loads(line)
        rows[r["id"]] = r


def fetch_one(url: str):
    try:
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            resp = requests.get(url, headers=HEADERS, timeout=30, verify=False)
            if not resp.encoding or resp.encoding.lower() in ("iso-8859-1", "ascii"):
                resp.encoding = resp.apparent_encoding or "utf-8"
            downloaded = resp.text
        meta = trafilatura.bare_extraction(
            downloaded,
            include_comments=False,
            include_tables=False,
            favor_precision=True,
            url=url,
        )
        if meta is None:
            text = trafilatura.extract(downloaded, favor_precision=True, url=url) or ""
            title = ""
        elif isinstance(meta, dict):
            title = (meta.get("title") or "").strip()
            text = (meta.get("text") or "").strip()
        else:
            title = (getattr(meta, "title", None) or "").strip()
            text = (getattr(meta, "text", None) or "").strip()
        status = "ok" if text and len(text) >= 200 else "thin"
        return status, title, text
    except Exception as e:  # noqa: BLE001
        return f"error:{type(e).__name__}:{e}", "", ""


for it in items:
    rid = it["id"]
    cur = rows.get(rid, {})
    if rid == "A24" or cur.get("chars", 0) < 800:
        print("refetch", rid)
        st, title, text = fetch_one(it["url"])
        rows[rid] = {
            "id": rid,
            "section": it["section"],
            "url": it["url"],
            "catalog_title": it["title"],
            "fetched_title": title,
            "status": st,
            "text": text,
            "chars": len(text),
        }
        print(" ->", st, len(text))
        time.sleep(0.4)

with JSONL.open("w", encoding="utf-8") as f:
    for it in items:
        f.write(json.dumps(rows[it["id"]], ensure_ascii=False) + "\n")

spec = importlib.util.spec_from_file_location("bld", ROOT / "build_longform_corpus.py")
bld = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bld)
doc = bld.build_doc(items, list(rows.values()))
doc.save(OUT)

ok = sum(1 for it in items if rows[it["id"]]["status"] == "ok")
thin = sum(1 for it in items if rows[it["id"]]["status"] == "thin")
err = sum(1 for it in items if str(rows[it["id"]]["status"]).startswith("error"))
avg = sum(rows[it["id"]]["chars"] for it in items) / 100
print("final", ok, thin, err, "avg", avg)
(ROOT / "longform_fetch_summary.json").write_text(
    json.dumps(
        {
            "total": 100,
            "ok": ok,
            "thin": thin,
            "err": err,
            "avg_chars": avg,
            "section_A": 30,
            "section_B": 70,
            "docx": str(OUT),
        },
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)
print("saved", OUT)
