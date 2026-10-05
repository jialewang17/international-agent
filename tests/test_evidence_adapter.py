"""I0-B2 — Evidence Adapter + Suzhou Evidence Contract Integration tests.

Two layers:

* **Unit** — ``build_evidence_pack`` alone: mapping, deterministic IDs,
  dedup, fail-closed.
* **Integration** — the real, un-faked Suzhou chain::

      retrieve_statements("苏绣")   ←真实 tracked JSON retrieval
          → legacy rows
          → build_evidence_pack()
          → EvidencePack
          → manual Claim (no extraction)
          → api.binding.resolve_claim_trace()   ←既有 Core，未修改
          → EvidenceItem → Source → traceable

Scope guard: this file touches the adapter only. It does NOT test / implement
Claim extraction, retrieval internals, KG, Graph RAG, generation, evaluation,
revision, fact safety, human review or Gate C.
"""

from __future__ import annotations

import pytest

from api.binding import BindingError, resolve_claim_trace
from api.evidence_adapter import (
    EvidenceAdapterError,
    build_evidence_pack,
    canonical_digest,
    evidence_id_for,
    evidence_pack_id_for,
    source_id_for,
)
from api.schemas import Claim, EvidencePack
from tools.kb_local import retrieve_statements

# The two verified official Suzhou sources (frozen in I0-B1).
SRC_A = "https://www.ihchina.cn/project_details/13978/"
SRC_B = (
    "https://dfzb.suzhou.gov.cn/dfzb/szdq/201506/"
    "33cc064585a649d78d76af7e2ac86766.shtml"
)
ALLOWED_SOURCES = {SRC_A, SRC_B}

SUZHOU_MARKERS = ("苏绣", "苏州刺绣", "苏州")


def _row(statement="a fact", source="https://example.test/x", **extra):
    return {"category": "culture", "statement": statement, "source": source,
            "retrieval": "category", **extra}


# ===========================================================================
# Unit — construction
# ===========================================================================


def test_single_valid_row_builds_a_pack():
    pack = build_evidence_pack([_row()])
    assert isinstance(pack, EvidencePack)
    assert len(pack.items) == 1
    assert len(pack.sources) == 1
    assert pack.status == "ready"


def test_multiple_valid_rows_build_a_pack():
    pack = build_evidence_pack([_row(statement="s1", source="https://a.test/1"),
                                _row(statement="s2", source="https://a.test/2")])
    assert len(pack.items) == 2
    assert len(pack.sources) == 2


def test_source_preserves_original_provenance_verbatim():
    pack = build_evidence_pack([_row(source=SRC_A)])
    assert pack.sources[0].uri == SRC_A


def test_statement_and_category_are_mapped_and_stripped():
    pack = build_evidence_pack([_row(statement="  F  act  ", category=" culture ")])
    assert pack.items[0].statement == "F  act"  # inner whitespace untouched
    assert pack.items[0].category == "culture"


def test_evidence_item_source_id_resolves_to_a_pack_source():
    pack = build_evidence_pack([_row()])
    assert pack.items[0].source_id in {s.source_id for s in pack.sources}


def test_spans_are_empty_and_never_fabricated():
    pack = build_evidence_pack([_row()])
    assert pack.items[0].spans == []


def test_known_source_type_is_carried_over():
    pack = build_evidence_pack([_row(source_type="本地库")])
    assert pack.sources[0].source_type == "本地库"


def test_unknown_source_type_is_not_invented():
    pack = build_evidence_pack([_row(source_type="totally-made-up")])
    assert pack.sources[0].source_type == ""


def test_title_is_not_guessed():
    pack = build_evidence_pack([_row()])
    assert pack.sources[0].title == ""


# ===========================================================================
# Unit — deterministic IDs
# ===========================================================================


def test_source_id_is_deterministic():
    assert source_id_for(SRC_A) == source_id_for(SRC_A)
    assert source_id_for(SRC_A) != source_id_for(SRC_B)


def test_evidence_id_is_deterministic():
    first = build_evidence_pack([_row()]).items[0].evidence_id
    second = build_evidence_pack([_row()]).items[0].evidence_id
    assert first == second


def test_evidence_pack_id_is_deterministic():
    first = build_evidence_pack([_row()]).evidence_pack_id
    second = build_evidence_pack([_row()]).evidence_pack_id
    assert first == second


def test_pack_id_is_unchanged_when_input_order_changes():
    rows = [_row(statement="s1", source="https://a.test/1"),
            _row(statement="s2", source="https://a.test/2"),
            _row(statement="s3", source="https://a.test/3")]
    assert (build_evidence_pack(rows).evidence_pack_id
            == build_evidence_pack(list(reversed(rows))).evidence_pack_id)


