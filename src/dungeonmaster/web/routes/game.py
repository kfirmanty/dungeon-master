"""
Game routes — WebSocket game loop + REST game management.

The WebSocket endpoint handles the real-time game interaction:
- Player sends actions
- Server streams DM narrative
- Dice rolls and state updates are pushed to the client
"""

import asyncio
import json
import tempfile
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, File, Form, UploadFile, WebSocket, WebSocketDisconnect

from bookworm.config import get_settings
from bookworm.db.connection import get_connection, register_vector_type
from bookworm.db.migrations import run_migrations
from bookworm.embeddings.local import TransformerEmbeddingProvider
from bookworm.llm.ollama import OllamaProvider

from bookworm.db import repository as bw_repo

from dungeonmaster.ai.dm import DungeonMasterAI
from dungeonmaster.config import get_game_settings
from dungeonmaster.content.converter import convert_book_to_adventure
from dungeonmaster.content.ingest import ingest_game_content
from dungeonmaster.db.migrations import run_game_migrations
from dungeonmaster.db import repository as repo
from dungeonmaster.game.session import create_new_game, load_game, save_game, append_entries
from dungeonmaster.game.turn import resolve_player_turn_stream
from dungeonmaster.models import NarrativeEntry
from dungeonmaster.rules.base import get_engine
from dungeonmaster.rules.dnd5e.engine import DnD5eEngine  # registers on import
from dungeonmaster.web.schemas import (
    DiceRollResult,
    ErrorMessage,
    GameStateUpdate,
    GameSessionSummary,
    NarrativeChunk,
    NewGameRequest,
    Thinking,
)

router = APIRouter(tags=["game"])


def _setup():
    """Initialize database, providers, and rules engine."""
    settings = get_game_settings()
    conn = get_connection(settings.database_url)
    run_migrations(conn)
    run_game_migrations(conn)
    register_vector_type(conn)

    embedding_provider = TransformerEmbeddingProvider(model_name=settings.embedding_model)
    llm_provider = OllamaProvider(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
    )
    engine = get_engine(settings.rules_system)

    return settings, conn, embedding_provider, llm_provider, engine


# ---------------------------------------------------------------------------
# REST Endpoints
# ---------------------------------------------------------------------------


@router.post("/game/new")
async def new_game(request: NewGameRequest):
    """Create a new game session."""
    settings, conn, embedding_provider, llm_provider, engine = await asyncio.to_thread(_setup)

    try:
        adventure_id = UUID(request.adventure_book_id) if request.adventure_book_id else None
        rulebook_id = UUID(request.rulebook_book_id) if request.rulebook_book_id else None

        session = await asyncio.to_thread(
            create_new_game,
            conn=conn,
            engine=engine,
            name=request.name,
            character_choices=request.character,
            companion_choices=request.companions,
            adventure_book_id=adventure_id,
            rulebook_book_id=rulebook_id,
        )

        return {
            "session_id": str(session.id),
            "character": session.player_character,
            "companions": session.companions,
        }
    finally:
        conn.close()


@router.get("/game/{session_id}")
async def get_game(session_id: str):
    """Get current game state."""
    settings, conn, _, _, _ = await asyncio.to_thread(_setup)

    try:
        session = await asyncio.to_thread(load_game, conn, UUID(session_id))
        if session is None:
            return ErrorMessage(message=f"Session {session_id} not found").model_dump()

        return {
            "session_id": str(session.id),
            "name": session.name,
            "rules_system": session.rules_system,
            "character": session.player_character,
            "companions": session.companions,
            "scene": {
                "type": session.current_scene.scene_type.value,
                "description": session.current_scene.description,
                "location": session.current_scene.location,
            },
            "turn_count": session.turn_count,
            "in_combat": session.in_combat,
            "history": [
                {"actor": e.actor, "content": e.content, "action_type": e.action_type}
                for e in session.narrative_history[-20:]
            ],
        }
    finally:
        conn.close()


@router.delete("/game/{session_id}")
async def delete_game(session_id: str):
    """Delete a game session."""
    settings, conn, _, _, _ = await asyncio.to_thread(_setup)
    try:
        await asyncio.to_thread(repo.delete_session, conn, UUID(session_id))
        return {"status": "deleted"}
    finally:
        conn.close()


