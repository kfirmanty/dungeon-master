# PRD-03: Game Engine

## Purpose

The game engine handles RPG mechanics: dice rolling, ability checks, combat resolution, character creation, and game state management. It is designed as a swappable Protocol so different RPG systems (D&D 5e, WFRP, AD&D) can be plugged in without changing the game loop or AI DM.

## Functional Requirements

### FR-01: RulesEngine Protocol
- Define a `RulesEngine` Protocol that all RPG systems must implement
- Characters passed as `dict` (JSONB-compatible) — each engine defines its own schema
- Shared result types: `DiceResult`, `CheckResult`, `AttackResult`, `DamageResult`
- Engine self-describes via `get_rules_summary()` and `get_check_types()` for AI prompt adaptation
- Engine registry with factory function: `get_engine("dnd5e")` returns the appropriate implementation
- Config-driven selection via `RULES_SYSTEM` environment variable

### FR-02: Dice System
- Universal dice notation parser: `roll("2d6+3")`, `roll("d20")`, `roll("4d8-1")`
- Advantage/disadvantage: `roll_d20(advantage=True)` rolls 2d20 takes higher
- Percentile dice: `roll_d100()` for WFRP and similar systems
- Preserve all detail in `DiceResult`: expression, individual rolls, modifier, total, natural max/min flags
- Deterministic when seeded (for testing)

### FR-03: D&D 5e Implementation
- **Ability scores**: modifier calculation `(score - 10) // 2`
- **Ability checks**: d20 + ability modifier vs DC
- **Skill checks**: d20 + ability modifier + proficiency bonus (if proficient) vs DC, with skill-to-ability mapping (18 skills)
- **Saving throws**: d20 + ability modifier + proficiency (if proficient in that save) vs DC
- **Attack rolls**: d20 + ability modifier + proficiency vs AC; natural 20 = critical hit (double damage dice), natural 1 = auto miss
- **Damage**: roll weapon damage + ability modifier; critical hits double the damage dice
- **HP management**: temp HP absorbs first; 0 HP = unconscious; massive damage (overflow >= max HP) = instant death
- **Death saves**: d20 vs DC 10; natural 20 = revive with 1 HP; natural 1 = 2 failures; 3 successes = stabilize; 3 failures = death
- **Initiative**: d20 + DEX modifier
- **Character creation**: name, race (9 races with ability bonuses and speed), class (12 classes with hit dice, save proficiencies, starting equipment), ability scores (rolled 4d6-drop-lowest or standard array)
- **AC calculation**: base 10 + DEX mod, modified by armor type (light/medium/heavy) and shield

### FR-04: Game Session Management
- Create new sessions with character + companions + optional adventure/rulebook links
- Save/load session state (JSONB for character data, relational for game log)
- Append-only game log with sequence numbers for history reconstruction
- Track turn count, combat state, current scene

### FR-05: Turn Resolution
- Accept player input as natural language
- Route through AI DM for narrative + mechanical actions
- Execute mechanical actions through rules engine
- Feed results back to AI for outcome narration
- Persist all entries to game log
- Auto-save at configurable intervals

## Non-Functional Requirements

- **NFR-01**: Rules engine has zero I/O — pure Python functions, fully unit-testable
- **NFR-02**: Adding a new RPG system requires only implementing the Protocol + registering in the factory
- **NFR-03**: All randomness goes through `random` module (seedable for tests)

## Key Files

| File | Responsibility |
|------|---------------|
| `src/dungeonmaster/rules/base.py` | `RulesEngine` Protocol + registry/factory |
| `src/dungeonmaster/rules/dice.py` | Universal dice parser and roller |
| `src/dungeonmaster/rules/dnd5e/engine.py` | `DnD5eEngine` implementation |
| `src/dungeonmaster/rules/dnd5e/abilities.py` | Checks and saves |
| `src/dungeonmaster/rules/dnd5e/combat.py` | Attack, damage, initiative, death saves |
| `src/dungeonmaster/rules/dnd5e/characters.py` | Character creation and AC calculation |
| `src/dungeonmaster/rules/dnd5e/data.py` | D&D 5e constants and lookup tables |
| `src/dungeonmaster/models.py` | Shared domain dataclasses |
| `src/dungeonmaster/game/session.py` | Session lifecycle |
| `src/dungeonmaster/game/turn.py` | Turn resolution orchestrator |

## Acceptance Criteria

1. `DnD5eEngine` satisfies the `RulesEngine` Protocol
2. Dice rolls are fair (uniform distribution when not seeded)
3. Ability checks correctly apply modifiers and proficiency
4. Critical hits double damage dice; natural 1 always misses
5. Death save mechanics follow D&D 5e rules exactly
6. Character creation produces valid characters with proper racial bonuses and starting equipment
7. Unknown system IDs raise clear errors listing available systems
