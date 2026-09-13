"""冒烟测试：语义检索是否命中美食/文化论据。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.kb_local import retrieve_statements


SAMPLES = [
    (
        "Chinese food abroad is just greasy takeout. Real Chinese cuisine is boring.",
        ["food"],
    ),
    (
        "Chinese New Year is just shopping and fireworks. No real culture left.",
        ["culture"],
    ),
    (
        "Foreign YouTubers filming Chinese street food are paid propaganda.",
        ["celebrity", "food"],
    ),
]


def main() -> None:
    for q, cats in SAMPLES:
        print("=" * 60)
        print("Q:", q)
        print("cats:", cats)
        hits = retrieve_statements(cats, limit_per_cat=2, query=q)
        print(json.dumps(hits, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
