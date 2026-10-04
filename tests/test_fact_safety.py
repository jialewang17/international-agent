"""P0.5 Fact Safety — deterministic, fail-closed checks for direct revisions.

Each test maps to the accepted P0.5 semantics. Fail-closed behaviour is asserted
explicitly (raises or ``status == "locked"``); happy paths are asserted too so a
silent "lock everything" regression cannot pass.
"""
import pytest

from api.fact_safety import (
    ClaimIdentityRegistry,
    ClaimIdentityViolation,
    FactSafetyError,
    analyze_revision,
)
from api.schemas import Claim, EvidenceItem, EvidencePack, EvidenceSpan, Source
from api.versioning import ContentVersionStore


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def make_pack(pack_id: str = "pack") -> EvidencePack:
    """An evidence pack whose only evidence (``e1``) is fully traceable."""
    return EvidencePack(
        evidence_pack_id=pack_id,
        sources=[Source(source_id="s1")],
        items=[
            EvidenceItem(
                evidence_id="e1",
                source_id="s1",
                statement="fact",
                spans=[EvidenceSpan(span_id="sp", source_id="s1", text="fact")],
            )
        ],
    )


def build(parent_claim_ids, child_claim_ids, *, task_id="t", pack_id="pack"):
    """initial version (parent) -> revision (child), both on the same task."""
    store = ContentVersionStore()
    parent = store.create_initial_version(
        task_id, "parent", evidence_pack_id=pack_id, claim_ids=list(parent_claim_ids)
    )
    child = store.create_revision(
        parent.content_version_id, "child", claim_ids=list(child_claim_ids)
    )
    return store, parent, child


def registry_with(claims) -> ClaimIdentityRegistry:
    registry = ClaimIdentityRegistry()
    for claim in claims:
        registry.register(claim)
    return registry


# --------------------------------------------------------------------------- #
# TEST 1 — parent-aware diff (no evidence is inferred from diff alone)
# --------------------------------------------------------------------------- #
def test_parent_aware_diff():
    store, parent, child = build(["c1", "c2"], ["c1", "c2", "c3"])
    claims = {c: Claim(claim_id=c, text=c) for c in ["c1", "c2", "c3"]}
    registry = registry_with([claims["c1"], claims["c2"]])

    # No evidence pack passed on purpose: c3 is added, so it can never be safe.
    result = analyze_revision(child.content_version_id, store, claims, None, registry)

    assert result.retained_claim_ids == ["c1", "c2"]
    assert result.removed_claim_ids == []
    assert result.added_claim_ids == ["c3"]
    # The diff itself must not be read as "safe".
    assert result.status == "locked"


# --------------------------------------------------------------------------- #
# TEST 2 — traceable added claim -> safe, and committed for the next generation
# --------------------------------------------------------------------------- #
def test_traceable_added_claim_is_safe_then_become_retained():
    store, parent, child = build(["c1"], ["c1", "c2"])
    claims = {
        "c1": Claim(claim_id="c1", text="one"),
        "c2": Claim(claim_id="c2", text="two", evidence_ids=["e1"]),
    }
    registry = registry_with([claims["c1"]])

    first = analyze_revision(child.content_version_id, store, claims, make_pack(), registry)
    assert first.status == "safe"
    assert first.added_claim_ids == ["c2"]
    assert first.evidence_recheck_results["c2"] == "traceable"
    assert not first.drift_detected and not first.lock_reasons

    # The successful commit must be visible to the next generation: c2 is now
    # a retained claim and must NOT be locked as "not registered".
    grandchild = store.create_revision(child.content_version_id, "grandchild",
                                       claim_ids=["c1", "c2"])
    second = analyze_revision(grandchild.content_version_id, store, claims, make_pack(),
                              registry)
    assert second.retained_claim_ids == ["c1", "c2"]
    assert second.added_claim_ids == []
    assert second.status == "safe"


# --------------------------------------------------------------------------- #
# TEST 3 — added claim without evidence binding -> locked
# --------------------------------------------------------------------------- #
def test_added_unbound_claim_locks():
    store, parent, child = build(["c1"], ["c1", "c2"])
    claims = {
        "c1": Claim(claim_id="c1", text="one"),
        "c2": Claim(claim_id="c2", text="new"),  # no evidence_ids at all
    }
    registry = registry_with([claims["c1"]])

    result = analyze_revision(child.content_version_id, store, claims, make_pack(), registry)

    assert result.status == "locked"
    assert result.drift_detected is True
    assert result.evidence_recheck_results["c2"] == "unbound"
    assert any("c2" in reason for reason in result.lock_reasons)


