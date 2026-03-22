"""
Shared domain models for the Dungeon Master game engine.

These dataclasses are RPG-system-agnostic. System-specific character data
(D&D ability scores, WFRP careers, etc.) lives in dict/JSONB — each
RulesEngine implementation knows how to create and interpret its own schema.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4


# ---------------------------------------------------------------------------
# Dice & Mechanical Results (shared across all rules systems)
# ---------------------------------------------------------------------------


@dataclass
class DiceResult:
    """Result of a dice roll, preserving all detail for narration and display."""

    expression: str  # "2d6+3", "1d20"
    rolls: list[int]  # individual die results, e.g. [4, 2]
    modifier: int  # flat modifier, e.g. 3
    total: int  # final sum, e.g. 9
    # Critical hit / fumble flags (system-dependent interpretation)
    natural_max: bool = False  # rolled max on primary die (e.g. nat 20)
    natural_min: bool = False  # rolled min on primary die (e.g. nat 1)


@dataclass
class CheckResult:
    """Outcome of an ability check, skill check, saving throw, etc."""

    dice_result: DiceResult
    success: bool
    target_number: int  # DC, TN, or similar
    check_type: str  # "skill_check", "saving_throw", "ability_check", etc.
    detail: str  # "stealth", "dexterity", etc.
    actor: str  # character name
    description: str = ""  # human-readable summary, e.g. "Stealth check: 19 vs DC 15 — Success"


@dataclass
class AttackResult:
    """Outcome of an attack roll."""

    attack_roll: DiceResult
    hit: bool
    critical: bool
    damage_roll: DiceResult | None  # None if miss
    total_damage: int = 0
    attacker: str = ""
    defender: str = ""
    description: str = ""


@dataclass
class DamageResult:
    """Outcome of applying damage to a target."""

    damage_dealt: int
    target_unconscious: bool = False
    target_dead: bool = False
    target: str = ""
    description: str = ""


# ---------------------------------------------------------------------------
# Items
# ---------------------------------------------------------------------------


@dataclass
class Item:
    """A game item — weapons, armor, potions, treasure, etc."""

    name: str
    description: str = ""
    weight: float = 0.0
    quantity: int = 1
    equipped: bool = False
    # System-specific properties, e.g. {"damage": "1d8", "type": "slashing"}
    properties: dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Combat State
# ---------------------------------------------------------------------------


@dataclass
class CombatantState:
    """A character's state within an active combat encounter."""

    character_id: str  # name or UUID string
    initiative: int = 0
    has_acted: bool = False
    position: str = ""  # narrative position, e.g. "near the door"
    is_player: bool = False
    is_enemy: bool = False


@dataclass
class CombatState:
    """Full state of an active combat encounter."""

    combatants: list[CombatantState] = field(default_factory=list)
    turn_order: list[str] = field(default_factory=list)  # character IDs in initiative order
    current_turn_index: int = 0
    round_number: int = 1


# ---------------------------------------------------------------------------
# Scene
# ---------------------------------------------------------------------------


class SceneType(Enum):
    EXPLORATION = "exploration"
    COMBAT = "combat"
    SOCIAL = "social"
    REST = "rest"
    PUZZLE = "puzzle"


@dataclass
class Scene:
    """The current narrative scene/encounter."""

    scene_type: SceneType = SceneType.EXPLORATION
    description: str = ""
    location: str = ""
    npcs_present: list[str] = field(default_factory=list)
    enemies: list[dict] = field(default_factory=list)  # system-specific stat blocks
    combat_state: CombatState | None = None


# ---------------------------------------------------------------------------
# Narrative Log
# ---------------------------------------------------------------------------


@dataclass
class NarrativeEntry:
    """A single entry in the game log / conversation history."""

    actor: str  # "player", "dm", companion name, "system"
    content: str  # the narrative text or player input
    action_type: str = ""  # "dialogue", "combat_action", "skill_check", "narration", "dice_roll"
    dice_results: list[dict] = field(default_factory=list)  # serialized DiceResult dicts
    metadata: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Game Session (root aggregate)
# ---------------------------------------------------------------------------


@dataclass
class GameSession:
    """The full state of an active game session.

    Character data is stored as dict (JSONB in DB) so it is RPG-system-agnostic.
    Each RulesEngine knows how to create and interpret its own character schema.
    """

    id: UUID = field(default_factory=uuid4)
    name: str = ""
    rules_system: str = "dnd5e"  # which RulesEngine to load
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    # Character data as system-agnostic dicts
    player_character: dict = field(default_factory=dict)
    companions: list[dict] = field(default_factory=list)

    # World state
    current_scene: Scene = field(default_factory=Scene)
    narrative_history: list[NarrativeEntry] = field(default_factory=list)

    # Links to ingested content (bookworm books table UUIDs)
    adventure_book_id: UUID | None = None
    rulebook_book_id: UUID | None = None

    # Counters
    turn_count: int = 0
    in_combat: bool = False
