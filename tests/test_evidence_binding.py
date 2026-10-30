"""I2-C-002: Claim–Evidence binding loop tests.

All content is synthetic. No network access: the Token Plan client is driven
through an injected fake transport, and missing-credential behaviour is tested
against an empty environment mapping.
"""

from hashlib import sha256
from types import SimpleNamespace

import pytest

from api.claim_extraction import DeterministicClaimExtractor
from api.evidence_adapter import build_evidence_pack
from api.evidence_binding import (
    FACT_VERIFICATION_STATUS,
    PART_BINDING,
    STATUS_BLOCK,
    STATUS_PASS,
    STATUS_REVIEW,
    SUPPORT_CONTRADICTED,
    SUPPORT_DIRECT,
    SUPPORT_INFERRED,
    SUPPORT_UNSUPPORTED,
    EvidenceBinding,
    EvidenceBindingError,
    EvidenceBindingStore,
    derive_binding_id,
    evaluate_with_binding_gate,
    stale_binding_ids,
    validate_evidence_bindings,
)
from api.schemas import ContentVersion
from api.token_plan_client import (
    TOKEN_PLAN_MODEL_DEFAULT,
    TokenPlanClient,
    TokenPlanConfig,
    TokenPlanConfigError,
    TokenPlanResponseError,
)
from api.versioning import ContentVersionStore

BENCH_BODY = (
    "Suzhou produces more silk than Hangzhou. "
    "Suzhou embroidery sells well overseas."
)

E_ST_SILK = "Suzhou has produced more silk than Hangzhou since the Tang dynasty."
E_ST_EMBROIDERY = "Suzhou embroidery is exported to more than fifty countries."
E_ST_HANGZHOU = "Hangzhou is the capital of Zhejiang province."

NEWS_BODY = (
    "SUZHOU, China, Oct. 22 - Suzhou produces more silk than Hangzhou, "
    "according to local industry data. Suzhou embroidery sells well overseas, "
    "trade officials said on Wednesday."
)

POST_BODY = "Suzhou produces more silk than Hangzhou! #Silk #Suzhou"


# --------------------------------------------------------------------------- #
# fixtures
# --------------------------------------------------------------------------- #
def build_pack():
    rows = [
        {"statement": E_ST_SILK, "source": "Suzhou Industry Report 2024", "category": "economy"},
        {"statement": E_ST_EMBROIDERY, "source": "China Trade Yearbook", "category": "trade"},
        {"statement": E_ST_HANGZHOU, "source": "Zhejiang Gazetteer", "category": "geography"},
    ]
    return build_evidence_pack(rows)


def evidence_id_of(pack, statement):
    for item in pack.items:
        if item.statement == statement:
            return item.evidence_id
    raise AssertionError(f"statement not in pack: {statement!r}")


def claims_of(body):
    claims = DeterministicClaimExtractor().extract(body)
    assert claims
    return {c.claim_id: c for c in claims}


def digest_of(body):
    return sha256(body.encode("utf-8")).hexdigest()


def make_version(body, pack, claims, *, version_id="cv_binding_test", task_id="task-binding"):
    return ContentVersion(
        content_version_id=version_id,
        content=body,
        task_id=task_id,
        evidence_pack_id=pack.evidence_pack_id,
        claim_ids=list(claims),
    )


def make_binding(
    version,
    pack,
    claim_id,
    evidence_ids,
    support_type=SUPPORT_DIRECT,
    excerpts=(),
    note="",
):
    return EvidenceBinding(
        binding_id=derive_binding_id(
            version.content_version_id, claim_id, version.content
        ),
        content_version_id=version.content_version_id,
        content_sha256=sha256(
            version.content.encode("utf-8")
        ).hexdigest(),
        evidence_pack_id=pack.evidence_pack_id,
        claim_id=claim_id,
        evidence_ids=list(evidence_ids),
        excerpts=list(excerpts),
        support_type=support_type,
        uncertainty_note=note,
        judged_by="rule",
    )