@router.get("/game")
async def list_games():
    """List all game sessions."""
    settings, conn, _, _, _ = await asyncio.to_thread(_setup)
    try:
        sessions = await asyncio.to_thread(repo.list_sessions, conn)
        return [
            GameSessionSummary(
                id=str(s["id"]),
                name=s["name"],
                rules_system=s["rules_system"],
                character_name=s.get("character_name"),
                character_class=s.get("character_class"),
                hp_current=s.get("hp_current"),
                hp_max=s.get("hp_max"),
                turn_count=s["turn_count"],
                in_combat=s["in_combat"],
                created_at=str(s["created_at"]),
                updated_at=str(s["updated_at"]),
            ).model_dump()
            for s in sessions
        ]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Content Management (Adventures + Rulebooks)
# ---------------------------------------------------------------------------


@router.get("/content")
async def list_content():
    """List all ingested content (adventures, rulebooks, etc.) with chunk counts."""
    settings, conn, _, _, _ = await asyncio.to_thread(_setup)
    try:
        books = await asyncio.to_thread(bw_repo.list_books, conn)
        result = []
        for book in books:
            # Get content_type breakdown for this book
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT content_type, COUNT(*) as count
                    FROM chunks WHERE book_id = %s
                    GROUP BY content_type
                    """,
                    (book.id,),
                )
                type_counts = {row["content_type"]: row["count"] for row in cur.fetchall()}

            total_chunks = sum(type_counts.values())

            # Determine if this is an adventure, rulebook, or regular book
            has_encounters = type_counts.get("encounter", 0) > 0
            has_rules = type_counts.get("rule", 0) > 0
            has_monsters = type_counts.get("monster", 0) > 0

            if has_encounters or has_monsters:
                category = "adventure"
            elif has_rules:
                category = "rulebook"
            else:
                category = "book"

            result.append({
                "id": str(book.id),
                "title": book.title,
                "file_path": book.file_path,
                "ingested_at": str(book.ingested_at),
                "total_chunks": total_chunks,
                "content_types": type_counts,
                "category": category,
            })

        return result
    finally:
        conn.close()


@router.post("/content/ingest")
async def ingest_content(
    file: UploadFile = File(...),
    title: str = Form(...),
    content_type: str = Form("adventure"),
):
    """Ingest a text file as game content (adventure, rulebook, etc.).

    The file is chunked, embedded, and tagged with content_type for filtered retrieval.
    """
    settings, conn, embedding_provider, _, _ = await asyncio.to_thread(_setup)
    try:
        # Save uploaded file to temp location
        content = await file.read()
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="wb") as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)

        try:
            result = await asyncio.to_thread(
                ingest_game_content,
                file_path=tmp_path,
                title=title,
                content_type=content_type,
                settings=settings,
                conn=conn,
                embedding_provider=embedding_provider,
            )
            return {
                "status": "success",
                "book_id": str(result["book_id"]),
                "title": result["title"],
                "content_type_counts": result["content_type_counts"],
            }
        finally:
            tmp_path.unlink(missing_ok=True)
    except Exception as e:
        return ErrorMessage(message=f"Ingestion failed: {e}").model_dump()
    finally:
        conn.close()


@router.post("/content/convert")
async def convert_content(
    file: UploadFile = File(...),
    title: str = Form(...),
):
    """Convert a novel into a structured RPG adventure.

    Reads the book, processes each chapter through the LLM to extract
    locations, NPCs, encounters, and creatures, then ingests the result.
    This can take several minutes for a full novel.
    """
    settings, conn, embedding_provider, llm_provider, _ = await asyncio.to_thread(_setup)
    try:
        content = await file.read()
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="wb") as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)

        try:
            result = await asyncio.to_thread(
                convert_book_to_adventure,
                file_path=tmp_path,
                title=title,
                llm=llm_provider,
                settings=settings,
                conn=conn,
                embedding_provider=embedding_provider,
            )

            if "error" in result:
                return ErrorMessage(message=result["error"]).model_dump()

            return {
                "status": "complete",
                "adventure_book_id": result["adventure_book_id"],
                "title": result["title"],
                "content_type_counts": result.get("content_type_counts", {}),
                "stats": result.get("stats", {}),
                "chapters_processed": result.get("chapters_processed", 0),
            }
        finally:
            tmp_path.unlink(missing_ok=True)
    except Exception as e:
        return ErrorMessage(message=f"Conversion failed: {e}").model_dump()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# WebSocket Game Loop
# ---------------------------------------------------------------------------


@router.websocket("/game/{session_id}/play")
async def game_websocket(websocket: WebSocket, session_id: str):
    """Real-time game interaction via WebSocket."""
    await websocket.accept()

    try:
        settings, conn, embedding_provider, llm_provider, engine = await asyncio.to_thread(_setup)
    except Exception as e:
        await websocket.send_json(ErrorMessage(message=str(e), recoverable=False).model_dump())
        await websocket.close()
        return

    try:
        session = await asyncio.to_thread(load_game, conn, UUID(session_id))
        if session is None:
            await websocket.send_json(
                ErrorMessage(message=f"Session {session_id} not found").model_dump()
            )
            await websocket.close()
            return

        dm = DungeonMasterAI(
            llm=llm_provider,
            engine=engine,
            embedding_provider=embedding_provider,
            conn=conn,
        )

        # Send initial state
        await websocket.send_json(GameStateUpdate(
            character=session.player_character,
            companions=session.companions,
            scene={
                "type": session.current_scene.scene_type.value,
                "description": session.current_scene.description,
                "location": session.current_scene.location,
            },
            turn_count=session.turn_count,
            in_combat=session.in_combat,
        ).model_dump())

        # Main game loop
        while True:
            raw = await websocket.receive_json()
            msg_type = raw.get("type", "")

            if msg_type == "player_action":
                await _handle_player_action(websocket, dm, session, conn, raw["text"])
            elif msg_type == "system_command":
                await _handle_system_command(websocket, session, conn, raw["command"])
            else:
                await websocket.send_json(
                    ErrorMessage(message=f"Unknown message type: {msg_type}").model_dump()
                )

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json(
                ErrorMessage(message=f"Server error: {e}").model_dump()
            )
        except Exception:
            pass
    finally:
        conn.close()


async def _handle_player_action(
    ws: WebSocket,
    dm: DungeonMasterAI,
    session,
    conn,
    text: str,
):
    """Process a player action through the DM AI with streaming."""
    await ws.send_json(Thinking(active=True).model_dump())

    entries_to_save: list[NarrativeEntry] = []

    def _run_turn():
        """Run the turn resolution in a thread (sync LLM/DB calls)."""
        results = []
        for item in dm.process_player_input_stream(session, text):
            results.append(item)
        return results

    # Run sync turn resolution in thread pool
    results = await asyncio.to_thread(_run_turn)

    # Process results and send to client
    for item in results:
        if isinstance(item, str):
            # LLM token — stream to client
            await ws.send_json(NarrativeChunk(text=item).model_dump())
        elif isinstance(item, NarrativeEntry):
            entries_to_save.append(item)
            if item.action_type == "dice_roll" and item.dice_results:
                # Send dice roll visualization
                for dice_data in item.dice_results:
                    await ws.send_json(DiceRollResult(
                        roller=item.actor,
                        description=dice_data.get("description", ""),
                        dice=dice_data.get("expression", ""),
                        rolls=dice_data.get("rolls", []),
                        modifier=dice_data.get("modifier", 0),
                        total=dice_data.get("total", 0),
                        success=None,
                        dc=None,
                    ).model_dump())

    # Signal end of narrative
    await ws.send_json(NarrativeChunk(text="", is_final=True).model_dump())
    await ws.send_json(Thinking(active=False).model_dump())

    # Persist entries
    await asyncio.to_thread(append_entries, conn, session, entries_to_save)

    # Auto-save periodically
    game_settings = get_game_settings()
    if session.turn_count % game_settings.auto_save_interval == 0:
        await asyncio.to_thread(save_game, conn, session)

    # Send updated state
    await ws.send_json(GameStateUpdate(
        character=session.player_character,
        companions=session.companions,
        turn_count=session.turn_count,
        in_combat=session.in_combat,
    ).model_dump())


async def _handle_system_command(ws: WebSocket, session, conn, command: str):
    """Handle system commands (save, inventory, etc.)."""
    if command == "save":
        await asyncio.to_thread(save_game, conn, session)
        await ws.send_json(NarrativeChunk(
            text="Game saved.", is_final=True,
        ).model_dump())
    elif command == "status":
        await ws.send_json(GameStateUpdate(
            character=session.player_character,
            companions=session.companions,
            turn_count=session.turn_count,
            in_combat=session.in_combat,
        ).model_dump())
    else:
        await ws.send_json(ErrorMessage(
            message=f"Unknown command: {command}",
        ).model_dump())
