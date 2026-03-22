# Rules Engine Implementation Guide

How to add a new RPG system (e.g., WFRP, AD&D 2e, Pathfinder) to the Dungeon Master.

## Overview

The rules engine uses Python's `Protocol` for structural typing. Any class that implements the required methods is automatically a valid `RulesEngine` — no inheritance needed.

## Step 1: Create the Package

```
src/dungeonmaster/rules/wfrp/
├── __init__.py
├── engine.py      # WfrpEngine class
├── tests.py       # System-specific mechanics (percentile rolls, opposed tests, etc.)
├── characters.py  # Character creation (careers, skills, talents)
└── data.py        # System constants (career list, skill list, etc.)
```

## Step 2: Implement the Protocol

Your engine class must implement every method in the `RulesEngine` Protocol:

```python
# src/dungeonmaster/rules/wfrp/engine.py

from dungeonmaster.models import (
    AttackResult, CheckResult, DamageResult, DiceResult,
)
from dungeonmaster.rules.base import register_engine


class WfrpEngine:
    """Warhammer Fantasy Roleplay 4th Edition rules engine."""

    @property
    def system_name(self) -> str:
        return "Warhammer Fantasy Roleplay 4e"

    def roll_check(
        self, character: dict, check_type: str, detail: str,
        target: int, **kwargs,
    ) -> CheckResult:
        """WFRP uses d100 roll-under: roll percentile dice, succeed if <= target."""
        from dungeonmaster.rules.dice import roll_d100
        dice = roll_d100()
        success = dice.total <= target
        return CheckResult(
            dice_result=dice,
            success=success,
            target_number=target,
            check_type=check_type,
            detail=detail,
            actor=character.get("name", "Unknown"),
            description=f"{detail} test: {dice.total} vs {target} — {'Success' if success else 'Failure'}",
        )

    def roll_initiative(self, character: dict) -> DiceResult:
        """WFRP initiative: I + 1d10."""
        from dungeonmaster.rules.dice import roll
        initiative_bonus = character.get("characteristics", {}).get("initiative", 30)
        return roll(f"1d10+{initiative_bonus // 10}")

    def resolve_attack(
        self, attacker: dict, defender: dict,
        weapon: dict | None = None, **kwargs,
    ) -> AttackResult:
        """WFRP melee: d100 vs weapon skill, damage = SB + weapon damage."""
        # ... implement WFRP combat mechanics
        pass

    def apply_damage(
        self, target: dict, damage: int, damage_type: str = "",
    ) -> DamageResult:
        """WFRP: damage reduces wounds. At 0 wounds, critical injury table."""
        wounds = target.get("wounds", {})
        current = wounds.get("current", 0)
        new_wounds = max(0, current - damage)
        wounds["current"] = new_wounds
        target["wounds"] = wounds
        return DamageResult(
            damage_dealt=current - new_wounds,
            target_unconscious=new_wounds == 0,
            target=target.get("name", "Unknown"),
        )

    def create_character(self, choices: dict) -> dict:
        """WFRP character: species, career, characteristics, skills, talents."""
        return {
            "name": choices.get("name", "Unknown"),
            "species": choices.get("species", "human"),
            "career": choices.get("career", "Rat Catcher"),
            "career_level": 1,
            "characteristics": {
                "weapon_skill": 30, "ballistic_skill": 25,
                "strength": 30, "toughness": 30,
                "initiative": 30, "agility": 30,
                "dexterity": 25, "intelligence": 30,
                "willpower": 30, "fellowship": 25,
            },
            "wounds": {"current": 12, "max": 12},
            "fate": {"current": 2, "max": 2},
            "resilience": {"current": 1, "max": 1},
            "skills": choices.get("skills", []),
            "talents": choices.get("talents", []),
            "inventory": [],
            "gold_crowns": 2,
            "silver_shillings": 4,
            "brass_pennies": 8,
        }

    def get_character_summary(self, character: dict) -> str:
        wounds = character.get("wounds", {})
        return (
            f"{character.get('name')} — {character.get('species', '').title()} "
            f"{character.get('career', '')} | "
            f"Wounds {wounds.get('current', 0)}/{wounds.get('max', 0)}"
        )

    def get_available_actions(self, character: dict, scene_type: str) -> list[str]:
        if scene_type == "combat":
            return ["attack", "cast spell", "dodge", "flee", "use item"]
        return ["investigate", "talk", "use skill", "rest"]

    def get_rules_summary(self) -> str:
        return """Warhammer Fantasy Roleplay 4e core mechanics:
- All tests use d100 roll-under: roll percentile dice, succeed if result <= your skill value.
- Skill values range from 01-99. Typical starting value: 25-40.
- Degrees of success/failure: every 10 points above/below the target.
- Combat: d100 vs Weapon Skill to hit. Damage = Strength Bonus + weapon damage - Toughness Bonus - armor.
- Wounds track health. At 0 wounds, consult the Critical Injury table.
- Fate points can be spent to reroll or avoid death.
- Careers define advancement: each career level grants access to skills and talents."""

    def get_check_types(self) -> list[str]:
        return ["basic_test", "opposed_test", "dramatic_test", "attack"]


# Register so get_engine("wfrp") works
register_engine("wfrp", WfrpEngine)
```

