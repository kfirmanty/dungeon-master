"""
Game-specific database operations — raw SQL, same pattern as bookworm.

Handles:
- Game session CRUD (create, load, save, list, delete)
- Game log append and retrieval
- Content-type filtered vector search for RAG
"""

import json
from datetime import datetime
from uuid import UUID

import psycopg

from dungeonmaster.models import NarrativeEntry


# ---------------------------------------------------------------------------
# Game Sessions
# ---------------------------------------------------------------------------


def create_session(
    conn: psycopg.Connection,
    name: str,
    rules_system: str,
    player_character: dict,
    companions: list[dict],
    adventure_book_id: UUID | None = None,
    rulebook_book_id: UUID | None = None,
) -> UUID:
    """Create a new game session and return its ID."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO game_sessions
                (name, rules_system, player_character, companions,
                 current_scene, adventure_book_id, rulebook_book_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                name,
                rules_system,
                json.dumps(player_character),
                json.dumps(companions),
                json.dumps({"scene_type": "exploration", "description": "", "location": ""}),
                adventure_book_id,
                rulebook_book_id,
            ),
        )
        row = cur.fetchone()
    conn.commit()
    return row["id"]


def load_session(conn: psycopg.Connection, session_id: UUID) -> dict | None:
    """Load a game session by ID. Returns None if not found."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, name, rules_system, player_character, companions,
                   current_scene, adventure_book_id, rulebook_book_id,
                   turn_count, in_combat, created_at, updated_at
            FROM game_sessions WHERE id = %s
            """,
            (session_id,),
        )
        row = cur.fetchone()

    if row is None:
        return None

    return {
        "id": row["id"],
        "name": row["name"],
        "rules_system": row["rules_system"],
        "player_character": row["player_character"],
        "companions": row["companions"],
        "current_scene": row["current_scene"],
        "adventure_book_id": row["adventure_book_id"],
        "rulebook_book_id": row["rulebook_book_id"],
        "turn_count": row["turn_count"],
        "in_combat": row["in_combat"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def save_session(
    conn: psycopg.Connection,
    session_id: UUID,
    player_character: dict,
    companions: list[dict],
    current_scene: dict,
    turn_count: int,
    in_combat: bool,
) -> None:
    """Update an existing game session's mutable state."""
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE game_sessions
            SET player_character = %s,
                companions = %s,
                current_scene = %s,
                turn_count = %s,
                in_combat = %s,
                updated_at = now()
            WHERE id = %s
            """,
            (
                json.dumps(player_character),
                json.dumps(companions),
                json.dumps(current_scene),
                turn_count,
                in_combat,
                session_id,
            ),
        )
    conn.commit()


def list_sessions(conn: psycopg.Connection) -> list[dict]:
    """List all game sessions, most recent first."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, name, rules_system, turn_count, in_combat,
                   player_character->>'name' AS character_name,
                   player_character->>'character_class' AS character_class,
                   player_character->'hp'->>'current' AS hp_current,
                   player_character->'hp'->>'max' AS hp_max,
                   created_at, updated_at
            FROM game_sessions
            ORDER BY updated_at DESC
            """
        )
        rows = cur.fetchall()

    return [dict(row) for row in rows]


def delete_session(conn: psycopg.Connection, session_id: UUID) -> None:
    """Delete a game session and all its log entries (CASCADE)."""
    with conn.cursor() as cur:
        cur.execute("DELETE FROM game_sessions WHERE id = %s", (session_id,))
    conn.commit()


# ---------------------------------------------------------------------------
# Game Log
# ---------------------------------------------------------------------------


def append_log_entry(
    conn: psycopg.Connection,
    session_id: UUID,
    entry: NarrativeEntry,
) -> None:
    """Append a narrative entry to the game log.

    Uses a subquery to atomically compute the next sequence number,
    avoiding race conditions with concurrent inserts.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO game_log
                (session_id, sequence_number, actor, content, action_type,
                 dice_results, metadata)
            VALUES (
                %s,
                (SELECT COALESCE(MAX(sequence_number), 0) + 1 FROM game_log WHERE session_id = %s),
                %s, %s, %s, %s, %s
            )
            """,
            (
                session_id,
                session_id,
                entry.actor,
                entry.content,
                entry.action_type,
                json.dumps(entry.dice_results),
                json.dumps(entry.metadata),
            ),
        )
    conn.commit()


def get_log_entries(
    conn: psycopg.Connection,
    session_id: UUID,
    limit: int = 50,
    offset: int = 0,
) -> list[NarrativeEntry]:
    """Get game log entries, most recent first."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT actor, content, action_type, dice_results, metadata, created_at
            FROM game_log
            WHERE session_id = %s
            ORDER BY sequence_number DESC
            LIMIT %s OFFSET %s
            """,
            (session_id, limit, offset),
        )
        rows = cur.fetchall()

    # Reverse to get chronological order
    return [
        NarrativeEntry(
            actor=row["actor"],
            content=row["content"],
            action_type=row["action_type"],
            dice_results=row["dice_results"] if row["dice_results"] else [],
            metadata=row["metadata"] if row["metadata"] else {},
            timestamp=row["created_at"],
        )
        for row in reversed(rows)
    ]


def get_recent_log(
    conn: psycopg.Connection,
    session_id: UUID,
    count: int = 10,
) -> list[NarrativeEntry]:
    """Get the N most recent log entries in chronological order."""
    return get_log_entries(conn, session_id, limit=count)


# ---------------------------------------------------------------------------
# Content-Type Filtered Vector Search
# ---------------------------------------------------------------------------


def search_by_content_type(
    conn: psycopg.Connection,
    query_embedding: list[float],
    content_types: list[str],
    top_k: int = 5,
    book_id: UUID | None = None,
) -> list[dict]:
    """Vector similarity search filtered by content_type.

    Used by the AI DM to retrieve:
    - Rules: content_types=["rule"] — for mechanical lookups
    - Adventure: content_types=["encounter", "npc", "monster", "lore"] — for DM context
    """
    sql = """
        SELECT
            c.content,
            c.chapter_title,
            c.chapter_number,
            c.chunk_index,
            c.content_type,
            1 - (c.embedding <=> %s::vector) AS similarity_score
        FROM chunks c
        WHERE c.content_type = ANY(%s)
          AND (%s::uuid IS NULL OR c.book_id = %s::uuid)
        ORDER BY c.embedding <=> %s::vector
        LIMIT %s
    """

    with conn.cursor() as cur:
        cur.execute(
            sql,
            (query_embedding, content_types, book_id, book_id, query_embedding, top_k),
        )
        rows = cur.fetchall()

    return [
        {
            "content": row["content"],
            "chapter_title": row["chapter_title"],
            "chapter_number": row["chapter_number"],
            "chunk_index": row["chunk_index"],
            "content_type": row["content_type"],
            "similarity_score": float(row["similarity_score"]),
        }
        for row in rows
    ]
