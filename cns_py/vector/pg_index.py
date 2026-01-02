"""
Postgres pgvector Vector Index Backend.
Uses psycopg and pgvector extension.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from cns_py.storage.db import get_conn

from .index import ScoredResult, Vector, VectorIndex

logger = logging.getLogger(__name__)


class PgVectorIndex(VectorIndex):
    def __init__(self, table_name: str = "vector_store", dim: int = 384):
        self.table_name = table_name
        self.dim = dim
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        """Ensure the table and extension exist."""
        with get_conn() as conn:
            # Note: Extension creation requires superuser usually, but db.py tries it too.
            # We assume it's there or we fail gracefully if we can't create it.
            # However, for this slice, we'll try to create table.
            conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    id TEXT PRIMARY KEY,
                    embedding vector({self.dim}),
                    metadata JSONB
                )
            """
            )

    def upsert(self, id: str, vector: Vector, metadata: Optional[Dict[str, Any]] = None) -> None:
        if len(vector) != self.dim:
            raise ValueError(f"Vector dimension mismatch. Expected {self.dim}, got {len(vector)}")

        with get_conn() as conn:
            conn.execute(
                f"""
                INSERT INTO {self.table_name} (id, embedding, metadata)
                VALUES (%s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    embedding = EXCLUDED.embedding,
                    metadata = EXCLUDED.metadata
                """,
                (id, vector, metadata),
            )

    def delete(self, id: str) -> None:
        with get_conn() as conn:
            conn.execute(f"DELETE FROM {self.table_name} WHERE id = %s", (id,))

    def query(
        self, vector: Vector, k: int = 10, filter: Optional[Dict[str, Any]] = None
    ) -> List[ScoredResult]:
        if len(vector) != self.dim:
            raise ValueError(f"Vector dimension mismatch. Expected {self.dim}, got {len(vector)}")

        # Cosine distance operator is <=>
        # We want Cosine Similarity = 1 - Cosine Distance
        # Deterministic tie-break: dist ASC, id ASC

        # Filter support (metadata) - simplistic JSONB containment
        where_clause = ""
        params = [vector]
        if filter:
            where_clause = "WHERE metadata @> %s"
            params.append(filter)

        params.append(k)  # Limit

        query_sql = f"""
            SELECT id, (embedding <=> %s) as dist
            FROM {self.table_name}
            {where_clause}
            ORDER BY dist ASC, id ASC
            LIMIT %s
        """

        with get_conn() as conn:
            cursor = conn.execute(query_sql, params)
            results = []
            for row in cursor.fetchall():
                doc_id, dist = row
                # Convert distance back to similarity (approx)
                # dist ranges 0..2 for cosine. sim = 1 - dist.
                sim = 1.0 - float(dist)
                results.append((doc_id, sim))
            return results

    def bulk_load(self, items: List[Tuple[str, Vector, Optional[Dict[str, Any]]]]) -> None:
        if not items:
            return

        with get_conn() as conn:
            with conn.cursor() as cur:
                with cur.copy(
                    f"COPY {self.table_name} (id, embedding, metadata) FROM STDIN"
                ) as copy:
                    for id, vector, meta in items:
                        if len(vector) != self.dim:
                            continue  # Skip bad dims or raise? Skip for robustness in bulk?
                        copy.write_row((id, vector, meta))

    def save(self, path: str) -> None:
        """
        Persistence for PgVectorIndex is managed by PostgreSQL.
        """
        raise NotImplementedError("PgVectorIndex persistence is managed by the database backend.")

    def load(self, path: str) -> None:
        """
        Persistence for PgVectorIndex is managed by PostgreSQL.
        """
        raise NotImplementedError("PgVectorIndex persistence is managed by the database backend.")
