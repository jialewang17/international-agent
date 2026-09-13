"""从 evidence.json 构建 Chroma 向量库。

用法:
  cd D:\\大创\\anyclaw
  .\\venv\\Scripts\\activate
  python scripts/build_chroma_kb.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.chroma_kb import build_chroma_kb


def main() -> None:
    print("Building Chroma KB from evidence.json ...")
    print("(First run may download Chroma ONNX MiniLM ~80MB.)")
    info = build_chroma_kb(reset=True)
    print(json.dumps(info, ensure_ascii=False, indent=2))
    print("Done.")


if __name__ == "__main__":
    main()
