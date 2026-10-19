"""I2-C-001B-P2A-R1: offline atomic fact annotation contract tests.

Structural contract only. These tests never assert a real Claim Recall
value and never treat sentence-candidate overlap as atomic enumeration.
"""

import dataclasses

import pytest

from api.atomic_gold_contract import (
    ATOMIC_ENUMERATION_NOT_VERIFIED,
    NOT_EVALUATED,
    AtomicAnnotationError,
    derive_fact_occurrence_id,
    validate_atomic_annotations,
)
from api.claim_extraction import DeterministicClaimExtractor
from api.schemas import ContentVersion
from api.source_text_index import (
    HumanGoldAtomicFact,
    build_source_text_index,
    evaluate_human_gold_recall,
)

BENCH = "bm_gold_fixture"
PACK = "ep_gold"
TASK = "task_gold"


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def make_index(body, cvs="cv_gold", pack=PACK, with_claims=False):
    """Build a canonical SourceTextIndex for ``body`` (read-only helpers)."""
    if with_claims:
        claims = DeterministicClaimExtractor().extract(body)
        claim_ids = [c.claim_id for c in claims]
    else:
        claims = []
        claim_ids = []

    version = ContentVersion(
        content_version_id=cvs,
        content=body,
        task_id=TASK,
        evidence_pack_id=pack,
        claim_ids=claim_ids,
    )
    return build_source_text_index(version, claims), claims


def ann(
    index,
    source,
    group,
    quote,
    *,
    start=None,
    end=None,
    proposition=None,
    subject_ref="",
    polarity="POSITIVE",
    fact_kind="OTHER",
    language="zh",
    benchmark=BENCH,
    status="ADJUDICATED",
    annotator="alice",
    adjudicator=None,
    note="",
    requires_context=False,
    context_start=None,
    context_end=None,
    fact_occurrence_id="",
    content_version_id=None,
    content_sha256=None,
    evidence_pack_id=None,
):
    """Construct one annotation anchored on ``quote`` inside ``source``."""
    if start is None:
        start = source.index(quote)
    if end is None:
        end = start + len(quote)

    if proposition is None:
        proposition = quote

    if adjudicator is None:
        adjudicator = "bob" if status == "ADJUDICATED" else ""

    return dict(
        benchmark_id=benchmark,
        content_version_id=(
            index.content_version_id
            if content_version_id is None
            else content_version_id
        ),
        content_sha256=(
            index.content_sha256
            if content_sha256 is None
            else content_sha256
        ),
        evidence_pack_id=(
            index.evidence_pack_id
            if evidence_pack_id is None
            else evidence_pack_id
        ),
        fact_group_id=group,
        fact_occurrence_id=fact_occurrence_id,
        start=start,
        end=end,
        source_quote=quote,
        proposition=proposition,
        subject_ref=subject_ref,
        polarity=polarity,
        fact_kind=fact_kind,
        language=language,
        requires_context=requires_context,
        context_start=context_start,
        context_end=context_end,
        review_status=status,
        annotator_id=annotator,
        adjudicator_id=adjudicator,
        note=note,
    )


def build(**kwargs):
    from api.atomic_gold_contract import AtomicFactAnnotation

    return AtomicFactAnnotation(**kwargs)


def validate(index, source, annotations):
    return validate_atomic_annotations(
        index,
        source,
        [build(**kwargs) for kwargs in annotations],
    )


# --------------------------------------------------------------------------- #
# 01-03: languages
# --------------------------------------------------------------------------- #
def test_01_chinese_atomic_fact_is_structurally_valid():
    body = "苏绣是苏州的传统工艺。"
    index, _ = make_index(body)

    result = validate(
        index,
        body,
        [
            ann(
                index,
                body,
                "af_zh_craft",
                "苏绣是苏州的传统工艺",
                subject_ref="苏绣",
                fact_kind="IDENTITY_RELATION",
                language="zh",
            )
        ],
    )

    assert result.status == "STRUCTURE_VALID"
    assert result.errors == ()
    assert result.fact_group_count == 1
    assert result.claim_recall_status == NOT_EVALUATED


