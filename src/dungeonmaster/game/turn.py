"""
Turn resolution — the core game loop that ties everything together.

Each player turn:
1. Player submits input
2. AI DM processes it (RAG → LLM → roll tags → rules engine → narration)
3. State is updated and persisted
4. If in combat, companion/enemy turns follow
"""

from typing import Iterator

from dungeonmaster.ai.dm import DungeonMasterAI
from dungeonmaster.models import GameSession, NarrativeEntry


def resolve_player_turn(
    dm: DungeonMasterAI,
    session: GameSession,
    player_input: str,
) -> list[NarrativeEntry]:
    """Resolve a single player turn (non-streaming).

    Returns all narrative entries generated during the turn.
    """
    entries = dm.process_player_input(session, player_input)

    # Update session with new entries
    for entry in entries:
        session.narrative_history.append(entry)
    session.turn_count += 1

    return entries


def resolve_player_turn_stream(
    dm: DungeonMasterAI,
    session: GameSession,
    player_input: str,
) -> Iterator[NarrativeEntry | str]:
    """Resolve a player turn with streaming (for WebSocket).

    Yields:
    - str: LLM tokens for real-time display
    - NarrativeEntry: completed entries for state tracking
    """
    entries_collected: list[NarrativeEntry] = []

    for item in dm.process_player_input_stream(session, player_input):
        if isinstance(item, NarrativeEntry):
            entries_collected.append(item)
            session.narrative_history.append(item)
        yield item

    session.turn_count += 1


def resolve_combat_round(
    dm: DungeonMasterAI,
    session: GameSession,
) -> list[NarrativeEntry]:
    """Resolve all companion and enemy turns in a combat round.

    Called after the player's turn during combat. The DM AI controls
    each companion and enemy in initiative order.
    """
    if not session.in_combat or not session.current_scene.combat_state:
        return []

    all_entries: list[NarrativeEntry] = []

    # Run companion turns
    for companion in session.companions:
        hp = companion.get("hp", {})
        if hp.get("current", 0) <= 0:
            continue  # skip unconscious companions

        entries = dm.run_companion_turn(session, companion)
        for entry in entries:
            session.narrative_history.append(entry)
        all_entries.extend(entries)

    return all_entries
