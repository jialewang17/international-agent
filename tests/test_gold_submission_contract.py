"""I2-C-001B-P2B-R1/R2: submission & adjudication contract tests.

All data below is synthetic. It must never be presented as real annotation
work or as a real gold standard.
"""

from dataclasses import fields, replace
from hashlib import sha256

import pytest

from api.atomic_gold_contract import (
    AtomicFactAnnotation,
    validate_atomic_annotations,
)
from api.claim_extraction import DeterministicClaimExtractor
from api.gold_submission_contract import (
    COMPLETENESS_NOT_VERIFIED,
    DECISION_STATUSES,
    NOT_EVALUATED,
    STRUCTURE_INVALID,
    STRUCTURE_VALID,
    AdjudicationValidationResult,
    AnnotationBatch,
    AnnotationSubmission,
    GoldAdjudicationDecision,
    GoldSubmissionError,
    SubmissionValidationResult,
    derive_adjudication_id,
    derive_batch_id,
    derive_submission_id,
    validate_adjudications,
    validate_annotation_batches,
    validate_annotation_submissions,
)
from api.schemas import ContentVersion
from api.source_text_index import build_source_text_index


BENCH = "bm_gold_synthetic"
CV = "cv_gold_synthetic"
PACK = "ep_gold_synthetic"
TASK = "task-gold-synthetic"

BODY = "Suzhou is a craft. Suzhou produces more silk than Hangzhou."
FACT = "Suzhou is a craft."


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def build(body=BODY, *, version_id=CV, pack_id=PACK):
    claims = DeterministicClaimExtractor().extract(body)
    version = ContentVersion(
        content_version_id=version_id,
        content=body,
        task_id=TASK,
        evidence_pack_id=pack_id,
        claim_ids=[claim.claim_id for claim in claims],
    )
    return build_source_text_index(version, claims), claims


def span(body, needle, occurrence=0):
    start = -1
    for _ in range(occurrence + 1):
        start = body.index(needle, start + 1)
    return start, start + len(needle)


def annotation(
    body=BODY,
    needle=FACT,
    *,
    group="grp_f1",
    annotator="ann_A",
    subject="",
    polarity="POSITIVE",
    kind="OTHER",
    language="en",
    occurrence=0,
    status="INDEPENDENT_ANNOTATED",
    adjudicator="",
    benchmark=BENCH,
    version_id=CV,
    pack_id=PACK,
    proposition=None,
):
    start, end = span(body, needle, occurrence)
    return AtomicFactAnnotation(
        benchmark_id=benchmark,
        content_version_id=version_id,
        content_sha256=sha256(body.encode("utf-8")).hexdigest(),
        evidence_pack_id=pack_id,
        fact_group_id=group,
        start=start,
        end=end,
        source_quote=body[start:end],
        proposition=proposition or needle,
        subject_ref=subject,
        polarity=polarity,
        fact_kind=kind,
        language=language,
        requires_context=False,
        review_status=status,
        annotator_id=annotator,
        adjudicator_id=adjudicator,
    )


def batch(
    *,
    annotator="ann_A",
    round_id="r1",
    batch_nonce="bn1",
    submission_ids=(),
    declared_complete=False,
    benchmark=BENCH,
    version_id=CV,
    pack_id=PACK,
    body=BODY,
):
    return AnnotationBatch(
        benchmark_id=benchmark,
        content_version_id=version_id,
        content_sha256=sha256(body.encode("utf-8")).hexdigest(),
        evidence_pack_id=pack_id,
        annotator_id=annotator,
        round_id=round_id,
        batch_nonce=batch_nonce,
        submission_ids=tuple(submission_ids),
        declared_complete=declared_complete,
    )


def submission(
    *,
    batch_id,
    annotator="ann_A",
    ann=None,
    round_id="r1",
    nonce="s1",
    submitted_at="2026-10-18T09:00:00Z",
):
    return AnnotationSubmission(
        batch_id=batch_id,
        round_id=round_id,
        annotator_id=annotator,
        annotation=ann if ann is not None else annotation(annotator=annotator),
        submission_nonce=nonce,
        submitted_at=submitted_at,
    )


def pair(
    body=BODY,
    needle=FACT,
    *,
    group_a="grp_f1",
    group_b="grp_f1",
    annotator_a="ann_A",
    annotator_b="ann_B",
    subject_a="",
    subject_b="",
    polarity_a="POSITIVE",
    polarity_b="POSITIVE",
    occurrence=0,
    batch_nonce_a="bn1",
    batch_nonce_b="bn2",
    declared_complete=(False, False),
):
    """Build two independent batches (one submission each) over one document."""
    stub_a = batch(
        annotator=annotator_a, batch_nonce=batch_nonce_a, body=body
    )
    stub_b = batch(
        annotator=annotator_b, batch_nonce=batch_nonce_b, body=body
    )

    sub_a = submission(
        batch_id=stub_a.batch_id,
        annotator=annotator_a,
        ann=annotation(
            body,
            needle,
            group=group_a,
            annotator=annotator_a,
            subject=subject_a,
            polarity=polarity_a,
            occurrence=occurrence,
        ),
        nonce="sa",
    )
    sub_b = submission(
        batch_id=stub_b.batch_id,
        annotator=annotator_b,
        ann=annotation(
            body,
            needle,
            group=group_b,
            annotator=annotator_b,
            subject=subject_b,
            polarity=polarity_b,
            occurrence=occurrence,
        ),
        nonce="sb",
    )

    batch_a = batch(
        annotator=annotator_a,
        batch_nonce=batch_nonce_a,
        submission_ids=(sub_a.submission_id,),
        declared_complete=declared_complete[0],
        body=body,
    )
    batch_b = batch(
        annotator=annotator_b,
        batch_nonce=batch_nonce_b,
        submission_ids=(sub_b.submission_id,),
        declared_complete=declared_complete[1],
        body=body,
    )

    return batch_a, batch_b, sub_a, sub_b


def decision(
    *,
    batches,
    members,
    adjudicator="adj_X",
    canonical="grp_canonical",
    resolved_subject="",
    resolved_polarity="",
    omission=(),
    status="CONFIRMED",
    benchmark=BENCH,
    version_id=CV,
    pack_id=PACK,
    body=BODY,
    proposition="Suzhou is a craft (adjudicated).",
    rationale="Synthetic adjudication rationale.",
):
    return GoldAdjudicationDecision(
        benchmark_id=benchmark,
        content_version_id=version_id,
        content_sha256=sha256(body.encode("utf-8")).hexdigest(),
        evidence_pack_id=pack_id,
        canonical_fact_group_id=canonical,
        resolved_proposition=proposition,
        source_batch_ids=tuple(b.batch_id for b in batches),
        member_submission_ids=tuple(s.submission_id for s in members),
        adjudicator_id=adjudicator,
        rationale=rationale,
        resolved_subject_ref=resolved_subject,
        resolved_polarity=resolved_polarity,
        omission_batch_ids=tuple(b.batch_id for b in omission),
        decision_status=status,
        adjudicated_at="2026-10-18T12:00:00Z",
    )


