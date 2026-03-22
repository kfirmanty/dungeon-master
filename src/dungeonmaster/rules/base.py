"""
Abstract interface for RPG rules engines.

Same structural typing approach as BookWorm's EmbeddingProvider and LLMProvider —
any class with matching methods is a valid RulesEngine without explicit inheritance.

To add a new RPG system (WFRP, AD&D 2e, etc.), implement this Protocol and
register it in the engine factory.
"""

from typing import Protocol

from dungeonmaster.models import (
    AttackResult,
    CheckResult,
    DamageResult,
    DiceResult,
)


class RulesEngine(Protocol):
    """Abstract interface for any tabletop RPG rules system.

    Characters are passed as dicts (from JSONB) so each engine can define
    its own schema without coupling the game session to a specific system.
    """

    @property
    def system_name(self) -> str:
        """Human-readable system name, e.g. 'D&D 5th Edition', 'WFRP 4e'."""
        ...

    # --- Checks (ability, skill, saving throw, or system equivalent) ---

    def roll_check(
        self,
        character: dict,
        check_type: str,
        detail: str,
        target: int,
        **kwargs,
    ) -> CheckResult:
        """Resolve a check (skill, ability, saving throw, etc.).

        Args:
            character: The character dict (system-specific schema).
            check_type: Type of check, from get_check_types().
            detail: Specifics, e.g. "stealth", "dexterity", "perception".
            target: Difficulty / target number (DC, TN, etc.).
            **kwargs: System-specific options (advantage, etc.).
        """
        ...

    # --- Combat ---

    def roll_initiative(self, character: dict) -> DiceResult:
        """Roll initiative for a character."""
        ...

    def resolve_attack(
        self,
        attacker: dict,
        defender: dict,
        weapon: dict | None = None,
        **kwargs,
    ) -> AttackResult:
        """Resolve a full attack: attack roll + damage if hit."""
        ...

    def apply_damage(
        self,
        target: dict,
        damage: int,
        damage_type: str = "",
    ) -> DamageResult:
        """Apply damage to a character, mutating the target dict in place.

        Returns a DamageResult describing what happened (unconscious, dead, etc.).
        """
        ...

    # --- Characters ---

    def create_character(self, choices: dict) -> dict:
        """Create a new character dict from player choices.

        Args:
            choices: System-specific creation options (race, class, abilities, etc.).

        Returns:
            A complete character dict ready for gameplay.
        """
        ...

    def get_character_summary(self, character: dict) -> str:
        """Return a human-readable summary of a character for display / prompts."""
        ...

    def get_available_actions(self, character: dict, scene_type: str) -> list[str]:
        """Return valid player actions given character state and scene type."""
        ...

    # --- Lifecycle (resting, leveling, spells) ---

    def take_rest(self, character: dict, rest_type: str) -> dict:
        """Process a rest period, restoring resources.

        Args:
            character: The character dict (mutated in place).
            rest_type: System-specific rest type (e.g. "short", "long" for D&D;
                       "overnight" for WFRP).

        Returns:
            Dict describing what was restored (e.g. {"hp_restored": 5, "slots_restored": [1,1,0,...]}).
        """
        ...

    def resolve_spell(
        self,
        caster: dict,
        spell: dict,
        targets: list[dict],
        **kwargs,
    ) -> CheckResult | AttackResult:
        """Resolve a spell effect (attack roll or save DC).

        Systems without magic can raise NotImplementedError.

        Args:
            caster: The caster's character dict.
            spell: Spell definition dict (system-specific schema).
            targets: List of target character/enemy dicts.
        """
        ...

    def level_up(self, character: dict, choices: dict) -> dict:
        """Apply a level-up to a character.

        Args:
            character: The character dict (mutated in place).
            choices: Level-up options (e.g. ability score improvement, new spells).

        Returns:
            Dict describing what changed (e.g. {"new_level": 5, "hp_gained": 8, "features": ["Extra Attack"]}).
        """
        ...

    # --- System info (used by AI DM to adapt prompts) ---

    def get_rules_summary(self) -> str:
        """Brief rules summary injected into the DM system prompt.

        Should explain the core mechanic, what checks look like, and how
        combat works — enough for the AI to request appropriate rolls.
        """
        ...

    def get_check_types(self) -> list[str]:
        """Valid check_type values for [ROLL:...] tags.

        E.g. D&D 5e: ['ability_check', 'skill_check', 'saving_throw', 'attack']
        WFRP: ['basic_test', 'opposed_test', 'dramatic_test']
        """
        ...


# ---------------------------------------------------------------------------
# Engine registry / factory
# ---------------------------------------------------------------------------

_ENGINE_REGISTRY: dict[str, type] = {}


def register_engine(system_id: str, engine_class: type) -> None:
    """Register a RulesEngine implementation for a system ID."""
    _ENGINE_REGISTRY[system_id] = engine_class


def get_engine(system_id: str) -> RulesEngine:
    """Instantiate a RulesEngine by system ID.

    Raises KeyError if the system is not registered.
    """
    if system_id not in _ENGINE_REGISTRY:
        available = ", ".join(sorted(_ENGINE_REGISTRY.keys())) or "(none)"
        raise KeyError(
            f"Unknown rules system '{system_id}'. Available: {available}"
        )
    return _ENGINE_REGISTRY[system_id]()
