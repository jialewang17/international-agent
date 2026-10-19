"""Offline unit tests for api.claim_extraction (I2-B-001).

Every test runs fully offline: no real LLM, no network, no dependencies beyond
the standard library, pytest and the project's own modules.
"""

import re

import pytest

from api.claim_extraction import ClaimExtractor, DeterministicClaimExtractor
from api.fact_safety import _fingerprint
from api.schemas import Claim


def extract(content):
    """Convenience wrapper around a fresh extractor instance."""
    return DeterministicClaimExtractor().extract(content)


# ---------------------------------------------------------------------------
# Test 01 -- English single sentence
# ---------------------------------------------------------------------------
def test_01_english_single_sentence():
    text = "Suzhou embroidery carries a living craft tradition."
    claims = extract(text)

    assert len(claims) == 1
    claim = claims[0]
    assert isinstance(claim, Claim)
    assert claim.text == text
    assert claim.claim_id.startswith("clm_")
    assert claim.evidence_ids == []


# ---------------------------------------------------------------------------
# Test 02 -- English multiple sentences keep order
# ---------------------------------------------------------------------------
def test_02_english_multiple_sentences():
    text = "Suzhou embroidery is a traditional craft. It has a long history."
    claims = extract(text)

    assert [c.text for c in claims] == [
        "Suzhou embroidery is a traditional craft.",
        "It has a long history.",
    ]


# ---------------------------------------------------------------------------
# Test 03 -- Chinese multiple sentences
# ---------------------------------------------------------------------------
def test_03_chinese_multiple_sentences():
    text = "苏绣是中国传统工艺之一。苏绣具有悠久历史。"
    claims = extract(text)

    assert [c.text for c in claims] == [
        "苏绣是中国传统工艺之一。",
        "苏绣具有悠久历史。",
    ]


# ---------------------------------------------------------------------------
# Test 04 -- Mixed Chinese / English
# ---------------------------------------------------------------------------
def test_04_mixed_language():
    text = "苏绣是一种传统工艺。Suzhou embroidery has a long history."
    claims = extract(text)

    assert [c.text for c in claims] == [
        "苏绣是一种传统工艺。",
        "Suzhou embroidery has a long history.",
    ]


# ---------------------------------------------------------------------------
# Test 05 -- Decimal numbers are not split
# ---------------------------------------------------------------------------
def test_05_decimal_not_split():
    text = "The growth rate was 3.14% in 2024. It later declined."
    claims = extract(text)

    assert len(claims) == 2
    assert claims[0].text == "The growth rate was 3.14% in 2024."
    assert "3.14" in claims[0].text
    assert claims[1].text == "It later declined."


# ---------------------------------------------------------------------------
# Test 06 -- English abbreviations are not split
# ---------------------------------------------------------------------------
def test_06_abbreviations_not_split():
    text = "Dr. Li studied embroidery in the U.S. in 2024. She later returned."
    claims = extract(text)

    assert len(claims) == 2
    assert claims[0].text == "Dr. Li studied embroidery in the U.S. in 2024."
    assert claims[1].text == "She later returned."


# ---------------------------------------------------------------------------
# Test 07 -- Negation is preserved verbatim
# ---------------------------------------------------------------------------
def test_07_negation_preserved():
    text = "Suzhou embroidery was not recognized by UNESCO in 2006."
    claims = extract(text)

    assert len(claims) == 1
    assert claims[0].text == text
    assert "not" in claims[0].text


# ---------------------------------------------------------------------------
# Test 08 -- Compound sentence is not split on "but"
# ---------------------------------------------------------------------------
def test_08_compound_sentence_not_split():
    text = "The craft is important, but its export value is unknown."
    claims = extract(text)

    assert len(claims) == 1
    assert claims[0].text == text


# ---------------------------------------------------------------------------
# Test 09 -- Markdown list prefix is cleaned, prose kept
# ---------------------------------------------------------------------------
def test_09_markdown_list_item():
    text = "- 苏绣于2006年入选相关名录。"
    claims = extract(text)

    assert len(claims) == 1
    assert claims[0].text == "苏绣于2006年入选相关名录。"


# ---------------------------------------------------------------------------
# Test 10 -- Duplicate claims are de-duplicated by id
# ---------------------------------------------------------------------------
def test_10_duplicate_claims_deduped():
    text = "Suzhou is a craft. Suzhou is a craft."
    claims = extract(text)

    assert len(claims) == 1
    assert claims[0].text == "Suzhou is a craft."