def all_direct(version, pack, claims, mapping):
    """One DIRECT binding per claim; mapping: claim_id -> [evidence_id, ...]."""
    return [
        make_binding(version, pack, claim_id, ids)
        for claim_id, ids in mapping.items()
    ]


def bound_claims(claims, mapping):
    """Claims with evidence_ids filled in, as the existing Part 1 requires."""
    return {
        claim_id: claims[claim_id].model_copy(update={"evidence_ids": list(ids)})
        for claim_id, ids in mapping.items()
    }


class SpyJudge:
    """Part 3 judge that must never be called when a gate blocks."""

    def __init__(self):
        self.called = False
        self.name = "spy-judge"
        self.model = "spy"

    def judge(self, content, task_context, rubric):
        self.called = True
        raise AssertionError("Part 3 must not run behind a failed gate")


class FakeOpenAIShape:
    """Mimics client.chat.completions.create just enough for tests."""

    def __init__(self, payloads):
        self._payloads = list(payloads)
        self.calls = []
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(create=self._create)
        )

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        content = self._payloads.pop(0)
        message = SimpleNamespace(content=content)
        choice = SimpleNamespace(message=message)
        return SimpleNamespace(choices=[choice])


# --------------------------------------------------------------------------- #
# 1. one evidence directly supports one claim
# --------------------------------------------------------------------------- #
def test_01_single_evidence_direct_support_pass():
    pack = build_pack()
    claims = claims_of(BENCH_BODY)
    version = make_version(BENCH_BODY, pack, claims)
    ev_silk = evidence_id_of(pack, E_ST_SILK)
    ev_emb = evidence_id_of(pack, E_ST_EMBROIDERY)

    bindings = all_direct(
        version, pack, claims,
        {c: [ev_silk if "silk" in claims[c].text else ev_emb] for c in claims},
    )
    result = validate_evidence_bindings(BENCH_BODY, version, pack, claims, bindings)

    assert result.status == STATUS_PASS
    assert result.blocking_issues == []
    assert result.review_issues == []
    assert result.fact_verification_status == FACT_VERIFICATION_STATUS
    assert result.verified is False


# --------------------------------------------------------------------------- #
# 2. multiple evidence jointly support one claim (many-to-many)
# --------------------------------------------------------------------------- #
def test_02_multiple_evidence_joint_support_many_to_many():
    pack = build_pack()
    claims = claims_of(BENCH_BODY)
    version = make_version(BENCH_BODY, pack, claims)
    ev_silk = evidence_id_of(pack, E_ST_SILK)
    ev_emb = evidence_id_of(pack, E_ST_EMBROIDERY)

    silk_claim = next(c for c in claims.values() if "silk" in c.text)
    bindings = [
        make_binding(version, pack, silk_claim.claim_id, [ev_silk, ev_emb]),
    ] + [
        make_binding(version, pack, cid, [ev_emb])
        for cid in claims
        if cid != silk_claim.claim_id
    ]

    result = validate_evidence_bindings(BENCH_BODY, version, pack, claims, bindings)

    assert result.status == STATUS_PASS
    # the same evidence id backs two different claims: many-to-many holds
    assert sum(1 for c in claims if c != silk_claim.claim_id) >= 1


# --------------------------------------------------------------------------- #
# 3. claim references a non-existent evidence id
# --------------------------------------------------------------------------- #
def test_03_unknown_evidence_id_blocks():
    pack = build_pack()
    claims = claims_of(BENCH_BODY)
    version = make_version(BENCH_BODY, pack, claims)

    bindings = [
        make_binding(version, pack, cid, ["ev_does_not_exist"])
        for cid in claims
    ]
    result = validate_evidence_bindings(BENCH_BODY, version, pack, claims, bindings)

    assert result.status == STATUS_BLOCK
    assert result.unknown_evidence_ids == ["ev_does_not_exist"]
    assert any("unknown evidence id" in i for i in result.blocking_issues)


