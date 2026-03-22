# ADR-004: Swappable Rules Engine

## Status
Accepted

## Context
The initial target is D&D 5e, but users want to run adventures with other systems (AD&D 2e for classic modules, WFRP for Warhammer campaigns). The rules engine — dice mechanics, ability checks, combat resolution, character creation — differs significantly between systems.

Options:
1. **Hardcode D&D 5e** — simpler, but locks users into one system
2. **Config-driven rules** — define rules in YAML/JSON files loaded at runtime
3. **Protocol-based engine** — each system is a Python class implementing a shared interface

## Decision
Use a `RulesEngine` Protocol with a registry/factory pattern. D&D 5e ships as the default. Each system is a separate Python module that implements the Protocol and registers itself.

Key design: characters are `dict` (not typed dataclasses) so the engine can define its own schema. The engine also self-describes via `get_rules_summary()` and `get_check_types()`, which the AI DM uses to adapt its prompts.

## Consequences

**Positive:**
- Adding WFRP or AD&D = implementing one Python class + registering it
- AI DM automatically adapts — it learns what kinds of rolls to request from the engine
- Character data is system-agnostic (JSONB dict) — no DB migrations when adding systems
- Rules engine is pure Python with zero I/O — 100% unit-testable

**Negative:**
- Each new system requires significant implementation effort (not just config)
- The `dict`-based character API loses type safety — easy to mistype keys
- System-specific UI elements (e.g., WFRP career display) need frontend work

**Implementation:**
- `rules/base.py` — Protocol definition + `register_engine()` / `get_engine()` factory
- `rules/dnd5e/` — D&D 5e implementation (engine, abilities, combat, characters, data)
- `config.py` — `rules_system: str = "dnd5e"` setting
