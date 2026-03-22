"""
Database migrations — create tables and extensions.

All statements use IF NOT EXISTS / IF EXISTS to be idempotent: you can run
migrations multiple times safely without errors or data loss.
"""

import psycopg


def run_migrations(conn: psycopg.Connection) -> None:
    """Create the pgvector extension and application tables.

    HOW PGVECTOR WORKS:

    PostgreSQL doesn't natively understand vectors. The pgvector extension adds:

    1. A `vector(N)` column type — stores N float32 values per row, packed
       efficiently in the table's storage.

    2. Distance operators:
       <=>  cosine distance    (1 - cosine_similarity)  — most common for text
       <->  L2 (Euclidean) distance
       <#>  negative inner product

    3. Index types for approximate nearest neighbor (ANN) search:
       IVFFlat — clusters vectors, searches only nearby clusters
       HNSW    — graph-based, generally faster but uses more memory

    Without an index, every query scans ALL vectors (exact search).
    For small datasets (<10K rows), exact search is fast enough.
    The index becomes important at scale.
    """
    with conn.cursor() as cur:
        # Enable the vector extension (ships with the pgvector Docker image)
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector")

        # Books table: one row per ingested book
        cur.execute("""
            CREATE TABLE IF NOT EXISTS books (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                title TEXT NOT NULL,
                file_path TEXT NOT NULL,
                ingested_at TIMESTAMPTZ DEFAULT now()
            )
        """)

        # Chunks table: one row per text segment, with its embedding vector
        # ON DELETE CASCADE means deleting a book automatically deletes all its chunks
        cur.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                book_id UUID NOT NULL REFERENCES books(id) ON DELETE CASCADE,
                content TEXT NOT NULL,
                chapter_title TEXT,
                chapter_number INTEGER,
                chunk_index INTEGER NOT NULL,
                start_char INTEGER NOT NULL,
                end_char INTEGER NOT NULL,
                embedding vector(384) NOT NULL,
                created_at TIMESTAMPTZ DEFAULT now()
            )
        """)

        # IVFFlat INDEX for approximate nearest neighbor search
        #
        # How IVFFlat works:
        # 1. TRAINING: k-means clusters all existing vectors into `lists` groups.
        #    Each cluster has a centroid (average position).
        # 2. QUERYING: Find the nearest cluster centroid(s) to the query vector,
        #    then only search vectors within those clusters.
        # 3. TRADE-OFF: Faster than exact search (skip distant clusters) but may
        #    miss some true nearest neighbors in boundary regions.
        #
        # lists = 100: Rule of thumb is sqrt(num_rows) for up to 1M rows.
        # 100 works for up to ~10K chunks. For larger datasets, increase this
        # or switch to HNSW indexes which don't need this tuning.
        #
        # vector_cosine_ops: tells pgvector to use cosine distance for this index.
        #
        # NOTE: IVFFlat indexes are built from existing data using k-means.
        # On an empty table, the index exists but is not effective until you
        # INSERT data and REINDEX. For Phase 1's small datasets, PostgreSQL
        # may choose sequential scan anyway (faster for <1000 rows).
        cur.execute("""
            CREATE INDEX IF NOT EXISTS chunks_embedding_idx
            ON chunks USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100)
        """)

    conn.commit()
