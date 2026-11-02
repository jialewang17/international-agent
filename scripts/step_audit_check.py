#!/usr/bin/env python3
"""步骤审计复核 CLI：把"每一步都跑了吗、依据对不对"变成一条可执行的检查命令。

用法::

    # 1) 复核某次运行的审计 JSON（生成或评测）
    python scripts/step_audit_check.py trace.json

    # 2) 只检查步骤契约本身（依据锚点是否还在仓库里真实存在）
    python scripts/step_audit_check.py --evidence

    # 3) 打印「步骤 → 方法依据」对照表（写文档/汇报时直接用）
    python scripts/step_audit_check.py --index

    # 4) 严格模式：verdict 必须是 COMPLETE，否则退出码 1（可用于 CI / 交付前自检）
    python scripts/step_audit_check.py trace.json --require-complete

退出码：0 = 通过；1 = 有问题（逐条打印原因）。

本脚本只做确定性检查，不调用模型、不联网，也不修改任何文件。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.step_audit import (  # noqa: E402
    STEP_SPECS_BY_PIPELINE,
    VERTICT_COMPLETE,
    check_audit,
    evidence_index,
    evidence_problems,
    summarize,
)


def _print_index() -> None:
    rows = evidence_index(PROJECT_ROOT)
    current = None
    for row in rows:
        if row["step_id"] != current:
            current = row["step_id"]
            print(f"\n[{row['pipeline']}] {row['step_id']} {row['name']}")
        flag = "OK " if row["exists"] else "MISSING"
        print(f"  - {flag} {row['file']}  :: {row['anchor']}")
    print()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ChinaStory 步骤审计复核")
    parser.add_argument("trace", nargs="?", help="审计 JSON 文件（含 pipeline/steps/verdict）")
    parser.add_argument("--evidence", action="store_true", help="只校验步骤依据锚点")
    parser.add_argument("--index", action="store_true", help="打印步骤→依据对照表")
    parser.add_argument("--require-complete", action="store_true", help="verdict 必须为 COMPLETE")
    args = parser.parse_args(argv)

    exit_code = 0

    if args.index:
        _print_index()

    problems = evidence_problems(PROJECT_ROOT)
    if problems or args.evidence:
        if problems:
            print("步骤依据锚点校验：失败")
            for item in problems:
                print(f"  - {item}")
            exit_code = 1
        else:
            total = len(evidence_index(PROJECT_ROOT))
            print(f"步骤依据锚点校验：通过（{len(STEP_SPECS_BY_PIPELINE)} 条管线 / {total} 个锚点）")

    if args.trace:
        path = Path(args.trace)
        if not path.is_file():
            print(f"找不到审计文件：{path}")
            return 1
        data = json.loads(path.read_text(encoding="utf-8"))
        # 既接受裸审计（pipeline/steps/verdict 在顶层），也接受运行结果包装
        # （审计放在 step_audit 字段里，样例就是这种形态）。
        if isinstance(data, dict) and "pipeline" not in data and isinstance(data.get("step_audit"), dict):
            data = data["step_audit"]
        problems = check_audit(data)
        print(f"\n审计复核 {path.name}：{summarize(data)}")
        if problems:
            exit_code = 1
            for item in problems:
                print(f"  - {item}")
        else:
            print("  结构与状态自洽：通过")
        if args.require_complete and data.get("verdict") != VERTICT_COMPLETE:
            print(f"  - 要求 COMPLETE，实际 {data.get('verdict')}")
            exit_code = 1

    if not args.trace and not args.evidence and not args.index:
        parser.print_help()

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
