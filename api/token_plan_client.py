"""OpenAI-compatible client for the Token Plan judging service.

Safety rules enforced here:

* Credentials come **only** from environment variables
  (``TOKEN_PLAN_API_KEY`` / ``TOKEN_PLAN_BASE_URL`` / ``TOKEN_PLAN_MODEL``).
  Missing variables fail closed; the key is never logged, never put in
  ``repr``, never written to disk, never echoed in errors.
* The project has not published a Token Plan compatible base URL yet, so the
  default is empty and the client refuses to run without an explicit one
  (``TOKEN_PLAN_BASE_URL``). No fabricated endpoint.
* The model output is *untrusted*: every parsed verdict must pass the
  :mod:`api.evidence_binding` validation before it can become a stored
  binding. The client never writes to a store itself.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Mapping, Optional, Protocol, Sequence

from api.evidence_binding import (
    EvidenceBinding,
    EvidenceBindingError,
    SUPPORT_CONTRADICTED,
    SUPPORT_DIRECT,
    SUPPORT_INFERRED,
    SUPPORT_TYPES,
    SUPPORT_UNSUPPORTED,
    derive_binding_id,
)
from api.schemas import Claim, ContentVersion, EvidencePack

__all__ = [
    "TokenPlanConfigError",
    "TokenPlanResponseError",
    "TokenPlanConfig",
    "SupportJudge",
    "TokenPlanClient",
    "TOKEN_PLAN_MODEL_DEFAULT",
    "SUPPORT_TYPE_INSTRUCTIONS",
]

#: Default test model required by the task.
TOKEN_PLAN_MODEL_DEFAULT = "qwen3.7-plus"

#: The project has not published a Token Plan compatible base URL yet.
#: Empty default = fail closed; TOKEN_PLAN_BASE_URL must be provided.
TOKEN_PLAN_BASE_URL_DEFAULT = ""

_API_KEY_ENV = "TOKEN_PLAN_API_KEY"
_BASE_URL_ENV = "TOKEN_PLAN_BASE_URL"
_MODEL_ENV = "TOKEN_PLAN_MODEL"

SUPPORT_TYPE_INSTRUCTIONS = (
    f"{SUPPORT_DIRECT}: at least one evidence statement directly states the "
    "claim;\n"
    f"{SUPPORT_INFERRED}: the claim is an explanatory inference from the "
    "evidence, not stated outright;\n"
    f"{SUPPORT_CONTRADICTED}: at least one evidence statement conflicts with "
    "the claim;\n"
    f"{SUPPORT_UNSUPPORTED}: no evidence gives sufficient support."
)


class TokenPlanConfigError(RuntimeError):
    """Missing or invalid Token Plan configuration. Never includes the key."""


class TokenPlanResponseError(RuntimeError):
    """The model returned something that is not a usable verdict."""


class SupportJudge(Protocol):
    """Anything that can produce one raw support verdict for one claim."""

    def judge(
        self, claim_text: str, evidence_items: Sequence[Mapping[str, str]]
    ) -> Dict[str, Any]: ...


class TokenPlanConfig:
    """Immutable, masked credential bundle read from the environment."""

    __slots__ = ("api_key", "base_url", "model")

    def __init__(self, api_key: str, base_url: str, model: str) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.model = model

    @classmethod
    def from_env(cls, env: Optional[Mapping[str, str]] = None) -> "TokenPlanConfig":
        source = os.environ if env is None else env
        api_key = (source.get(_API_KEY_ENV) or "").strip()
        base_url = (source.get(_BASE_URL_ENV) or TOKEN_PLAN_BASE_URL_DEFAULT).strip()
        model = (source.get(_MODEL_ENV) or TOKEN_PLAN_MODEL_DEFAULT).strip()

        missing = [
            name
            for name, value in (
                (_API_KEY_ENV, api_key),
                (_BASE_URL_ENV, base_url),
            )
            if not value
        ]
        if missing:
            raise TokenPlanConfigError(
                f"missing required environment variable(s): {', '.join(missing)}"
            )
        if not model:
            raise TokenPlanConfigError(
                f"{_MODEL_ENV} must not be blank when set"
            )
        return cls(api_key=api_key, base_url=base_url, model=model)

    def __repr__(self) -> str:  # the key must never leak through repr
        return (
            f"TokenPlanConfig(api_key=<redacted {len(self.api_key)} chars>, "
            f"base_url={self.base_url!r}, model={self.model!r})"
        )


def _mask_error(exc: Exception) -> str:
    """Flatten an SDK exception without echoing request headers/keys."""
    return type(exc).__name__ + ": " + str(exc).splitlines()[0][:200]


class TokenPlanClient:
    """Thin OpenAI-compatible client; ``transport`` is injectable for tests."""

    def __init__(
        self,
        config: TokenPlanConfig,
        transport: Optional[Any] = None,
    ) -> None:
        self._config = config
        if transport is None:
            try:
                from openai import OpenAI  # imported lazily; never at import time
            except Exception as exc:  # pragma: no cover - depends on env
                raise TokenPlanConfigError(
                    f"openai package unavailable: {_mask_error(exc)}"
                ) from exc
            self._client = OpenAI(
                api_key=config.api_key,
                base_url=config.base_url,
            )
        else:
            self._client = transport

    @property
    def model(self) -> str:
        return self._config.model

    # ------------------------------------------------------------------ #
    # prompt / parse
    # ------------------------------------------------------------------ #
    @staticmethod
    def evidence_menu(pack: EvidencePack) -> List[Dict[str, str]]:
        """Prompt-side view of the pack: ids + statements, nothing else."""
        return [
            {"evidence_id": item.evidence_id, "statement": item.statement}
            for item in pack.items
        ]

    @staticmethod
    def _build_prompt(claim_text: str, evidence_items: Sequence[Mapping[str, str]]) -> str:
        lines = [f"- {item['evidence_id']}: {item['statement']}" for item in evidence_items]
        return (
            "You are a strict fact-support checker. Decide how the EVIDENCE "
            "relates to the CLAIM. Never invent evidence ids; only use the ids "
            "listed below. Quote evidence verbatim for excerpts (exact "
            "substrings).\n\n"
            "SUPPORT TYPES:\n"
            f"{SUPPORT_TYPE_INSTRUCTIONS}\n\n"
            "CLAIM:\n"
            f"{claim_text}\n\n"
            "EVIDENCE:\n"
            + ("\n".join(lines) if lines else "(no evidence items)")
            + "\n\n"
            'Answer with STRICT JSON only: {"evidence_ids": ["..."], '
            '"excerpts": ["..."], "support_type": "...", '
            '"uncertainty_note": "..."}'
        )

    @staticmethod
    def _parse_verdict(raw: str) -> Dict[str, Any]:
        text = (raw or "").strip()
        # Tolerate a fenced code block, but nothing else.
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise TokenPlanResponseError(f"model output is not JSON: {exc}") from exc
        if not isinstance(payload, dict):
            raise TokenPlanResponseError("model output is not a JSON object")

        support_type = str(payload.get("support_type") or "").strip()
        if support_type not in SUPPORT_TYPES:
            raise TokenPlanResponseError(
                f"unknown support_type in model output: {support_type!r}"
            )

        evidence_ids = payload.get("evidence_ids") or []
        excerpts = payload.get("excerpts") or []
        if not isinstance(evidence_ids, list) or any(
            not isinstance(e, str) or not e.strip() for e in evidence_ids
        ):
            raise TokenPlanResponseError("evidence_ids must be a list of strings")
        if not isinstance(excerpts, list) or any(
            not isinstance(e, str) for e in excerpts
        ):
            raise TokenPlanResponseError("excerpts must be a list of strings")

        return {
            "evidence_ids": list(dict.fromkeys(evidence_ids)),
            "excerpts": [str(e) for e in excerpts],
            "support_type": support_type,
            "uncertainty_note": str(payload.get("uncertainty_note") or ""),
        }

    # ------------------------------------------------------------------ #
    # public verdict API
    # ------------------------------------------------------------------ #
    def judge(
        self, claim_text: str, evidence_items: Sequence[Mapping[str, str]]
    ) -> Dict[str, Any]:
        """One model call; returns the parsed (still untrusted) verdict."""
        prompt = self._build_prompt(claim_text, evidence_items)
        try:
            response = self._client.chat.completions.create(
                model=self._config.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a fact-support checker. Output strict "
                            "JSON only."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0,
            )
        except Exception as exc:
            raise TokenPlanResponseError(
                f"token plan call failed: {_mask_error(exc)}"
            ) from exc

        try:
            raw = response.choices[0].message.content or ""
        except (AttributeError, IndexError) as exc:
            raise TokenPlanResponseError(
                f"unexpected response shape: {_mask_error(exc)}"
            ) from exc
        return self._parse_verdict(raw)

    def build_bindings(
        self,
        content: str,
        version: ContentVersion,
        pack: EvidencePack,
        claims: Mapping[str, Claim],
    ) -> List[EvidenceBinding]:
        """Judge every claim of one version and return validated bindings.

        Every verdict is converted into an :class:`EvidenceBinding` with a
        deterministic id bound to ``(version, claim, content digest)``. The
        result is *not* stored here and has *not* been gate-checked; the caller
        must run :func:`validate_evidence_bindings` before trusting it.
        """
        from hashlib import sha256 as _sha256

        digest = _sha256(content.encode("utf-8")).hexdigest()
        menu = self.evidence_menu(pack)

        bindings: List[EvidenceBinding] = []
        for claim_id in version.claim_ids:
            claim = claims.get(claim_id)
            if claim is None:
                raise EvidenceBindingError(f"missing claim: {claim_id}")
            verdict = self.judge(claim.text, menu)
            bindings.append(
                EvidenceBinding(
                    binding_id=derive_binding_id(
                        version.content_version_id, claim_id, digest
                    ),
                    content_version_id=version.content_version_id,
                    content_sha256=digest,
                    evidence_pack_id=pack.evidence_pack_id,
                    claim_id=claim_id,
                    evidence_ids=verdict["evidence_ids"],
                    excerpts=verdict["excerpts"],
                    support_type=verdict["support_type"],
                    uncertainty_note=verdict["uncertainty_note"],
                    judged_by="llm",
                )
            )
        return bindings