## Step 3: Register the Engine

The `register_engine()` call at the bottom of your engine module adds it to the global registry. Import the module to trigger registration:

```python
# In the game setup code or __init__.py:
from dungeonmaster.rules.wfrp.engine import WfrpEngine  # registers on import
```

## Step 4: Configure

Set the rules system in `.env`:

```
RULES_SYSTEM=wfrp
```

Or pass it when creating a game session via the API:

```json
{"rules_system": "wfrp", "character": {...}}
```

## Step 5: AI Prompt Adaptation

The AI DM automatically adapts because it calls your engine's methods:

- `get_rules_summary()` → injected into the system prompt so the AI understands WFRP mechanics
- `get_check_types()` → tells the AI what `[ROLL:...]` tag types are valid

For WFRP, the AI would generate tags like:
```
[ROLL:basic_test:perception:35:Klaus]
[ROLL:attack:sword:42:Klaus]
```

## Key Requirements

Your engine **must** implement all Protocol methods. The Protocol is defined in `src/dungeonmaster/rules/base.py`:

| Method | Signature | Purpose |
|--------|-----------|---------|
| `system_name` | `@property -> str` | Human-readable name |
| `roll_check()` | `(character, check_type, detail, target, **kwargs) -> CheckResult` | Resolve any check |
| `roll_initiative()` | `(character) -> DiceResult` | Roll initiative |
| `resolve_attack()` | `(attacker, defender, weapon?, **kwargs) -> AttackResult` | Full attack resolution |
| `apply_damage()` | `(target, damage, damage_type?) -> DamageResult` | Apply damage, mutate target |
| `create_character()` | `(choices) -> dict` | Create a character from choices |
| `get_character_summary()` | `(character) -> str` | Human-readable character summary |
| `get_available_actions()` | `(character, scene_type) -> list[str]` | Valid actions for context |
| `get_rules_summary()` | `() -> str` | Rules explanation for AI prompt |
| `get_check_types()` | `() -> list[str]` | Valid roll tag types |

## Shared Utilities

The `dungeonmaster.rules.dice` module provides system-agnostic dice functions:

- `roll("2d6+3")` — parse and roll any dice expression
- `roll_d20(modifier, advantage, disadvantage)` — d20 with D&D mechanics
- `roll_d100()` — percentile dice for WFRP/CoC
- `roll_multiple("4d6", 6)` — roll the same expression N times

These are shared across all systems. Use them in your engine implementation.

## Testing

Write tests in `tests/test_wfrp_*.py` following the same patterns as the D&D 5e tests:

```python
def test_engine_registered():
    engine = get_engine("wfrp")
    assert isinstance(engine, WfrpEngine)

def test_basic_test_roll_under():
    random.seed(42)
    result = engine.roll_check(character, "basic_test", "perception", 35)
    assert result.success == (result.dice_result.total <= 35)
```