# --------------------------------------------------------------------------- #
# 4. claim without any supporting evidence
# --------------------------------------------------------------------------- #
def test_04_claim_without_evidence_is_review_not_pass():
    pack = build_pack()
    claims = claims_of(BENCH_BODY)
    version = make_version(BENCH_BODY, pack, claims)

    bindings = [
        make_binding(version, pack, cid, [], support_type=SUPPORT_UNSUPPORTED,
                     note="no evidence found")
        for cid in claims
    ]
    result = validate_evidence_bindings(BENCH_BODY, version, pack, claims, bindings)

    assert result.status == STATUS_REVIEW
    assert set(result.unsupported_claim_ids) == set(claims)
    assert any("insufficient evidence support" in i for i in result.review_issues)


# --------------------------------------------------------------------------- #
# 5. evidence contradicts the claim - conflict kept, never auto-resolved
# --------------------------------------------------------------------------- #
def test_05_conflicting_evidence_retained_not_resolved():
    pack = build_pack()
    claims = claims_of(BENCH_BODY)
    version = make_version(BENCH_BODY, pack, claims)
    ev_hangzhou = evidence_id_of(pack, E_ST_HANGZHOU)

    bindings = [
        make_binding(
            version, pack, cid, [ev_hangzhou],
            support_type=SUPPORT_CONTRADICTED,
            note="conflicting source kept for human review",
        )
        for cid in claims
    ]
    result = validate_evidence_bindings(BENCH_BODY, version, pack, claims, bindings)

    assert result.status == STATUS_REVIEW
    assert set(result.conflicted_claim_ids) == set(claims)
    # the conflicting evidence stays inside the binding record
    assert all(b.evidence_ids == [ev_hangzhou] for b in bindings)
    assert any("conflict retained" in i for i in result.review_issues)
    assert result.status != STATUS_PASS


# --------------------------------------------------------------------------- #
# 6. factual claim in content but evidence_map misses it
# --------------------------------------------------------------------------- #
def test_06_unmapped_factual_claim_blocks():
    pack = build_pack()
    claims = claims_of(BENCH_BODY)
    version = make_version(BENCH_BODY, pack, claims)
    ev_silk = evidence_id_of(pack, E_ST_SILK)

    silk_claim = next(c for c in claims.values() if "silk" in c.text)
    bindings = [make_binding(version, pack, silk_claim.claim_id, [ev_silk])]

    result = validate_evidence_bindings(BENCH_BODY, version, pack, claims, bindings)

    assert result.status == STATUS_BLOCK
    assert len(result.unmapped_claim_ids) == len(claims) - 1
    assert any("unmapped factual claim" in i for i in result.blocking_issues)


# --------------------------------------------------------------------------- #
# 7. revision invalidates the old bindings; they are not reused
# --------------------------------------------------------------------------- #
def test_07_revision_invalidates_old_bindings():
    pack = build_pack()
    claims = claims_of(BENCH_BODY)
    version_store = ContentVersionStore()
    parent = version_store.create_initial_version(
        "task-binding", BENCH_BODY,
        evidence_pack_id=pack.evidence_pack_id,
        claim_ids=list(claims),
    )
    ev_silk = evidence_id_of(pack, E_ST_SILK)
    parent_bindings = all_direct(
        parent, pack, claims, {c: [ev_silk] for c in claims}
    )
    store = EvidenceBindingStore()
    store.put_many(parent_bindings)
    assert len(store) == len(claims)

    revised = BENCH_BODY.replace("more silk", "slightly more silk")
    child_claims = claims_of(revised)
    child = version_store.create_revision(
        parent.content_version_id, revised,
        claim_ids=list(child_claims),
    )

    # the parent bindings are stale for the child document state
    stale = stale_binding_ids(child, child_claims, store.for_version(parent.content_version_id))
    assert len(stale) == len(parent_bindings)

    # reusing them fails closed: content digest mismatch blocks
    reused = [
        b.model_copy(update={
            "content_version_id": child.content_version_id,
            "binding_id": derive_binding_id(
                child.content_version_id, b.claim_id,
                sha256(revised.encode("utf-8")).hexdigest(),
            ),
        })
        for b in parent_bindings
    ]
    result = validate_evidence_bindings(revised, child, pack, child_claims, reused)
    assert result.status == STATUS_BLOCK
    assert any("stale binding" in i for i in result.blocking_issues)

    # fresh bindings built on the child content pass again
    fresh = all_direct(child, pack, child_claims, {c: [ev_silk] for c in child_claims})
    ok = validate_evidence_bindings(revised, child, pack, child_claims, fresh)
    assert ok.status == STATUS_PASS


