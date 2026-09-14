"""
app/main.py

FastAPI application exposing a lightweight semantic search API over a
document store, using TF-IDF + cosine similarity as the retrieval engine.

Run locally with:
    uvicorn app.main:app --reload

Then visit http://127.0.0.1:8000/docs for interactive API docs.
"""

from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app import store
from app.search import SearchIndex

app = FastAPI(
    title="Lightweight RAG / Semantic Search API",
    description=(
        "Indexes text documents and lets you search them with natural "
        "language queries, using TF-IDF + cosine similarity. See the "
        "README for how this compares to true neural embedding search."
    ),
    version="1.0.0",
)

search_index = SearchIndex()


class DocumentCreateRequest(BaseModel):
    text: str = Field(..., min_length=1, description="The document's text content.")
    metadata: Optional[dict] = Field(default_factory=dict, description="Arbitrary metadata to store alongside the document.")


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Natural language search query.")
    top_k: int = Field(5, ge=1, le=50, description="Maximum number of results to return.")


@app.on_event("startup")
def on_startup():
    store.init_db()


@app.get("/")
def root():
    return {
        "message": "Lightweight RAG / Semantic Search API",
        "docs": "/docs",
        "endpoints": {
            "POST /documents": "Add a document to the index",
            "GET /documents": "List all indexed documents",
            "GET /documents/{id}": "Get a single document",
            "DELETE /documents/{id}": "Remove a document from the index",
            "POST /search": "Search indexed documents with a natural language query",
        },
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/documents", status_code=201)
def add_document(request: DocumentCreateRequest):
    document = store.insert_document(request.text, request.metadata)
    search_index.invalidate()
    return document


@app.get("/documents")
def list_all_documents():
    return {"documents": store.list_documents(), "count": store.count_documents()}


@app.get("/documents/{doc_id}")
def get_one_document(doc_id: int):
    document = store.get_document(doc_id)
    if document is None:
        raise HTTPException(status_code=404, detail=f"No document with id {doc_id}.")
    return document


@app.delete("/documents/{doc_id}")
def remove_document(doc_id: int):
    deleted = store.delete_document(doc_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"No document with id {doc_id}.")
    search_index.invalidate()
    return {"deleted": True, "id": doc_id}


@app.post("/search")
def search_documents(request: SearchRequest):
    if store.count_documents() == 0:
        return {"query": request.query, "results": [], "note": "No documents indexed yet."}

    results = search_index.search(request.query, top_k=request.top_k)
    return {"query": request.query, "results": results, "count": len(results)}
