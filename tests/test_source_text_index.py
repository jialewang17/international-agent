"""I2-C-001A-R2: strictly conservative, offline negative tests."""

from dataclasses import FrozenInstanceError
from hashlib import sha256

import pytest

from api.claim_extraction import DeterministicClaimExtractor
from api.fact_safety import _fingerprint
from api.schemas import Claim, ContentVersion
from api.source_text_index import (
    CLAIM_MAPPED,
    NON_FACTUAL_WITH_REASON,
    UNCERTAIN_REVIEW_REQUIRED,
    NOT_EVALUATED,
    CONTEXT_EQUIVALENCE_NOT_EVALUATED,
    HumanGoldAtomicFact,
    build_source_text_index,
    evaluate_human_gold_recall,
)


def snapshots(text):
    return DeterministicClaimExtractor().extract(text)


def build(text, *, pack_id="ep_A", version_id="cv_A"):
    claims = snapshots(text)

    version = ContentVersion(
        content_version_id=version_id,
        task_id="task_1",
        content=text,
        evidence_pack_id=pack_id,
        claim_ids=[c.claim_id for c in claims],
    )

    return (
        version,
        claims,
        build_source_text_index(version, claims),
    )


def exact_partition(text, index):
    assert index.source_length == len(text)

    assert index.content_sha256 == sha256(
        text.encode("utf-8")
    ).hexdigest()

    assert index.offset_unit == "python_unicode_codepoints"

    assert "".join(
        s.text for s in index.segments
    ) == text

    cursor = 0

    for s in index.segments:
        assert s.start == cursor
        assert s.start < s.end
        assert text[s.start:s.end] == s.text
        cursor = s.end

    assert cursor == len(text)

    for o in index.occurrences:
        assert text[o.start:o.end] == o.source_text

        assert (
            o.context_status
            == CONTEXT_EQUIVALENCE_NOT_EVALUATED
        )

    assert index.semantic_support_status == NOT_EVALUATED
    assert index.claim_recall_status == NOT_EVALUATED


@pytest.mark.parametrize(
    "text",
    [
        "",
        "\n",
        "\r\n",
        "   \r\n",
        "苏绣😀\r\n下一行。",
        "A\n\nB",
        "---\n#Suzhou\n😀",
        "- 3.5% in 2025.\nhttps://example.com/x?id=7",
        "\u2028here is a sentence.",
    ],
)
def test_exact_original_partition(text):
    _v, _c, idx = build(text)
    exact_partition(text, idx)


def test_repeated_sentence_twice_same_line_only_one_claim():
    body = "Suzhou is a craft. Suzhou is a craft."

    _v, claims, idx = build(body)

    assert len(claims) == 1
    assert len(idx.unique_claim_ids) == 1
    assert len(idx.occurrences) == 2

    assert (
        idx.occurrences[0].claim_id
        == idx.occurrences[1].claim_id
    )

    assert (
        idx.occurrences[0].start
        != idx.occurrences[1].start
    )

    assert idx.segments[0].status == CLAIM_MAPPED


def test_repeated_sentence_twice_separate_lines_only_one_claim():
    body = (
        "Suzhou is a craft.\n"
        "Suzhou is a craft."
    )

    _v, claims, idx = build(body)

    assert len(claims) == 1
    assert len(idx.occurrences) == 2

    assert [s.status for s in idx.segments] == [
        CLAIM_MAPPED,
        CLAIM_MAPPED,
    ]

    exact_partition(body, idx)


def test_same_text_different_context_does_not_inherit_support():
    body = (
        "Company A reported results. It increased.\n\n"
        "Company B reported results. It increased."
    )

    _v, claims, idx = build(body)

    referent = next(
        c for c in claims
        if c.text == "It increased."
    )

    hits = [
        o for o in idx.occurrences
        if o.claim_id == referent.claim_id
    ]

    assert len(hits) == 2

    assert all(
        o.context_status
        == CONTEXT_EQUIVALENCE_NOT_EVALUATED
        for o in hits
    )

    assert all(
        s.status == UNCERTAIN_REVIEW_REQUIRED
        for s in idx.segments
        if "It increased" in s.text
    )

    assert idx.semantic_support_status == NOT_EVALUATED


