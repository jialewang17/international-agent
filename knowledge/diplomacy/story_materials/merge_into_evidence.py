"""Merge story packs into ../evidence.json."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence.json"
STORY_DIR = Path(__file__).resolve().parent
GITHUB_PACKS = ROOT / "story_kb_github" / "packs"

STORY_FILES = sorted(STORY_DIR.glob("story_evidence_v*.json"))
if GITHUB_PACKS.exists():
    packs = sorted(GITHUB_PACKS.glob("*.json"))
    if packs:
        STORY_FILES = packs


def main() -> None:
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    topics = evidence.setdefault("topics_raw", {})

    existing_sources = {
        (item.get("source"), item.get("statement"))
        for cat_items in topics.values()
        for item in cat_items
    }

    added = 0
    touched: set[str] = set()
    for story_path in STORY_FILES:
        story = json.loads(story_path.read_text(encoding="utf-8"))
        for item in story.get("items", []):
            cat = item["category"]
            topics.setdefault(cat, [])
            statement = item.get("statement_for_kb") or item.get("quote_en")
            source = item["url"]
            key = (source, statement)
            if key in existing_sources:
                continue
            row = {
                "statement": statement,
                "source": source,
                "theme": item.get("theme"),
                "category": cat,
                "source_type": item.get("source_type"),
                "id": item.get("id"),
                "quote_en": item.get("quote_en"),
                "quote_cn": item.get("quote_cn"),
                "tags": item.get("tags", []),
            }
            if item.get("creator"):
                row["creator"] = item["creator"]
            topics[cat].append(row)
            existing_sources.add(key)
            touched.add(cat)
            added += 1

    by_cat = evidence.setdefault("by_category", {})
    for cat in set(topics) | touched:
        by_cat[cat] = topics[cat]

    EVIDENCE.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    summary = {c: len(topics.get(c, [])) for c in sorted(touched)}
    print(f"Merged from {[p.name for p in STORY_FILES]}. Added {added}. counts={summary}")


if __name__ == "__main__":
    main()
