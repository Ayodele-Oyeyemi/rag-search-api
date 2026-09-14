"""
app/search.py

A lightweight semantic-ish search engine using TF-IDF (term frequency /
inverse document frequency) + cosine similarity - a classical information
retrieval technique, not a neural embedding model. See the README for an
honest discussion of what this catches (keyword/phrase overlap) versus what
it doesn't (true synonyms, paraphrasing).

The vectorizer must be re-fit whenever the document set changes (TF-IDF
scores depend on the whole corpus, not just one document), so this module
keeps a small in-memory cache that's invalidated on add/delete and rebuilt
lazily on the next search.
"""

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app import store


class SearchIndex:
    def __init__(self, db_path: str = None):
        self.db_path = db_path
        self._vectorizer = None
        self._matrix = None
        self._documents = None  # list of dicts, same order as _matrix rows
        self._dirty = True

    def invalidate(self):
        """Call this after any add/delete so the next search rebuilds the index."""
        self._dirty = True

    def _rebuild(self):
        self._documents = store.list_documents(self.db_path)

        if not self._documents:
            self._vectorizer = None
            self._matrix = None
            self._dirty = False
            return

        texts = [doc["text"] for doc in self._documents]
        self._vectorizer = TfidfVectorizer(stop_words="english")
        self._matrix = self._vectorizer.fit_transform(texts)
        self._dirty = False

    def search(self, query: str, top_k: int = 5) -> list:
        """
        Returns up to `top_k` documents ranked by cosine similarity to the
        query, each as {**document, "score": float}. Documents with zero
        similarity (no meaningful overlap at all) are excluded.
        """
        if self._dirty:
            self._rebuild()

        if not self._documents or self._vectorizer is None:
            return []

        query_vector = self._vectorizer.transform([query])
        similarities = cosine_similarity(query_vector, self._matrix)[0]

        ranked_indices = similarities.argsort()[::-1]

        results = []
        for idx in ranked_indices[:top_k]:
            score = float(similarities[idx])
            if score <= 0:
                continue
            results.append({**self._documents[idx], "score": round(score, 4)})

        return results