@pytest.mark.parametrize(
    "a,b",
    [
        ("苏绣是传统工艺。", "苏绣不是传统工艺。"),
        ("Revenue rose 3%.", "Revenue fell 3%."),
        (
            "Revenue rose 3% in 2024.",
            "Revenue rose 3% in 2025.",
        ),
        (
            "The work may finish in 2026.",
            "The work did finish in 2026.",
        ),
        ("A公司获得批准。", "B公司获得批准。"),
        ("超过100亿元。", "不超过100亿元。"),
        ("Hello World.", "Hello World!"),
        ("Hello World.", "hello World."),
    ],
)
def test_one_character_or_semantic_marker_difference_never_dedup(
    a, b,
):
    _, claims, idx = build(a + "\n" + b)

    assert len(claims) == 2
    assert claims[0].claim_id != claims[1].claim_id

    assert len(idx.unique_claim_ids) == 2
    assert len(idx.occurrences) == 2

    assert (
        idx.occurrences[0].claim_id
        != idx.occurrences[1].claim_id
    )


def test_forged_claim_id_rejected():
    version, claims, _idx = build("A claim.")

    fake = claims[0].model_copy(deep=True)
    fake.claim_id = "clm_fake"

    version.claim_ids = [fake.claim_id]

    with pytest.raises(ValueError, match="fingerprint"):
        build_source_text_index(version, [fake])


def test_same_id_different_claim_text_is_fail_closed():
    version, claims, _idx = build("A claim.")

    fake = claims[0].model_copy(deep=True)
    fake.text = "A CLAIM."

    with pytest.raises(ValueError, match="collision"):
        build_source_text_index(
            version,
            [claims[0], fake],
        )


def test_same_id_different_evidence_refs_is_fail_closed():
    version, claims, _idx = build("A claim.")

    altered = claims[0].model_copy(deep=True)
    altered.evidence_ids = ["ev_1"]

    with pytest.raises(ValueError, match="collision"):
        build_source_text_index(
            version,
            [claims[0], altered],
        )


def test_noncanonical_claim_whitespace_rejected_even_if_hash_matches():
    version, _claims, _idx = build("A B.")

    impostor = Claim(
        claim_id="clm_" + _fingerprint("A  B."),
        text="A  B.",
        evidence_ids=[],
    )

    with pytest.raises(ValueError, match="canonical"):
        build_source_text_index(
            version,
            [impostor],
        )


def test_partial_prefix_with_valid_id_not_mapped_as_sentence():
    text = "Source says something but lacks context."

    v, _c, _i = build(text)

    partial = Claim(
        claim_id=(
            "clm_" + _fingerprint("Source says something")
        ),
        text="Source says something",
    )

    v.claim_ids = [partial.claim_id]

    idx = build_source_text_index(v, [partial])

    assert idx.occurrences == ()
    assert idx.unlocated_claim_ids == (
        partial.claim_id,
    )

    assert (
        idx.segments[0].status
        == UNCERTAIN_REVIEW_REQUIRED
    )


def test_markdown_prefix_is_not_part_of_claim_text():
    text = (
        "# Title\n"
        "- Suzhou is a craft.\n"
        "---\n"
        "#Suzhou\n"
        "😀\n"
    )

    _v, claims, idx = build(text)

    assert any(
        x.text == "Suzhou is a craft."
        for x in claims
    )

    assert [s.status for s in idx.segments] == [
        CLAIM_MAPPED,
        CLAIM_MAPPED,
        NON_FACTUAL_WITH_REASON,
        UNCERTAIN_REVIEW_REQUIRED,
        UNCERTAIN_REVIEW_REQUIRED,
    ]

    exact_partition(text, idx)


def test_crossline_sentence_keeps_true_offsets():
    text = "This is\n  a claim."

    _, claims, idx = build(text)

    assert len(claims) == 1
    assert len(idx.occurrences) == 1

    assert idx.occurrences[0].source_text == text

    assert (
        idx.occurrences[0].alignment
        == "WHITESPACE_NORMALIZED_SOURCE"
    )

    assert all(
        s.status == CLAIM_MAPPED
        for s in idx.segments
    )