def test_02_english_atomic_fact_is_structurally_valid():
    body = "Suzhou is a city in Jiangsu province."
    index, _ = make_index(body, cvs="cv_en")

    result = validate(
        index,
        body,
        [
            ann(
                index,
                body,
                "af_en_city",
                "Suzhou is a city in Jiangsu province",
                subject_ref="Suzhou",
                language="en",
            )
        ],
    )

    assert result.status == "STRUCTURE_VALID"
    assert result.errors == ()
    assert result.benchmark_id == BENCH


def test_03_mixed_language_content_is_structurally_valid():
    body = "苏绣（Su embroidery）有2000多年历史。"
    index, _ = make_index(body, cvs="cv_mixed")

    result = validate(
        index,
        body,
        [
            ann(
                index,
                body,
                "af_mixed_history",
                "有2000多年历史",
                subject_ref="苏绣",
                proposition="苏绣的历史超过2000年",
                fact_kind="NUMERIC",
                language="mixed",
            ),
            ann(
                index,
                body,
                "af_mixed_name",
                "Su embroidery",
                subject_ref="苏绣",
                proposition="苏绣的英文名称为 Su embroidery",
                language="mixed",
            ),
        ],
    )

    assert result.status == "STRUCTURE_VALID"
    assert result.errors == ()
    assert result.fact_group_count == 2


# --------------------------------------------------------------------------- #
# 04-07: multi-fact sentences
# --------------------------------------------------------------------------- #
def test_04_multiple_facts_in_one_sentence_stay_separate():
    body = (
        "The project began in 2020, "
        "and revenue reached 100 million in 2024."
    )
    index, _ = make_index(body, cvs="cv_multi", with_claims=True)

    result = validate(
        index,
        body,
        [
            ann(
                index,
                body,
                "af_begin",
                "The project began in 2020",
                subject_ref="the project",
                fact_kind="DATE",
                language="en",
            ),
            ann(
                index,
                body,
                "af_revenue",
                "revenue reached 100 million in 2024",
                subject_ref="the project",
                fact_kind="NUMERIC",
                language="en",
            ),
        ],
    )

    assert result.status == "STRUCTURE_VALID"
    assert result.fact_group_count == 2
    # Both are covered by the same sentence Claim candidate, but overlap
    # must never be promoted to enumeration or recall.
    assert len(result.sentence_candidate_covered_occurrence_ids) == 2
    assert (
        result.atomic_enumeration_status
        == ATOMIC_ENUMERATION_NOT_VERIFIED
    )
    assert result.claim_recall_status == NOT_EVALUATED


def test_05_dunhao_parallel_objects_are_separate_facts():
    body = "苏绣、缂丝、宋锦并称苏州三绝。"
    index, _ = make_index(body, cvs="cv_dunhao")

    result = validate(
        index,
        body,
        [
            ann(
                index,
                body,
                "af_suxiu",
                "苏绣、缂丝、宋锦并称苏州三绝",
                subject_ref="苏绣",
            ),
            ann(
                index,
                body,
                "af_kesi",
                "苏绣、缂丝、宋锦并称苏州三绝",
                subject_ref="缂丝",
            ),
            ann(
                index,
                body,
                "af_songjin",
                "苏绣、缂丝、宋锦并称苏州三绝",
                subject_ref="宋锦",
            ),
        ],
    )

    assert result.status == "STRUCTURE_VALID"
    assert result.fact_group_count == 3
    # Three groups share one span: identities must still be distinct.
    assert result.fact_occurrence_count == 3


def test_06_dash_inserted_fact_is_annotatable():
    body = "苏绣——中国四大名绣之一——起源于苏州。"
    index, _ = make_index(body, cvs="cv_dash")

    result = validate(
        index,
        body,
        [
            ann(
                index,
                body,
                "af_four",
                "中国四大名绣之一",
                subject_ref="苏绣",
                fact_kind="IDENTITY_RELATION",
            ),
            ann(
                index,
                body,
                "af_origin",
                "起源于苏州",
                subject_ref="苏绣",
            ),
        ],
    )

    assert result.status == "STRUCTURE_VALID"
    assert result.errors == ()


