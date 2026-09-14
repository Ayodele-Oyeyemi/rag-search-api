# Lightweight RAG / Semantic Search API

A REST API that indexes text documents and lets you search them with
natural language queries — the retrieval half of a RAG (Retrieval-Augmented
Generation) pipeline, built to be genuinely **lightweight**: no model
downloads, no API keys, no cost, runs instantly on any machine.

Built with **FastAPI**, **scikit-learn** (TF-IDF + cosine similarity), and
**SQLite**.

## An honest note on "semantic" search

This uses **TF-IDF (term frequency / inverse document frequency) + cosine
similarity** — a classical, well-established information retrieval
technique, not a neural embedding model. It's genuinely good at:

- ✅ Keyword and phrase overlap ("coral reef australia" → finds the document about the Great Barrier Reef)
- ✅ Ranking documents by how much relevant vocabulary they share with your query
- ✅ Running instantly, offline, with zero setup

It will **not** catch:

- ❌ True synonyms it hasn't seen ("automobile" won't match a document that only says "car")
- ❌ Paraphrased meaning with no shared vocabulary

See [Upgrading to real neural embeddings](#upgrading-to-real-neural-embeddings-v2)
below for how to swap in a proper embedding model later without changing
the API surface at all.

## Features

- ✅ `POST /documents` — add a document (text + optional metadata) to the index
- ✅ `GET /documents` — list all indexed documents
- ✅ `GET /documents/{id}` — fetch a single document
- ✅ `DELETE /documents/{id}` — remove a document from the index
- ✅ `POST /search` — natural language query, ranked results with similarity scores
- ✅ Persisted to SQLite — the index survives restarts
- ✅ Zero-relevance results are filtered out (won't return documents that share nothing with your query)
- ✅ Interactive API docs at `/docs`

## Requirements

- Python 3.9+
- Dependencies listed in `requirements.txt`

## Running the server

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Then open **http://127.0.0.1:8000/docs** for interactive Swagger UI.

## Usage

### Add documents

```bash
curl -X POST http://localhost:8000/documents \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Python is a versatile programming language used for web development, data science, and automation.",
    "metadata": {"topic": "programming"}
  }'
```

```json
{
  "id": 1,
  "text": "Python is a versatile programming language used for web development, data science, and automation.",
  "metadata": { "topic": "programming" },
  "created_at": 1789371494.15
}
```

### Search

```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "AI and data models", "top_k": 3}'
```

```json
{
  "query": "AI and data models",
  "results": [
    {
      "id": 3,
      "text": "Machine learning is a subset of artificial intelligence focused on training models from data.",
      "metadata": { "topic": "AI" },
      "score": 0.4289
    },
    {
      "id": 1,
      "text": "Python is a versatile programming language used for web development, data science, and automation.",
      "metadata": { "topic": "programming" },
      "score": 0.1488
    }
  ],
  "count": 2
}
```

Documents with **zero** overlap with the query are excluded entirely.
Searching `"coral reef australia"` above would only return the one document
about the Great Barrier Reef, not the Python or ML documents.

### List / get / delete

```bash
curl http://localhost:8000/documents
curl http://localhost:8000/documents/1
curl -X DELETE http://localhost:8000/documents/1
```

### Request reference

**`POST /documents`**

| Field | Type | Required | Description |
|---|---|---|---|
| `text` | string | yes | The document's content |
| `metadata` | object | no | Any JSON-serializable metadata to store alongside it |

**`POST /search`**

| Field | Type | Required | Description |
|---|---|---|---|
| `query` | string | yes | Natural language search query |
| `top_k` | int | no (default `5`) | Max results to return (1–50) |

## How it works

1. Each document's raw text is stored in SQLite.
2. On search, **all** documents are fit into a single `TfidfVectorizer`.
   TF-IDF scores are relative to the whole corpus, so the vectorizer must
   be rebuilt whenever documents are added or removed. This project caches
   the fitted vectorizer in memory and only rebuilds it lazily, right
   before the next search after a change (not on every single request).
3. The query is projected into that same vector space, and **cosine
   similarity** ranks every document by how closely its vocabulary
   distribution matches the query's.
4. Results with a similarity score of exactly `0` (no shared vocabulary at
   all) are filtered out rather than returned as irrelevant noise.

## Upgrading to real neural embeddings (v2)

The API surface here (`POST /documents`, `POST /search`) is intentionally
generic. To upgrade to true semantic search later, you'd only need to swap
the internals of `app/search.py`:

- Replace `TfidfVectorizer` with a model from `sentence-transformers`
  (e.g. `all-MiniLM-L6-v2`) to generate real dense embeddings
- Replace the in-memory cosine similarity matrix with a proper vector
  store (e.g. `chromadb`, `faiss`, or even just `numpy` cosine similarity
  over embedding vectors) for better scaling
- Everything else — the SQLite document store, the FastAPI routes, the
  request/response shapes. Stays exactly the same

## Limitations

- **Single-process only.** The in-memory search index cache (`SearchIndex`)
  lives in one process's memory. Running multiple worker processes (e.g.
  `uvicorn --workers 4`) would mean each worker has its own inconsistent
  cache. Fine for a personal project or single-instance deployment; would
  need a shared cache (e.g. Redis) for a real multi-worker production setup.
- **No stemming/lemmatization.** "running" and "run" are treated as
  different tokens. `scikit-learn`'s `TfidfVectorizer` doesn't stem by
  default. This could be added with a custom tokenizer using a library
  like NLTK if needed.
- **Scales to thousands, not millions, of documents.** Rebuilding the full
  TF-IDF matrix on every change is fine for a small-to-medium corpus, but
  isn't the right approach for a huge document set. That's where a real
  vector database becomes necessary.

## Running tests

```bash
python -m unittest discover tests
```

## Project structure

```
rag-search-api/
├── app/
│   ├── main.py       # FastAPI app and route handlers
│   ├── store.py       # SQLite document storage
│   └── search.py       # TF-IDF search engine
├── tests/
│   ├── test_store.py
│   ├── test_search.py
│   └── test_main.py
├── requirements.txt
└── README.md
```