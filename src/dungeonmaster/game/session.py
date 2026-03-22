"""
Game session lifecycle — create, load, save game sessions.

Bridges the in-memory GameSession model with database persistence.
"""

from uuid import UUID

import psycopg

from dungeonmaster.db import repository as repo
from dungeonmaster.models import GameSession, NarrativeEntry, Scene, SceneType
from dungeonmaster.rules.base import RulesEngine


def create_new_game(
    conn: psycopg.Connection,
    engine: RulesEngine,
    name: str,
    character_choices: dict,
    companion_choices: list[dict] | None = None,
    adventure_book_id: UUID | None = None,
    rulebook_book_id: UUID | None = None,
) -> GameSession:
    """Create a new game session with a freshly created character.

    Args:
        conn: Database connection
        engine: The active RulesEngine (creates characters)
        name: Session name
        character_choices: Player's character creation choices
        companion_choices: Optional companion creation choices
        adventure_book_id: ID of ingested adventure content
        rulebook_book_id: ID of ingested rulebook content
    """
    # Create player character
    player_char = engine.create_character(character_choices)

    # Create companions
    companions = []
    if companion_choices:
        for choices in companion_choices:
            choices["is_player"] = False
            companions.append(engine.create_character(choices))

    # Persist to database
    session_id = repo.create_session(
        conn=conn,
        name=name,
        rules_system=getattr(engine, "_system_id", "dnd5e"),
        player_character=player_char,
        companions=companions,
        adventure_book_id=adventure_book_id,
        rulebook_book_id=rulebook_book_id,
    )

    # Build in-memory session
    session = GameSession(
        id=session_id,
        name=name,
        player_character=player_char,
        companions=companions,
        adventure_book_id=adventure_book_id,
        rulebook_book_id=rulebook_book_id,
        current_scene=Scene(
            scene_type=SceneType.EXPLORATION,
            description="The adventure begins...",
            location="Starting location",
        ),
    )

    return session


def load_game(conn: psycopg.Connection, session_id: UUID) -> GameSession | None:
    """Load a game session from the database."""
    data = repo.load_session(conn, session_id)
    if data is None:
        return None

    # Load narrative history
    history = repo.get_log_entries(conn, session_id, limit=100)

    # Reconstruct scene
    scene_data = data.get("current_scene", {})
    scene = Scene(
        scene_type=SceneType(scene_data.get("scene_type", "exploration")),
        description=scene_data.get("description", ""),
        location=scene_data.get("location", ""),
        npcs_present=scene_data.get("npcs_present", []),
        enemies=scene_data.get("enemies", []),
    )

    return GameSession(
        id=data["id"],
        name=data["name"],
        rules_system=data["rules_system"],
        player_character=data["player_character"],
        companions=data["companions"],
        current_scene=scene,
        narrative_history=history,
        adventure_book_id=data["adventure_book_id"],
        rulebook_book_id=data["rulebook_book_id"],
        turn_count=data["turn_count"],
        in_combat=data["in_combat"],
        created_at=data["created_at"],
        updated_at=data["updated_at"],
    )


def save_game(conn: psycopg.Connection, session: GameSession) -> None:
    """Persist the current game session state to the database."""
    scene_dict = {
        "scene_type": session.current_scene.scene_type.value,
        "description": session.current_scene.description,
        "location": session.current_scene.location,
        "npcs_present": session.current_scene.npcs_present,
        "enemies": session.current_scene.enemies,
    }

    repo.save_session(
        conn=conn,
        session_id=session.id,
        player_character=session.player_character,
        companions=session.companions,
        current_scene=scene_dict,
        turn_count=session.turn_count,
        in_combat=session.in_combat,
    )


def append_entries(
    conn: psycopg.Connection,
    session: GameSession,
    entries: list[NarrativeEntry],
) -> None:
    """Append narrative entries to both the session's history and the database."""
    for entry in entries:
        session.narrative_history.append(entry)
        repo.append_log_entry(conn, session.id, entry)
    session.turn_count += 1