# --------------------------------------------------------------------------- #
# 8. explanatory inference must not be treated as a direct fact
# --------------------------------------------------------------------------- #
def test_08_inference_is_review_and_never_verified_fact():
    pack = build_pack()
    claims = claims_of(BENCH_BODY)
    version = make_version(BENCH_BODY, pack, claims)
    ev_silk = evidence_id_of(pack, E_ST_SILK)

    bindings = [
        make_binding(version, pack, cid, [ev_silk],
                     support_type=SUPPORT_INFERRED,
                     note="inferred from silk output comparison")
        for cid in claims
    ]
    result = validate_evidence_bindings(BENCH_BODY, version, pack, claims, bindings)

    assert result.status == STATUS_REVIEW
    assert set(result.inferred_claim_ids) == set(claims)
    assert any("indirect inference" in i for i in result.review_issues)
    assert result.fact_verification_status == FACT_VERIFICATION_STATUS == "NOT_VERIFIED"
    assert result.verified is False


# --------------------------------------------------------------------------- #
# 9. normal news release passes the binding gate
# --------------------------------------------------------------------------- #
def test_09_normal_news_release_passes():
    pack = build_pack()
    claims = claims_of(NEWS_BODY)
    version = make_version(NEWS_BODY, pack, claims, version_id="cv_news")
    ev_silk = evidence_id_of(pack, E_ST_SILK)
    ev_emb = evidence_id_of(pack, E_ST_EMBROIDERY)

    bindings = [
        make_binding(
            version, pack, cid,
            [ev_silk if "silk" in claims[cid].text else ev_emb],
        )
        for cid in claims
    ]
    result = validate_evidence_bindings(NEWS_BODY, version, pack, claims, bindings)

    assert result.status == STATUS_PASS
    assert result.content_version_id == "cv_news"


# --------------------------------------------------------------------------- #
# 10. normal social post passes the binding gate
# --------------------------------------------------------------------------- #
def test_10_normal_social_post_passes():
    pack = build_pack()
    claims = claims_of(POST_BODY)
    version = make_version(POST_BODY, pack, claims, version_id="cv_post")
    ev_silk = evidence_id_of(pack, E_ST_SILK)

    bindings = all_direct(version, pack, claims, {c: [ev_silk] for c in claims})
    result = validate_evidence_bindings(POST_BODY, version, pack, claims, bindings)

    assert result.status == STATUS_PASS


# --------------------------------------------------------------------------- #
# store behaviour
# --------------------------------------------------------------------------- #
def test_11_store_roundtrip_deep_copy_and_collision():
    pack = build_pack()
    claims = claims_of(BENCH_BODY)
    version = make_version(BENCH_BODY, pack, claims)
    ev_silk = evidence_id_of(pack, E_ST_SILK)

    store = EvidenceBindingStore()
    first = make_binding(version, pack, next(iter(claims)), [ev_silk])
    stored = store.put(first)

    assert stored == first
    assert stored is not first
    assert store.get(version.content_version_id, first.claim_id) == first
    assert len(store.for_version(version.content_version_id)) == 1

    conflicting = make_binding(
        version, pack, first.claim_id, [evidence_id_of(pack, E_ST_EMBROIDERY)]
    )
    with pytest.raises(EvidenceBindingError):
        store.put(conflicting)

    # unknown support_type never enters the store
    with pytest.raises(EvidenceBindingError):
        store.put(
            first.model_copy(update={"support_type": "TRUST_ME"})
        )

    # unknown support_type is also a gate block, not a crash
    claims_map = claims
    result = validate_evidence_bindings(
        BENCH_BODY, version, pack, claims_map,
        [first.model_copy(update={"support_type": "TRUST_ME"})],
    )
    assert result.status == STATUS_BLOCK


