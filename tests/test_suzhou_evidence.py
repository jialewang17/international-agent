"""I0-B1 — Suzhou (苏绣) mini evidence dataset regression tests.

Purpose
-------
The I0 milestone needs a small, *real*, *traceable* engineering baseline dataset.
These tests pin down only the retrieval-visible contract:

1. A clean-checkout retrieval for theme "苏绣" returns at least one Suzhou
   evidence row.
2. The returned statement is genuinely about Suzhou / Suzhou embroidery.
3. Every Suzhou source is one of the two verified official URLs.
4. Retrieval needs no Chroma DB, no network, no external API / LLM.
5. The pre-existing Spring Festival retrieval behaviour is unchanged.

Scope guard: this file touches retrieval only. It deliberately does NOT test
KG, Graph RAG, claim extraction, the evidence adapter, content versioning,
evaluation, revision, fact safety, human review or Gate C.
"""

from __future__ import annotations

import json
import pathlib

import pytest

from tools.kb_local import (
    guess_categories,
    normalize_category,
    retrieve_statements,
)
from tools.user_materials import merge_evidence, normalize_user_materials

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE_JSON = REPO_ROOT / "knowledge" / "diplomacy" / "evidence.json"

# The only two sources permitted for the Suzhou fixture (both verified manually).
SRC_A = "https://www.ihchina.cn/project_details/13978/"
SRC_B = (
    "https://dfzb.suzhou.gov.cn/dfzb/szdq/201506/"
    "33cc064585a649d78d76af7e2ac86766.shtml"
)
ALLOWED_SOURCES = {SRC_A, SRC_B}

SUZHOU_IDS = ["suzhou-001", "suzhou-002", "suzhou-003", "suzhou-004", "suzhou-005"]

# Tokens that must appear in a statement for it to count as "about Suzhou".
SUZHOU_MARKERS = ("苏绣", "苏州刺绣", "苏州")


def _load_evidence() -> dict:
    with EVIDENCE_JSON.open(encoding="utf-8") as fh:
        return json.load(fh)


def _culture_rows() -> list:
    return _load_evidence()["by_category"]["culture"]


def _suzhou_rows() -> list:
    return [row for row in _culture_rows() if row.get("id") in SUZHOU_IDS]


# ---------------------------------------------------------------------------
# 1. Dataset integrity — the fixture exists and is stored twice as a mirror
# ---------------------------------------------------------------------------


def test_all_five_suzhou_items_exist_in_culture():
    rows = _suzhou_rows()
    assert [row["id"] for row in rows] == SUZHOU_IDS


def test_topics_raw_and_by_category_are_identical_mirrors():
    data = _load_evidence()
    assert data["topics_raw"]["culture"] == data["by_category"]["culture"]


def test_suzhou_items_use_the_culture_category():
    for row in _suzhou_rows():
        assert row["category"] == "culture"


def test_every_suzhou_item_carries_a_quote_and_a_tag_list():
    for row in _suzhou_rows():
        assert row.get("quote_cn", "").strip()
        assert row.get("quote_en", "").strip()
        assert isinstance(row.get("tags"), list) and row["tags"]


# ---------------------------------------------------------------------------
# 2. Source whitelist — no fabricated provenance
# ---------------------------------------------------------------------------


def test_every_suzhou_source_is_one_of_the_two_official_urls():
    for row in _suzhou_rows():
        assert row["source"] in ALLOWED_SOURCES, row["id"]


def test_both_official_sources_are_actually_exercised():
    used = {row["source"] for row in _suzhou_rows()}
    assert used == ALLOWED_SOURCES


# ---------------------------------------------------------------------------
# 3. Category mapping — "苏绣" resolves to culture
# ---------------------------------------------------------------------------


def test_normalize_category_maps_suxiu_aliases_to_culture():
    for alias in ["苏绣", "苏州刺绣", "苏绣 ", "embroidery", "suzhou embroidery", "suxiu"]:
        assert normalize_category(alias) == "culture", alias


def test_guess_categories_detects_culture_for_suxiu_query():
    assert "culture" in guess_categories("苏绣")
    assert "culture" in guess_categories("苏绣 刺绣")
    assert "culture" in guess_categories("Suzhou embroidery")


# ---------------------------------------------------------------------------
# 4. Retrieval core — the Suzhou evidence surfaces and is genuinely Suzhou
# ---------------------------------------------------------------------------


