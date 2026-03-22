"""
Database repository — CRUD operations using raw SQL.

No ORM here. Raw SQL is more educational and gives you full control over the
queries. You can see exactly what's being sent to PostgreSQL, which helps when
debugging performance or understanding pgvector's operators.
"""

from uuid import UUID

import psycopg
from pgvector.psycopg import register_vector

from bookworm.models import BookMetadata, Chunk, ChunkResult


def insert_book(conn: psycopg.Connection, title: str, file_path: str) -> UUID:
    """Insert a book record and return its generated UUID."""
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO books (title, file_path) VALUES (%s, %s) RETURNING id",
            (title, file_path),
        )
        row = cur.fetchone()
        conn.commit()
        return row["id"]


def insert_chunks(
    conn: psycopg.Connection,
    book_id: UUID,
    chunks: list[Chunk],
    embeddings: list[list[float]],
) -> None:
    """Batch-insert chunks with their embedding vectors.

    We use executemany() which sends one INSERT per chunk but in a single
    transaction. For larger datasets, COPY would be faster, but executemany
    is simpler and sufficient for Phase 1.
    """
    sql = """
        INSERT INTO chunks
            (book_id, content, chapter_title, chapter_number,
             chunk_index, start_char, end_char, embedding)
        VALUES
            (%s, %s, %s, %s, %s, %s, %s, %s)
    """

    rows = [
        (
            book_id,
            chunk.content,
            chunk.chapter_title,
            chunk.chapter_number,
            chunk.chunk_index,
            chunk.start_char,
            chunk.end_char,
            embedding,
        )
        for chunk, embedding in zip(chunks, embeddings)
    ]

    with conn.cursor() as cur:
        cur.executemany(sql, rows)
    conn.commit()


def search_similar(
    conn: psycopg.Connection,
    query_embedding: list[float],
    top_k: int = 5,
    book_id: UUID | None = None,
) -> list[ChunkResult]:
    """Find the most similar chunks using pgvector's cosine distance.

    THE VECTOR SEARCH QUERY:

    pgvector's <=> operator computes cosine DISTANCE = 1 - cosine_similarity.
    ORDER BY ... <=> ... ASC finds nearest neighbors (smallest distance = most similar).

    We convert back to similarity (1 - distance) for the user-facing score
    because "0.92 similarity" is more intuitive than "0.08 distance".

    The IVFFlat index makes this sublinear: instead of comparing the query
    against all N vectors (O(N)), it only checks the nearest clusters.
    """
    sql = """
        SELECT
            c.content,
            c.chapter_title,
            c.chapter_number,
            c.chunk_index,
            1 - (c.embedding <=> %s::vector) AS similarity_score
        FROM chunks c
        WHERE (%s::uuid IS NULL OR c.book_id = %s::uuid)
        ORDER BY c.embedding <=> %s::vector
        LIMIT %s
    """

    with conn.cursor() as cur:
        cur.execute(sql, (query_embedding, book_id, book_id, query_embedding, top_k))
        rows = cur.fetchall()

    return [
        ChunkResult(
            content=row["content"],
            chapter_title=row["chapter_title"],
            chapter_number=row["chapter_number"],
            chunk_index=row["chunk_index"],
            similarity_score=float(row["similarity_score"]),
        )
        for row in rows
    ]


def list_books(conn: psycopg.Connection) -> list[BookMetadata]:
    """List all ingested books, ordered by ingestion time."""
    with conn.cursor() as cur:
        cur.execute("SELECT id, title, file_path, ingested_at FROM books ORDER BY ingested_at DESC")
        rows = cur.fetchall()

    return [
        BookMetadata(
            id=row["id"],
            title=row["title"],
            file_path=row["file_path"],
            ingested_at=row["ingested_at"],
        )
        for row in rows
    ]


def get_book_by_title(conn: psycopg.Connection, title: str) -> BookMetadata | None:
    """Find a book by its title (case-insensitive)."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, title, file_path, ingested_at FROM books WHERE lower(title) = lower(%s)",
            (title,),
        )
        row = cur.fetchone()

    if row is None:
        return None

    return BookMetadata(
        id=row["id"],
        title=row["title"],
        file_path=row["file_path"],
        ingested_at=row["ingested_at"],
    )


def get_latest_book(conn: psycopg.Connection) -> BookMetadata | None:
    """Get the most recently ingested book."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, title, file_path, ingested_at FROM books ORDER BY ingested_at DESC LIMIT 1"
        )
        row = cur.fetchone()

    if row is None:
        return None

    return BookMetadata(
        id=row["id"],
        title=row["title"],
        file_path=row["file_path"],
        ingested_at=row["ingested_at"],
    )


def delete_book(conn: psycopg.Connection, book_id: UUID) -> None:
    """Delete a book and all its chunks (CASCADE handles chunk deletion)."""
    with conn.cursor() as cur:
        cur.execute("DELETE FROM books WHERE id = %s", (book_id,))
    conn.commit()
