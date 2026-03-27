"""Tests for ExampleLibrary and normalize_slug.

No external packages required — only stdlib + project code.
Run from GIFPT_AI/: python3 -m unittest studio.tests.test_example_library
"""
import json
import sys
import os
import tempfile
import unittest
from pathlib import Path

# Project root on path
_ROOT = Path(__file__).resolve().parents[2]  # GIFPT_AI/
sys.path.insert(0, str(_ROOT))

from studio.ai.example_library import normalize_slug, ExampleLibrary
from studio.ai.patterns import PatternType


class TestNormalizeSlug(unittest.TestCase):

    def test_valid_passes_through(self):
        self.assertEqual(normalize_slug("bubble_sort"), "bubble_sort")

    def test_spaces_replaced_with_underscore(self):
        self.assertEqual(normalize_slug("bubble sort"), "bubble_sort")

    def test_dash_replaced(self):
        self.assertEqual(normalize_slug("Floyd-Warshall"), "floyd_warshall")

    def test_star_replaced(self):
        self.assertEqual(normalize_slug("A*"), "a_star")

    def test_plus_replaced(self):
        self.assertEqual(normalize_slug("C++"), "c_plus_plus")

    def test_strips_unicode(self):
        # 한글 등 비ASCII → 빈 문자열 또는 정규화된 형태
        result = normalize_slug("버블정렬")
        self.assertEqual(result, "")

    def test_strips_path_traversal(self):
        result = normalize_slug("../../etc/passwd")
        # / → _, then non-alnum stripped → "etcpasswd" or similar, no dots
        self.assertNotIn(".", result)
        self.assertNotIn("/", result)

    def test_truncated_at_64(self):
        long_name = "a" * 100
        self.assertEqual(len(normalize_slug(long_name)), 64)

    def test_collapses_multiple_underscores(self):
        self.assertEqual(normalize_slug("merge__sort"), "merge_sort")

    def test_strips_leading_trailing_underscores(self):
        self.assertEqual(normalize_slug("_bubble_sort_"), "bubble_sort")

    def test_empty_string(self):
        self.assertEqual(normalize_slug(""), "")

    def test_case_lowered(self):
        self.assertEqual(normalize_slug("QuickSort"), "quicksort")


class TestExampleLibrary(unittest.TestCase):

    def _make_jsonl(self, examples: list[dict]) -> Path:
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".jsonl", delete=False, encoding="utf-8"
        )
        for ex in examples:
            tmp.write(json.dumps(ex) + "\n")
        tmp.close()
        return Path(tmp.name)

    def _sample_examples(self):
        return [
            {"tag": "bubble_sort", "pattern_type": "SEQUENCE", "quality_score": 8, "code": "# bubble"},
            {"tag": "quick_sort", "pattern_type": "SEQUENCE", "quality_score": 7, "code": "# quick"},
            {"tag": "cnn", "pattern_type": "GRID", "quality_score": 9, "code": "# cnn"},
            {"tag": "bfs", "pattern_type": "GRAPH", "quality_score": 6, "code": "# bfs"},
        ]

    def test_get_examples_matching_pattern_returns_correct_subset(self):
        path = self._make_jsonl(self._sample_examples())
        try:
            lib = ExampleLibrary(path)
            results = lib.get_examples(PatternType.SEQUENCE, top_k=3)
            tags = [r["tag"] for r in results]
            self.assertIn("bubble_sort", tags)
            self.assertIn("quick_sort", tags)
            self.assertNotIn("cnn", tags)
        finally:
            os.unlink(path)

    def test_get_examples_sorted_by_quality_score_descending(self):
        path = self._make_jsonl(self._sample_examples())
        try:
            lib = ExampleLibrary(path)
            results = lib.get_examples(PatternType.SEQUENCE, top_k=2)
            self.assertEqual(results[0]["tag"], "bubble_sort")  # quality 8 > 7
        finally:
            os.unlink(path)

    def test_get_examples_fallback_when_no_pattern_match(self):
        # No SEQ_ATTENTION examples → should return all, sorted by quality
        path = self._make_jsonl(self._sample_examples())
        try:
            lib = ExampleLibrary(path)
            results = lib.get_examples(PatternType.SEQ_ATTENTION, top_k=3)
            self.assertGreater(len(results), 0)
            # Top result should be the highest quality overall
            self.assertEqual(results[0]["tag"], "cnn")  # quality 9
        finally:
            os.unlink(path)

    def test_get_examples_fewer_than_topk(self):
        # Only 1 GRAPH example, top_k=3 → returns 1
        path = self._make_jsonl(self._sample_examples())
        try:
            lib = ExampleLibrary(path)
            results = lib.get_examples(PatternType.GRAPH, top_k=3)
            self.assertEqual(len(results), 1)
        finally:
            os.unlink(path)

    def test_get_examples_no_pattern_returns_all_sorted(self):
        path = self._make_jsonl(self._sample_examples())
        try:
            lib = ExampleLibrary(path)
            results = lib.get_examples(None, top_k=10)
            scores = [r["quality_score"] for r in results]
            self.assertEqual(scores, sorted(scores, reverse=True))
        finally:
            os.unlink(path)

    def test_init_missing_jsonl_raises_no_exception(self):
        # Missing JSONL → library is empty (logs warning, does not raise)
        lib = ExampleLibrary(Path("/nonexistent/path.jsonl"))
        self.assertEqual(lib.get_examples(), [])

    def test_get_examples_empty_library(self):
        path = self._make_jsonl([])
        try:
            lib = ExampleLibrary(path)
            self.assertEqual(lib.get_examples(PatternType.SEQUENCE), [])
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