def test_ids_are_not_random_across_processes():
    """Frozen literals: a silent switch to UUID/random would break these."""
    assert source_id_for(SRC_A) == "src_23064deac47dd5250fd60df6"
    pack = build_evidence_pack([_row(statement="stable", source="https://a.test/1")])
    assert pack.items[0].evidence_id == "ev_" + canonical_digest(
        pack.items[0].source_id, "stable")
    assert pack.evidence_pack_id == "ep_" + canonical_digest(
        pack.items[0].source_id, pack.items[0].evidence_id)


def test_no_uuid_style_ids_and_no_rank_dependence():
    """IDs must be sha256 hex, not UUIDs, and must not encode list position."""
    pack = build_evidence_pack([_row(statement="s1", source="https://a.test/1"),
                                _row(statement="s2", source="https://a.test/2")])
    for value in (pack.evidence_pack_id, pack.items[0].evidence_id,
                  pack.items[1].evidence_id, pack.sources[0].source_id):
        assert "-" not in value, value          # UUID form would contain dashes
        hex_part = value.split("_", 1)[1]
        assert len(hex_part) == 24
        int(hex_part, 16)                       # hex only
    # swapping rank must swap nothing: each evidence keeps its own id
    swapped = build_evidence_pack([_row(statement="s2", source="https://a.test/2"),
                                   _row(statement="s1", source="https://a.test/1")])
    assert {it.evidence_id for it in pack.items} == {
        it.evidence_id for it in swapped.items}


def test_id_helpers_agree_with_pack_output():
    pack = build_evidence_pack([_row()])
    item = pack.items[0]
    assert item.source_id == source_id_for(pack.sources[0].uri)
    assert item.evidence_id == evidence_id_for(item.source_id, item.statement)
    assert pack.evidence_pack_id == evidence_pack_id_for(
        [(it.source_id, it.evidence_id) for it in pack.items])


# ===========================================================================
# Unit — normalization / dedup
# ===========================================================================


def test_same_source_same_statement_is_deduplicated():
    pack = build_evidence_pack([_row(), _row()])
    assert len(pack.items) == 1
    assert len(pack.sources) == 1


def test_dedup_ignores_surrounding_whitespace():
    pack = build_evidence_pack([_row(), _row(statement=" a fact ")])
    assert len(pack.items) == 1


def test_same_statement_different_source_is_not_deduplicated():
    pack = build_evidence_pack([
        _row(statement="shared", source=SRC_A),
        _row(statement="shared", source=SRC_B),
    ])
    assert len(pack.items) == 2
    assert len(pack.sources) == 2


# ===========================================================================
# Unit — fail closed
# ===========================================================================


def test_missing_source_key_is_invalid():
    pack = build_evidence_pack([{"category": "c", "statement": "ok"},
                                _row(statement="ok2")])
    assert len(pack.items) == 1
    assert pack.items[0].statement == "ok2"


def test_blank_source_is_invalid():
    pack = build_evidence_pack([_row(source="   "), _row(statement="ok2")])
    assert [it.statement for it in pack.items] == ["ok2"]


def test_missing_statement_key_is_invalid():
    pack = build_evidence_pack([{"category": "c", "source": SRC_A},
                                _row(statement="ok2")])
    assert [it.statement for it in pack.items] == ["ok2"]


def test_blank_statement_is_invalid():
    pack = build_evidence_pack([_row(statement="  \t "), _row(statement="ok2")])
    assert [it.statement for it in pack.items] == ["ok2"]


def test_all_invalid_rows_raise():
    with pytest.raises(EvidenceAdapterError):
        build_evidence_pack([_row(source=""), _row(statement="  ")])


def test_empty_rows_raise():
    with pytest.raises(EvidenceAdapterError):
        build_evidence_pack([])


def test_non_mapping_row_raises():
    with pytest.raises(EvidenceAdapterError):
        build_evidence_pack(["not a row"])


def test_rows_must_be_a_sequence_not_a_mapping():
    with pytest.raises(EvidenceAdapterError):
        build_evidence_pack({"statement": "x", "source": SRC_A})


def test_mixed_valid_and_invalid_keeps_only_valid():
    rows = [
        _row(statement="keep-1", source="https://a.test/1"),
        _row(source=""),                       # invalid: blank source
        _row(statement=""),                    # invalid: blank statement
        {"category": "c"},                     # invalid: both missing
        _row(statement="keep-2", source="https://a.test/2"),
    ]
    pack = build_evidence_pack(rows)
    assert sorted(it.statement for it in pack.items) == ["keep-1", "keep-2"]
    assert len(pack.sources) == 2
    # no phantom evidence leaked from the invalid rows
    assert all(it.source_id in {s.source_id for s in pack.sources}
               for it in pack.items)


