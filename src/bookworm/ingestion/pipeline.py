"""
Ingestion pipeline — orchestrates the full book-to-vectors flow.

    .txt File → Reader → Chunker → Embedding Model → PostgreSQL (pgvector)

This is the "write" side of RAG: preparing a book so it can be searched later.
"""

import logging
import time
from pathlib import Path
from typing import Callable

import psycopg

from bookworm.config import Settings
from bookworm.embeddings.base import EmbeddingProvider
from bookworm.ingestion.reader import read_book
from bookworm.ingestion.chunker import chunk_text
from bookworm.db import repository
from bookworm.models import BookMetadata

logger = logging.getLogger(__name__)

# How many chunks to embed in one batch. Larger batches are faster (GPU
# parallelism) but use more memory. 32 is a safe default for CPU inference.
EMBEDDING_BATCH_SIZE = 32


def ingest_book(
    file_path: Path,
    title: str,
    settings: Settings,
    conn: psycopg.Connection,
    embedding_provider: EmbeddingProvider,
    on_progress: Callable[[dict], None] | None = None,
) -> BookMetadata:
    """Ingest a book: read → chunk → embed → store.

    This is the core "indexing" operation in any RAG system. After ingestion,
    the book's content is searchable via vector similarity.

    on_progress: Optional callback receiving {"status": str, "message": str, "progress": float}
    """
    start_time = time.time()

    def _progress(status: str, message: str, progress: float = 0.0):
        logger.info(message)
        if on_progress:
            on_progress({"status": status, "message": message, "progress": progress})

    # Step 1: Read the book and detect chapters
    _progress("reading", f"Reading '{file_path.name}'...")
    full_text, chapters = read_book(file_path)
    _progress("reading", f"Found {len(chapters)} chapter(s)", 0.1)

    # Step 2: Split into chunks
    chunks = chunk_text(
        chapters,
        full_text,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )
    _progress("chunking", f"Created {len(chunks)} chunks (size={settings.chunk_size}, overlap={settings.chunk_overlap})", 0.2)

    if not chunks:
        raise ValueError("No chunks were created. Is the file empty?")

    # Step 3: Generate embeddings in batches
    all_embeddings: list[list[float]] = []
    total_batches = (len(chunks) + EMBEDDING_BATCH_SIZE - 1) // EMBEDDING_BATCH_SIZE

    for i in range(0, len(chunks), EMBEDDING_BATCH_SIZE):
        batch = chunks[i : i + EMBEDDING_BATCH_SIZE]
        batch_num = (i // EMBEDDING_BATCH_SIZE) + 1
        embed_progress = 0.2 + (batch_num / total_batches) * 0.6  # 20%-80% of total
        _progress("embedding", f"Embedding batch {batch_num}/{total_batches}...", embed_progress)
        batch_embeddings = embedding_provider.embed_texts([c.content for c in batch])
        all_embeddings.extend(batch_embeddings)

    # Step 4: Store in database
    _progress("storing", "Storing in database...", 0.85)
    book_id = repository.insert_book(conn, title, str(file_path))
    repository.insert_chunks(conn, book_id, chunks, all_embeddings)

    elapsed = time.time() - start_time
    _progress("complete", f"Ingested '{title}': {len(chapters)} chapters, {len(chunks)} chunks in {elapsed:.1f}s", 1.0)

    return BookMetadata(
        id=book_id,
        title=title,
        file_path=str(file_path),
        ingested_at=None,
    )
