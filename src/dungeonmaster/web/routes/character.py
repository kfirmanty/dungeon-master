"""
Character management routes — creation choices and character sheet.
"""

import asyncio
from uuid import UUID

from fastapi import APIRouter

from dungeonmaster.config import get_game_settings
from dungeonmaster.game.session import load_game
from dungeonmaster.rules.base import get_engine
from dungeonmaster.rules.dnd5e.engine import DnD5eEngine  # registers on import
from dungeonmaster.web.schemas import ErrorMessage

from bookworm.db.connection import get_connection, register_vector_type
from bookworm.db.migrations import run_migrations
from dungeonmaster.db.migrations import run_game_migrations

router = APIRouter(tags=["character"])


def _get_conn():
    settings = get_game_settings()
    conn = get_connection(settings.database_url)
    run_migrations(conn)
    run_game_migrations(conn)
    register_vector_type(conn)
    return conn


@router.get("/game/{session_id}/character")
async def get_character(session_id: str):
    """Get the player character sheet."""
    conn = await asyncio.to_thread(_get_conn)
    try:
        session = await asyncio.to_thread(load_game, conn, UUID(session_id))
        if session is None:
            return ErrorMessage(message="Session not found").model_dump()

        engine = get_engine(session.rules_system)
        summary = engine.get_character_summary(session.player_character)

        return {
            "character": session.player_character,
            "summary": summary,
            "companions": [
                {
                    "character": c,
                    "summary": engine.get_character_summary(c),
                }
                for c in session.companions
            ],
        }
    finally:
        conn.close()


@router.get("/rules/{system_id}/creation-options")
async def get_creation_options(system_id: str):
    """Get available character creation options for a rules system."""
    try:
        engine = get_engine(system_id)
    except KeyError as e:
        return ErrorMessage(message=str(e)).model_dump()

    # Return system-specific creation options
    # For D&D 5e, these come from the data module
    if system_id == "dnd5e":
        from dungeonmaster.rules.dnd5e.data import (
            CLASS_HIT_DICE,
            RACE_ABILITY_BONUSES,
            RACE_SPEED,
        )
        return {
            "system": engine.system_name,
            "races": list(RACE_ABILITY_BONUSES.keys()),
            "classes": list(CLASS_HIT_DICE.keys()),
            "race_details": {
                race: {"speed": RACE_SPEED.get(race, 30), "bonuses": bonuses}
                for race, bonuses in RACE_ABILITY_BONUSES.items()
            },
        }

    return {"system": engine.system_name, "note": "Custom creation options not yet implemented"}