# ---------------------------------------------------------------------------
# Test 11 -- Whitespace normalization yields the same claim id
# ---------------------------------------------------------------------------
def test_11_whitespace_normalization_same_id():
    a = extract("Hello   World.")
    b = extract("Hello World.")

    assert a[0].text == "Hello World."
    assert b[0].text == "Hello World."
    assert a[0].claim_id == b[0].claim_id


# ---------------------------------------------------------------------------
# Test 12 -- Claim id is case sensitive
# ---------------------------------------------------------------------------
def test_12_claim_id_case_sensitive():
    a = extract("Hello World.")
    b = extract("hello World.")

    assert a[0].text != b[0].text
    assert a[0].claim_id != b[0].claim_id


# ---------------------------------------------------------------------------
# Test 13 -- Claim id is punctuation sensitive
# ---------------------------------------------------------------------------
def test_13_claim_id_punctuation_sensitive():
    a = extract("Hello World.")
    b = extract("Hello World!")

    assert a[0].text != b[0].text
    assert a[0].claim_id != b[0].claim_id


# ---------------------------------------------------------------------------
# Test 14 -- Unsupported statement is kept; no evidence is fabricated
# ---------------------------------------------------------------------------
def test_14_no_fabricated_evidence():
    text = "Suzhou embroidery generated 12 billion USD in exports in 2025."
    claims = extract(text)

    assert len(claims) == 1
    claim = claims[0]
    assert claim.text == text
    assert "12 billion" in claim.text
    assert "2025" in claim.text
    assert claim.evidence_ids == []


# ---------------------------------------------------------------------------
# Test 15 -- Empty / whitespace-only input
# ---------------------------------------------------------------------------
def test_15_empty_and_whitespace_input():
    assert extract("") == []
    assert extract("   \n\t  ") == []


# ---------------------------------------------------------------------------
# Test 16 -- Non-string input raises TypeError
# ---------------------------------------------------------------------------
def test_16_non_string_input_raises_type_error():
    for bad in (None, 123, 3.14, ["a"], {"a": 1}, ("a",)):
        with pytest.raises(TypeError):
            extract(bad)


# ---------------------------------------------------------------------------
# Test 17 -- Pure emoji input
# ---------------------------------------------------------------------------
def test_17_pure_emoji():
    assert extract("😀 🎉") == []


# ---------------------------------------------------------------------------
# Test 18 -- Pure hashtags input
# ---------------------------------------------------------------------------
def test_18_pure_hashtags():
    assert extract("#Suzhou #Embroidery") == []


# ---------------------------------------------------------------------------
# Test 19 -- CRLF line endings
# ---------------------------------------------------------------------------
def test_19_crlf_newlines():
    text = "Suzhou is a craft.\r\nIt has a long history.\r\n"
    claims = extract(text)

    assert [c.text for c in claims] == [
        "Suzhou is a craft.",
        "It has a long history.",
    ]


# ---------------------------------------------------------------------------
# Test 20 -- Determinism: repeated runs and separate instances agree
# ---------------------------------------------------------------------------
def test_20_determinism():
    text = "Suzhou is a craft. It has a long history. 苏绣具有悠久历史。"

    first = DeterministicClaimExtractor()
    second = DeterministicClaimExtractor()

    run_a = first.extract(text)
    run_b = first.extract(text)
    run_c = second.extract(text)

    def signature(claims):
        return [(c.claim_id, c.text, c.evidence_ids) for c in claims]

    assert signature(run_a) == signature(run_b)
    assert signature(run_a) == signature(run_c)


# ---------------------------------------------------------------------------
# Test 21 -- Long content: every sentence is processed, no truncation
# ---------------------------------------------------------------------------
def test_21_long_content_no_truncation():
    sentences = [f"Sentence number {i} states a fact." for i in range(1, 31)]
    text = " ".join(sentences)
    claims = extract(text)

    assert len(claims) == 30
    assert claims[0].text == "Sentence number 1 states a fact."
    assert claims[-1].text == "Sentence number 30 states a fact."


# ---------------------------------------------------------------------------
# Test 22 -- Protocol conformance
# ---------------------------------------------------------------------------
def test_22_protocol_conformance():
    extractor = DeterministicClaimExtractor()

    assert isinstance(extractor, ClaimExtractor)

    result = extractor.extract("A simple sentence.")
    assert isinstance(result, list)
    assert all(isinstance(claim, Claim) for claim in result)


