"""Single-call Token Plan smoke test (I2-C-002).

Reads credentials from the environment only:
    TOKEN_PLAN_API_KEY / TOKEN_PLAN_BASE_URL / TOKEN_PLAN_MODEL

Exit codes:
    0 - call succeeded and the verdict was parsed
    2 - configuration missing/invalid (the missing variable names are printed;
        the key itself is never printed)
    3 - call or response failed
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.token_plan_client import (  # noqa: E402
    TokenPlanClient,
    TokenPlanConfig,
    TokenPlanConfigError,
    TokenPlanResponseError,
)


def main() -> int:
    try:
        config = TokenPlanConfig.from_env()
    except TokenPlanConfigError as exc:
        print(f"SMOKE TEST BLOCKED: {exc}")
        return 2

    client = TokenPlanClient(config)

    claim_text = "Suzhou produces more silk than Hangzhou."
    evidence_items = [
        {
            "evidence_id": "ev_smoke_1",
            "statement": "Suzhou has produced more silk than Hangzhou since the Tang dynasty.",
        },
        {
            "evidence_id": "ev_smoke_2",
            "statement": "Hangzhou is the capital of Zhejiang province.",
        },
    ]

    print(f"model={config.model} base_url={config.base_url} api_key=<redacted>")
    try:
        verdict = client.judge(claim_text, evidence_items)
    except TokenPlanResponseError as exc:
        print(f"SMOKE TEST FAILED: {exc}")
        return 3

    print("SMOKE TEST OK — parsed verdict:")
    print(f"  support_type    = {verdict['support_type']}")
    print(f"  evidence_ids    = {verdict['evidence_ids']}")
    print(f"  excerpts        = {verdict['excerpts']}")
    print(f"  uncertainty_note= {verdict['uncertainty_note'][:120]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