# --------------------------------------------------------------------------- #
# 1. two annotators, same occurrence, same fact group
# --------------------------------------------------------------------------- #
def test_01_two_annotators_same_occurrence_coexist():
    index, _ = build()
    ba, bb, sa, sb = pair()

    assert sa.submission_id != sb.submission_id
    assert sa.fact_occurrence_id == sb.fact_occurrence_id

    result = validate_annotation_batches(index, BODY, [ba, bb], [sa, sb])

    assert result.status == STRUCTURE_VALID
    assert result.errors == ()
    assert result.submission_count == 2
    assert result.batch_count == 2
    assert result.annotator_count == 2
    assert result.shared_occurrence_ids == (sa.fact_occurrence_id,)


# --------------------------------------------------------------------------- #
# 2. the old validator must not receive a flat two-annotator list
# --------------------------------------------------------------------------- #
def test_02_flat_list_still_collides_in_old_contract():
    index, _ = build()
    _, _, sa, sb = pair()

    flat = validate_atomic_annotations(
        index, BODY, [sa.annotation, sb.annotation]
    )

    assert flat.status == STRUCTURE_INVALID
    assert any(
        "duplicate fact_occurrence_id" in error for error in flat.errors
    )

    # The new layer validates each submission separately and succeeds.
    layered = validate_annotation_submissions(index, BODY, [sa, sb])
    assert layered.status == STRUCTURE_VALID


# --------------------------------------------------------------------------- #
# 3. different fact group ids require an explicit canonical mapping
# --------------------------------------------------------------------------- #
def test_03_different_group_ids_need_explicit_canonical():
    index, _ = build()
    ba, bb, sa, sb = pair(group_a="grp_literal", group_b="grp_paraphrase")

    assert sa.annotation.fact_group_id == "grp_literal"
    assert sb.annotation.fact_group_id == "grp_paraphrase"

    d = decision(batches=[ba, bb], members=[sa, sb], canonical="grp_canonical")
    result = validate_adjudications(
        index, BODY, [ba, bb], [sa, sb], [d]
    )

    assert result.status == STRUCTURE_VALID
    assert result.adjudicated_fact_group_ids == ("grp_canonical",)

    # Original submissions are never rewritten by adjudication.
    assert sa.annotation.fact_group_id == "grp_literal"
    assert sb.annotation.fact_group_id == "grp_paraphrase"

    with pytest.raises(GoldSubmissionError):
        GoldAdjudicationDecision(
            benchmark_id=BENCH,
            content_version_id=CV,
            content_sha256=sha256(BODY.encode("utf-8")).hexdigest(),
            evidence_pack_id=PACK,
            canonical_fact_group_id="",
            resolved_proposition="x",
            source_batch_ids=(ba.batch_id, bb.batch_id),
            member_submission_ids=(sa.submission_id, sb.submission_id),
            adjudicator_id="adj_X",
            rationale="x",
        )


# --------------------------------------------------------------------------- #
# 4. duplicate submission ids
# --------------------------------------------------------------------------- #
def test_04_duplicate_submission_id_rejected():
    index, _ = build()
    _, _, sa, _ = pair()

    result = validate_annotation_submissions(index, BODY, [sa, sa])

    assert result.status == STRUCTURE_INVALID
    assert any(
        "duplicate submission_id" in error for error in result.errors
    )


def test_05_forged_submission_id_rejected():
    _, _, sa, _ = pair()

    with pytest.raises(GoldSubmissionError):
        AnnotationSubmission(
            batch_id=sa.batch_id,
            round_id=sa.round_id,
            annotator_id=sa.annotator_id,
            annotation=sa.annotation,
            submission_nonce=sa.submission_nonce,
            submission_id="sub_forged",
        )


# --------------------------------------------------------------------------- #
# 5. re-submission keeps a distinct event identity
# --------------------------------------------------------------------------- #
def test_06_resubmission_with_new_nonce_keeps_distinct_identity():
    index, _ = build()

    first_batch = batch(annotator="ann_A", batch_nonce="bn1")
    first = submission(
        batch_id=first_batch.batch_id,
        annotator="ann_A",
        ann=annotation(annotator="ann_A"),
        nonce="s1",
    )
    first_batch = batch(
        annotator="ann_A",
        batch_nonce="bn1",
        submission_ids=(first.submission_id,),
    )

    second_batch = batch(annotator="ann_A", batch_nonce="bn2")
    second = submission(
        batch_id=second_batch.batch_id,
        annotator="ann_A",
        ann=annotation(annotator="ann_A"),
        nonce="s2",
    )
    second_batch = batch(
        annotator="ann_A",
        batch_nonce="bn2",
        submission_ids=(second.submission_id,),
    )

    assert first.submission_id != second.submission_id
    assert first.fact_occurrence_id == second.fact_occurrence_id

    result = validate_annotation_batches(
        index, BODY, [first_batch, second_batch], [first, second]
    )

    assert result.status == STRUCTURE_VALID
    assert result.annotator_count == 1


# --------------------------------------------------------------------------- #
# 6. one annotator cannot impersonate two
# --------------------------------------------------------------------------- #
def test_07_two_batches_by_one_annotator_are_not_independence():
    index, _ = build()

    b1 = batch(annotator="ann_A", batch_nonce="bn1")
    s1 = submission(
        batch_id=b1.batch_id,
        annotator="ann_A",
        ann=annotation(annotator="ann_A"),
        nonce="s1",
    )
    b1 = batch(
        annotator="ann_A",
        batch_nonce="bn1",
        submission_ids=(s1.submission_id,),
    )

    b2 = batch(annotator="ann_A", batch_nonce="bn2")
    s2 = submission(
        batch_id=b2.batch_id,
        annotator="ann_A",
        ann=annotation(annotator="ann_A"),
        nonce="s2",
    )
    b2 = batch(
        annotator="ann_A",
        batch_nonce="bn2",
        submission_ids=(s2.submission_id,),
    )

    d = decision(
        batches=[b1, b2],
        members=[s1, s2],
        omission=[b2],
    )

    result = validate_adjudications(
        index, BODY, [b1, b2], [s1, s2], [d]
    )

    assert result.status == STRUCTURE_INVALID
    assert any(
        "at least two distinct annotators" in error
        for error in result.errors
    )