def test_07_parenthetical_fact_is_annotatable():
    body = "Suzhou (population 12 million) is a craft centre."
    index, _ = make_index(body, cvs="cv_paren")

    result = validate(
        index,
        body,
        [
            ann(
                index,
                body,
                "af_population",
                "population 12 million",
                subject_ref="Suzhou",
                fact_kind="NUMERIC",
                language="en",
            ),
            ann(
                index,
                body,
                "af_craft_centre",
                "Suzhou (population 12 million) is a craft centre",
                subject_ref="Suzhou",
                language="en",
            ),
        ],
    )

    assert result.status == "STRUCTURE_VALID"
    assert result.fact_group_count == 2


# --------------------------------------------------------------------------- #
# 08-10: numeric, years, polarity
# --------------------------------------------------------------------------- #
def test_08_single_numeric_fact_is_annotatable():
    body = "苏绣有2000多年历史。"
    index, _ = make_index(body, cvs="cv_num")

    result = validate(
        index,
        body,
        [
            ann(
                index,
                body,
                "af_2000",
                "2000多年",
                subject_ref="苏绣",
                proposition="苏绣的历史超过2000年",
                fact_kind="NUMERIC",
            ),
        ],
    )

    assert result.status == "STRUCTURE_VALID"
    assert result.fact_group_count == 1


def test_09_different_years_are_different_facts():
    body = "The project began in 2020 and ended in 2024."
    index, _ = make_index(body, cvs="cv_years")

    start_2020 = body.index("2020")
    start_2024 = body.index("2024")

    result = validate(
        index,
        body,
        [
            ann(
                index,
                body,
                "af_begin_year",
                "2020",
                start=start_2020,
                end=start_2020 + 4,
                subject_ref="the project",
                proposition="项目始于2020年",
                fact_kind="DATE",
                language="en",
            ),
            ann(
                index,
                body,
                "af_end_year",
                "2024",
                start=start_2024,
                end=start_2024 + 4,
                subject_ref="the project",
                proposition="项目止于2024年",
                fact_kind="DATE",
                language="en",
            ),
        ],
    )

    assert result.status == "STRUCTURE_VALID"
    assert result.fact_group_count == 2


def test_10_negation_polarity_is_explicit_and_conflicts_rejected():
    body = "苏州不是江苏省的省会。"
    index, _ = make_index(body, cvs="cv_neg")

    ok = validate(
        index,
        body,
        [
            ann(
                index,
                body,
                "af_not_capital",
                "苏州不是江苏省的省会",
                subject_ref="苏州",
                proposition="苏州不是江苏省省会",
                polarity="NEGATIVE",
                fact_kind="NEGATION",
            )
        ],
    )

    assert ok.status == "STRUCTURE_VALID"

    # Same group with conflicting polarity must be rejected, never merged.
    conflict = validate(
        index,
        body,
        [
            ann(
                index,
                body,
                "af_capital",
                "苏州不是江苏省的省会",
                subject_ref="苏州",
                polarity="NEGATIVE",
            ),
            ann(
                index,
                body,
                "af_capital",
                "苏州不是江苏省的省会",
                subject_ref="苏州",
                polarity="POSITIVE",
            ),
        ],
    )

    assert conflict.status == "STRUCTURE_INVALID"
    assert any(
        "conflicting polarity" in error for error in conflict.errors
    )


# --------------------------------------------------------------------------- #
# 11-13: comparison, causality, attribution
# --------------------------------------------------------------------------- #
def test_11_comparative_and_superlative_keep_scope():
    body = (
        "Suzhou produces more silk than Hangzhou. "
        "苏州丝绸产量居全国之首。"
    )
    index, _ = make_index(body, cvs="cv_comp")

    result = validate(
        index,
        body,
        [
            ann(
                index,
                body,
                "af_more_silk",
                "Suzhou produces more silk than Hangzhou",
                subject_ref="Suzhou",
                proposition="苏州丝绸产量高于杭州丝绸产量（基线数值缺失）",
                fact_kind="COMPARISON",
                language="en",
                note="比较范围：苏州 vs 杭州；无数值基线",
            ),
            ann(
                index,
                body,
                "af_top_nation",
                "苏州丝绸产量居全国之首",
                subject_ref="苏州",
                proposition="苏州丝绸产量在中国范围内排名第一",
                fact_kind="SUPERLATIVE",
                language="zh",
                note="比较范围：全国；范围不可丢失",
            ),
        ],
    )

    assert result.status == "STRUCTURE_VALID"
    assert result.fact_group_count == 2