def test_atomic_compound_and_numbers_still_unresolved():
    text = (
        "The project began in 2020, "
        "and revenue reached 100 million in 2024."
    )

    _, claims, idx = build(text)

    assert len(claims) == 1
    assert len(idx.occurrences) == 1

    assert (
        idx.segments[0].status
        == UNCERTAIN_REVIEW_REQUIRED
    )

    assert (
        "COMPOUND_CLAUSE_POSSIBLE"
        in idx.segments[0].atomic_risks
    )

    assert (
        "MULTIPLE_NUMERIC_FACTS_POSSIBLE"
        in idx.segments[0].atomic_risks
    )


def test_causal_signal_stays_review_required():
    _, claims, idx = build(
        "The decline caused a shortage."
    )

    assert len(claims) == 1

    assert (
        idx.segments[0].status
        == UNCERTAIN_REVIEW_REQUIRED
    )

    assert (
        "CAUSAL_ASSERTION_REVIEW"
        in idx.segments[0].atomic_risks
    )


def test_cross_pack_same_claim_id_does_not_share_evidence_scope():
    _, ca, a = build(
        "Same claim.",
        pack_id="ep_A",
    )
    _, cb, b = build(
        "Same claim.",
        pack_id="ep_B",
    )

    assert ca[0].claim_id == cb[0].claim_id

    assert a.occurrences[0].evidence_pack_id == "ep_A"
    assert b.occurrences[0].evidence_pack_id == "ep_B"

    assert (
        a.semantic_support_status
        == b.semantic_support_status
        == NOT_EVALUATED
    )


def test_duplicated_input_claim_id_does_not_create_second_unique():
    ver, claims, _ = build(
        "A claim. A claim."
    )

    idx = build_source_text_index(
        ver,
        [
            claims[0],
            claims[0].model_copy(deep=True),
        ],
    )

    assert len(idx.unique_claim_ids) == 1
    assert len(idx.occurrences) == 2


def test_missing_snapshot_fails_closed():
    ver, claims, _ = build("A claim.")

    with pytest.raises(ValueError, match="IDs must equal"):
        build_source_text_index(ver, [])


def test_duplicate_version_claim_ids_fail_closed():
    ver, claims, _ = build("A claim.")

    ver.claim_ids = [
        claims[0].claim_id,
        claims[0].claim_id,
    ]

    with pytest.raises(ValueError, match="duplicate IDs"):
        build_source_text_index(ver, claims)


def test_mutable_source_changes_index_digest_without_mutating_old_index():
    ver, claims, idx = build("A claim.")

    old_digest = idx.content_sha256
    ver.content = "A different claim."

    ver.claim_ids = [
        c.claim_id for c in snapshots(ver.content)
    ]

    new_idx = build_source_text_index(
        ver,
        snapshots(ver.content),
    )

    assert old_digest != new_idx.content_sha256

    assert (
        idx.occurrences[0].source_text
        == "A claim."
    )


def test_models_are_immutable():
    _v, _c, idx = build("A claim.")

    with pytest.raises(FrozenInstanceError):
        idx.source_length = 999

    with pytest.raises(FrozenInstanceError):
        idx.occurrences[0].claim_id = "clm_tampered"


def annotation(
    index,
    fact_id,
    match_id=None,
    proposition=None,
):
    return HumanGoldAtomicFact(
        fact_id=fact_id,
        content_version_id=index.content_version_id,
        content_sha256=index.content_sha256,
        start=0,
        end=index.source_length,
        proposition=proposition or fact_id,
        reviewed_matching_claim_id=match_id,
    )


def test_no_human_gold_does_not_fabricate_recall():
    _, _, idx = build("A claim.")

    result = evaluate_human_gold_recall(idx)

    assert result.status == NOT_EVALUATED
    assert result.recall is None


