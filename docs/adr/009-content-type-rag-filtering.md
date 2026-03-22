# ADR-009: Content-Type Tagging for Filtered RAG Retrieval

## Status
Accepted

## Context
The RAG system stores chunks from multiple document types: rulebooks, adventure modules, monster manuals, and novels. When the AI DM retrieves context, it needs different content for different purposes: rules for mechanical questions, adventure details for scene narration, monster stats for combat. It must also never expose adventure spoilers to the player.

Options:
1. **Separate vector stores** — One pgvector table per content type
2. **Content-type column + filtered search** — Single table, filter at query time
3. **Separate books, no filtering** — Retrieve from specific book IDs only

## Decision
Add a `content_type TEXT` column to the existing `chunks` table. Values: `rule`, `encounter`, `npc`, `monster`, `lore`, `book`. Filter with `WHERE content_type = ANY(...)` during vector search.

Classification is done automatically during ingestion via regex pattern matching on chunk content and chapter titles.

## Consequences

**Positive:**
- Single table, single index — simpler than managing multiple vector stores
- Flexible filtering: "give me rules + lore" or "just encounters" in one query
- Automatic classification means no manual labeling effort
- Anti-spoiler design: adventure content is only retrieved server-side for the DM prompt
- Combined with `book_id` filtering: "rules from the D&D 5e SRD" vs "encounters from Curse of Strahd"

**Negative:**
- Classification is heuristic — regex patterns may miscategorize some chunks
- The `content_type` column slightly widens the chunks table
- Need to handle the case where classification is wrong (falls back to `lore` default)

**Anti-spoiler guarantee:**
- `search_by_content_type()` with `content_types=["rule"]` for player-visible lookups
- `content_types=["encounter","npc","monster","lore"]` for DM-only context (never sent to frontend)
