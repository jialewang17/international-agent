"""Deterministic sentence-level claim candidate extraction (I2-B-001).

This module converts a generated body of prose into a list of ``Claim``
candidates so that later stages can review them.

Scope of this patch (deliberately narrow):

* No LLM calls, no network access, no third-party dependencies.
* No EvidencePack lookups and no automatic ``evidence_ids`` binding.
* No translation, rewording or fact rewriting of the source text.
* Pure sentence-level candidate extraction: the *approach A* approved for
  I2-B-001 ("Deterministic Sentence-Level Claim Candidate Extraction").

A ``Claim`` produced here is a *candidate for review*. It is not a verified
fact, and a non-empty result does not mean the body's factual coverage is
complete. Semantic fact detection, atomic decomposition, cross-lingual
entailment and evidence-support assessment are explicitly **out of scope**.

Determinism: the same input always yields the same output, including order,
claim identifiers, text and ``evidence_ids``.
"""

import re
from typing import List, Protocol, runtime_checkable

from api.fact_safety import _fingerprint
from api.schemas import Claim

__all__ = ["ClaimExtractor", "DeterministicClaimExtractor"]

CLAIM_ID_PREFIX = "clm_"

_WHITESPACE_RE = re.compile(r"\s+")

# Sentence-ending characters. CJK enders never need a following space.
_ENDERS = ".!?。！？"
_ENDER_RUN_RE = re.compile(r"[.!?。！？]+")

# Closing punctuation/quotes absorbed into the preceding sentence.
_TRAILING_CLOSERS = "\"'”’»)]}）】》」』"

# Abbreviations whose trailing period must not start a new sentence.
_ABBREVIATIONS = frozenset(
    {
        "dr", "mr", "mrs", "ms", "prof", "rev", "hon", "sr", "jr", "st",
        "e.g", "i.e", "etc", "vs", "no", "fig", "al", "approx",
        "dept", "est", "vol", "ed", "eds", "inc", "ltd", "co", "corp",
        "u.s", "u.k", "u.n", "a.m", "p.m",
    }
)

# Dotted initialisms such as ``U.S.``, ``U.K.``, ``e.g.``, ``i.e.``.
_INITIALISM_RE = re.compile(r"(?:[A-Za-z]\.)+[A-Za-z]?")

# Line-leading Markdown structural markers (pure formatting, no prose).
_MD_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+")
_MD_BULLET_RE = re.compile(r"^\s{0,3}[-*+]\s+")
_MD_NUMBERED_RE = re.compile(r"^\s{0,3}\d{1,2}[.)]\s+")
# Four-digit year at the start of a sentence (e.g. ``2006.``) must not be
# mistaken for a Markdown ordered-list index.
_YEAR_PREFIX_RE = re.compile(r"^(?:1\d{3}|2\d{3})$")

# URLs, so that ``?``/``.`` inside them are never treated as sentence enders.
_URL_RE = re.compile(
    r"https?://[^\s<>\[\]{}\"'()。！？]+",
    re.IGNORECASE,
)
# Horizontal rule / separator made only of structural characters.
_MD_SEPARATOR_RE = re.compile(r"^\s*(?:[-*_=]\s*){3,}$")


def _normalize_text(text: str) -> str:
    """Strip ends and collapse internal whitespace runs to one space.

    Vocabulary, case, punctuation, negation and numeric/date qualifiers are
    preserved exactly. No lowercasing, no translation, no synonym replacement.
    """
    return _WHITESPACE_RE.sub(" ", text.strip())


def _is_separator(line: str) -> bool:
    """True for a horizontal rule / structural separator line."""
    return bool(_MD_SEPARATOR_RE.match(line))


def _clean_markdown_prefix(line: str) -> str:
    """Drop line-leading Markdown structure markers only.

    Removes heading (``# ``..``###### ``), bullet (``- ``/``* ``/``+ ``) and
    ordered-list (``1. ``/``1) ``) prefixes. Prose, factual numbers and any
    other vocabulary are left untouched.
    """
    cleaned = line
    for _ in range(4):  # tolerate a few nested prefixes
        candidate = _MD_HEADING_RE.sub("", cleaned)
        bullet = _MD_BULLET_RE.match(candidate)

        if bullet:
            after_bullet = candidate[bullet.end():]

            if (
                not after_bullet
                or after_bullet[0]
                not in "0123456789$¥￥€£"
            ):
                candidate = candidate[bullet.end():]
        candidate = _MD_NUMBERED_RE.sub("", candidate)
        if candidate == cleaned:
            break
        cleaned = candidate
    return cleaned.strip()


def _is_skippable_text(text: str) -> bool:
    """True when a block carries no reviewable prose.

    Skippable: empty/whitespace-only content, a pure hashtag line, or content
    with no word characters at all (e.g. a bare emoji line).
    """
    stripped = text.strip()
    if not stripped:
        return True
    tokens = stripped.split()
    if tokens and all(token.startswith("#") and len(token) > 1 for token in tokens):
        return True
    if not any(ch.isalnum() for ch in stripped):
        return True
    return False