# --------------------------------------------------------------------------- #
# TEST 4 — dangling evidence id -> locked
# --------------------------------------------------------------------------- #
def test_dangling_evidence_locks():
    store, parent, child = build(["c1"], ["c1", "c2"])
    claims = {
        "c1": Claim(claim_id="c1", text="one"),
        "c2": Claim(claim_id="c2", text="two", evidence_ids=["does-not-exist"]),
    }
    registry = registry_with([claims["c1"]])

    result = analyze_revision(child.content_version_id, store, claims, make_pack(), registry)

    assert result.status == "locked"
    assert result.drift_detected is True
    assert result.evidence_recheck_results["c2"] == "binding_error"
    assert any("c2" in reason for reason in result.lock_reasons)


# --------------------------------------------------------------------------- #
# TEST 5 — retained claim identity mutation -> locked
# --------------------------------------------------------------------------- #
def test_retained_claim_identity_mutation_locks():
    store, parent, child = build(["c1", "c2"], ["c1"])
    original = Claim(claim_id="c1", text="original")
    registry = registry_with([original])

    mutated = Claim(claim_id="c1", text="changed")
    result = analyze_revision(child.content_version_id, store, {"c1": mutated}, None, registry)

    assert result.status == "locked"
    assert result.drift_detected is True
    assert any("identity changed" in reason for reason in result.lock_reasons)
    assert any("identity changed" in v for v in result.identity_violations)


def test_registry_rejects_identity_change_directly():
    registry = registry_with([Claim(claim_id="c1", text="original")])
    with pytest.raises(ClaimIdentityViolation):
        registry.register(Claim(claim_id="c1", text="changed"))
    with pytest.raises(ClaimIdentityViolation):
        registry.check(Claim(claim_id="c1", text="changed"))
    with pytest.raises(ClaimIdentityViolation):
        registry.check(Claim(claim_id="never-seen", text="x"))


# --------------------------------------------------------------------------- #
# TEST 6 — retained claim missing from the claims mapping -> locked
# --------------------------------------------------------------------------- #
def test_missing_retained_claim_locks():
    store, parent, child = build(["c1"], ["c1"])

    result = analyze_revision(child.content_version_id, store, {}, None,
                              ClaimIdentityRegistry())

    assert result.status == "locked"
    assert any("missing claim" in reason for reason in result.lock_reasons)


# --------------------------------------------------------------------------- #
# TEST 7 — transactional snapshot: a failed revision must not pollute the registry
# --------------------------------------------------------------------------- #
def test_added_snapshots_are_transactional():
    store, parent, child = build(["c1"], ["c1", "c2", "c3"])
    claims = {
        "c1": Claim(claim_id="c1", text="one"),
        "c2": Claim(claim_id="c2", text="two", evidence_ids=["e1"]),   # traceable
        "c3": Claim(claim_id="c3", text="three"),                       # unbound
    }
    registry = registry_with([claims["c1"]])

    failed = analyze_revision(child.content_version_id, store, claims, make_pack(), registry)
    assert failed.status == "locked"
    assert failed.evidence_recheck_results["c2"] == "traceable"
    assert failed.evidence_recheck_results["c3"] == "unbound"

    # Core assertion: c2 passed its own check, yet the failed revision must not
    # have written it into the registry.
    assert "c2" not in registry._snapshots

    # A branch off the *parent* that adds c2 as an added claim (not retained)
    # must therefore exercise the evidence path again and succeed.
    retry = store.create_revision(parent.content_version_id, "retry", claim_ids=["c1", "c2"])
    recovered = analyze_revision(retry.content_version_id, store, claims, make_pack(), registry)
    assert recovered.added_claim_ids == ["c2"]
    assert recovered.status == "safe"
    assert "c2" in registry._snapshots


# --------------------------------------------------------------------------- #
# TEST 8 — branching resolves the authoritative direct parent
# --------------------------------------------------------------------------- #
def test_branching_uses_authoritative_direct_parent():
    store = ContentVersionStore()
    v1 = store.create_initial_version("t", "one", claim_ids=["c1"])
    v2 = store.create_revision(v1.content_version_id, "two", claim_ids=["c1"])
    v2b = store.create_revision(v1.content_version_id, "two-b", claim_ids=["c1"])
    v3 = store.create_revision(v2.content_version_id, "three", claim_ids=["c1"])

    claim = Claim(claim_id="c1", text="one")
    registry = registry_with([claim])

    out_v3 = analyze_revision(v3.content_version_id, store, {"c1": claim}, None, registry)
    out_v2b = analyze_revision(v2b.content_version_id, store, {"c1": claim}, None, registry)

    assert out_v3.parent_version_id == v2.content_version_id
    assert out_v2b.parent_version_id == v1.content_version_id
    # v2 is newer than v1 but must not become v2b's parent.
    assert out_v2b.parent_version_id != v2.content_version_id