def test_gold_coverage_exposes_second_atomic_fact_missing():
    body = (
        "The project began in 2020, "
        "and revenue reached 100 million in 2024."
    )

    _, claims, idx = build(body)

    report = evaluate_human_gold_recall(
        idx,
        [
            annotation(
                idx,
                "startup",
                claims[0].claim_id,
            ),
            annotation(
                idx,
                "revenue",
            ),
        ],
        benchmark_id="synthetic",
        annotator_id="synthetic",
    )

    assert (
        report.status
        == "SUPPLIED_GOLD_SCORED_NOT_VERIFIED"
    )

    assert report.recall == 0.5
    assert report.missing_fact_ids == ("revenue",)


def test_one_candidate_cannot_double_credit_atomic_gold():
    _, claims, idx = build("A claim.")

    with pytest.raises(
        ValueError,
        match="one sentence Claim",
    ):
        evaluate_human_gold_recall(
            idx,
            [
                annotation(
                    idx,
                    "fact1",
                    claims[0].claim_id,
                ),
                annotation(
                    idx,
                    "fact2",
                    claims[0].claim_id,
                ),
            ],
            benchmark_id="synthetic",
            annotator_id="synthetic",
        )


def test_literal_duplicate_gold_not_auto_counted_twice():
    _, claims, idx = build(
        "A claim. A claim."
    )

    with pytest.raises(
        ValueError,
        match="ambiguous duplicate gold",
    ):
        evaluate_human_gold_recall(
            idx,
            [
                annotation(
                    idx,
                    "f1",
                    claims[0].claim_id,
                    "same proposition",
                ),
                annotation(
                    idx,
                    "f2",
                    None,
                    "same proposition",
                ),
            ],
            benchmark_id="synthetic",
            annotator_id="synthetic",
        )


def test_same_literal_gold_different_context_requires_human_review():
    _, claims, idx = build(
        "It increased. It increased."
    )

    with pytest.raises(
        ValueError,
        match="ambiguous duplicate gold",
    ):
        evaluate_human_gold_recall(
            idx,
            [
                annotation(
                    idx,
                    "f1",
                    claims[0].claim_id,
                    "It increased.",
                ),
                annotation(
                    idx,
                    "f2",
                    None,
                    "It increased.",
                ),
            ],
            benchmark_id="synthetic",
            annotator_id="synthetic",
        )


def test_gold_wrong_body_fingerprint_fails_closed():
    _, claims, idx = build("A claim.")

    wrong = HumanGoldAtomicFact(
        "fact1",
        idx.content_version_id,
        "bad_hash",
        0,
        8,
        "A claim.",
        claims[0].claim_id,
    )

    with pytest.raises(ValueError, match="fingerprint"):
        evaluate_human_gold_recall(
            idx,
            [wrong],
            benchmark_id="synthetic",
            annotator_id="synthetic",
        )


def test_gold_unknown_claim_id_fails_closed():
    _, claims, idx = build("A claim.")

    with pytest.raises(ValueError, match="unknown"):
        evaluate_human_gold_recall(
            idx,
            [
                annotation(
                    idx,
                    "fact1",
                    "clm_unknown",
                )
            ],
            benchmark_id="synthetic",
            annotator_id="synthetic",
        )


def test_gold_source_offsets_must_be_valid():
    _, claims, idx = build("A claim.")

    wrong = HumanGoldAtomicFact(
        "f1",
        idx.content_version_id,
        idx.content_sha256,
        -1,
        1,
        "A claim.",
        None,
    )

    with pytest.raises(ValueError, match="offset"):
        evaluate_human_gold_recall(
            idx,
            [wrong],
            benchmark_id="synthetic",
            annotator_id="synthetic",
        )


def test_gold_manual_metadata_required():
    _, claims, idx = build("A claim.")

    with pytest.raises(ValueError, match="benchmark_id"):
        evaluate_human_gold_recall(
            idx,
            [
                annotation(
                    idx,
                    "fact1",
                )
            ],
        )


def test_mismatch_pack_id_rejected():
    ver, claims, _ = build("A claim.")

    ver.evidence_pack_id = None

    with pytest.raises(ValueError, match="evidence_pack_id"):
        build_source_text_index(
            ver,
            claims,
        )
