"""Read v6.1 domain skill instructions without silently truncating.

This is a prompt resource loader, not a workflow executor or evaluator.
The caller must supply confirmed task/context/evidence separately and must
run fact gates, evaluation and human approval in the existing backend.
"""
from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

ALLOWED_GENRES = frozenset({"post", "news", "feature", "indepth", "script", "faq"})
ROOT = Path(__file__).resolve().parents[1]

class SkillLoadError(RuntimeError):
    pass

@dataclass(frozen=True)
class LoadedSkill:
    text: str
    files: tuple[str, ...]
    sha256: str


def _read_files(root: Path, paths: tuple[str, ...], max_chars: int) -> LoadedSkill:
    blocks = []
    actual = []
    for rel in paths:
        p = (root / rel).resolve()
        if not p.is_relative_to(root.resolve()):
            raise SkillLoadError(f"Path escapes repository root: {rel}")
        if not p.is_file():
            raise SkillLoadError(f"Required Skill/rubric file is missing: {rel}")
        value = p.read_text(encoding="utf-8")
        if not value.strip():
            raise SkillLoadError(f"Required Skill/rubric file is empty: {rel}")
        actual.append(rel)
        blocks.append(f"### Document: {rel}\n{value}")
    text = "\n\n".join(blocks)
    if max_chars <= 0 or len(text) > max_chars:
        raise SkillLoadError(f"Skill context {len(text)} chars exceeds budget {max_chars}; no silent truncation")
    return LoadedSkill(text=text, files=tuple(actual), sha256=sha256(text.encode("utf-8")).hexdigest())


def load_generation_skill(genre: str, root: Path = ROOT, max_chars: int = 65000) -> LoadedSkill:
    genre = genre.strip().lower()
    if genre not in ALLOWED_GENRES:
        raise SkillLoadError(f"Unsupported genre: {genre}")
    return _read_files(Path(root), (
        "skills/china-story-generation/SKILL.md",
        "skills/china-story-generation/references/writing-constraints.md",
        "skills/china-story-generation/references/transcreation.md",
        "skills/china-story-generation/references/output-contracts.md",
        f"skills/china-story-generation/references/genres/{genre}.md",
    ), max_chars)


def load_evaluation_skill(root: Path = ROOT, max_chars: int = 110000) -> LoadedSkill:
    return _read_files(Path(root), (
        "skills/china-story-evaluation/SKILL.md",
        "eval/CHINASTORY_CONTENT_QUALITY_RUBRIC_v2.1.md",
        "skills/china-story-evaluation/references/rubric-usage.md",
        "skills/china-story-evaluation/references/input-contracts.md",
        "skills/china-story-evaluation/references/output-contracts.md",
        "skills/china-story-evaluation/references/cross-cultural-review.md",
        "skills/china-story-evaluation/references/genre-checks.md",
        "skills/china-story-evaluation/references/revision-feedback.md",
    ), max_chars)
