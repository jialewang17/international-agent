# -*- coding: utf-8 -*-
import json
import re
from collections import Counter
from pathlib import Path

rows = [
    json.loads(l)
    for l in Path(r"D:\大创\anyclaw\docs\corpus\longform_fetched.jsonl")
    .read_text(encoding="utf-8")
    .splitlines()
    if l.strip()
]
phrases = [
    "win-win",
    "clean energy",
    "rural revitalization",
    "ecological",
    "herder",
    "photovoltaic",
    "desertification",
    "livelihood",
    "green development",
    "microclimate",
    "forage",
    "common prosperity",
    "Belt and Road",
    "modernization",
    "virtuous cycle",
    "ecology-first",
]
c = Counter()
quotes = 0
for r in rows:
    if r["section"] != "B":
        continue
    t = r.get("text") or ""
    tl = t.lower()
    for p in phrases:
        if p.lower() in tl:
            c[p] += 1
    quotes += len(re.findall(r'"[^"]{15,200}"', t))
out = Path(r"D:\大创\anyclaw\docs\corpus\_pattern_mine.txt")
lines = ["phrase hits B: " + str(c.most_common()), f"quotes~ {quotes}"]
for rid in ["B28", "B08", "B16", "A05", "A02", "A19"]:
    r = next(x for x in rows if x["id"] == rid)
    paras = [p.strip() for p in (r.get("text") or "").split("\n") if p.strip()]
    lines.append(f"\n## {rid} paras={len(paras)} chars={r['chars']}")
    for i, p in enumerate(paras[:8]):
        lines.append(f"P{i+1}: {p[:220]}")
out.write_text("\n".join(lines), encoding="utf-8")
print("wrote", out)
