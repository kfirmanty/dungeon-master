"""
Ingestion pipeline — orchestrates the full book-to-vectors flow.

    .txt File → Reader → Chunker → Embedding Model → PostgreSQL (pgvector)

This is the "write" side of RAG: preparing a book so it can be searched later.
"""

import time
from pathlib import Path

import psycopg

from bookworm.config import Settings
from bookworm.embeddings.base import EmbeddingProvider
from bookworm.ingestion.reader import read_book
from bookworm.ingestion.chunker import chunk_text
from bookworm.db import repository
from bookworm.models import BookMetadata


# How many chunks to embed in one batch. Larger batches are faster (GPU
# parallelism) but use more memory. 32 is a safe default for CPU inference.
EMBEDDING_BATCH_SIZE = 32


def ingest_book(
    file_path: Path,
    title: str,
    settings: Settings,
    conn: psycopg.Connection,
    embedding_provider: EmbeddingProvider,
) -> BookMetadata:
    """Ingest a book: read → chunk → embed → store.

    This is the core "indexing" operation in any RAG system. After ingestion,
    the book's content is searchable via vector similarity.
    """
    start_time = time.time()

    # Step 1: Read the book and detect chapters
    print(f"Reading '{file_path.name}'...")
    full_text, chapters = read_book(file_path)
    print(f"  Found {len(chapters)} chapter(s)")

    # Step 2: Split into chunks
    chunks = chunk_text(
        chapters,
        full_text,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )
    print(f"  Created {len(chunks)} chunks (size={settings.chunk_size}, overlap={settings.chunk_overlap})")

    if not chunks:
        raise ValueError("No chunks were created. Is the file empty?")

    # Step 3: Generate embeddings in batches
    # Batching prevents memory issues with large books (thousands of chunks).
    # Each batch sends N texts through the transformer in one forward pass,
    # which is faster than embedding one at a time due to GPU/CPU parallelism.
    all_embeddings: list[list[float]] = []
    total_batches = (len(chunks) + EMBEDDING_BATCH_SIZE - 1) // EMBEDDING_BATCH_SIZE

    for i in range(0, len(chunks), EMBEDDING_BATCH_SIZE):
        batch = chunks[i : i + EMBEDDING_BATCH_SIZE]
        batch_num = (i // EMBEDDING_BATCH_SIZE) + 1
        print(f"  Embedding batch {batch_num}/{total_batches}...")
        batch_embeddings = embedding_provider.embed_texts([c.content for c in batch])
        all_embeddings.extend(batch_embeddings)

    # Step 4: Store in database
    print("  Storing in database...")
    book_id = repository.insert_book(conn, title, str(file_path))
    repository.insert_chunks(conn, book_id, chunks, all_embeddings)

    elapsed = time.time() - start_time
    print(f"\nIngested '{title}': {len(chapters)} chapters, {len(chunks)} chunks in {elapsed:.1f}s")

    return BookMetadata(
        id=book_id,
        title=title,
        file_path=str(file_path),
        ingested_at=None,  # not critical for the return value
    )