# --------------------------------------------------------------------------- #
# TEST 9 — broken parent pointer -> fail closed
# --------------------------------------------------------------------------- #
def test_broken_parent_fails_closed():
    store, parent, child = build(["c1"], ["c1"])
    child.parent_version_id = "missing-parent-id"

    with pytest.raises(FactSafetyError):
        analyze_revision(child.content_version_id, store, {}, None, ClaimIdentityRegistry())


def test_unknown_child_version_fails_closed():
    store, parent, child = build(["c1"], ["c1"])

    with pytest.raises(FactSafetyError):
        analyze_revision("no-such-child", store, {}, None, ClaimIdentityRegistry())


# --------------------------------------------------------------------------- #
# TEST 10 — parent/child task mismatch -> fail closed
# --------------------------------------------------------------------------- #
def test_parent_child_task_mismatch_fails_closed():
    store, parent, child = build(["c1"], ["c1"])
    child.task_id = "other-task"

    with pytest.raises(FactSafetyError):
        analyze_revision(child.content_version_id, store, {}, None, ClaimIdentityRegistry())


# --------------------------------------------------------------------------- #
# TEST 11 — initial version has no parent -> fail closed
# --------------------------------------------------------------------------- #
def test_initial_version_fails_closed():
    store = ContentVersionStore()
    initial = store.create_initial_version("t", "x")

    with pytest.raises(FactSafetyError):
        analyze_revision(initial.content_version_id, store, {}, None, ClaimIdentityRegistry())


# --------------------------------------------------------------------------- #
# TEST 12 — duplicate parent claim_id -> fail closed
# --------------------------------------------------------------------------- #
def test_duplicate_parent_claim_id_fails_closed():
    store, parent, child = build(["c1", "c1"], ["c1"])

    with pytest.raises(FactSafetyError):
        analyze_revision(child.content_version_id, store, {}, None, ClaimIdentityRegistry())


# --------------------------------------------------------------------------- #
# TEST 13 — duplicate child claim_id -> fail closed
# --------------------------------------------------------------------------- #
def test_duplicate_child_claim_id_fails_closed():
    store, parent, child = build(["c1"], ["c1", "c1"])

    with pytest.raises(FactSafetyError):
        analyze_revision(child.content_version_id, store, {}, None, ClaimIdentityRegistry())


# --------------------------------------------------------------------------- #
# extra: removed claim, evidence-pack mismatch, determinism
# --------------------------------------------------------------------------- #
def test_removed_claim_does_not_lock_by_itself():
    store, parent, child = build(["c1", "c2"], ["c1"])
    claims = {"c1": Claim(claim_id="c1", text="one"), "c2": Claim(claim_id="c2", text="two")}
    registry = registry_with([claims["c1"], claims["c2"]])

    result = analyze_revision(child.content_version_id, store, claims, None, registry)

    assert result.removed_claim_ids == ["c2"]
    assert result.added_claim_ids == []
    assert result.status == "safe"
    assert result.drift_detected is False


def test_evidence_pack_mismatch_locks():
    store, parent, child = build(["c1"], ["c1", "c2"])
    claims = {
        "c1": Claim(claim_id="c1", text="one"),
        "c2": Claim(claim_id="c2", text="two", evidence_ids=["e1"]),
    }
    registry = registry_with([claims["c1"]])

    mismatched = analyze_revision(child.content_version_id, store, claims,
                                  make_pack("other-pack"), registry)

    assert mismatched.status == "locked"
    assert mismatched.evidence_recheck_results["c2"] == "missing_evidence_pack"


def test_result_is_deterministic_and_ordered():
    store, parent, child = build(["c1", "c2", "c3"], ["c3", "c1", "c4"])
    claims = {c: Claim(claim_id=c, text=c) for c in ["c1", "c2", "c3", "c4"]}
    registry = registry_with([claims["c1"], claims["c3"]])
    pack = make_pack()

    results = [
        analyze_revision(child.content_version_id, store, claims, pack, registry)
        for _ in range(3)
    ]

    first = results[0]
    # retained/added follow child order, removed follows parent order.
    assert first.retained_claim_ids == ["c3", "c1"]
    assert first.removed_claim_ids == ["c2"]
    assert first.added_claim_ids == ["c4"]
    for other in results[1:]:
        assert other.retained_claim_ids == first.retained_claim_ids
        assert other.removed_claim_ids == first.removed_claim_ids
        assert other.added_claim_ids == first.added_claim_ids
        assert other.lock_reasons == first.lock_reasons