def test_12_excerpt_mismatch_blocks():
    pack = build_pack()
    claims = claims_of(BENCH_BODY)
    version = make_version(BENCH_BODY, pack, claims)
    ev_silk = evidence_id_of(pack, E_ST_SILK)

    bindings = [
        make_binding(
            version, pack, cid, [ev_silk], excerpts=["fabricated quote"]
        )
        for cid in claims
    ]
    result = validate_evidence_bindings(BENCH_BODY, version, pack, claims, bindings)

    assert result.status == STATUS_BLOCK
    assert any("not a substring" in i for i in result.blocking_issues)

    # verbatim excerpts are accepted
    good = [
        make_binding(version, pack, cid, [ev_silk], excerpts=[E_ST_SILK])
        for cid in claims
    ]
    assert validate_evidence_bindings(
        BENCH_BODY, version, pack, claims, good
    ).status == STATUS_PASS


# --------------------------------------------------------------------------- #
# orchestrator: gate ordering
# --------------------------------------------------------------------------- #
def test_13_blocked_binding_gate_never_reaches_part3():
    pack = build_pack()
    claims = claims_of(BENCH_BODY)
    store = ContentVersionStore()
    version = store.create_initial_version(
        "task-gate", BENCH_BODY,
        evidence_pack_id=pack.evidence_pack_id,
        claim_ids=list(claims),
    )
    ev_silk = evidence_id_of(pack, E_ST_SILK)
    # Part 1 needs claim.evidence_ids bound; the binding gate audits the
    # separate LLM binding graph on top of that.
    part1_claims = bound_claims(claims, {c: [ev_silk] for c in claims})
    judge = SpyJudge()

    # zero bindings -> unmapped claims -> BLOCK
    part1, gate, final = evaluate_with_binding_gate(
        version.content_version_id, store, part1_claims, pack, [],
        judge=judge, evaluation_id="eval-gate-block",
    )

    assert part1.status == "PASS"
    assert gate is not None and gate.status == STATUS_BLOCK
    assert final.status == "BLOCKED"
    assert final.part == PART_BINDING
    assert judge.called is False


def test_14_passing_gate_reaches_part3():
    pack = build_pack()
    claims = claims_of(BENCH_BODY)
    store = ContentVersionStore()
    version = store.create_initial_version(
        "task-gate", BENCH_BODY,
        evidence_pack_id=pack.evidence_pack_id,
        claim_ids=list(claims),
    )
    ev_silk = evidence_id_of(pack, E_ST_SILK)
    part1_claims = bound_claims(claims, {c: [ev_silk] for c in claims})
    bindings = all_direct(version, pack, claims, {c: [ev_silk] for c in claims})

    part1, gate, final = evaluate_with_binding_gate(
        version.content_version_id, store, part1_claims, pack, bindings,
        judge=None,  # no judge configured -> Part 3 returns INSUFFICIENT_CONTEXT
        evaluation_id="eval-gate-pass",
    )

    assert part1.status == "PASS"
    assert gate.status == STATUS_PASS
    # reaching Part 3 is exactly what INSUFFICIENT_CONTEXT proves here
    assert final.status == "INSUFFICIENT_CONTEXT"
    assert final.part == "evaluation"  # orchestrator-level part label