def test_12_causal_chain_is_explicitly_separated():
    body = "Because demand rose, prices doubled."
    index, _ = make_index(body, cvs="cv_causal")

    result = validate(
        index,
        body,
        [
            ann(
                index,
                body,
                "af_demand",
                "demand rose",
                subject_ref="demand",
                proposition="需求上升",
                language="en",
            ),
            ann(
                index,
                body,
                "af_prices",
                "prices doubled",
                subject_ref="prices",
                proposition="价格上涨一倍",
                fact_kind="NUMERIC",
                language="en",
            ),
            ann(
                index,
                body,
                "af_causal_link",
                "Because demand rose, prices doubled",
                subject_ref="demand",
                proposition="需求上升导致价格上涨一倍",
                fact_kind="CAUSAL",
                language="en",
                note="因果单列，规则统一：本基准将因果关系单列为一条",
            ),
        ],
    )

    assert result.status == "STRUCTURE_VALID"
    assert result.fact_group_count == 3


def test_13_attribution_does_not_imply_support():
    body = "According to UNESCO, the craft dates back centuries."
    index, _ = make_index(body, cvs="cv_attr")

    result = validate(
        index,
        body,
        [
            ann(
                index,
                body,
                "af_unesco_says",
                "According to UNESCO",
                subject_ref="UNESCO",
                proposition="UNESCO 作出了该表述",
                fact_kind="ATTRIBUTION",
                language="en",
            ),
            ann(
                index,
                body,
                "af_craft_age",
                "the craft dates back centuries",
                subject_ref="the craft",
                proposition="该技艺已有数百年历史",
                language="en",
                note="引述不构成对命题的证实",
            ),
        ],
    )

    assert result.status == "STRUCTURE_VALID"
    # Attribution is recorded; evidence support is never derived here.
    assert result.evidence_support_status == NOT_EVALUATED
    assert result.claim_recall_status == NOT_EVALUATED


# --------------------------------------------------------------------------- #
# 14-17: context, repetition, shared spans, near-duplicates
# --------------------------------------------------------------------------- #
def test_14_same_sentence_different_context_never_merges():
    body_a = "Hangzhou is known for tea.\nThe city has 2000 years of history."
    body_b = "Suzhou is known for silk.\nThe city has 2000 years of history."

    index_a, _ = make_index(body_a, cvs="cv_ctx_a")
    index_b, _ = make_index(body_b, cvs="cv_ctx_b")

    sentence = "The city has 2000 years of history"

    result_a = validate(
        index_a,
        body_a,
        [
            ann(
                index_a,
                body_a,
                "af_city_history",
                sentence,
                subject_ref="杭州",
                proposition="杭州有2000年历史",
                requires_context=True,
                context_start=body_a.index("Hangzhou"),
                context_end=body_a.index("Hangzhou") + len("Hangzhou"),
                language="zh",
            )
        ],
    )

    result_b = validate(
        index_b,
        body_b,
        [
            ann(
                index_b,
                body_b,
                "af_city_history",
                sentence,
                subject_ref="苏州",
                proposition="苏州有2000年历史",
                requires_context=True,
                context_start=body_b.index("Suzhou"),
                context_end=body_b.index("Suzhou") + len("Suzhou"),
                language="zh",
            )
        ],
    )

    assert result_a.status == "STRUCTURE_VALID"
    assert result_b.status == "STRUCTURE_VALID"

    built_a = build(**ann(index_a, body_a, "af_city_history", sentence,
                          subject_ref="杭州"))
    built_b = build(**ann(index_b, body_b, "af_city_history", sentence,
                          subject_ref="苏州"))

    # Same group name and same sentence text, but version/digest differ:
    # occurrence identities must never collide across versions.
    assert (
        built_a.fact_occurrence_id != built_b.fact_occurrence_id
    )


