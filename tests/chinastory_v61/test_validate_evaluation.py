"""Deterministic examples only. No claim is made about LLM judge validity."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "utils"))
from validate_evaluation import validate_result  # noqa: E402


class EvaluationValidatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.content = (HERE / "fixtures" / "content.txt").read_text(encoding="utf-8")
        cls.base = json.loads((HERE / "fixtures" / "valid_evaluation.json").read_text(encoding="utf-8"))

    def test_valid_fixture(self):
        self.assertEqual(validate_result(self.base, self.content), [])

    def test_schema_path_after_relocation(self):
        self.assertTrue((PROJECT_ROOT / "eval" / "contracts" / "evaluation-result-v6.1.schema.json").is_file())

    def test_score_range(self):
        data = copy.deepcopy(self.base)
        data["dimensions"][0]["score"] = 6
        self.assertTrue(validate_result(data, self.content))

    def test_missing_dimension(self):
        data = copy.deepcopy(self.base)
        data["dimensions"].pop()
        self.assertTrue(validate_result(data, self.content))

    def test_duplicate_dimension(self):
        data = copy.deepcopy(self.base)
        data["dimensions"][1]["dimension_id"] = data["dimensions"][0]["dimension_id"]
        self.assertIn("Repeated dimension_id", " ".join(validate_result(data, self.content)))

    def test_false_source_span(self):
        data = copy.deepcopy(self.base)
        data["dimensions"][0]["evidence_spans"][0]["end"] += 1
        self.assertIn("does not match", " ".join(validate_result(data, self.content)))

    def test_unicode_codepoint_index(self):
        data = copy.deepcopy(self.base)
        start = self.content.index("🧵")
        data["dimensions"][0]["evidence_spans"].append({"text": "🧵", "start": start, "end": start + 1})
        self.assertEqual(validate_result(data, self.content), [])

    def test_wrong_content_hash(self):
        data = copy.deepcopy(self.base)
        data["audit"]["content_sha256"] = "0" * 64
        self.assertIn("content_sha256", " ".join(validate_result(data, self.content)))

    def test_no_overall_score(self):
        data = copy.deepcopy(self.base)
        data["overall_score"] = 4.5
        self.assertTrue(validate_result(data, self.content))

    def test_no_auto_approval(self):
        data = copy.deepcopy(self.base)
        data["human_review"] = "APPROVED"
        self.assertTrue(validate_result(data, self.content))

    def test_state_contradiction(self):
        data = copy.deepcopy(self.base)
        data["return_to_part1"] = True
        data["review_decision"] = "READY_FOR_HUMAN_REVIEW"
        self.assertIn("Cannot return", " ".join(validate_result(data, self.content)))

    def test_suggestion_span_mismatch(self):
        data = copy.deepcopy(self.base)
        data["revision_suggestions"][0]["location"]["text"] = "wrong phrase"
        self.assertIn("does not match", " ".join(validate_result(data, self.content)))

    def test_nullable_confidence(self):
        data = copy.deepcopy(self.base)
        self.assertIsNone(data["dimensions"][0]["confidence"])
        self.assertEqual(validate_result(data, self.content), [])

    def test_false_calibrated_confidence(self):
        data = copy.deepcopy(self.base)
        data["dimensions"][0]["confidence_status"] = "CALIBRATED"
        self.assertTrue(validate_result(data, self.content))

    def test_return_to_part1_no_dimensions(self):
        data = copy.deepcopy(self.base)
        data.update({"status": "RETURN_TO_PART1", "execution_status": "RETURN_TO_PART1",
                     "review_decision": "RETURN_TO_PART1", "return_to_part1": True,
                     "dimensions": [], "revision_suggestions": [], "priority_issues": []})
        self.assertEqual(validate_result(data, self.content), [])

    def test_insufficient_context_no_scores(self):
        data = copy.deepcopy(self.base)
        data.update({"status": "INSUFFICIENT_CONTEXT", "execution_status": "INSUFFICIENT_CONTEXT",
                     "review_decision": "NEEDS_HUMAN", "dimensions": [],
                     "revision_suggestions": [], "priority_issues": []})
        self.assertEqual(validate_result(data, self.content), [])


if __name__ == "__main__":
    unittest.main()
