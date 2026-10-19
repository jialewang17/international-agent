"""Offline packaging/structure checks for ChinaStory Skills v5.1."""
from pathlib import Path
import json
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "china-story-evaluation"
GEN = ROOT / "china-story-generation"

class PackageLayoutTests(unittest.TestCase):
    def test_only_two_skill_entrypoints(self):
        entries = sorted(p.parent.name for p in ROOT.rglob("SKILL.md"))
        self.assertEqual(entries, ["china-story-evaluation", "china-story-generation"])

    def test_evaluation_is_method_only(self):
        self.assertEqual({p.name for p in EVAL.iterdir()}, {"SKILL.md", "agents", "references"})
        self.assertEqual(len(list((EVAL / "references").glob("*.md"))), 7)

    def test_eval_runtime_local_markdown_links_resolve(self):
        missing = []
        for p in EVAL.rglob("*.md"):
            for target in re.findall(r"\]\(([^)]+)\)", p.read_text(encoding="utf-8")):
                target = target.split("#")[0].strip("<>")
                if not target or ":" in target or target.startswith("/"):
                    continue
                if not (p.parent / target).is_file():
                    missing.append((p.relative_to(EVAL).as_posix(), target))
        self.assertEqual(missing, [])

    def test_backend_schema_and_validator_paths_exist(self):
        schema = ROOT / "api/schemas/evaluation-result-v5.1.schema.json"
        self.assertTrue(schema.is_file())
        self.assertTrue((ROOT / "utils/validate_evaluation.py").is_file())
        doc = json.loads(schema.read_text(encoding="utf-8"))
        self.assertEqual(doc["properties"]["overall_score"]["type"], "null")
        self.assertEqual(doc["properties"]["rubric_version"]["const"], "CHINASTORY_CONTENT_QUALITY_RUBRIC_v2.1")

    def test_generation_post_and_news_present(self):
        for name in ("post.md", "news.md"):
            self.assertTrue((GEN / "references/genres" / name).is_file())

    def test_provenance_and_new_handoff_files_exist(self):
        for rel in (
            "docs/evaluation/Evaluation_v5.1_Changes_and_Evidence.md",
            "docs/evaluation/Evaluation_v5.1_Test_Plan.md",
            "docs/generation/Post_News_v3.1_Changes_and_Sources.md",
            "handoff-to-backend/06-evaluation-v5.1-integration.md",
            "docs/evaluation/history/Evaluation_v4.1_Changes_and_Evidence.md",
        ):
            self.assertTrue((ROOT / rel).is_file(), rel)

    def test_docs_markdown_links_resolve(self):
        broken = []
        for p in ROOT.rglob("*.md"):
            for target in re.findall(r"\]\(([^)]+)\)", p.read_text(encoding="utf-8")):
                target = target.split("#")[0].split(" ")[0].strip("<>")
                if not target or ":" in target or target.startswith("/"):
                    continue
                if not (p.parent / target).exists():
                    broken.append((str(p.relative_to(ROOT)), target))
        self.assertEqual(broken, [])

if __name__ == "__main__":
    unittest.main()