def test_15_part1_block_skips_binding_gate_entirely():
    pack = build_pack()
    store = ContentVersionStore()
    empty = store.create_initial_version(
        "task-empty", BENCH_BODY,
        evidence_pack_id=pack.evidence_pack_id,
        claim_ids=[],  # zero claims -> existing Part 1 blocks
    )

    part1, gate, final = evaluate_with_binding_gate(
        empty.content_version_id, store, {}, pack, [],
    )

    assert part1.status == "BLOCKED"
    assert gate is None
    assert final is part1
    assert final.return_to_part1 is True


# --------------------------------------------------------------------------- #
# token plan client (no network)
# --------------------------------------------------------------------------- #
def test_16_missing_credentials_fail_closed():
    with pytest.raises(TokenPlanConfigError) as exc:
        TokenPlanConfig.from_env(env={})
    assert "TOKEN_PLAN_API_KEY" in str(exc.value)

    with pytest.raises(TokenPlanConfigError) as exc:
        TokenPlanConfig.from_env(env={"TOKEN_PLAN_API_KEY": "x"})
    assert "TOKEN_PLAN_BASE_URL" in str(exc.value)

    # model default applies when only the two required vars are present
    config = TokenPlanConfig.from_env(env={
        "TOKEN_PLAN_API_KEY": "secret-key",
        "TOKEN_PLAN_BASE_URL": "https://example.invalid/v1",
    })
    assert config.model == TOKEN_PLAN_MODEL_DEFAULT == "qwen3.7-plus"


def test_17_client_builds_bindings_from_model_verdicts():
    pack = build_pack()
    claims = claims_of(BENCH_BODY)
    version = make_version(BENCH_BODY, pack, claims)
    ev_silk = evidence_id_of(pack, E_ST_SILK)
    ev_emb = evidence_id_of(pack, E_ST_EMBROIDERY)

    verdicts = []
    for claim in claims.values():
        evidence_id = ev_silk if "silk" in claim.text else ev_emb
        verdicts.append(
            '{"evidence_ids": ["%s"], "excerpts": [], '
            '"support_type": "DIRECT_SUPPORT", "uncertainty_note": "clear"}'
            % evidence_id
        )
    transport = FakeOpenAIShape(verdicts)
    config = TokenPlanConfig(
        api_key="k", base_url="https://example.invalid/v1", model="test-model"
    )
    client = TokenPlanClient(config, transport=transport)

    bindings = client.build_bindings(BENCH_BODY, version, pack, claims)

    assert len(bindings) == len(claims)
    assert all(b.judged_by == "llm" for b in bindings)
    assert all(
        b.support_type == SUPPORT_DIRECT and b.uncertainty_note == "clear"
        for b in bindings
    )
    # bindings are bound to exactly this document state
    digest = digest_of(BENCH_BODY)
    assert all(b.content_sha256 == digest for b in bindings)
    # the verdicts pass the gate
    result = validate_evidence_bindings(BENCH_BODY, version, pack, claims, bindings)
    assert result.status == STATUS_PASS
    # temperature is pinned to 0 for reproducibility
    assert all(call["temperature"] == 0 for call in transport.calls)


def test_18_garbage_model_output_is_rejected():
    config = TokenPlanConfig(
        api_key="k", base_url="https://example.invalid/v1", model="m"
    )
    client = TokenPlanClient(config, transport=FakeOpenAIShape(["not json at all"]))
    with pytest.raises(TokenPlanResponseError):
        client.judge("some claim", [{"evidence_id": "e1", "statement": "s"}])

    client2 = TokenPlanClient(
        config,
        transport=FakeOpenAIShape([
            '{"evidence_ids": ["e1"], "support_type": "MAKE_IT_PASS"}'
        ]),
    )
    with pytest.raises(TokenPlanResponseError):
        client2.judge("some claim", [{"evidence_id": "e1", "statement": "s"}])


def test_19_api_key_never_leaks_through_repr():
    config = TokenPlanConfig(
        api_key="super-secret-value", base_url="https://x/v1", model="m"
    )
    assert "super-secret-value" not in repr(config)
    assert "<redacted" in repr(config)
