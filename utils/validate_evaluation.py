#!/usr/bin/env python3
"""Validate a ChinaStory Evaluation Part 3 result, with optional original text.

Usage:
  python utils/validate_evaluation.py evaluation.json --content-file original.txt

Requirement: python -m pip install jsonschema>=4; source file moved in v6.1
This checks structure and deterministic contracts; it does NOT establish fact accuracy,
quality of the six scores, or resistance to prompt injection at inference time.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

try:
    from jsonschema import Draft202012Validator
except ImportError as exc:
    raise SystemExit("Please install jsonschema: python -m pip install jsonschema>=4") from exc

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = PROJECT_ROOT / "eval" / "contracts" / "evaluation-result-v6.1.schema.json"
DIMENSION_IDS = {
    "cross_cultural_comprehensibility", "cultural_expression_quality",
    "audience_fit", "narrative_engagement_potential", "genre_platform_fit",
    "naturalness_non_sloganeering"
}


def validate_result(data: dict, content: str | None = None) -> list[str]:
    """Return a list of errors, empty when structure + semantics validate."""
    errors: list[str] = []
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    for err in sorted(validator.iter_errors(data), key=lambda x: (str(list(x.path)), x.message)):
        path = ".".join(map(str, err.absolute_path)) or "root"
        errors.append(f"Schema {path}: {err.message}")

    if not isinstance(data, dict):
        return errors

    status = data.get("status")
    dims = data.get("dimensions")
    if isinstance(dims, list):
        ids = [d.get("dimension_id") for d in dims if isinstance(d, dict)]
        if len(ids) != len(set(ids)):
            errors.append("Repeated dimension_id in dimensions[]")
        if status == "COMPLETED" and set(ids) != DIMENSION_IDS:
            missing = sorted(DIMENSION_IDS - set(ids))
            unexpected = sorted(set(ids) - DIMENSION_IDS, key=str)
            errors.append(f"COMPLETED requires exactly the six dimension IDs; missing={missing}; unexpected={unexpected}")
    else:
        dims = []

    if data.get("human_review") == "APPROVED":
        errors.append("Evaluation Skill cannot set final APPROVED status")

    if data.get("return_to_part1") is True and data.get("review_decision") == "READY_FOR_HUMAN_REVIEW":
        errors.append("Cannot return to Part 1 and simultaneously mark READY_FOR_HUMAN_REVIEW")
    if status == "RETURN_TO_PART1" and data.get("return_to_part1") is not True:
        errors.append("status=RETURN_TO_PART1 requires return_to_part1=true")
    if status == "INSUFFICIENT_CONTEXT" and data.get("execution_status") == "COMPLETED":
        errors.append("INSUFFICIENT_CONTEXT and execution_status=COMPLETED conflict")
    if status == "COMPLETED" and data.get("execution_status") not in (None, "COMPLETED"):
        errors.append("COMPLETED and differing execution_status conflict")

    if isinstance(data.get("audit"), dict):
        a = data["audit"]
        if a.get("rubric_version") != data.get("rubric_version"):
            errors.append("audit.rubric_version must equal top-level rubric_version")
        if content is not None and "content_sha256" in a:
            expected = hashlib.sha256(content.encode("utf-8")).hexdigest()
            if a["content_sha256"] != expected:
                errors.append("audit.content_sha256 does not match original text (UTF-8 SHA-256)")

    # The span offsets are Unicode codepoint indices of the unmodified content string.
    for i, d in enumerate(dims):
        if not isinstance(d, dict):
            continue
        conf = d.get("confidence", "MISSING")
        conf_status = d.get("confidence_status")
        if conf is None and conf_status not in (None, "UNCALIBRATED", "NOT_APPLICABLE"):
            errors.append(f"dimensions[{i}]: null confidence cannot be CALIBRATED")
        if isinstance(conf, (int, float)) and conf_status == "UNCALIBRATED":
            errors.append(f"dimensions[{i}]: confidence is numeric but marked UNCALIBRATED; use null")
        spans = d.get("evidence_spans", [])
        if isinstance(spans, list):
            for j, span in enumerate(spans):
                errors.extend(_span_errors(span, content, f"dimensions[{i}].evidence_spans[{j}]"))
    for i, suggestion in enumerate(data.get("revision_suggestions", []) or []):
        if isinstance(suggestion, dict) and "location" in suggestion:
            errors.extend(_span_errors(suggestion["location"], content, f"revision_suggestions[{i}].location"))

    return errors


def _span_errors(span: object, content: str | None, path: str) -> list[str]:
    if not isinstance(span, dict):
        return []  # JSON Schema catches the shape error
    start, end, text = span.get("start"), span.get("end"), span.get("text")
    if not isinstance(start, int) or isinstance(start, bool) or not isinstance(end, int) or isinstance(end, bool):
        return []
    if start < 0 or end <= start:
        return [f"{path}: invalid half-open span range [{start}:{end}]"]
    if content is None:
        return []
    if end > len(content):
        return [f"{path}: end offset {end} beyond content length {len(content)}"]
    if content[start:end] != text:
        return [f"{path}: content[{start}:{end}] does not match span.text"]
    return []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evaluation", type=Path, help="JSON evaluation result")
    parser.add_argument("--content-file", type=Path, help="Exact unmodified original content.text (UTF-8)")
    args = parser.parse_args(argv)
    data = json.loads(args.evaluation.read_text(encoding="utf-8"))
    content = args.content_file.read_text(encoding="utf-8") if args.content_file else None
    issues = validate_result(data, content)
    if issues:
        for issue in issues:
            print("FAIL", issue)
        return 1
    print("PASS: schema and deterministic semantics validated")
    if content is None:
        print("NOTE: span-text and content-sha256 verification skipped; pass --content-file to check them")
    print("NOTE: this does not validate news facts, score accuracy or human calibration")
    return 0


if __name__ == "__main__":
    sys.exit(main())