def _period_is_boundary(
    text: str,
    index: int,
    sentence_start: int = 0,
) -> bool:
    """Decide whether the ASCII ``.`` at ``index`` ends a sentence.

    Conservative by design: when the boundary cannot be decided reliably the
    period is *not* treated as a sentence end, so the full text is preserved.
    """
    prev_ch = text[index - 1] if index > 0 else ""
    next_ch = text[index + 1] if index + 1 < len(text) else ""

    # Decimal number such as ``3.14``.
    if prev_ch.isdigit() and next_ch.isdigit():
        return False

    # Bare four-digit year at the start of the sentence, e.g. ``2006. 苏绣...``.
    if _YEAR_PREFIX_RE.fullmatch(text[sentence_start:index].strip()):
        return False

    word = re.search(r"[^\s]*$", text[:index]).group(0)
    word_lower = word.lower()

    # Known abbreviation, e.g. ``Dr.``, ``Prof.``, ``etc.``.
    if word_lower in _ABBREVIATIONS:
        return False

    # Dotted initialism, e.g. ``U.S.``, ``e.g.``, ``i.e.``.
    if word and _INITIALISM_RE.fullmatch(word + "."):
        return False

    # Domain / URL fragments such as ``example.com``.
    if "://" in word:
        return False
    if word and next_ch and next_ch.isalnum():
        return False

    return True


def _split_sentences(text: str) -> List[str]:
    """Split ``text`` into sentence candidates, preserving order.

    Splits on ``.``/``!``/``?`` and ``。``/``！``/``？``. Runs of enders are kept
    together, trailing closing quotes/brackets join the finished sentence, and
    an ellipsis (``..``/``...``) is left intact. Compound sentences are *not*
    broken apart on commas, semicolons, ``and``, ``but`` or ``because`` -- that
    atomic decomposition belongs to approach B.
    """
    sentences: List[str] = []
    start = 0
    length = len(text)

    url_spans = []

    for url_match in _URL_RE.finditer(text):
        url_start, url_end = url_match.span()

        while (
            url_end > url_start
            and text[url_end - 1] in ".,;:!?"
        ):
            url_end -= 1

        if url_end > url_start:
            url_spans.append((url_start, url_end))

    for match in _ENDER_RUN_RE.finditer(text):
        mark_start = match.start()

        if any(
            s <= mark_start < e
            for s, e in url_spans
        ):
            continue

        immediately_after_url = any(
            e == mark_start
            for _, e in url_spans
        )

        run = match.group(0)

        if run and all(ch == "." for ch in run):
            if len(run) > 1:
                # Ellipsis -- keep the text intact rather than guessing.
                continue

            if (
                not immediately_after_url
                and not _period_is_boundary(
                    text,
                    mark_start,
                    start,
                )
            ):
                continue

        end = match.end()
        while end < length and text[end] in _TRAILING_CLOSERS:
            end += 1
        sentences.append(text[start:end])
        start = end

    if start < length:
        sentences.append(text[start:])

    return sentences


def _iter_blocks(content: str) -> List[str]:
    """Split content into ordered blocks: paragraphs and Markdown list items.

    Consecutive plain lines are joined into one paragraph block; blank lines,
    separators and each Markdown heading / bullet / numbered item start their
    own block. Newlines are never globally collapsed before this step.
    """
    normalized = content.replace("\r\n", "\n").replace("\r", "\n")
    blocks: List[str] = []
    paragraph: List[str] = []

    def flush_paragraph() -> None:
        if paragraph:
            blocks.append(" ".join(paragraph))
            paragraph.clear()

    for raw_line in normalized.split("\n"):
        line = raw_line.strip()
        if (
            not line
            or _is_separator(line)
            or _is_skippable_text(line)
        ):
            flush_paragraph()
            continue
        if (
            _MD_HEADING_RE.match(line)
            or _MD_BULLET_RE.match(line)
            or _MD_NUMBERED_RE.match(line)
        ):
            flush_paragraph()
            cleaned = _clean_markdown_prefix(line)
            if cleaned:
                blocks.append(cleaned)
            continue
        paragraph.append(line)

    flush_paragraph()
    return blocks


@runtime_checkable
class ClaimExtractor(Protocol):
    """Protocol for extracting claim candidates from generated content."""

    def extract(self, content: str) -> List[Claim]:
        """Return claim candidates, in order, for ``content``."""
        ...


class DeterministicClaimExtractor:
    """Approach A: deterministic sentence-level claim candidate extraction.

    Implements :class:`ClaimExtractor`. Never calls an LLM, never touches the
    network and never reads an EvidencePack.
    """

    def extract(self, content: str) -> List[Claim]:
        if not isinstance(content, str):
            raise TypeError(
                f"content must be str, got {type(content).__name__}"
            )
        if not content.strip():
            return []

        claims: List[Claim] = []
        seen_ids: set = set()

        for block in _iter_blocks(content):
            for sentence in _split_sentences(block):
                text = _normalize_text(sentence)
                if _is_skippable_text(text):
                    continue

                claim_id = CLAIM_ID_PREFIX + _fingerprint(text)
                if claim_id in seen_ids:
                    continue
                seen_ids.add(claim_id)

                claims.append(
                    Claim(claim_id=claim_id, text=text, evidence_ids=[])
                )

        return claims