# --------------------------------------------------------------------------- #
# 7. one-sided omission is legal and must be traced
# --------------------------------------------------------------------------- #
def test_08_one_sided_omission_allowed_and_traced():
    index, _ = build()

    # R2 fixture correction: B must be a genuinely silent batch. Under R1 this
    # test used ``pair()``, whose B batch really did submit the same fact, so
    # the "omission" label was factually false and the case was a false
    # positive. B now submits nothing and declares its review complete.
    ba, _, sa, _ = pair()
    silent_b = batch(
        annotator="ann_B",
        batch_nonce="bn2",
        submission_ids=(),
        declared_complete=True,
    )

    only_a = decision(
        batches=[ba, silent_b],
        members=[sa],
        omission=[silent_b],
        resolved_subject="suzhou",
    )

    result = validate_adjudications(
        index, BODY, [ba, silent_b], [sa], [only_a]
    )

    assert result.status == STRUCTURE_VALID
    assert result.omission_traced_decision_ids == (
        only_a.adjudication_id,
    )

    untraced = decision(
        batches=[ba, silent_b],
        members=[sa],
        resolved_subject="suzhou",
    )

    missing = validate_adjudications(
        index, BODY, [ba, silent_b], [sa], [untraced]
    )

    assert missing.status == STRUCTURE_INVALID
    assert any(
        "omission_batch_ids" in error for error in missing.errors
    )


def test_09_zero_fact_batch_is_structurally_legal():
    index, _ = build()
    ba, _, sa, _ = pair()

    empty_batch = batch(
        annotator="ann_C",
        batch_nonce="bn3",
        submission_ids=(),
        declared_complete=True,
    )

    result = validate_annotation_batches(
        index, BODY, [ba, empty_batch], [sa]
    )

    assert result.status == STRUCTURE_VALID
    assert result.zero_fact_batch_ids == (empty_batch.batch_id,)
    assert result.declared_complete_batch_ids == (empty_batch.batch_id,)
    assert result.completeness_status == COMPLETENESS_NOT_VERIFIED
    assert result.claim_recall_status == NOT_EVALUATED


# --------------------------------------------------------------------------- #
# 8. adjudicator independence
# --------------------------------------------------------------------------- #
def test_10_adjudicator_must_differ_from_annotators():
    index, _ = build()
    ba, bb, sa, sb = pair()

    d = decision(
        batches=[ba, bb],
        members=[sa, sb],
        adjudicator="ann_A",
        resolved_subject="suzhou",
    )

    result = validate_adjudications(
        index, BODY, [ba, bb], [sa, sb], [d]
    )

    assert result.status == STRUCTURE_INVALID
    assert any(
        "adjudicator must differ" in error for error in result.errors
    )


# --------------------------------------------------------------------------- #
# 9. missing provenance references
# --------------------------------------------------------------------------- #
def test_11_missing_member_submission_rejected():
    index, _ = build()
    ba, bb, sa, sb = pair()

    d = decision(batches=[ba, bb], members=[sa, sb])
    # Rewrite the decision with a bogus member id through reconstruction.
    broken = GoldAdjudicationDecision(
        benchmark_id=d.benchmark_id,
        content_version_id=d.content_version_id,
        content_sha256=d.content_sha256,
        evidence_pack_id=d.evidence_pack_id,
        canonical_fact_group_id=d.canonical_fact_group_id,
        resolved_proposition=d.resolved_proposition,
        source_batch_ids=d.source_batch_ids,
        member_submission_ids=("sub_missing",),
        adjudicator_id=d.adjudicator_id,
        rationale=d.rationale,
        resolved_subject_ref="suzhou",
        decision_status="CONFIRMED",
    )

    result = validate_adjudications(
        index, BODY, [ba, bb], [sa, sb], [broken]
    )

    assert result.status == STRUCTURE_INVALID
    assert any(
        "unknown member submission" in error for error in result.errors
    )


def test_12_missing_source_batch_rejected():
    index, _ = build()
    ba, bb, sa, sb = pair()

    d = GoldAdjudicationDecision(
        benchmark_id=BENCH,
        content_version_id=CV,
        content_sha256=sha256(BODY.encode("utf-8")).hexdigest(),
        evidence_pack_id=PACK,
        canonical_fact_group_id="grp_canonical",
        resolved_proposition="x",
        source_batch_ids=("bat_missing", bb.batch_id),
        member_submission_ids=(sa.submission_id, sb.submission_id),
        adjudicator_id="adj_X",
        rationale="x",
    )

    result = validate_adjudications(
        index, BODY, [ba, bb], [sa, sb], [d]
    )

    assert result.status == STRUCTURE_INVALID
    assert any("unknown source batch" in error for error in result.errors)


def test_13_single_source_batch_rejected():
    index, _ = build()
    ba, _, sa, _ = pair()

    d = GoldAdjudicationDecision(
        benchmark_id=BENCH,
        content_version_id=CV,
        content_sha256=sha256(BODY.encode("utf-8")).hexdigest(),
        evidence_pack_id=PACK,
        canonical_fact_group_id="grp_canonical",
        resolved_proposition="x",
        source_batch_ids=(ba.batch_id,),
        member_submission_ids=(sa.submission_id,),
        adjudicator_id="adj_X",
        rationale="x",
    )

    result = validate_adjudications(index, BODY, [ba], [sa], [d])

    assert result.status == STRUCTURE_INVALID
    assert any(
        "at least two source batches" in error for error in result.errors
    )


# --------------------------------------------------------------------------- #
# 10. cross-boundary references
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "field_name, bad_value, expected",
    [
        ("version_id", "cv_other", "content_version_id"),
        ("pack_id", "ep_other", "evidence_pack_id"),
        ("benchmark", "bm_other", "benchmark_id"),
    ],
)
def test_14_cross_boundary_reference_rejected(
    field_name, bad_value, expected
):
    index, _ = build()
    ba, bb, sa, sb = pair()

    overrides = {field_name: bad_value}
    d = decision(
        batches=[ba, bb],
        members=[sa, sb],
        resolved_subject="suzhou",
        **overrides,
    )

    result = validate_adjudications(
        index, BODY, [ba, bb], [sa, sb], [d]
    )

    assert result.status == STRUCTURE_INVALID
    assert any(expected in error for error in result.errors)


def test_15_wrong_digest_reference_rejected():
    index, _ = build()
    ba, bb, sa, sb = pair()

    d = GoldAdjudicationDecision(
        benchmark_id=BENCH,
        content_version_id=CV,
        content_sha256="0" * 64,
        evidence_pack_id=PACK,
        canonical_fact_group_id="grp_canonical",
        resolved_proposition="x",
        source_batch_ids=(ba.batch_id, bb.batch_id),
        member_submission_ids=(sa.submission_id, sb.submission_id),
        adjudicator_id="adj_X",
        rationale="x",
        resolved_subject_ref="suzhou",
        decision_status="CONFIRMED",
    )

    result = validate_adjudications(
        index, BODY, [ba, bb], [sa, sb], [d]
    )

    assert result.status == STRUCTURE_INVALID
    assert any("content_sha256" in error for error in result.errors)