# ===========================================================================
# Unit — internal locator provenance
# ===========================================================================


def test_user_paste_locator_is_not_disguised_as_a_url():
    pack = build_evidence_pack([_row(source="user_paste:用户资料#1")])
    uri = pack.sources[0].uri
    assert uri == "user_paste:用户资料#1"
    assert not uri.startswith("http")


# ===========================================================================
# Integration — real Suzhou retrieval, no fakes
# ===========================================================================


@pytest.fixture(scope="module")
def suzhou_pack():
    rows = retrieve_statements(["culture"], limit_per_cat=6, query="苏绣")
    assert rows, "real Suzhou retrieval returned nothing"
    return rows, build_evidence_pack(rows)


def test_real_suzhou_retrieval_yields_evidence(suzhou_pack):
    _, pack = suzhou_pack
    assert len(pack.items) >= 1


def test_real_suzhou_pack_contains_a_suzhou_statement(suzhou_pack):
    _, pack = suzhou_pack
    assert any(any(m in it.statement for m in SUZHOU_MARKERS)
               for it in pack.items)


def test_real_suzhou_pack_preserves_official_provenance(suzhou_pack):
    _, pack = suzhou_pack
    suzhou_sources = {s.uri for s in pack.sources
                      if any(m in s.uri for m in ("ihchina.cn", "suzhou.gov.cn"))}
    assert suzhou_sources
    assert suzhou_sources <= ALLOWED_SOURCES


def test_real_suzhou_claim_trace_is_traceable(suzhou_pack):
    _, pack = suzhou_pack
    target = next(it for it in pack.items
                  if any(m in it.statement for m in SUZHOU_MARKERS))
    claim = Claim(
        claim_id="claim_suzhou_trace_test",
        text=target.statement,
        evidence_ids=[target.evidence_id],
    )
    trace = resolve_claim_trace(claim, pack)
    assert trace["status"] == "traceable"
    assert trace["claim_id"] == "claim_suzhou_trace_test"
    assert [e["evidence_id"] for e in trace["evidence"]] == [target.evidence_id]
    assert trace["evidence"][0]["source_id"] == target.source_id
    assert any(s["source_id"] == target.source_id for s in trace["sources"])


def test_real_suzhou_trace_source_uri_is_the_real_official_url(suzhou_pack):
    rows, pack = suzhou_pack
    target = next(it for it in pack.items
                  if any(m in it.statement for m in SUZHOU_MARKERS))
    trace = resolve_claim_trace(
        Claim(claim_id="c", text=target.statement, evidence_ids=[target.evidence_id]),
        pack,
    )
    resolved = next(s for s in trace["sources"] if s["source_id"] == target.source_id)
    assert resolved["uri"] in ALLOWED_SOURCES
    # and the row the adapter consumed really came from tracked retrieval
    assert any(r["source"] == resolved["uri"] for r in rows)


def test_real_suzhou_multi_evidence_claim_traces_all(suzhou_pack):
    _, pack = suzhou_pack
    ids = [it.evidence_id for it in pack.items][:2]
    trace = resolve_claim_trace(
        Claim(claim_id="c2", text="multi", evidence_ids=ids), pack)
    assert trace["status"] == "traceable"
    assert [e["evidence_id"] for e in trace["evidence"]] == ids


def test_real_suzhou_pack_id_is_stable_across_retrieval_calls():
    first = build_evidence_pack(
        retrieve_statements(["culture"], limit_per_cat=6, query="苏绣")
    ).evidence_pack_id
    second = build_evidence_pack(
        retrieve_statements(["culture"], limit_per_cat=6, query="苏绣")
    ).evidence_pack_id
    assert first == second


# ===========================================================================
# Integration — fail-closed binding against an adapter-built pack
# ===========================================================================


def test_adapter_pack_with_dangling_evidence_id_fails_closed(suzhou_pack):
    _, pack = suzhou_pack
    with pytest.raises(BindingError, match="missing evidence"):
        resolve_claim_trace(
            Claim(claim_id="c", text="x", evidence_ids=["ev_does_not_exist"]),
            pack,
        )


def test_adapter_pack_with_dangling_source_id_fails_closed(suzhou_pack):
    _, pack = suzhou_pack
    target = pack.items[0]
    broken = pack.model_copy(deep=True)
    broken.items[0].source_id = "src_does_not_exist"
    with pytest.raises(BindingError, match="missing source"):
        resolve_claim_trace(
            Claim(claim_id="c", text="x", evidence_ids=[target.evidence_id]),
            broken,
        )


def test_adapter_pack_unbound_claim_is_not_traceable(suzhou_pack):
    _, pack = suzhou_pack
    trace = resolve_claim_trace(Claim(claim_id="c", text="no evidence"), pack)
    assert trace["status"] == "unbound"
