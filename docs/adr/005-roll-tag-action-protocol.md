# ADR-005: [ROLL:...] Tag Protocol for AI-Rules Integration

## Status
Accepted

## Context
The AI DM needs to request mechanical resolution (dice rolls, ability checks, attacks) from the rules engine. The question is how to communicate these requests.

Options:
1. **OpenAI-style function calling** — LLM outputs structured JSON tool calls
2. **[ROLL:...] text tags** — LLM embeds simple tags in its narrative output
3. **Post-hoc NLP parsing** — A second model extracts actions from the narrative

## Decision
Use inline `[ROLL:type:detail:DC:actor]` text tags that the AI embeds directly in its narrative output. A regex parser extracts them.

Format: `[ROLL:check_type:detail:DC_or_AC_value:actor_name]`

Examples:
- `[ROLL:skill_check:stealth:DC15:Aelindra]`
- `[ROLL:saving_throw:dexterity:DC13:Thorin]`
- `[ROLL:attack:longsword:AC16:Aelindra]`

Regex: `\[ROLL:(\w+):(\w+):(?:DC|AC)?(\d+):([^\]]+)\]` (case-insensitive)

## Consequences

**Positive:**
- Works reliably with small local models (8B parameters) that struggle with structured JSON
- The tag format is simple enough for few-shot prompting to teach
- Tags coexist naturally with narrative text — no separate output channels
- Regex parsing is fast and forgiving (partial matches, case-insensitive)
- Easy to debug — just read the raw LLM output
- The tag vocabulary is dynamic — `get_check_types()` tells the AI what tags are valid for the active system

**Negative:**
- Less structured than JSON function calls — harder to validate complex actions
- The LLM may sometimes omit tags, malformat them, or put them in wrong places
- Can't express compound actions (e.g., "attack with advantage using a flame tongue") in a single tag

**Mitigated by:**
- Forgiving regex parser that handles DC/AC prefix variations
- If parsing fails, the response is treated as pure narration (game continues)
- The DM prompt includes explicit examples showing the exact format