# --------------------------------------------------------------------------- #
# 11. same span, different fact groups must not merge
# --------------------------------------------------------------------------- #
def test_16_same_span_different_groups_not_merged():
    index, _ = build()
    ba, bb, sa, sb = pair(group_a="grp_silk", group_b="grp_craft")

    assert sa.annotation.start == sb.annotation.start
    assert sa.annotation.end == sb.annotation.end
    assert sa.fact_occurrence_id != sb.fact_occurrence_id

    d = decision(
        batches=[ba, bb],
        members=[sa, sb],
        canonical="grp_declared_canonical",
        resolved_subject="suzhou",
    )

    result = validate_adjudications(
        index, BODY, [ba, bb], [sa, sb], [d]
    )

    assert result.status == STRUCTURE_VALID
    assert result.adjudicated_fact_group_ids == ("grp_declared_canonical",)
    assert sa.annotation.fact_group_id == "grp_silk"
    assert sb.annotation.fact_group_id == "grp_craft"


# --------------------------------------------------------------------------- #
# 12. unresolved polarity / subject conflicts
# --------------------------------------------------------------------------- #
def test_17_unresolved_polarity_conflict_rejected():
    index, _ = build()
    ba, bb, sa, sb = pair(
        group_a="grp_a", group_b="grp_b", polarity_b="NEGATIVE"
    )

    d = decision(batches=[ba, bb], members=[sa, sb])

    result = validate_adjudications(
        index, BODY, [ba, bb], [sa, sb], [d]
    )

    assert result.status == STRUCTURE_INVALID
    assert any(
        "unresolved polarity conflict" in error for error in result.errors
    )


def test_18_resolved_polarity_accepted():
    index, _ = build()
    ba, bb, sa, sb = pair(
        group_a="grp_a", group_b="grp_b", polarity_b="NEGATIVE"
    )

    d = decision(
        batches=[ba, bb],
        members=[sa, sb],
        resolved_polarity="NEGATIVE",
    )

    result = validate_adjudications(
        index, BODY, [ba, bb], [sa, sb], [d]
    )

    assert result.status == STRUCTURE_VALID
    assert d.resolved_polarity == "NEGATIVE"


def test_19_unresolved_subject_conflict_rejected():
    index, _ = build()
    ba, bb, sa, sb = pair(
        group_a="grp_a",
        group_b="grp_b",
        subject_a="suzhou",
        subject_b="hangzhou",
    )

    unresolved = decision(batches=[ba, bb], members=[sa, sb])

    result = validate_adjudications(
        index, BODY, [ba, bb], [sa, sb], [unresolved]
    )

    assert result.status == STRUCTURE_INVALID
    assert any(
        "resolved_subject_ref" in error for error in result.errors
    )

    resolved = decision(
        batches=[ba, bb],
        members=[sa, sb],
        resolved_subject="suzhou",
    )

    ok = validate_adjudications(
        index, BODY, [ba, bb], [sa, sb], [resolved]
    )

    assert ok.status == STRUCTURE_VALID

    # Original annotator values are preserved, never overwritten.
    assert sa.annotation.subject_ref == "suzhou"
    assert sb.annotation.subject_ref == "hangzhou"


# --------------------------------------------------------------------------- #
# 13. stale document state
# --------------------------------------------------------------------------- #
def test_20_stale_adjudication_rejected_after_text_change():
    new_body = BODY + " A new sentence was appended."
    new_index, _ = build(new_body)

    ba, bb, sa, sb = pair()
    d = decision(batches=[ba, bb], members=[sa, sb], resolved_subject="suzhou")

    result = validate_adjudications(
        new_index, new_body, [ba, bb], [sa, sb], [d]
    )

    assert result.status == STRUCTURE_INVALID
    assert any("does not match index" in e for e in result.errors)

    # The occurrence identity of the old decision no longer exists in the
    # new document state.
    assert d.content_sha256 != new_index.content_sha256


# --------------------------------------------------------------------------- #
# 14. gold completeness / recall safety
# --------------------------------------------------------------------------- #
def test_21_single_adjudicated_fact_is_not_complete_gold():
    index, _ = build()
    ba, bb, sa, sb = pair()

    d = decision(batches=[ba, bb], members=[sa, sb], resolved_subject="suzhou")

    result = validate_adjudications(
        index, BODY, [ba, bb], [sa, sb], [d]
    )

    assert isinstance(result, AdjudicationValidationResult)
    assert result.status == STRUCTURE_VALID
    assert result.confirmed_decision_count == 1
    assert result.gold_completeness_status == COMPLETENESS_NOT_VERIFIED
    assert result.claim_recall_status == NOT_EVALUATED
    assert result.evidence_support_status == NOT_EVALUATED
    assert result.identity_verified is False

    # No numeric recall surface exists anywhere in the contract.
    assert "recall" not in {
        field.name for field in fields(GoldAdjudicationDecision)
    }
    assert "recall" not in {
        field.name for field in fields(AdjudicationValidationResult)
    }
    assert not hasattr(result, "recall")


def test_22_identity_verified_true_is_not_constructible():
    with pytest.raises(GoldSubmissionError):
        GoldAdjudicationDecision(
            benchmark_id=BENCH,
            content_version_id=CV,
            content_sha256=sha256(BODY.encode("utf-8")).hexdigest(),
            evidence_pack_id=PACK,
            canonical_fact_group_id="grp_canonical",
            resolved_proposition="x",
            source_batch_ids=("bat_a", "bat_b"),
            member_submission_ids=("sub_a",),
            adjudicator_id="adj_X",
            rationale="x",
            identity_verified=True,
        )


@pytest.mark.parametrize(
    "privileged_status", ["PASS", "APPROVED", "SUPPORTED", "ACCEPTED"]
)
def test_23_privileged_statuses_rejected(privileged_status):
    assert privileged_status not in DECISION_STATUSES

    with pytest.raises(GoldSubmissionError):
        GoldAdjudicationDecision(
            benchmark_id=BENCH,
            content_version_id=CV,
            content_sha256=sha256(BODY.encode("utf-8")).hexdigest(),
            evidence_pack_id=PACK,
            canonical_fact_group_id="grp_canonical",
            resolved_proposition="x",
            source_batch_ids=("bat_a", "bat_b"),
            member_submission_ids=("sub_a",),
            adjudicator_id="adj_X",
            rationale="x",
            decision_status=privileged_status,
        )


# --------------------------------------------------------------------------- #
# 15. submission-level structural rejections
# --------------------------------------------------------------------------- #
def test_24_submission_cannot_claim_adjudicated_state():
    ann = annotation(status="ADJUDICATED", adjudicator="adj_X")

    with pytest.raises(GoldSubmissionError):
        AnnotationSubmission(
            batch_id="bat_x",
            round_id="r1",
            annotator_id="ann_A",
            annotation=ann,
            submission_nonce="s1",
        )


def test_25_submission_annotator_must_match_annotation():
    ann = annotation(annotator="ann_B")

    with pytest.raises(GoldSubmissionError):
        AnnotationSubmission(
            batch_id="bat_x",
            round_id="r1",
            annotator_id="ann_A",
            annotation=ann,
            submission_nonce="s1",
        )


