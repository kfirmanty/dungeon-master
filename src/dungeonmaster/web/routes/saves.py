"""
Save/load game state routes.
"""

import asyncio
from uuid import UUID

from fastapi import APIRouter

from dungeonmaster.config import get_game_settings
from dungeonmaster.game.session import load_game, save_game
from dungeonmaster.db import repository as repo
from dungeonmaster.web.schemas import ErrorMessage

from bookworm.db.connection import get_connection, register_vector_type
from bookworm.db.migrations import run_migrations
from dungeonmaster.db.migrations import run_game_migrations

router = APIRouter(tags=["saves"])


def _get_conn():
    settings = get_game_settings()
    conn = get_connection(settings.database_url)
    run_migrations(conn)
    run_game_migrations(conn)
    register_vector_type(conn)
    return conn


@router.get("/saves")
async def list_saves():
    """List all saved game sessions."""
    conn = await asyncio.to_thread(_get_conn)
    try:
        sessions = await asyncio.to_thread(repo.list_sessions, conn)
        return [
            {
                "id": str(s["id"]),
                "name": s["name"],
                "rules_system": s["rules_system"],
                "character_name": s.get("character_name"),
                "character_class": s.get("character_class"),
                "turn_count": s["turn_count"],
                "updated_at": str(s["updated_at"]),
            }
            for s in sessions
        ]
    finally:
        conn.close()


@router.post("/saves/{session_id}")
async def save_current_game(session_id: str):
    """Save the current game state."""
    conn = await asyncio.to_thread(_get_conn)
    try:
        session = await asyncio.to_thread(load_game, conn, UUID(session_id))
        if session is None:
            return ErrorMessage(message="Session not found").model_dump()

        await asyncio.to_thread(save_game, conn, session)
        return {"status": "saved", "session_id": session_id}
    finally:
        conn.close()
