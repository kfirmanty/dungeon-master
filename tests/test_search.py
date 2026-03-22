"""Integration tests for vector search (requires running PostgreSQL with pgvector).

These tests are skipped if PostgreSQL is not available. To run them:
    docker compose up -d
    uv run pytest tests/test_search.py -v
"""

import os
import pytest
import psycopg
from uuid import UUID

# Skip entire module if Postgres is not available
try:
    _test_url = os.environ.get("DATABASE_URL", "postgresql://bookworm:bookworm@localhost:5432/bookworm")
    _conn = psycopg.connect(_test_url)
    _conn.close()
    POSTGRES_AVAILABLE = True
except Exception:
    POSTGRES_AVAILABLE = False

pytestmark = pytest.mark.skipif(not POSTGRES_AVAILABLE, reason="PostgreSQL not available")


@pytest.fixture
def db_conn():
    """Fresh database connection with pgvector support and clean test data."""
    from bookworm.db.connection import get_connection
    from bookworm.db.migrations import run_migrations

    url = os.environ.get("DATABASE_URL", "postgresql://bookworm:bookworm@localhost:5432/bookworm")
    conn = get_connection(url)
    run_migrations(conn)

    yield conn

    # Cleanup: remove test data
    with conn.cursor() as cur:
        cur.execute("DELETE FROM books WHERE title LIKE 'TEST_%'")
    conn.commit()
    conn.close()


@pytest.fixture
def sample_book(db_conn) -> UUID:
    """Insert a test book with known embeddings for deterministic search tests."""
    from bookworm.db import repository
    from bookworm.models import Chunk

    book_id = repository.insert_book(db_conn, "TEST_search_book", "/tmp/test.txt")

    # Create chunks with hand-crafted embeddings (384-dim zero vectors with a
    # few dimensions set, so we can predict similarity ordering)
    chunks = [
        Chunk(content="About cats and dogs", chapter_title="Animals", chapter_number=1,
              chunk_index=0, start_char=0, end_char=19),
        Chunk(content="About programming", chapter_title="Tech", chapter_number=2,
              chunk_index=1, start_char=20, end_char=37),
        Chunk(content="About cooking recipes", chapter_title="Food", chapter_number=3,
              chunk_index=2, start_char=38, end_char=58),
    ]

    # Simple embeddings: mostly zeros, with one "topic" dimension set to 1.0
    # This lets us test that search returns chunks in the right order
    embeddings = [
        [1.0] + [0.0] * 383,  # "animals" direction
        [0.0, 1.0] + [0.0] * 382,  # "tech" direction
        [0.0, 0.0, 1.0] + [0.0] * 381,  # "food" direction
    ]

    repository.insert_chunks(db_conn, book_id, chunks, embeddings)
    return book_id


class TestVectorSearch:
    def test_search_returns_results(self, db_conn, sample_book):
        from bookworm.db import repository

        # Query in the "animals" direction — should rank the animals chunk first
        query_embedding = [1.0] + [0.0] * 383
        results = repository.search_similar(db_conn, query_embedding, top_k=3, book_id=sample_book)

        assert len(results) == 3
        assert results[0].content == "About cats and dogs"
        assert results[0].similarity_score > 0.9

    def test_search_respects_top_k(self, db_conn, sample_book):
        from bookworm.db import repository

        query_embedding = [1.0] + [0.0] * 383
        results = repository.search_similar(db_conn, query_embedding, top_k=1, book_id=sample_book)
        assert len(results) == 1

    def test_search_filters_by_book_id(self, db_conn, sample_book):
        from bookworm.db import repository
        from uuid import uuid4

        # Search with a non-existent book_id should return no results
        query_embedding = [1.0] + [0.0] * 383
        results = repository.search_similar(db_conn, query_embedding, top_k=3, book_id=uuid4())
        assert len(results) == 0


class TestBookCRUD:
    def test_list_books(self, db_conn, sample_book):
        from bookworm.db import repository

        books = repository.list_books(db_conn)
        titles = [b.title for b in books]
        assert "TEST_search_book" in titles

    def test_delete_book_cascades(self, db_conn):
        from bookworm.db import repository
        from bookworm.models import Chunk

        book_id = repository.insert_book(db_conn, "TEST_delete_me", "/tmp/del.txt")
        chunks = [Chunk(content="x", chapter_title=None, chapter_number=None,
                        chunk_index=0, start_char=0, end_char=1)]
        embeddings = [[0.1] * 384]
        repository.insert_chunks(db_conn, book_id, chunks, embeddings)

        repository.delete_book(db_conn, book_id)

        # Book should be gone
        book = repository.get_book_by_title(db_conn, "TEST_delete_me")
        assert book is None

        # Chunks should be gone too (CASCADE)
        results = repository.search_similar(db_conn, [0.1] * 384, top_k=10, book_id=book_id)
        assert len(results) == 0