def test_26_batch_cannot_list_duplicate_submission_ids():
    with pytest.raises(GoldSubmissionError):
        AnnotationBatch(
            benchmark_id=BENCH,
            content_version_id=CV,
            content_sha256=sha256(BODY.encode("utf-8")).hexdigest(),
            evidence_pack_id=PACK,
            annotator_id="ann_A",
            round_id="r1",
            batch_nonce="bn1",
            submission_ids=("sub_a", "sub_a"),
        )


def test_27_forged_batch_id_rejected():
    with pytest.raises(GoldSubmissionError):
        AnnotationBatch(
            benchmark_id=BENCH,
            content_version_id=CV,
            content_sha256=sha256(BODY.encode("utf-8")).hexdigest(),
            evidence_pack_id=PACK,
            annotator_id="ann_A",
            round_id="r1",
            batch_nonce="bn1",
            submission_ids=(),
            batch_id="bat_forged",
        )


# --------------------------------------------------------------------------- #
# 16. batch membership integrity
# --------------------------------------------------------------------------- #
def test_28_duplicate_occurrence_inside_one_batch_rejected():
    index, _ = build()
    owner = batch(annotator="ann_A", batch_nonce="bn1")

    first = submission(
        batch_id=owner.batch_id,
        annotator="ann_A",
        ann=annotation(annotator="ann_A"),
        nonce="s1",
    )
    second = submission(
        batch_id=owner.batch_id,
        annotator="ann_A",
        ann=annotation(annotator="ann_A"),
        nonce="s2",
    )

    owner = batch(
        annotator="ann_A",
        batch_nonce="bn1",
        submission_ids=(first.submission_id, second.submission_id),
    )

    result = validate_annotation_batches(
        index, BODY, [owner], [first, second]
    )

    assert result.status == STRUCTURE_INVALID
    assert any(
        "duplicate fact_occurrence_id" in error for error in result.errors
    )
    assert any("new round or batch" in error for error in result.errors)


def test_29_batch_must_list_its_member_submission():
    index, _ = build()
    empty = batch(annotator="ann_A", batch_nonce="bn1", submission_ids=())
    s = submission(batch_id=empty.batch_id, annotator="ann_A")

    result = validate_annotation_batches(index, BODY, [empty], [s])

    assert result.status == STRUCTURE_INVALID
    assert any(
        "does not list its member submission" in error
        for error in result.errors
    )


def test_30_unknown_batch_reference_rejected():
    index, _ = build()
    orphan = submission(batch_id="bat_unknown", annotator="ann_A")

    result = validate_annotation_batches(index, BODY, [], [orphan])

    assert result.status == STRUCTURE_INVALID
    assert any(
        "references unknown batch" in error for error in result.errors
    )


def test_31_conflicting_payload_under_one_submission_identity():
    index, _ = build()
    owner = batch(annotator="ann_A", batch_nonce="bn1")

    first = submission(
        batch_id=owner.batch_id,
        annotator="ann_A",
        ann=annotation(annotator="ann_A"),
        nonce="s1",
    )
    # Same event identity, different payload (a different span).
    second = submission(
        batch_id=owner.batch_id,
        annotator="ann_A",
        ann=annotation(annotator="ann_A", needle="Suzhou produces more silk "
                                              "than Hangzhou."),
        nonce="s1",
    )

    assert first.submission_id == second.submission_id

    result = validate_annotation_submissions(index, BODY, [first, second])

    assert result.status == STRUCTURE_INVALID
    assert any(
        "conflicting payload" in error for error in result.errors
    )


# --------------------------------------------------------------------------- #
# 17. determinism and purity
# --------------------------------------------------------------------------- #
def test_32_validation_is_deterministic_and_side_effect_free():
    index, _ = build()
    ba, bb, sa, sb = pair()
    d = decision(batches=[ba, bb], members=[sa, sb], resolved_subject="suzhou")

    first = validate_adjudications(
        index, BODY, [ba, bb], [sa, sb], [d]
    )
    second = validate_adjudications(
        index, BODY, [ba, bb], [sa, sb], [d]
    )

    assert first == second

    submission_first = validate_annotation_batches(
        index, BODY, [ba, bb], [sa, sb]
    )
    submission_second = validate_annotation_batches(
        index, BODY, [ba, bb], [sa, sb]
    )

    assert submission_first == submission_second
    assert isinstance(submission_first, SubmissionValidationResult)

    # Frozen inputs are unchanged by validation.
    assert ba.submission_ids == (sa.submission_id,)
    assert bb.submission_ids == (sb.submission_id,)
    assert sa.annotation.start == span(BODY, FACT)[0]


# --------------------------------------------------------------------------- #
# 18. identity helpers are stable and namespaced
# --------------------------------------------------------------------------- #
def test_33_identity_prefixes_are_namespaced_and_stable():
    _, _, sa, sb = pair()

    assert sa.submission_id.startswith("sub_")
    assert sa.annotation.fact_occurrence_id.startswith("focc_")

    assert sa.submission_id == derive_submission_id(
        "ann_A", sa.batch_id, "r1", "sa"
    )
    assert sa.batch_id == derive_batch_id(
        BENCH,
        CV,
        sha256(BODY.encode("utf-8")).hexdigest(),
        PACK,
        "ann_A",
        "r1",
        "bn1",
    )

    d = decision(batches=[pair()[0]], members=[sa])
    assert d.adjudication_id.startswith("adj_")
    assert d.adjudication_id == derive_adjudication_id(
        BENCH,
        CV,
        sha256(BODY.encode("utf-8")).hexdigest(),
        PACK,
        "grp_canonical",
    )

    # Two annotators on one occurrence never share a submission identity.
    assert sa.submission_id != sb.submission_id


# --------------------------------------------------------------------------- #
# 19. R2-01: a CONFIRMED decision may only use finished, accepted records
# --------------------------------------------------------------------------- #
def test_34_confirmed_decision_rejects_draft_member():
    index, _ = build()
    ba, bb, _, sb = pair()

    draft = submission(
        batch_id=ba.batch_id,
        annotator="ann_A",
        ann=annotation(annotator="ann_A", status="DRAFT"),
        nonce="sa",
    )
    ba = batch(
        annotator="ann_A",
        batch_nonce="bn1",
        submission_ids=(draft.submission_id,),
    )

    d = decision(
        batches=[ba, bb],
        members=[draft, sb],
        resolved_subject="suzhou",
        status="CONFIRMED",
    )

    result = validate_adjudications(index, BODY, [ba, bb], [draft, sb], [d])

    assert result.status == STRUCTURE_INVALID
    assert any(
        draft.submission_id in error and "review_status" in error
        for error in result.errors
    )
    assert any(
        "INDEPENDENT_ANNOTATED" in error for error in result.errors
    )
    # The unfinished record never becomes confirmed gold.
    assert d.decision_status == "CONFIRMED"
    assert any(
        "CONFIRMED" in error for error in result.errors
    )


