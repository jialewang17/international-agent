import pytest

from api.binding import BindingError, resolve_claim_trace
from api.schemas import Claim, EvidenceItem, EvidencePack, EvidenceSpan, Source


def pack():
    source = Source(source_id="src-1", uri="https://example.test/source")
    item = EvidenceItem(
        evidence_id="ev-1", source_id="src-1", statement="fact",
        spans=[EvidenceSpan(span_id="span-1", source_id="src-1", text="fact")],
    )
    second = EvidenceItem(evidence_id="ev-2", source_id="src-1", statement="more fact")
    return EvidencePack(evidence_pack_id="pack-1", sources=[source], items=[item, second])


def test_valid_and_multiple_evidence_trace():
    trace = resolve_claim_trace(Claim(claim_id="c", text="fact", evidence_ids=["ev-1", "ev-2"]), pack())
    assert trace["status"] == "traceable"
    assert [x["evidence_id"] for x in trace["evidence"]] == ["ev-1", "ev-2"]
    assert [x["source_id"] for x in trace["sources"]] == ["src-1"]


def test_dangling_evidence_fails_closed():
    with pytest.raises(BindingError, match="missing evidence"):
        resolve_claim_trace(Claim(claim_id="c", text="x", evidence_ids=["nope"]), pack())


def test_dangling_source_fails_closed():
    broken = EvidencePack(evidence_pack_id="p", items=[EvidenceItem(evidence_id="e", source_id="nope", statement="x")])
    with pytest.raises(BindingError, match="missing source"):
        resolve_claim_trace(Claim(claim_id="c", text="x", evidence_ids=["e"]), broken)


def test_unbound_claim_is_not_traceable():
    trace = resolve_claim_trace(Claim(claim_id="c", text="unsupported"), pack())
    assert trace["status"] == "unbound"


def test_shared_source_is_preserved_for_multiple_claims():
    evidence = pack()
    first = resolve_claim_trace(Claim(claim_id="c1", text="x", evidence_ids=["ev-1"]), evidence)
    second = resolve_claim_trace(Claim(claim_id="c2", text="y", evidence_ids=["ev-2"]), evidence)
    assert first["sources"] == second["sources"]


def test_item_and_span_sources_are_both_in_trace():
    sources = [Source(source_id="src-a"), Source(source_id="src-b")]
    item = EvidenceItem(
        evidence_id="ev-a", source_id="src-a", statement="fact",
        spans=[EvidenceSpan(span_id="span-b", source_id="src-b", text="fact")],
    )
    trace = resolve_claim_trace(
        Claim(claim_id="c", text="fact", evidence_ids=["ev-a"]),
        EvidencePack(evidence_pack_id="p", sources=sources, items=[item]),
    )
    assert [s["source_id"] for s in trace["sources"]] == ["src-a", "src-b"]


def test_span_dangling_source_fails_closed():
    item = EvidenceItem(
        evidence_id="ev-a", source_id="src-a", statement="fact",
        spans=[EvidenceSpan(span_id="span-x", source_id="missing", text="fact")],
    )
    with pytest.raises(BindingError, match="missing source for span"):
        resolve_claim_trace(
            Claim(claim_id="c", text="fact", evidence_ids=["ev-a"]),
            EvidencePack(evidence_pack_id="p", sources=[Source(source_id="src-a")], items=[item]),
        )


def test_item_and_span_same_source_is_not_duplicated():
    source = Source(source_id="src-a")
    item = EvidenceItem(
        evidence_id="ev-a", source_id="src-a", statement="fact",
        spans=[EvidenceSpan(span_id="span-a", source_id="src-a", text="fact")],
    )
    trace = resolve_claim_trace(
        Claim(claim_id="c", text="fact", evidence_ids=["ev-a"]),
        EvidencePack(evidence_pack_id="p", sources=[source], items=[item]),
    )
    assert [s["source_id"] for s in trace["sources"]] == ["src-a"]


def test_duplicate_evidence_refs_keep_first_occurrence_only():
    trace = resolve_claim_trace(
        Claim(claim_id="c", text="fact", evidence_ids=["ev-1", "ev-1"]), pack()
    )
    assert [e["evidence_id"] for e in trace["evidence"]] == ["ev-1"]
