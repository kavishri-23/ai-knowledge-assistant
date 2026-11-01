"""A tiny SQLite table that remembers which documents exist and how far processing got."""

import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from app.schemas import DocumentInfo

_SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    status TEXT NOT NULL,
    total_pages INTEGER,
    total_chunks INTEGER,
    error TEXT,
    created_at TEXT NOT NULL
)
"""


class Registry:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self._path = str(path)
        self._run(_SCHEMA)

    def _run(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        with closing(sqlite3.connect(self._path, timeout=10)) as connection:
            connection.row_factory = sqlite3.Row
            with connection:  # commits on success, rolls back on error
                return connection.execute(sql, params).fetchall()

    def upsert_pending(self, doc_id: str, filename: str) -> None:
        created = datetime.now(timezone.utc).isoformat(timespec="seconds")
        self._run(
            "INSERT OR REPLACE INTO documents "
            "(id, filename, status, total_pages, total_chunks, error, created_at) "
            "VALUES (?, ?, 'pending', NULL, NULL, NULL, ?)",
            (doc_id, filename, created),
        )

    def set_status(
        self,
        doc_id: str,
        status: str,
        *,
        total_pages: int | None = None,
        total_chunks: int | None = None,
        error: str | None = None,
    ) -> None:
        self._run(
            "UPDATE documents SET status = ?, "
            "total_pages = COALESCE(?, total_pages), "
            "total_chunks = COALESCE(?, total_chunks), "
            "error = ? WHERE id = ?",
            (status, total_pages, total_chunks, error, doc_id),
        )

    def get(self, doc_id: str) -> DocumentInfo | None:
        rows = self._run("SELECT * FROM documents WHERE id = ?", (doc_id,))
        return DocumentInfo(**dict(rows[0])) if rows else None

    def list(self) -> list[DocumentInfo]:
        rows = self._run("SELECT * FROM documents ORDER BY created_at DESC, rowid DESC")
        return [DocumentInfo(**dict(row)) for row in rows]

    def delete(self, doc_id: str) -> None:
        self._run("DELETE FROM documents WHERE id = ?", (doc_id,))

    def fail_interrupted(self) -> None:
        """After a restart, nothing can still be processing: mark those documents failed."""
        self._run(
            "UPDATE documents SET status = 'failed', "
            "error = 'Processing was interrupted by a server restart. Upload the file again.' "
            "WHERE status IN ('pending', 'processing')"
        )