def test_35_confirmed_decision_rejects_rejected_member():
    index, _ = build()
    ba, bb, _, sb = pair()

    rejected = submission(
        batch_id=ba.batch_id,
        annotator="ann_A",
        ann=annotation(annotator="ann_A", status="REJECTED"),
        nonce="sa",
    )
    ba = batch(
        annotator="ann_A",
        batch_nonce="bn1",
        submission_ids=(rejected.submission_id,),
    )

    d = decision(
        batches=[ba, bb],
        members=[rejected, sb],
        resolved_subject="suzhou",
        status="CONFIRMED",
    )

    result = validate_adjudications(
        index, BODY, [ba, bb], [rejected, sb], [d]
    )

    assert result.status == STRUCTURE_INVALID
    assert any(
        rejected.submission_id in error for error in result.errors
    )
    assert any("'REJECTED'" in error for error in result.errors)


def test_36_needs_more_review_may_keep_unfinished_member():
    index, _ = build()
    ba, bb, _, sb = pair()

    draft = submission(
        batch_id=ba.batch_id,
        annotator="ann_A",
        ann=annotation(annotator="ann_A", status="DRAFT"),
        nonce="sa",
    )
    ba = batch(
        annotator="ann_A",
        batch_nonce="bn1",
        submission_ids=(draft.submission_id,),
    )

    d = decision(
        batches=[ba, bb],
        members=[draft, sb],
        resolved_subject="suzhou",
        status="NEEDS_MORE_REVIEW",
    )

    result = validate_adjudications(index, BODY, [ba, bb], [draft, sb], [d])

    # Keeping an unfinished record is legal, but it confirms nothing.
    assert result.status == STRUCTURE_VALID
    assert result.confirmed_decision_count == 0
    assert result.unresolved_decision_count == 1
    assert result.gold_completeness_status == COMPLETENESS_NOT_VERIFIED
    assert result.claim_recall_status == NOT_EVALUATED


# --------------------------------------------------------------------------- #
# 20. R2-02: a batch that did submit the fact cannot be called silent
# --------------------------------------------------------------------------- #
def test_37_false_omission_rejected_when_batch_did_submit():
    index, _ = build()
    ba, bb, sa, sb = pair()

    # B really did submit the same occurrence, so labelling B as an omission
    # batch is a false provenance claim.
    assert sb.fact_occurrence_id == sa.fact_occurrence_id

    d = decision(
        batches=[ba, bb],
        members=[sa],
        omission=[bb],
        resolved_subject="suzhou",
    )

    result = validate_adjudications(
        index, BODY, [ba, bb], [sa, sb], [d]
    )

    assert result.status == STRUCTURE_INVALID
    assert any(
        sb.submission_id in error and bb.batch_id in error
        for error in result.errors
    )
    assert any(
        "same fact occurrence" in error for error in result.errors
    )


def test_38_genuine_one_sided_discovery_stays_valid():
    index, _ = build()
    ba, _, sa, _ = pair()

    silent_b = batch(
        annotator="ann_B",
        batch_nonce="bn2",
        submission_ids=(),
        declared_complete=True,
    )

    d = decision(
        batches=[ba, silent_b],
        members=[sa],
        omission=[silent_b],
        resolved_subject="suzhou",
    )

    result = validate_adjudications(
        index, BODY, [ba, silent_b], [sa], [d]
    )

    assert result.status == STRUCTURE_VALID
    assert result.omission_traced_decision_ids == (d.adjudication_id,)
    # declared_complete is only the annotator's own statement.
    assert result.gold_completeness_status == COMPLETENESS_NOT_VERIFIED
    assert result.claim_recall_status == NOT_EVALUATED


def test_39_omission_batch_must_declare_complete():
    index, _ = build()
    ba, _, sa, _ = pair()

    unfinished_b = batch(
        annotator="ann_B",
        batch_nonce="bn2",
        submission_ids=(),
        declared_complete=False,
    )

    d = decision(
        batches=[ba, unfinished_b],
        members=[sa],
        omission=[unfinished_b],
        resolved_subject="suzhou",
    )

    result = validate_adjudications(
        index, BODY, [ba, unfinished_b], [sa], [d]
    )

    assert result.status == STRUCTURE_INVALID
    assert any(
        "declared_complete" in error for error in result.errors
    )


def test_40_duplicate_omission_batch_ids_rejected():
    ba, bb, sa, _ = pair()

    with pytest.raises(GoldSubmissionError):
        decision(
            batches=[ba, bb],
            members=[sa],
            omission=[bb, bb],
            resolved_subject="suzhou",
        )


# --------------------------------------------------------------------------- #
# 21. R2-03: one observation cannot back two gold groups
# --------------------------------------------------------------------------- #
def test_41_same_submission_cannot_confirm_two_gold_groups():
    index, _ = build()
    ba, bb, sa, sb = pair()

    first = decision(
        batches=[ba, bb],
        members=[sa, sb],
        canonical="grp_G1",
        resolved_subject="suzhou",
    )
    second = decision(
        batches=[ba, bb],
        members=[sa, sb],
        canonical="grp_G2",
        resolved_subject="suzhou",
    )

    result = validate_adjudications(
        index, BODY, [ba, bb], [sa, sb], [first, second]
    )

    assert result.status == STRUCTURE_INVALID
    assert any(
        sa.submission_id in error and "already supports" in error
        for error in result.errors
    )


def test_42_same_occurrence_cannot_confirm_two_gold_groups():
    index, _ = build()

    ba1, bb1, sa1, sb1 = pair(batch_nonce_a="bn1", batch_nonce_b="bn2")
    ba2, bb2, sa2, sb2 = pair(batch_nonce_a="bn3", batch_nonce_b="bn4")

    # Distinct submission events over the identical fact occurrence.
    assert sa1.submission_id != sa2.submission_id
    assert sa1.fact_occurrence_id == sa2.fact_occurrence_id

    first = decision(
        batches=[ba1, bb1],
        members=[sa1, sb1],
        canonical="grp_G1",
        resolved_subject="suzhou",
    )
    second = decision(
        batches=[ba2, bb2],
        members=[sa2, sb2],
        canonical="grp_G2",
        resolved_subject="suzhou",
    )

    result = validate_adjudications(
        index,
        BODY,
        [ba1, bb1, ba2, bb2],
        [sa1, sb1, sa2, sb2],
        [first, second],
    )

    assert result.status == STRUCTURE_INVALID
    assert any(
        sa1.fact_occurrence_id in error and "already confirmed" in error
        for error in result.errors
    )


