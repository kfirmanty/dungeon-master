# ADR-003: JSONB for Character Storage

## Status
Accepted

## Context
RPG character sheets are deeply nested structures: ability scores, inventory (items with properties), spell slots by level, conditions with durations, death saves, etc. We need to store character state in PostgreSQL.

Options:
1. **Fully relational** — Separate tables for abilities, inventory, spell_slots, conditions (~8-10 tables with complex joins)
2. **JSONB columns** — Store the character as a single JSON document in a JSONB column
3. **Hybrid** — Relational for indexed fields, JSONB for the rest

The additional constraint: the rules engine is swappable. D&D 5e characters have different fields than WFRP characters (careers, wounds, fate points) or AD&D characters (THAC0, saving throw categories).

## Decision
Store `player_character`, `companions`, and `current_scene` as JSONB columns in the `game_sessions` table. Each `RulesEngine` implementation defines its own character dict schema. The game engine passes characters as `dict` without interpreting their structure.

## Consequences

**Positive:**
- Single-read load of complete character state (no joins)
- Schema flexibility — adding new RPG systems requires zero DB migrations
- Natural fit for the Protocol pattern — each engine interprets its own dict
- PostgreSQL JSONB supports indexing if we ever need to query by character attributes
- Trivial serialization: `json.dumps(character)` to save, parse from DB to load

**Negative:**
- No referential integrity on character fields (a typo in a key silently succeeds)
- Can't use SQL queries to find "all characters with STR > 16" efficiently
- Larger row sizes than normalized relational storage
- Must validate character structure in application code, not DB constraints

**Mitigated by:**
- The `RulesEngine.create_character()` method is the only place characters are created — it enforces the schema
- The game log (`game_log` table) remains relational for efficient range queries