def test_15_repeated_fact_keeps_one_group_two_positions():
    body = "Suzhou is a craft. Suzhou is a craft."
    index, _ = make_index(body, cvs="cv_repeat")

    second = body.index("Suzhou is a craft.", 1)

    result = validate(
        index,
        body,
        [
            ann(index, body, "af_craft", "Suzhou is a craft",
                subject_ref="Suzhou", language="en"),
            ann(index, body, "af_craft", "Suzhou is a craft",
                start=second, end=second + len("Suzhou is a craft"),
                subject_ref="Suzhou", language="en"),
        ],
    )

    assert result.status == "STRUCTURE_VALID"
    assert result.annotation_count == 2
    assert result.fact_group_count == 1
    assert result.fact_occurrence_count == 2
    assert result.adjudicated_group_count == 1


def test_16_two_groups_may_share_the_exact_same_span():
    body = "Suzhou is a craft centre with a long history."
    index, _ = make_index(body, cvs="cv_shared_span")

    quote = "Suzhou is a craft centre with a long history"

    result = validate(
        index,
        body,
        [
            ann(index, body, "af_group_one", quote,
                subject_ref="Suzhou", language="en"),
            ann(index, body, "af_group_two", quote,
                subject_ref="Suzhou", language="en"),
        ],
    )

    assert result.status == "STRUCTURE_VALID"
    assert result.errors == ()
    assert result.fact_group_count == 2

    built_one = build(**ann(index, body, "af_group_one", quote))
    built_two = build(**ann(index, body, "af_group_two", quote))

    assert (
        built_one.fact_occurrence_id != built_two.fact_occurrence_id
    )


def test_17_one_character_difference_changes_identity():
    body_one = "苏绣有2000多年历史。"
    body_two = "苏绣有2001多年历史。"

    index_one, _ = make_index(body_one, cvs="cv_char_a")
    index_two, _ = make_index(body_two, cvs="cv_char_b")

    assert index_one.content_sha256 != index_two.content_sha256

    stale = validate(
        index_two,
        body_two,
        [
            ann(
                index_one,  # annotation bound to the OLD fingerprint
                body_one,
                "af_history",
                "2000多年",
                subject_ref="苏绣",
                proposition="苏绣的历史超过2000年",
                fact_kind="NUMERIC",
            )
        ],
    )

    assert stale.status == "STRUCTURE_INVALID"
    assert any(
        "content_sha256" in error for error in stale.errors
    )


# --------------------------------------------------------------------------- #
# 18-19: binding and structural violations
# --------------------------------------------------------------------------- #
def test_18_wrong_sha_and_wrong_pack_are_rejected():
    body = "苏绣是苏州的传统工艺。"
    index, _ = make_index(body, cvs="cv_bind")

    wrong_sha = validate(
        index,
        body,
        [
            ann(
                index, body, "af_bind_sha", "苏绣是苏州的传统工艺",
                content_sha256="0" * 64,
            )
        ],
    )

    assert wrong_sha.status == "STRUCTURE_INVALID"
    assert any(
        "content_sha256" in error for error in wrong_sha.errors
    )

    wrong_pack = validate(
        index,
        body,
        [
            ann(
                index, body, "af_bind_pack", "苏绣是苏州的传统工艺",
                evidence_pack_id="ep_other",
            )
        ],
    )

    assert wrong_pack.status == "STRUCTURE_INVALID"
    assert any(
        "evidence_pack_id" in error for error in wrong_pack.errors
    )


