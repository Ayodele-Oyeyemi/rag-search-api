"""
Tests for app/search.py.

Run with:
    python -m unittest discover tests
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import store
from app.search import SearchIndex


class TestSearchIndex(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.db_path = str(Path(self.tmp_dir) / "test.db")
        store.init_db(self.db_path)
        self.index = SearchIndex(self.db_path)

    def _add(self, text, metadata=None):
        return store.insert_document(text, metadata, db_path=self.db_path)

    def test_empty_index_returns_no_results(self):
        results = self.index.search("anything", top_k=5)
        self.assertEqual(results, [])

    def test_relevant_document_ranks_first(self):
        self._add("The quick brown fox jumps over the lazy dog")
        self._add("Python is a popular programming language")
        self._add("JavaScript is used for web development")

        results = self.index.search("python programming", top_k=3)
        self.assertGreater(len(results), 0)
        self.assertIn("Python", results[0]["text"])

    def test_unrelated_query_returns_empty(self):
        self._add("The quick brown fox jumps over the lazy dog")
        self._add("Python is a popular programming language")

        results = self.index.search("zzz nonexistent unrelated term qqq", top_k=5)
        self.assertEqual(results, [])

    def test_top_k_limits_results(self):
        for i in range(10):
            self._add(f"Document number {i} talks about cats and dogs")

        results = self.index.search("cats and dogs", top_k=3)
        self.assertLessEqual(len(results), 3)

    def test_results_sorted_descending_by_score(self):
        self._add("cats cats cats cats cats")
        self._add("cats and dogs together")
        self._add("just dogs here")

        results = self.index.search("cats", top_k=3)
        scores = [r["score"] for r in results]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_invalidate_forces_rebuild_after_new_document(self):
        self._add("Original document about oranges")

        results_before = self.index.search("bananas", top_k=5)
        self.assertEqual(results_before, [])

        self._add("A document specifically about bananas")
        self.index.invalidate()

        results_after = self.index.search("bananas", top_k=5)
        self.assertEqual(len(results_after), 1)
        self.assertIn("bananas", results_after[0]["text"])

    def test_metadata_is_preserved_in_results(self):
        self._add("A document about rockets", metadata={"category": "space"})

        results = self.index.search("rockets", top_k=1)
        self.assertEqual(results[0]["metadata"], {"category": "space"})


if __name__ == "__main__":
    unittest.main()