# ---------------------------------------------------------------------------
# Test 23 -- Every claim text traces back to the source text
# ---------------------------------------------------------------------------
def test_23_claim_text_traces_to_source():
    source = "Suzhou embroidery is a craft. 苏绣具有悠久历史。"
    normalized_source = re.sub(r"\s+", " ", source)

    claims = extract(source)
    assert claims
    for claim in claims:
        assert claim.text in normalized_source

    # Markdown prefix removal keeps the body verbatim.
    markdown_source = "- 苏绣于2006年入选相关名录。"
    markdown_claims = extract(markdown_source)
    assert markdown_claims
    for claim in markdown_claims:
        assert claim.text in markdown_source


# ---------------------------------------------------------------------------
# Test 24 -- Missing terminal punctuation keeps the sentence
# ---------------------------------------------------------------------------
def test_24_missing_terminal_punctuation():
    text = "Suzhou embroidery is a traditional craft"
    claims = extract(text)

    assert len(claims) == 1
    assert claims[0].text == text


# ---------------------------------------------------------------------------
# Test 25 -- Full fingerprint alignment (not just the prefix)
# ---------------------------------------------------------------------------
def test_25_full_fingerprint_alignment():
    text = "Suzhou embroidery is a craft. It has a long history."
    claims = extract(text)

    assert claims
    for claim in claims:
        assert claim.claim_id == "clm_" + _fingerprint(claim.text)
        assert len(claim.claim_id) == len("clm_") + 64


# ---------------------------------------------------------------------------
# I2-B-001-R1 regression tests
#
# Cover the four reported defects: four-digit years being dropped as Markdown
# list indices, URLs split at ``?``/``.``, leading minus signs lost with the
# bullet prefix, and pure hashtag/emoji lines being merged into the following
# paragraph.
#
# The inputs below are test fixtures only; they do not represent real
# historical facts or statistics.
# ---------------------------------------------------------------------------
R1_REGRESSION_CASES = [
    (
        "four_digit_year",
        "2006. 苏绣入选首批国家级非遗。",
        ["2006. 苏绣入选首批国家级非遗。"],
    ),
    (
        "english_four_digit_year",
        "2025. Suzhou embroidery reached 12 billion USD in exports.",
        ["2025. Suzhou embroidery reached 12 billion USD in exports."],
    ),
    (
        "parenthesised_year",
        "1999) 苏绣具有悠久历史。",
        ["1999) 苏绣具有悠久历史。"],
    ),
    (
        "year_at_later_sentence_start",
        "Sources were reviewed. 2006. 苏绣入选首批国家级非遗。",
        ["Sources were reviewed.", "2006. 苏绣入选首批国家级非遗。"],
    ),
    (
        "plain_markdown_number",
        "1. 苏绣具有悠久历史。",
        ["苏绣具有悠久历史。"],
    ),
    (
        "negative_percentage",
        "- 3.5% of output was lost.",
        ["- 3.5% of output was lost."],
    ),
    (
        "negative_currency",
        "- $12 billion USD were lost.",
        ["- $12 billion USD were lost."],
    ),
    (
        "plain_bullet",
        "- 苏绣具有悠久历史。",
        ["苏绣具有悠久历史。"],
    ),
    (
        "url_with_query",
        "See https://example.com/project?id=7 for details. Suzhou is famous.",
        [
            "See https://example.com/project?id=7 for details.",
            "Suzhou is famous.",
        ],
    ),
    (
        "url_at_sentence_end",
        "See https://example.com. Suzhou is famous.",
        ["See https://example.com.", "Suzhou is famous."],
    ),
    (
        "cjk_url",
        "详见https://example.com/project?type=heritage。该项目发布于2006年。",
        [
            "详见https://example.com/project?type=heritage。",
            "该项目发布于2006年。",
        ],
    ),
    (
        "hashtag_only_line",
        "#Suzhou\nIt is a traditional craft.",
        ["It is a traditional craft."],
    ),
    (
        "emoji_only_line",
        "😀\n苏绣是一种传统工艺。",
        ["苏绣是一种传统工艺。"],
    ),
]


@pytest.mark.parametrize(
    "text,expected",
    [(case[1], case[2]) for case in R1_REGRESSION_CASES],
    ids=[case[0] for case in R1_REGRESSION_CASES],
)
def test_r1_regressions(text, expected):
    claims = extract(text)

    assert [claim.text for claim in claims] == expected

    for claim in claims:
        assert claim.evidence_ids == []
        assert claim.claim_id == "clm_" + _fingerprint(claim.text)
