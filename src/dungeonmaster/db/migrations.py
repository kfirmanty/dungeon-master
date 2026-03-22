"""
Game-specific database migrations.

Extends the bookworm schema with:
- content_type column on chunks (for filtered RAG retrieval)
- game_sessions table (JSONB for character state)
- game_log table (append-only narrative log)

All statements are idempotent (IF NOT EXISTS / IF EXISTS).
"""

import psycopg


def run_game_migrations(conn: psycopg.Connection) -> None:
    """Create game-specific tables and extend the chunks table."""
    with conn.cursor() as cur:
        # --- Extend existing chunks table with content_type ---
        # This enables filtered retrieval: rules vs adventure vs monsters
        cur.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'chunks' AND column_name = 'content_type'
                ) THEN
                    ALTER TABLE chunks ADD COLUMN content_type TEXT DEFAULT 'book';
                END IF;
            END $$
        """)

        cur.execute("""
            CREATE INDEX IF NOT EXISTS chunks_content_type_idx ON chunks(content_type)
        """)

        # --- Game sessions ---
        # JSONB columns for deeply nested character data (system-agnostic).
        # Each rules engine defines its own character schema; we don't
        # impose a relational structure on it.
        cur.execute("""
            CREATE TABLE IF NOT EXISTS game_sessions (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name TEXT NOT NULL,
                rules_system TEXT NOT NULL DEFAULT 'dnd5e',
                player_character JSONB NOT NULL,
                companions JSONB NOT NULL DEFAULT '[]',
                current_scene JSONB NOT NULL DEFAULT '{}',
                adventure_book_id UUID REFERENCES books(id),
                rulebook_book_id UUID REFERENCES books(id),
                turn_count INTEGER DEFAULT 0,
                in_combat BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMPTZ DEFAULT now(),
                updated_at TIMESTAMPTZ DEFAULT now()
            )
        """)

        # --- Game log (append-only) ---
        # Relational for efficient range queries when assembling
        # conversation history for the AI context window.
        cur.execute("""
            CREATE TABLE IF NOT EXISTS game_log (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                session_id UUID NOT NULL REFERENCES game_sessions(id) ON DELETE CASCADE,
                sequence_number INTEGER NOT NULL,
                actor TEXT NOT NULL,
                content TEXT NOT NULL,
                action_type TEXT NOT NULL DEFAULT 'narration',
                dice_results JSONB DEFAULT '[]',
                metadata JSONB DEFAULT '{}',
                created_at TIMESTAMPTZ DEFAULT now(),
                UNIQUE(session_id, sequence_number)
            )
        """)

        cur.execute("""
            CREATE INDEX IF NOT EXISTS game_log_session_idx
            ON game_log(session_id, sequence_number)
        """)

    conn.commit()