def test_43_same_span_different_facts_still_confirmable():
    index, _ = build()

    stub_a = batch(annotator="ann_A", batch_nonce="bn1")
    stub_b = batch(annotator="ann_B", batch_nonce="bn2")

    a_silk = submission(
        batch_id=stub_a.batch_id,
        annotator="ann_A",
        ann=annotation(group="grp_silk", annotator="ann_A"),
        nonce="a_silk",
    )
    a_craft = submission(
        batch_id=stub_a.batch_id,
        annotator="ann_A",
        ann=annotation(group="grp_craft", annotator="ann_A"),
        nonce="a_craft",
    )
    b_silk = submission(
        batch_id=stub_b.batch_id,
        annotator="ann_B",
        ann=annotation(group="grp_silk", annotator="ann_B"),
        nonce="b_silk",
    )
    b_craft = submission(
        batch_id=stub_b.batch_id,
        annotator="ann_B",
        ann=annotation(group="grp_craft", annotator="ann_B"),
        nonce="b_craft",
    )

    ba = batch(
        annotator="ann_A",
        batch_nonce="bn1",
        submission_ids=(a_silk.submission_id, a_craft.submission_id),
    )
    bb = batch(
        annotator="ann_B",
        batch_nonce="bn2",
        submission_ids=(b_silk.submission_id, b_craft.submission_id),
    )

    # Same span, genuinely different atomic facts.
    assert a_silk.annotation.start == a_craft.annotation.start
    assert a_silk.fact_occurrence_id != a_craft.fact_occurrence_id

    silk = decision(
        batches=[ba, bb],
        members=[a_silk, b_silk],
        canonical="grp_gold_silk",
    )
    craft = decision(
        batches=[ba, bb],
        members=[a_craft, b_craft],
        canonical="grp_gold_craft",
    )

    result = validate_adjudications(
        index,
        BODY,
        [ba, bb],
        [a_silk, a_craft, b_silk, b_craft],
        [silk, craft],
    )

    assert result.status == STRUCTURE_VALID
    assert result.confirmed_decision_count == 2
    assert result.adjudicated_fact_group_ids == (
        "grp_gold_craft",
        "grp_gold_silk",
    )


# --------------------------------------------------------------------------- #
# 22. R2-04: batch identity and round consistency
# --------------------------------------------------------------------------- #
def test_44_duplicate_batch_id_rejected_even_when_identical():
    index, _ = build()
    owner = batch(annotator="ann_A", batch_nonce="bn1", submission_ids=())
    twin = batch(annotator="ann_A", batch_nonce="bn1", submission_ids=())

    assert owner == twin

    result = validate_annotation_batches(index, BODY, [owner, twin], [])

    assert result.status == STRUCTURE_INVALID
    assert any(
        "duplicate batch_id" in error for error in result.errors
    )


def test_45_same_batch_id_different_payload_rejected():
    index, _ = build()
    quiet = batch(
        annotator="ann_A",
        batch_nonce="bn1",
        submission_ids=(),
        declared_complete=False,
    )
    loud = batch(
        annotator="ann_A",
        batch_nonce="bn1",
        submission_ids=(),
        declared_complete=True,
    )

    assert quiet.batch_id == loud.batch_id

    result = validate_annotation_batches(index, BODY, [quiet, loud], [])

    assert result.status == STRUCTURE_INVALID
    assert any(
        "duplicate batch_id" in error for error in result.errors
    )
    assert any(
        "conflicting batch payload" in error for error in result.errors
    )


def test_46_submission_round_must_match_batch_round():
    index, _ = build()
    owner = batch(annotator="ann_A", batch_nonce="bn1", round_id="r1")

    drifted = submission(
        batch_id=owner.batch_id,
        annotator="ann_A",
        round_id="r2",
        nonce="sa",
    )
    owner = batch(
        annotator="ann_A",
        batch_nonce="bn1",
        round_id="r1",
        submission_ids=(drifted.submission_id,),
    )

    result = validate_annotation_batches(index, BODY, [owner], [drifted])

    assert result.status == STRUCTURE_INVALID
    assert any(
        "round_id" in error and "'r2'" in error for error in result.errors
    )


# --------------------------------------------------------------------------- #
# 23. R2-05: identity encoding must not be ambiguous
# --------------------------------------------------------------------------- #
def test_47_nul_injection_rejected_and_normal_hashes_stable():
    digest = sha256(BODY.encode("utf-8")).hexdigest()

    # Normal inputs keep the exact R1 hashes: the fix only rejects, it does
    # not re-serialise.
    assert derive_submission_id("ann_A", "bat_x", "r1", "s1") == (
        "sub_98eb9144adec79ee085781f7c9223c08f8e69115dc2794db1c46269f6f62f812"
    )
    assert derive_batch_id(
        BENCH, CV, digest, PACK, "ann_A", "r1", "bn1"
    ) == (
        "bat_490049e59295dff8e1da689aad623052bc4c97a14ad9a39c93273709091ba551"
    )
    assert derive_adjudication_id(
        BENCH, CV, digest, PACK, "grp_canonical"
    ) == (
        "adj_ff3363d31ed534a6ed0d992afcee3a82a0f128d3c1b9946ffe41596fe1205d8a"
    )

    # The two ambiguous tuples that used to collide now both fail closed.
    with pytest.raises(GoldSubmissionError):
        derive_submission_id("ann_A", "bat_x", "r1\x00s", "s1")
    with pytest.raises(GoldSubmissionError):
        derive_submission_id("ann_A", "bat_x", "r1", "s\x00s1")

    with pytest.raises(GoldSubmissionError):
        derive_batch_id(
            BENCH, CV, digest, PACK, "ann_A", "r1\x00x", "bn1"
        )

    with pytest.raises(GoldSubmissionError):
        derive_adjudication_id(BENCH, CV, digest, PACK, "grp\x00canonical")

    with pytest.raises(GoldSubmissionError):
        derive_submission_id("ann\x00A", "bat_x", "r1", "s1")


def test_48_nul_inside_annotation_identity_cannot_enter_submission_layer():
    ba, _, _, _ = pair()

    poisoned = annotation(group="grp_\x00f1", annotator="ann_A")

    with pytest.raises(GoldSubmissionError):
        AnnotationSubmission(
            batch_id=ba.batch_id,
            round_id="r1",
            annotator_id="ann_A",
            annotation=poisoned,
            submission_nonce="sa",
        )


# --------------------------------------------------------------------------- #
# 24. safety invariants hold on invalid graphs too
# --------------------------------------------------------------------------- #
def test_49_safety_invariants_hold_on_invalid_graph():
    index, _ = build()
    ba, bb, sa, sb = pair()

    broken = decision(
        batches=[ba, bb],
        members=[sa],
        omission=[bb],
        resolved_subject="suzhou",
    )
    invalid = validate_adjudications(
        index, BODY, [ba, bb], [sa, sb], [broken]
    )

    assert invalid.status == STRUCTURE_INVALID
    assert invalid.gold_completeness_status == COMPLETENESS_NOT_VERIFIED
    assert invalid.claim_recall_status == NOT_EVALUATED
    assert invalid.evidence_support_status == NOT_EVALUATED
    assert invalid.identity_verified is False
    assert not hasattr(invalid, "recall")
    assert "recall" not in {
        field.name for field in fields(AdjudicationValidationResult)
    }

    # A structurally valid graph carries the same ceilings.
    healthy = decision(
        batches=[ba, bb], members=[sa, sb], resolved_subject="suzhou"
    )
    valid = validate_adjudications(
        index, BODY, [ba, bb], [sa, sb], [healthy]
    )

    assert valid.status == STRUCTURE_VALID
    assert valid.confirmed_decision_count == 1
    assert valid.gold_completeness_status == COMPLETENESS_NOT_VERIFIED
    assert valid.claim_recall_status == NOT_EVALUATED
    assert valid.evidence_support_status == NOT_EVALUATED
    assert valid.identity_verified is False


