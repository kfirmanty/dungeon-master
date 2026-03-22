"""
Pydantic schemas for API request/response models and WebSocket messages.

All WebSocket messages use a `type` discriminator field so the frontend
can dispatch rendering based on message type.
"""

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Client → Server (WebSocket)
# ---------------------------------------------------------------------------


class PlayerAction(BaseModel):
    type: str = "player_action"
    text: str


class CombatAction(BaseModel):
    type: str = "combat_action"
    action: str  # "attack", "cast_spell", "dash", etc.
    target: str | None = None
    details: str | None = None


class SystemCommand(BaseModel):
    type: str = "system_command"
    command: str  # "save", "inventory", "help", "status"


# ---------------------------------------------------------------------------
# Server → Client (WebSocket)
# ---------------------------------------------------------------------------


class NarrativeChunk(BaseModel):
    type: str = "narrative_chunk"
    text: str
    is_final: bool = False


class DiceRollResult(BaseModel):
    type: str = "dice_roll"
    roller: str
    description: str
    dice: str  # expression, e.g. "1d20+5"
    rolls: list[int]
    modifier: int
    total: int
    success: bool | None = None
    dc: int | None = None


class GameStateUpdate(BaseModel):
    type: str = "game_state_update"
    character: dict | None = None
    companions: list[dict] | None = None
    scene: dict | None = None
    turn_count: int | None = None
    in_combat: bool | None = None


class CombatUpdate(BaseModel):
    type: str = "combat_update"
    active: bool
    round_number: int = 1
    initiative_order: list[dict] = []
    current_turn: str = ""
    available_actions: list[str] | None = None


class Thinking(BaseModel):
    type: str = "thinking"
    active: bool


class ErrorMessage(BaseModel):
    type: str = "error"
    message: str
    recoverable: bool = True


# ---------------------------------------------------------------------------
# REST API Schemas
# ---------------------------------------------------------------------------


class NewGameRequest(BaseModel):
    name: str
    rules_system: str = "dnd5e"
    character: dict  # character creation choices
    companions: list[dict] | None = None
    adventure_book_id: str | None = None
    rulebook_book_id: str | None = None


class GameSessionSummary(BaseModel):
    id: str
    name: str
    rules_system: str
    character_name: str | None = None
    character_class: str | None = None
    hp_current: str | None = None
    hp_max: str | None = None
    turn_count: int
    in_combat: bool
    created_at: str
    updated_at: str


class SaveGameRequest(BaseModel):
    session_id: str