def test_19_illegal_quotes_offsets_context_and_vocabularies():
    body = "苏绣有2000多年历史。"
    index, _ = make_index(body, cvs="cv_bad")

    # source_quote mismatch
    bad_quote = validate(
        index, body,
        [ann(index, body, "af_q", "2000多年", note="")],
    )
    mismatched = build(
        **ann(index, body, "af_q", "2000多年")
    )
    tampered = dataclasses.replace(mismatched, source_quote="3000多年")
    # frozen dataclass: replace creates a new instance whose occurrence id
    # was derived from identical span fields, so identity stays consistent;
    # only the quote equality can fail.
    result = validate_atomic_annotations(index, body, [tampered])

    assert bad_quote.status == "STRUCTURE_VALID"
    assert result.status == "STRUCTURE_INVALID"
    assert any(
        "source_quote does not" in error for error in result.errors
    )

    # out-of-bounds span
    oob = validate_atomic_annotations(
        index,
        body,
        [
            build(
                **ann(index, body, "af_oob", "x",
                      start=len(body), end=len(body) + 5)
            )
        ],
    )

    assert oob.status == "STRUCTURE_INVALID"
    assert any("out of bounds" in error for error in oob.errors)

    # context out of bounds
    bad_ctx = validate(
        index, body,
        [
            ann(
                index, body, "af_ctx", "2000多年",
                subject_ref="苏绣",
                requires_context=True,
                context_start=0,
                context_end=len(body) + 10,
            )
        ],
    )

    assert bad_ctx.status == "STRUCTURE_INVALID"
    assert any("context span" in error for error in bad_ctx.errors)

    # invalid vocabulary values must fail at construction time
    with pytest.raises(AtomicAnnotationError):
        build(**ann(index, body, "af_lang", "2000多年", language="fr"))

    with pytest.raises(AtomicAnnotationError):
        build(**ann(index, body, "af_status", "2000多年",
                    status="APPROVED"))

    with pytest.raises(AtomicAnnotationError):
        build(**ann(index, body, "af_kind", "2000多年",
                    fact_kind="MAGIC"))

    with pytest.raises(AtomicAnnotationError):
        build(**ann(index, body, "af_pol", "2000多年",
                    polarity="NEUTRAL"))

    # empty span is structurally impossible
    with pytest.raises(AtomicAnnotationError):
        build(
            **ann(index, body, "af_empty", "2000多年",
                  start=0, end=0)
        )

    # context offsets without requires_context are rejected
    with pytest.raises(AtomicAnnotationError):
        build(
            **ann(index, body, "af_orphan_ctx", "2000多年",
                  context_start=0, context_end=3)
        )


# --------------------------------------------------------------------------- #
# 20 + safety behaviours
# --------------------------------------------------------------------------- #
def test_20_identity_unverified_and_no_real_recall_is_ever_produced():
    body = "苏绣是苏州的传统工艺。"
    index, _ = make_index(body, cvs="cv_safe")

    result = validate(
        index, body,
        [ann(index, body, "af_safe", "苏绣是苏州的传统工艺")]
    )

    assert result.status == "STRUCTURE_VALID"
    assert result.annotator_identity_verified is False
    assert result.claim_recall_status == NOT_EVALUATED
    assert result.evidence_support_status == NOT_EVALUATED
    assert (
        result.atomic_enumeration_status
        == ATOMIC_ENUMERATION_NOT_VERIFIED
    )

    field_names = {f.name for f in dataclasses.fields(result)}
    assert "recall" not in field_names
    assert "recall_value" not in field_names


def test_21_sentence_overlap_is_never_atomic_enumeration():
    body = "Suzhou is a craft. Suzhou has 2000 years of history."
    index, claims = make_index(
        body, cvs="cv_overlap", with_claims=True
    )

    assert len(claims) == 2

    result = validate(
        index,
        body,
        [
            ann(
                index, body, "af_history_value", "2000 years",
                subject_ref="Suzhou",
                proposition="Suzhou has 2000 years of history",
                fact_kind="NUMERIC", language="en",
            ),
            ann(
                index, body, "af_history_holder", "Suzhou has",
                subject_ref="Suzhou",
                proposition="苏绣拥有该历史属性",
                language="en",
            ),
        ],
    )

    assert result.status == "STRUCTURE_VALID"
    # Both overlap sentence candidates — recorded, nothing more.
    assert (
        len(result.sentence_candidate_covered_occurrence_ids) == 2
    )
    assert (
        result.atomic_enumeration_status
        == ATOMIC_ENUMERATION_NOT_VERIFIED
    )
    assert result.claim_recall_status == NOT_EVALUATED


def test_22_empty_annotation_batch_is_valid_and_evaluates_nothing():
    body = "苏绣是苏州的传统工艺。"
    index, _ = make_index(body, cvs="cv_empty")

    result = validate_atomic_annotations(index, body, [])

    assert result.status == "STRUCTURE_VALID"
    assert result.annotation_count == 0
    assert result.fact_group_count == 0
    assert result.claim_recall_status == NOT_EVALUATED
    assert (
        result.atomic_enumeration_status
        == ATOMIC_ENUMERATION_NOT_VERIFIED
    )
    assert result.annotator_identity_verified is False