# --------------------------------------------------------------------------- #
# 25. R3-01: empty submissions must not bypass source integrity
# --------------------------------------------------------------------------- #
# ``STALE`` keeps the byte length of ``BODY`` on purpose: it proves the
# document check is a digest check, not an incidental length check.
STALE = BODY.replace("silk", "wool")

#: Documents whose last segment was truncated: same length, same digest
#: field, but the segments no longer rebuild the source losslessly.
def broken_segments(index):
    last = index.segments[-1]
    return replace(
        index,
        segments=index.segments[:-1] + (replace(last, text=last.text[:-1]),),
    )


def empty_batches():
    return (
        batch(annotator="ann_A", batch_nonce="bn1"),
        batch(annotator="ann_B", batch_nonce="bn2"),
    )


def test_50_zero_submissions_stale_source_is_rejected():
    index, _ = build()

    assert len(STALE) == len(BODY)
    assert sha256(STALE.encode("utf-8")).hexdigest() != index.content_sha256

    result = validate_annotation_submissions(index, STALE, [])

    assert result.status == STRUCTURE_INVALID
    assert result.submission_count == 0
    assert any("source sha256 mismatch" in error for error in result.errors)


def test_51_two_zero_fact_batches_stale_source_are_rejected():
    index, _ = build()
    ba, bb = empty_batches()

    result = validate_annotation_batches(index, STALE, [ba, bb], [])

    assert result.status == STRUCTURE_INVALID
    assert result.submission_count == 0
    assert result.batch_count == 2
    assert any("source sha256 mismatch" in error for error in result.errors)


def test_52_zero_decisions_stale_source_are_rejected():
    index, _ = build()
    ba, bb = empty_batches()

    result = validate_adjudications(index, STALE, [ba, bb], [], [])

    assert result.status == STRUCTURE_INVALID
    assert result.decision_count == 0
    assert result.confirmed_decision_count == 0
    assert any("source sha256 mismatch" in error for error in result.errors)


def test_53_broken_index_segments_rejected_without_any_submission():
    index, _ = build()
    broken = broken_segments(index)
    ba, bb = empty_batches()

    assert broken.source_length == len(BODY)
    assert broken.content_sha256 == index.content_sha256

    submissions = validate_annotation_submissions(broken, BODY, [])
    batches = validate_annotation_batches(broken, BODY, [ba, bb], [])
    adjudications = validate_adjudications(broken, BODY, [ba, bb], [], [])

    for result in (submissions, batches, adjudications):
        assert result.status == STRUCTURE_INVALID
        assert any(
            "index segments do not reconstruct source text losslessly"
            in error
            for error in result.errors
        )


def test_54_source_length_mismatch_rejected_without_any_submission():
    index, _ = build()
    # Digest and segments stay intact; only the declared length is wrong.
    stretched = replace(index, source_length=index.source_length + 1)

    result = validate_annotation_submissions(stretched, BODY, [])

    assert result.status == STRUCTURE_INVALID
    assert any(
        "index source_length does not match source text" in error
        for error in result.errors
    )


def test_55_empty_inputs_over_correct_source_stay_valid():
    index, _ = build()
    ba, bb = empty_batches()

    submissions = validate_annotation_submissions(index, BODY, [])
    assert submissions.status == STRUCTURE_VALID
    assert submissions.errors == ()
    assert submissions.submission_count == 0

    batches = validate_annotation_batches(index, BODY, [ba, bb], [])
    assert batches.status == STRUCTURE_VALID
    assert batches.errors == ()
    assert batches.batch_count == 2
    assert batches.zero_fact_batch_ids == tuple(
        sorted([ba.batch_id, bb.batch_id])
    )
    assert batches.declared_complete_batch_ids == ()

    adjudications = validate_adjudications(index, BODY, [ba, bb], [], [])
    assert adjudications.status == STRUCTURE_VALID
    assert adjudications.errors == ()
    assert adjudications.decision_count == 0
    assert adjudications.adjudicated_fact_group_ids == ()


def test_56_nonempty_path_is_unchanged():
    index, _ = build()
    ba, bb, sa, sb = pair()

    submissions = validate_annotation_submissions(index, BODY, [sa, sb])
    assert submissions.status == STRUCTURE_VALID
    assert submissions.errors == ()
    assert submissions.annotator_count == 2

    batches = validate_annotation_batches(index, BODY, [ba, bb], [sa, sb])
    assert batches.status == STRUCTURE_VALID
    assert batches.errors == ()
    assert batches.submission_count == 2
    assert batches.batch_count == 2
    assert batches.shared_occurrence_ids == (sa.fact_occurrence_id,)

    healthy = decision(
        batches=[ba, bb], members=[sa, sb], resolved_subject="suzhou"
    )
    adjudications = validate_adjudications(
        index, BODY, [ba, bb], [sa, sb], [healthy]
    )
    assert adjudications.status == STRUCTURE_VALID
    assert adjudications.errors == ()
    assert adjudications.confirmed_decision_count == 1


def test_57_nonempty_path_stale_source_still_rejected():
    index, _ = build()
    ba, bb, sa, sb = pair()

    submissions = validate_annotation_submissions(index, STALE, [sa, sb])
    batches = validate_annotation_batches(index, STALE, [ba, bb], [sa, sb])

    healthy = decision(
        batches=[ba, bb], members=[sa, sb], resolved_subject="suzhou"
    )
    adjudications = validate_adjudications(
        index, STALE, [ba, bb], [sa, sb], [healthy]
    )

    for result in (submissions, batches, adjudications):
        assert result.status == STRUCTURE_INVALID
        assert any(
            "source sha256 mismatch" in error for error in result.errors
        )


def test_58_empty_path_carries_no_extra_authority():
    index, _ = build()
    ba, bb = empty_batches()

    batches = validate_annotation_batches(index, BODY, [ba, bb], [])
    adjudications = validate_adjudications(index, BODY, [ba, bb], [], [])

    assert batches.completeness_status == COMPLETENESS_NOT_VERIFIED
    assert batches.claim_recall_status == NOT_EVALUATED
    assert batches.evidence_support_status == NOT_EVALUATED
    assert batches.annotator_identity_verified is False

    assert adjudications.gold_completeness_status == COMPLETENESS_NOT_VERIFIED
    assert adjudications.claim_recall_status == NOT_EVALUATED
    assert adjudications.evidence_support_status == NOT_EVALUATED
    assert adjudications.identity_verified is False
    assert adjudications.confirmed_decision_count == 0
    assert not hasattr(adjudications, "recall")
