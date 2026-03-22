# ADR-006: Two-Phase LLM Flow

## Status
Accepted

## Context
When a player acts, the AI needs to both narrate the scene AND resolve mechanical outcomes (dice rolls). The question is whether to do this in one LLM call or two.

Options:
1. **Single call** — LLM generates narrative including roll results (AI "rolls" its own dice)
2. **Two-phase** — LLM generates narrative + roll requests, engine resolves, LLM narrates outcomes
3. **Three-phase** — Separate calls for setup narration, action decision, and outcome narration

## Decision
Use a two-phase flow:
1. **Phase 1**: Player input + RAG context → LLM generates narrative with `[ROLL:...]` tags
2. **Phase 2**: Rules engine resolves rolls → results fed back to LLM → outcome narration

## Consequences

**Positive:**
- The AI never fabricates roll results — the rules engine is the sole authority
- Rolls are truly random and mechanically correct (proper modifiers, proficiency, advantage)
- Players can trust the game is fair — the same engine handles all resolution
- The AI focuses on what it's good at (narrative) while code handles what it's good at (math)

**Negative:**
- Two LLM calls per turn doubles latency (~60-120s on CPU Ollama)
- More complex orchestration code in `DungeonMasterAI`
- The second call's context includes the first call's output, consuming more tokens

**Mitigated by:**
- Phase 1 is streamed to the frontend immediately — player sees narrative while rolls resolve
- Dice results are displayed between the two narrative sections
- Switching to a faster model (3B) or GPU Ollama significantly reduces latency
