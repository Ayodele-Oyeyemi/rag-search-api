"""
Tests for app/store.py.

Run with:
    python -m unittest discover tests
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import store


class TestStore(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.db_path = str(Path(self.tmp_dir) / "test.db")
        store.init_db(self.db_path)

    def test_insert_and_get(self):
        doc = store.insert_document("Hello world", {"source": "test"}, db_path=self.db_path)
        self.assertIsNotNone(doc["id"])

        fetched = store.get_document(doc["id"], db_path=self.db_path)
        self.assertEqual(fetched["text"], "Hello world")
        self.assertEqual(fetched["metadata"], {"source": "test"})

    def test_get_nonexistent_returns_none(self):
        result = store.get_document(9999, db_path=self.db_path)
        self.assertIsNone(result)

    def test_list_documents(self):
        store.insert_document("Doc one", db_path=self.db_path)
        store.insert_document("Doc two", db_path=self.db_path)

        docs = store.list_documents(db_path=self.db_path)
        self.assertEqual(len(docs), 2)
        self.assertEqual(docs[0]["text"], "Doc one")
        self.assertEqual(docs[1]["text"], "Doc two")

    def test_delete_document(self):
        doc = store.insert_document("To be deleted", db_path=self.db_path)

        deleted = store.delete_document(doc["id"], db_path=self.db_path)
        self.assertTrue(deleted)

        fetched = store.get_document(doc["id"], db_path=self.db_path)
        self.assertIsNone(fetched)

    def test_delete_nonexistent_returns_false(self):
        result = store.delete_document(9999, db_path=self.db_path)
        self.assertFalse(result)

    def test_count_documents(self):
        self.assertEqual(store.count_documents(db_path=self.db_path), 0)
        store.insert_document("One", db_path=self.db_path)
        store.insert_document("Two", db_path=self.db_path)
        self.assertEqual(store.count_documents(db_path=self.db_path), 2)

    def test_metadata_defaults_to_empty_dict(self):
        doc = store.insert_document("No metadata given", db_path=self.db_path)
        self.assertEqual(doc["metadata"], {})


if __name__ == "__main__":
    unittest.main()
