from __future__ import annotations

import json
import hashlib
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

    def save_index(self, index: dict, source_url: str | None = None) -> dict:
        """Replace one repository snapshot atomically and return persisted counts."""
        root = index.get("root", "")
        with self.connection.transaction():
            with self.connection.cursor() as cursor:
                cursor.execute(
                    """INSERT INTO repositories (source_url, local_path)
                    VALUES (%s, %s)
                    ON CONFLICT (local_path) DO UPDATE SET source_url = EXCLUDED.source_url, updated_at = now()
                    RETURNING id""",
                    (source_url, root),
                )
                repository_id = cursor.fetchone()[0]
                cursor.execute("DELETE FROM repository_edges WHERE repository_id = %s", (repository_id,))
                cursor.execute("DELETE FROM evidence_documents WHERE repository_id = %s", (repository_id,))
                cursor.execute("DELETE FROM files WHERE repository_id = %s", (repository_id,))

                file_ids = {}
                for path in index.get("files", []):
                    content = "\n".join(doc["text"] for doc in index.get("documents", []) if doc.get("path") == path)
                    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
                    cursor.execute(
                        """INSERT INTO files (repository_id, path, language, content_sha256, line_count)
                        VALUES (%s, %s, %s, %s, %s) RETURNING id""",
                        (repository_id, path, Path(path).suffix.lstrip("."), digest, len(content.splitlines())),
                    )
                    file_ids[path] = cursor.fetchone()[0]

                chunk_count = 0
                evidence_count = 0
                for document in index.get("documents", []):
                    path = document.get("path", "")
                    if path in file_ids:
                        cursor.execute(
                            """INSERT INTO chunks
                            (file_id, symbol, kind, start_line, end_line, content, token_count)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                            (file_ids[path], document.get("symbol", path), document.get("kind", "text"), document.get("start", 1), document.get("end", 1), document.get("text", ""), len(document.get("text", "").split())),
                        )
                        chunk_count += 1
                    elif path.startswith(".git/") or path.startswith(".github/"):
                        cursor.execute(
                            """INSERT INTO evidence_documents
                            (repository_id, document_type, external_id, title, content, metadata)
                            VALUES (%s, %s, %s, %s, %s, %s::jsonb)""",
                            (repository_id, document.get("kind", "document"), document.get("id"), document.get("symbol", path), document.get("text", ""), json.dumps(document.get("metadata", {}))),
                        )
                        evidence_count += 1

                edge_count = 0
                for edge in index.get("edges", []):
                    if edge.get("source") not in file_ids or edge.get("target") not in file_ids:
                        continue
                    cursor.execute(
                        """INSERT INTO repository_edges
                        (repository_id, source_file_id, target_file_id, edge_type)
                        VALUES (%s, %s, %s, %s)""",
                        (repository_id, file_ids[edge["source"]], file_ids[edge["target"]], edge.get("kind", "related")),
                    )
                    edge_count += 1
        return {"repository_id": repository_id, "files": len(file_ids), "chunks": chunk_count, "edges": edge_count, "evidence": evidence_count}

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
