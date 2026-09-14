"""
Tests for app/main.py - the FastAPI endpoints.

Run with:
    python -m unittest discover tests
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient

from app import main, store
from app.search import SearchIndex


class TestDocumentsAndSearchEndpoints(unittest.TestCase):
    def setUp(self):
        # Isolate each test with its own temp database and a fresh search
        # index pointed at it, so tests never see each other's documents.
        self.tmp_dir = tempfile.mkdtemp()
        self.db_path = str(Path(self.tmp_dir) / "test.db")

        store.DEFAULT_DB_PATH = self.db_path
        store.init_db(self.db_path)
        main.search_index = SearchIndex(self.db_path)

        self.client = TestClient(main.app)

    def test_add_and_get_document(self):
        response = self.client.post("/documents", json={"text": "Hello world", "metadata": {"tag": "greeting"}})
        self.assertEqual(response.status_code, 201)
        doc = response.json()
        self.assertEqual(doc["text"], "Hello world")

        fetch_response = self.client.get(f"/documents/{doc['id']}")
        self.assertEqual(fetch_response.status_code, 200)
        self.assertEqual(fetch_response.json()["text"], "Hello world")

    def test_get_nonexistent_document_returns_404(self):
        response = self.client.get("/documents/9999")
        self.assertEqual(response.status_code, 404)

    def test_list_documents(self):
        self.client.post("/documents", json={"text": "Doc one"})
        self.client.post("/documents", json={"text": "Doc two"})

        response = self.client.get("/documents")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 2)

    def test_delete_document(self):
        add_response = self.client.post("/documents", json={"text": "Temporary doc"})
        doc_id = add_response.json()["id"]

        delete_response = self.client.delete(f"/documents/{doc_id}")
        self.assertEqual(delete_response.status_code, 200)

        fetch_response = self.client.get(f"/documents/{doc_id}")
        self.assertEqual(fetch_response.status_code, 404)

    def test_delete_nonexistent_returns_404(self):
        response = self.client.delete("/documents/9999")
        self.assertEqual(response.status_code, 404)

    def test_search_with_no_documents(self):
        response = self.client.post("/search", json={"query": "anything"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["results"], [])

    def test_search_returns_relevant_results(self):
        self.client.post("/documents", json={"text": "Python is great for data science"})
        self.client.post("/documents", json={"text": "JavaScript powers the web"})

        response = self.client.post("/search", json={"query": "python data science"})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertGreater(len(body["results"]), 0)
        self.assertIn("Python", body["results"][0]["text"])

    def test_search_respects_top_k(self):
        for i in range(5):
            self.client.post("/documents", json={"text": f"Document {i} about testing search"})

        response = self.client.post("/search", json={"query": "testing search", "top_k": 2})
        self.assertLessEqual(len(response.json()["results"]), 2)

    def test_deleted_document_excluded_from_search(self):
        add_response = self.client.post("/documents", json={"text": "Unique searchable phrase about kangaroos"})
        doc_id = add_response.json()["id"]

        self.client.delete(f"/documents/{doc_id}")

        response = self.client.post("/search", json={"query": "kangaroos"})
        self.assertEqual(response.json()["results"], [])

    def test_empty_text_rejected(self):
        response = self.client.post("/documents", json={"text": ""})
        self.assertEqual(response.status_code, 422)

    def test_empty_query_rejected(self):
        response = self.client.post("/search", json={"query": ""})
        self.assertEqual(response.status_code, 422)


class TestHealthAndRoot(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(main.app)

    def test_health(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_root(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("message", response.json())


if __name__ == "__main__":
    unittest.main()
