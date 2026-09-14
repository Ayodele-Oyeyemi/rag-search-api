"""
app/store.py

SQLite storage layer for indexed documents. Each document has raw text,
optional metadata (stored as JSON), and a timestamp.
"""

import json
import sqlite3
import time
from pathlib import Path

DEFAULT_DB_PATH = "documents.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at REAL NOT NULL
);
"""


def _resolve_path(db_path: str = None) -> str:
    return db_path or DEFAULT_DB_PATH


def init_db(db_path: str = None):
    db_path = _resolve_path(db_path)
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def insert_document(text: str, metadata: dict = None, db_path: str = None) -> dict:
    db_path = _resolve_path(db_path)
    metadata = metadata or {}
    created_at = time.time()

    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.execute(
            "INSERT INTO documents (text, metadata_json, created_at) VALUES (?, ?, ?)",
            (text, json.dumps(metadata), created_at),
        )
        conn.commit()
        doc_id = cursor.lastrowid
    finally:
        conn.close()

    return {"id": doc_id, "text": text, "metadata": metadata, "created_at": created_at}


def get_document(doc_id: int, db_path: str = None):
    db_path = _resolve_path(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
    finally:
        conn.close()

    if not row:
        return None
    return _row_to_dict(row)


def list_documents(db_path: str = None) -> list:
    db_path = _resolve_path(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute("SELECT * FROM documents ORDER BY id").fetchall()
    finally:
        conn.close()

    return [_row_to_dict(row) for row in rows]


def delete_document(doc_id: int, db_path: str = None) -> bool:
    db_path = _resolve_path(db_path)
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        conn.commit()
        deleted = cursor.rowcount > 0
    finally:
        conn.close()
    return deleted


def count_documents(db_path: str = None) -> int:
    db_path = _resolve_path(db_path)
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute("SELECT COUNT(*) FROM documents").fetchone()
    finally:
        conn.close()
    return row[0]


def _row_to_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "text": row["text"],
        "metadata": json.loads(row["metadata_json"]),
        "created_at": row["created_at"],
    }
