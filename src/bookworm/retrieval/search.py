"""
Vector similarity search — thin wrapper around the repository.

This module exists to keep the retrieval pipeline focused on orchestration
rather than database details.
"""

from uuid import UUID

import psycopg

from bookworm.db import repository
from bookworm.models import ChunkResult


def find_similar_chunks(
    conn: psycopg.Connection,
    query_embedding: list[float],
    top_k: int = 5,
    book_id: UUID | None = None,
) -> list[ChunkResult]:
    """Search for chunks most similar to the query embedding.

    Delegates to repository.search_similar() which uses pgvector's
    cosine distance operator (<=>). Results are ordered by similarity
    (highest first).
    """
    return repository.search_similar(conn, query_embedding, top_k, book_id)
