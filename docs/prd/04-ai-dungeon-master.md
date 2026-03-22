# PRD-04: AI Dungeon Master

## Purpose

The AI Dungeon Master is the central orchestrator that ties together RAG retrieval, the rules engine, and LLM generation. It processes player input, generates narrative, requests mechanical resolution via `[ROLL:...]` tags, and narrates outcomes.

## Functional Requirements

### FR-01: Two-Phase LLM Flow
Every player turn follows this sequence:
1. **Phase 1 (Narrative + Actions)**: Player input + RAG context sent to LLM. LLM generates narrative prose and embeds `[ROLL:...]` tags for uncertain outcomes.
2. **Phase 2 (Outcome Narration)**: Rules engine resolves the rolls. Results are fed back to the LLM, which narrates what happened.

This separation ensures the AI never fabricates roll results — the rules engine is the sole authority on mechanical outcomes.

### FR-02: Roll Tag Protocol
The AI embeds structured tags in its narrative output:

```
[ROLL:check_type:detail:DC_or_AC_value:actor_name]
```

- `check_type`: From the active engine's `get_check_types()` (e.g., `skill_check`, `saving_throw`, `attack`, `ability_check`)
- `detail`: Specific skill, ability, or weapon (e.g., `stealth`, `dexterity`, `longsword`)
- `DC_or_AC_value`: Target number, optionally prefixed with `DC` or `AC`
- `actor_name`: Character performing the action

Regex: `\[ROLL:(\w+):(\w+):(?:DC|AC)?(\d+):([^\]]+)\]` (case-insensitive)

### FR-03: Dynamic System Prompts
The DM system prompt is rebuilt every turn using:
- `RulesEngine.get_rules_summary()` — explains the active game system's core mechanics
- `RulesEngine.get_check_types()` — lists valid tag types
- Current party state (character summaries from the engine)
- Current scene (location, description, NPCs present)

This means the AI adapts automatically when the rules system changes (e.g., D&D tags vs WFRP tags).

### FR-04: Context Window Management
- Keep the 8 most recent narrative entries verbatim
- Summarize older entries into a compressed paragraph
- Cap RAG context at ~2000 characters per source (rules + adventure)
- Total history budget: ~4000 characters
- Question/input placed last in the user message (lost-in-the-middle mitigation)

### FR-05: RAG Retrieval
For each player action, retrieve:
- **Rules context** (`content_type='rule'`, up to 3 chunks) — game mechanics relevant to the action
- **Adventure context** (`content_type IN ('encounter','npc','monster','lore')`, up to 2 chunks) — plot/setting context

Adventure context is **server-side only** — never sent to the frontend (anti-spoiler design).

### FR-06: Companion NPC Control
- AI controls 2 companion NPCs with distinct personalities
- In combat, generates actions for each companion using personality-aware prompts
- Companion actions are resolved through the rules engine like player actions
- Companions skip their turn if unconscious (HP <= 0)

### FR-07: Streaming Output
- `generate_stream()` yields tokens as they're produced by the LLM
- Tokens are forwarded to the frontend via WebSocket for real-time display
- After streaming completes, `[ROLL:...]` tags are parsed from the full response

## Non-Functional Requirements

- **NFR-01**: The AI must never determine roll outcomes — it can only request rolls
- **NFR-02**: Malformed tags are handled gracefully (forgiving regex, skip on failure)
- **NFR-03**: Two LLM calls per turn is acceptable; streaming the first call hides latency

## Key Files

| File | Responsibility |
|------|---------------|
| `src/dungeonmaster/ai/dm.py` | `DungeonMasterAI` — main orchestrator |
| `src/dungeonmaster/ai/prompts.py` | System prompt templates |
| `src/dungeonmaster/ai/actions.py` | `[ROLL:...]` tag parser + rules engine execution |
| `src/dungeonmaster/ai/context.py` | History management, context assembly |

## Acceptance Criteria

1. Player input produces narrative + appropriate roll tags
2. Roll results are resolved by the rules engine, not the AI
3. Outcome narration reflects the actual roll results
4. Companion turns generate actions consistent with their personality
5. System prompt adapts when rules system changes
6. Malformed or missing tags don't crash the game
