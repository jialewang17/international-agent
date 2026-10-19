"""Offline staged-merge tests. Not tests against the live GitHub checkout."""
from __future__ import annotations
import hashlib
import importlib.util
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT / 'utils'))
from chinastory_skill_loader_v61 import (load_generation_skill, load_evaluation_skill, SkillLoadError)

spec=importlib.util.spec_from_file_location('apply_v61',ROOT/'scripts/apply_chinastory_v6_1.py')
install=importlib.util.module_from_spec(spec)
spec.loader.exec_module(install)

STUB_NEWS = '''def example():
    if genre == "news":
        article = (parsed.get("article") or "").strip()
        return {
            "theme": theme,
            "evidence_stats": {"user": n_user, "local": n_local},
            "post": article,
        }
    return {
        "_evidence_pack": evidence_pack.model_dump(mode="json"),
        "post": parsed.get("post", ""),
    }
'''


def create_fake_repo(path:Path):
    docs={
      'config/skills.yaml':'enabled: true\nskills:\n  china_story_post:\n    file: skills/genres/china-story-post.md\n',
      'tools/story_post_gen.py':STUB_NEWS,
      'api/main.py':'raise RuntimeError("successful generation missing canonical EvidencePack")\n',
      'api/schemas.py':'class EvaluationResult: pass\n',
      'requirements.txt':'fastapi>=0.115.0\n',
    }
    for rel,text in docs.items():
        p=path/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf-8')

class SkillLoaderTests(unittest.TestCase):
    def test_post_and_news_loader_reads_full_genre(self):
        for g in ('post','news'):
            loaded=load_generation_skill(g,ROOT)
            self.assertIn(f'references/genres/{g}.md',loaded.text)
            self.assertIn('SKILL.md',loaded.text)
            self.assertGreater(len(loaded.text),12000)
            self.assertEqual(loaded.sha256,hashlib.sha256(loaded.text.encode()).hexdigest())
    def test_all_six_genres_known(self):
        for g in ('post','news','feature','indepth','script','faq'):
            self.assertEqual(len(load_generation_skill(g,ROOT).files),5)
    def test_unknown_genre_rejected(self):
        with self.assertRaises(SkillLoadError):load_generation_skill('../../etc/passwd',ROOT)
    def test_budget_not_silently_truncated(self):
        with self.assertRaises(SkillLoadError):load_generation_skill('post',ROOT,max_chars=10)
    def test_evaluation_requires_official_rubric(self):
        # Missing-Rubric behavior is tested in an isolated directory even when
        # this suite is installed into the real repo (which has the Rubric).
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            shutil.copytree(ROOT/'skills/china-story-evaluation',root/'skills/china-story-evaluation')
            with self.assertRaises(SkillLoadError):load_evaluation_skill(root)
    def test_evaluation_loader_when_rubric_present(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            shutil.copytree(ROOT/'skills/china-story-evaluation',root/'skills/china-story-evaluation')
            p=root/'eval/CHINASTORY_CONTENT_QUALITY_RUBRIC_v2.1.md'
            p.parent.mkdir(parents=True,exist_ok=True);p.write_text('dummy rubric for loader path test only',encoding='utf-8')
            self.assertIn('dummy rubric',load_evaluation_skill(root).text)

    def test_six_genre_documents_match_v51_hashes(self):
        expected = {
            "post": "3aaf5117746395720ccaff91c79f7bbfdfffe1f4800a3a22ff712a74bd759018",
            "news": "8733f7e83e8c23ddb18369af95182f23ba6ce04fcad4ea6107628a019af960f5",
            "feature": "5b9a37b05f89778a6453ba81498db7a2782fe501407ccd113f8fe29dede5631a",
            "indepth": "695463358c7af212ab9a9e28e0a8883700f72403913f9a21ef14e54b8d72b264",
            "script": "18bd568e246e04626db425cd76b6bc4158c24f9dd0a7db5a123b0d9041328a8c",
            "faq": "7cba45c3d4304ddbb063a27b9919f2e95fc6bbb6a5f630409cff953a5ce09390",
        }
        for genre, original_hash in expected.items():
            p=ROOT/'skills/china-story-generation/references/genres'/f'{genre}.md'
            self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(), original_hash)

class InstallPlanTests(unittest.TestCase):
    def test_dry_run_is_no_op_and_apply_idempotent(self):
        with tempfile.TemporaryDirectory() as td:
            repo=Path(td);create_fake_repo(repo)
            before=(repo/'config/skills.yaml').read_bytes()
            expected=install.plan(repo)
            self.assertIn(repo/'tools/story_post_gen.py',expected)
            self.assertEqual(install.run(repo,apply=False),0)
            self.assertEqual(before,(repo/'config/skills.yaml').read_bytes())
            self.assertEqual(install.run(repo,apply=True),0)
            self.assertIn('"_evidence_pack": evidence_pack.model_dump(mode="json")', (repo/'tools/story_post_gen.py').read_text())
            self.assertIn('file: skills/china-story-evaluation/SKILL.md',(repo/'config/skills.yaml').read_text())
            self.assertEqual((repo/'requirements.txt').read_text().count('jsonschema>=4'),1)
            self.assertTrue((repo/'eval/contracts/evaluation-result-v6.1.schema.json').exists())
            self.assertEqual(install.plan(repo),{})
    def test_existing_nonmatching_file_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            repo=Path(td);create_fake_repo(repo)
            p=repo/'skills/china-story-evaluation/SKILL.md';p.parent.mkdir(parents=True);p.write_text('DIFFERENT')
            with self.assertRaisesRegex(RuntimeError,'Refusing to overwrite'):install.plan(repo)
    def test_upstream_source_drift_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            repo=Path(td);create_fake_repo(repo)
            (repo/'tools/story_post_gen.py').write_text('unsupported new implementation')
            with self.assertRaisesRegex(RuntimeError,'Cannot identify'):install.plan(repo)
    def test_bad_config_path_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            repo=Path(td);create_fake_repo(repo)
            (repo/'config/skills.yaml').write_text('skills:\n  china_story_generation:\n    file: wrong\n  china_story_evaluation:\n    file: wrong\n')
            with self.assertRaisesRegex(RuntimeError,'unexpected paths'):install.plan(repo)
    def test_no_api_package_collision(self):
        self.assertTrue((ROOT/'eval/contracts/evaluation-result-v6.1.schema.json').is_file())
        self.assertFalse((ROOT/'api/schemas').exists())

if __name__=='__main__': unittest.main()