def test_23_adjudicated_requires_adjudicator_identity():
    body = "苏绣是苏州的传统工艺。"
    index, _ = make_index(body, cvs="cv_adj")

    with pytest.raises(AtomicAnnotationError):
        build(
            **ann(index, body, "af_adj", "苏绣是苏州的传统工艺",
                  status="ADJUDICATED", adjudicator="")
        )


def test_24_occurrence_identity_is_deterministic_and_unforgeable():
    body = "苏绣有2000多年历史。"
    index, _ = make_index(body, cvs="cv_id")

    kwargs = ann(index, body, "af_id", "2000多年")

    first = build(**kwargs)
    second = build(**kwargs)

    assert first.fact_occurrence_id == second.fact_occurrence_id
    assert first.fact_occurrence_id.startswith("focc_")

    manual = derive_fact_occurrence_id(
        first.benchmark_id,
        first.content_version_id,
        first.content_sha256,
        first.evidence_pack_id,
        first.fact_group_id,
        first.start,
        first.end,
    )
    assert manual == first.fact_occurrence_id

    with pytest.raises(AtomicAnnotationError):
        build(**{**kwargs, "fact_occurrence_id": "focc_forged"})


def test_25_group_conflicts_and_duplicates_fail_closed():
    body = "Suzhou is a craft. Suzhou is a craft."
    index, _ = make_index(body, cvs="cv_conflict")

    # conflicting subject_ref inside one group
    subject_conflict = validate(
        index, body,
        [
            ann(index, body, "af_who", "Suzhou is a craft",
                subject_ref="Suzhou", language="en"),
            ann(index, body, "af_who", "Suzhou is a craft",
                start=body.index("Suzhou is a craft.", 1),
                end=body.index("Suzhou is a craft.", 1)
                + len("Suzhou is a craft"),
                subject_ref="Hangzhou", language="en"),
        ],
    )

    assert subject_conflict.status == "STRUCTURE_INVALID"
    assert any(
        "conflicting subject_ref" in error
        for error in subject_conflict.errors
    )

    # duplicate span inside one group -> duplicate occurrence identity
    duplicate = validate(
        index, body,
        [
            ann(index, body, "af_dup", "Suzhou is a craft",
                subject_ref="Suzhou", language="en"),
            ann(index, body, "af_dup", "Suzhou is a craft",
                subject_ref="Suzhou", language="en"),
        ],
    )

    assert duplicate.status == "STRUCTURE_INVALID"
    assert any(
        "duplicate fact_occurrence_id" in error
        for error in duplicate.errors
    )
    assert any(
        "duplicate occurrence span" in error
        for error in duplicate.errors
    )


def test_26_crlf_source_stays_lossless_for_annotations():
    body = "Suzhou is a craft.\r\n苏绣有2000多年历史。"
    index, _ = make_index(body, cvs="cv_crlf")

    # The index must reconstruct the CRLF source byte-for-byte.
    assert "".join(s.text for s in index.segments) == body

    result = validate(
        index,
        body,
        [
            ann(index, body, "af_crlf_history", "2000多年",
                subject_ref="苏绣", fact_kind="NUMERIC"),
        ],
    )

    assert result.status == "STRUCTURE_VALID"
    assert result.errors == ()


def test_27_legacy_gold_recall_limits_are_unchanged():
    """The approved conservative Gold scorer must stay exactly as it was."""
    body = "The project began in 2020, and revenue reached 100 million."
    index, claims = make_index(
        body, cvs="cv_legacy", with_claims=True
    )

    # no gold -> NOT_EVALUATED, no number
    empty = evaluate_human_gold_recall(index)
    assert empty.status == "NOT_EVALUATED"
    assert empty.recall is None
    assert empty.gold_count == 0

    # one sentence claim still cannot credit two atomic facts
    cid = claims[0].claim_id
    fact_one = HumanGoldAtomicFact(
        "f1", index.content_version_id, index.content_sha256,
        0, 20, "project began in 2020", cid,
    )
    fact_two = HumanGoldAtomicFact(
        "f2", index.content_version_id, index.content_sha256,
        20, len(body) - 1, "revenue reached 100 million", cid,
    )

    with pytest.raises(ValueError):
        evaluate_human_gold_recall(
            index, [fact_one, fact_two],
            benchmark_id="b", annotator_id="a",
        )