def test_retrieve_statements_returns_suzhou_evidence_for_suxiu_query():
    rows = retrieve_statements(["culture"], limit_per_cat=6, query="苏绣")
    assert rows, "retrieval returned nothing for 苏绣"
    assert any(
        any(marker in row["statement"] for marker in SUZHOU_MARKERS) for row in rows
    ), [row["statement"] for row in rows]


def test_primary_retrieval_result_is_about_suzhou_not_spring_festival():
    rows = retrieve_statements(["culture"], limit_per_cat=3, query="苏绣")
    assert "苏绣" in rows[0]["statement"] or "苏州刺绣" in rows[0]["statement"]
    assert "Spring Festival" not in rows[0]["statement"]


def test_retrieved_suzhou_rows_use_a_whitelisted_source():
    rows = retrieve_statements(["culture"], limit_per_cat=6, query="苏绣")
    suzhou_rows = [
        row for row in rows if any(m in row["statement"] for m in SUZHOU_MARKERS)
    ]
    assert suzhou_rows, "no Suzhou row retrieved"
    for row in suzhou_rows:
        assert row["source"] in ALLOWED_SOURCES, row["statement"][:40]


def test_raw_retrieval_rows_expose_only_the_normalized_field_set():
    """``retrieve_statements`` emits exactly these four fields (``source_type``
    is added later by ``merge_evidence``)."""
    rows = retrieve_statements(["culture"], limit_per_cat=6, query="苏绣")
    for row in rows:
        assert set(row.keys()) == {"category", "statement", "source", "retrieval"}


def test_retrieval_is_labelled_as_category_hit():
    rows = retrieve_statements(["culture"], limit_per_cat=6, query="苏绣")
    for row in rows:
        assert row["retrieval"] == "category"


# ---------------------------------------------------------------------------
# 5. Downstream merge — the Suzhou evidence reaches ``evidence_used``
# ---------------------------------------------------------------------------


def test_merged_evidence_contains_suzhou_rows():
    local = retrieve_statements(["culture"], limit_per_cat=6, query="苏绣")
    merged = merge_evidence(normalize_user_materials(None, theme="苏绣"), local)
    suzhou = [
        row for row in merged if any(m in row["statement"] for m in SUZHOU_MARKERS)
    ]
    assert suzhou
    assert suzhou[0]["source"] in ALLOWED_SOURCES


def test_merged_suzhou_rows_are_labelled_as_local_kb():
    local = retrieve_statements(["culture"], limit_per_cat=6, query="苏绣")
    merged = merge_evidence(normalize_user_materials(None, theme="苏绣"), local)
    suzhou = [
        row for row in merged if any(m in row["statement"] for m in SUZHOU_MARKERS)
    ]
    assert suzhou
    for row in suzhou:
        assert row["source_type"] == "本地库"


# ---------------------------------------------------------------------------
# 6. No heavyweight dependency — pure JSON path, offline, deterministic
# ---------------------------------------------------------------------------


def test_retrieval_falls_back_to_json_when_chroma_is_unavailable(monkeypatch):
    """Suzhou retrieval must work through JSON even when Chroma is unavailable."""
    import tools.chroma_kb as chroma_kb

    monkeypatch.setattr(chroma_kb, "chroma_ready", lambda: False)
    rows = retrieve_statements(["culture"], limit_per_cat=6, query="苏绣")
    assert any("苏绣" in row["statement"] for row in rows)


def test_retrieval_is_deterministic_across_calls():
    first = retrieve_statements(["culture"], limit_per_cat=6, query="苏绣")
    second = retrieve_statements(["culture"], limit_per_cat=6, query="苏绣")
    assert [r["statement"] for r in first] == [r["statement"] for r in second]


# ---------------------------------------------------------------------------
# 7. Regression — the pre-existing Spring Festival behaviour is unchanged
# ---------------------------------------------------------------------------


def test_spring_festival_query_still_returns_spring_festival():
    rows = retrieve_statements(["culture"], limit_per_cat=3, query="Spring Festival")
    assert rows
    assert "Spring Festival" in rows[0]["statement"]


def test_unqueried_retrieval_keeps_original_stored_order():
    """No query => no re-ranking; stored order is preserved."""
    plain = retrieve_statements(["culture"], limit_per_cat=3)
    assert plain
    assert "Spring Festival" in plain[0]["statement"]


def test_spring_festival_is_absent_from_the_suzhou_top_results():
    rows = retrieve_statements(["culture"], limit_per_cat=3, query="苏绣")
    assert all("Spring Festival" not in row["statement"] for row in rows)
