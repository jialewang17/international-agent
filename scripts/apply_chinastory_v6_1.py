#!/usr/bin/env python3
"""Conservative, idempotent merger for ChinaStory Skills v6.1 into repo checkout.

Usage:
  python scripts/apply_chinastory_v6_1.py /path/to/international-agent
  python scripts/apply_chinastory_v6_1.py /path/to/international-agent --apply

The first command is DRY RUN. Never runs git commit/push. Existing target
files with different content fail closed. Edits only two known code points:
registration of new Skill IDs, and the News _evidence_pack handoff bug;
plus jsonschema dependency. No claim of complete six-genre/Evaluation E2E.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def _payload_files() -> list[Path]:
    out = []
    for folder in ("skills/china-story-generation", "skills/china-story-evaluation", "eval/contracts", "tests/chinastory_v61", "docs/chinastory_v6.1"):
        out += [p for p in (ROOT / folder).rglob("*") if p.is_file() and "__pycache__" not in p.parts and p.suffix not in (".pyc", ".pyo")]
    out += [ROOT / "utils/validate_evaluation.py", ROOT / "utils/chinastory_skill_loader_v61.py", ROOT / "scripts/apply_chinastory_v6_1.py"]
    return sorted(out)


def _patch_config(text: str) -> str:
    if "china_story_generation:" in text or "china_story_evaluation:" in text:
        if "china_story_generation:" in text and "china_story_evaluation:" in text:
            if "file: skills/china-story-generation/SKILL.md" not in text or "file: skills/china-story-evaluation/SKILL.md" not in text:
                raise RuntimeError("Existing v6.1 skill IDs point to unexpected paths")
            return text
        raise RuntimeError("One v6.1 skill is already registered; please reconcile manually")
    needle = "skills:\n"
    if text.count(needle) != 1:
        raise RuntimeError("config/skills.yaml does not have exactly one skills: block")
    # With [] keywords, these entries do not auto-activate on ordinary requests;
    # the legacy router remains live until adapter/E2E integration is complete.
    block = (
        "skills:\n"
        "  china_story_generation:\n"
        "    file: skills/china-story-generation/SKILL.md\n"
        "    title: ChinaStory Generation v6.1 (staged)\n"
        "    enabled: true\n"
        "    priority: 80\n"
        "    keywords: []\n"
        "  china_story_evaluation:\n"
        "    file: skills/china-story-evaluation/SKILL.md\n"
        "    title: ChinaStory Evaluation Part 3 v6.1 (staged)\n"
        "    enabled: true\n"
        "    priority: 80\n"
        "    keywords: []\n"
    )
    return text.replace(needle, block, 1)


def _patch_news_pack(text: str) -> str:
    anchor = '    if genre == "news":\n        article = '
    if text.count(anchor) != 1:
        raise RuntimeError("Cannot identify the known News response branch in tools/story_post_gen.py")
    start = text.index(anchor)
    next_branch = text.find("\n    return {", start)
    if next_branch < 0:
        raise RuntimeError("Cannot find end of News response branch")
    section = text[start:next_branch]
    if '"_evidence_pack": evidence_pack.model_dump(mode="json")' in section:
        return text
    target = '            "evidence_stats": {"user": n_user, "local": n_local},\n'
    if section.count(target) != 1:
        raise RuntimeError("News response payload anchor changed; manual merge required")
    section = section.replace(target, target + '            "_evidence_pack": evidence_pack.model_dump(mode="json"),\n', 1)
    return text[:start] + section + text[next_branch:]


def _patch_requirements(text: str) -> str:
    lines = [line.strip().lower() for line in text.splitlines()]
    if any(line.startswith("jsonschema") for line in lines):
        return text
    return text.rstrip("\n") + "\n\n# ChinaStory Evaluation v6.1 JSON Schema validation\njsonschema>=4\n"


def plan(repo: Path) -> dict[Path, bytes]:
    repo=repo.resolve()
    for p in ("config/skills.yaml", "tools/story_post_gen.py", "api/main.py", "api/schemas.py", "requirements.txt"):
        if not (repo / p).is_file():
            raise RuntimeError(f"Not expected ChinaStory checkout: missing {p}")
    if 'successful generation missing canonical EvidencePack' not in (repo/'api/main.py').read_text(encoding='utf-8'):
        raise RuntimeError("api/main.py EvidencePack handoff differs from inspected upstream; review manually")
    proposed: dict[Path,bytes] = {}
    for src in _payload_files():
        if not src.is_file(): raise RuntimeError(f"Missing payload file: {src}")
        rel = src.relative_to(ROOT)
        target = (repo/rel)
        if not target.resolve().is_relative_to(repo):
            raise RuntimeError(f"Payload destination escapes repo: {rel}")
        if target.is_symlink(): raise RuntimeError(f"Symlink target rejected: {rel}")
        value=src.read_bytes()
        if target.exists() and target.read_bytes()!=value:
            raise RuntimeError(f"Refusing to overwrite existing distinct file: {rel}")
        if not target.exists(): proposed[target]=value
    edits={
        'config/skills.yaml':_patch_config,
        'tools/story_post_gen.py':_patch_news_pack,
        'requirements.txt':_patch_requirements,
    }
    for rel,patch in edits.items():
        p=repo/rel
        if p.is_symlink():raise RuntimeError(f"Symlink target rejected: {rel}")
        old=p.read_text(encoding='utf-8')
        new=patch(old)
        if old!=new: proposed[p]=new.encode('utf-8')
    return proposed


def run(repo: Path, apply: bool=False) -> int:
    repo=repo.resolve()
    if not repo.is_dir():raise RuntimeError('Repository checkout not found')
    # Refuse to write over existing uncommitted local changes.
    if apply and (repo/'.git').exists():
        proc=subprocess.run(['git','-C',str(repo),'status','--porcelain'],capture_output=True,text=True)
        if proc.returncode or proc.stdout.strip():
            raise RuntimeError('Working tree not clean; commit/stash changes before --apply')
    proposals=plan(repo)
    print(('APPLY' if apply else 'DRY RUN'),len(proposals),'file updates')
    for p in proposals:
        print(' +',p.relative_to(repo).as_posix())
    if not apply:return 0
    originals={p:(p.read_bytes() if p.exists() else None) for p in proposals}
    try:
        for p,blob in proposals.items():
            p.parent.mkdir(parents=True,exist_ok=True)
            p.write_bytes(blob)
    except Exception:
        for p,blob in originals.items():
            if blob is None:
                if p.exists():p.unlink()
            else:p.write_bytes(blob)
        raise
    print('Applied. Review git diff, run tests, then commit on your branch. No push performed.')
    return 0


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repo',type=Path)
    parser.add_argument('--apply',action='store_true')
    a=parser.parse_args()
    try: return run(a.repo,apply=a.apply)
    except Exception as exc:
        print('ERROR:',exc,file=sys.stderr)
        return 2

if __name__=='__main__':
    sys.exit(main())
