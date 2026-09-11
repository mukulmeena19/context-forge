from __future__ import annotations

import json
from pathlib import Path


class PostgresStore:
    """Small optional adapter; the retrieval engine remains usable without a DB."""

    def __init__(self, dsn: str, schema_path: str | Path | None = None):
        try:
            import psycopg
        except ImportError as error:
            raise RuntimeError("Install psycopg[binary] to use PostgreSQL storage.") from error
        self.connection = psycopg.connect(dsn)
        self.schema_path = Path(schema_path or Path(__file__).with_name("schema.sql"))

    def initialize(self) -> None:
        self.connection.execute(self.schema_path.read_text(encoding="utf-8"))
        self.connection.commit()

    def save_documents(self, repository_id: int, documents: list[dict]) -> int:
        with self.connection.cursor() as cursor:
            for document in documents:
                cursor.execute(
                    """INSERT INTO evidence_documents
                    (repository_id, document_type, external_id, title, content, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s::jsonb)
                    """,
                    (repository_id, document.get("kind", "document"), document.get("id"), document.get("symbol", document.get("path", "")), document.get("text", ""), json.dumps(document.get("metadata", {}))),
                )
        self.connection.commit()
        return len(documents)

    def close(self) -> None:
        self.connection.close()
