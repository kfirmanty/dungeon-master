# PRD-06: Content Pipeline

## Purpose

The content pipeline handles ingesting game content (rulebooks, adventure modules) with automatic classification, and converting novels into structured RPG adventures via LLM processing.

## Functional Requirements

### FR-01: Content Ingestion with Classification
- Wrap the BookWorm ingestion pipeline (read, chunk, embed, store)
- After ingestion, classify each chunk with a `content_type` tag:
  - `rule` — Game mechanics, ability descriptions, spell rules
  - `encounter` — Adventure encounters, room descriptions, events
  - `npc` — NPC descriptions, personalities, dialogue
  - `monster` — Creature stat blocks
  - `lore` — World-building, history, setting
  - `book` — Default (unclassified book content)
- Classification uses regex pattern matching on chunk content and chapter titles
- Patterns: "Armor Class" + "Hit Points" + "Challenge" = `monster`; "Area N:" + "read aloud" = `encounter`; etc.
- Caller can specify a default type for unclassified chunks

### FR-02: Content Listing
- List all ingested content with per-book chunk type breakdown
- Categorize books as "adventure", "rulebook", or "book" based on their chunk composition
- Return: id, title, file_path, ingested_at, total_chunks, content_types dict, category

### FR-03: Book-to-Adventure Conversion
Convert a novel chapter-by-chapter into structured RPG content using the LLM:

**Per-chapter extraction:**
- **Locations** — "Area N: [Name]" with DM-readable descriptions, features, arrival events
- **NPCs** — Name, personality traits (D&D format: personality, ideal, bond, flaw), roleplaying notes, race/class approximation
- **Encounters** — Trigger conditions, challenges with specific DCs, success/failure development, treasure
- **Creatures** — Full stat blocks (AC, HP, abilities, speed, challenge rating, special abilities)
- **Lore** — Setting details that don't fit other categories

**Processing:**
1. Read book and split into chapters (reuse `bookworm/ingestion/reader.py`)
2. For each chapter, send to LLM with structured extraction prompt
3. Truncate chapters > 6000 chars to fit context window
4. Assemble chapter outputs into one adventure document
5. Ingest the adventure document through the normal pipeline
6. Content classifier auto-tags the structured output

**Resilience:**
- If one chapter's LLM call fails, log the error and continue with remaining chapters
- Track progress: total chapters, current chapter, extracted element counts

### FR-04: Content-Type Filtered RAG Search
- `search_by_content_type()` filters pgvector search by one or more content types
- Optional additional filter by `book_id`
- Used by the AI DM to retrieve rules vs adventure content separately

## Classification Patterns

| Content Type | Chapter Title Keywords | Content Patterns (need 2+ matches) |
|-------------|----------------------|-------------------------------------|
| `monster` | "monster", "bestiary", "creature" | "Armor Class \d+", "Hit Points \d+\(\d+d\d+", "Challenge \d+", "STR DEX CON INT WIS CHA" |
| `npc` | "appendix: npc", "dramatis personae" | "personality\|ideal\|bond\|flaw\|trait", "roleplaying\|speaks with\|appears as" |
| `encounter` | — | "^Area \d+", "read or paraphrase\|read aloud", "encounter\|treasure\|tactics", "when the characters/players/party" |
| `rule` | "rule", "combat", "spell", "ability", "equipment" | "ability score\|saving throw\|hit points\|armor class", "difficulty class\|DC \d+", "short rest\|long rest\|concentration", "advantage\|disadvantage" |
| `lore` | — | Default for game content not matching above |

## Key Files

| File | Responsibility |
|------|---------------|
| `src/dungeonmaster/content/ingest.py` | Ingestion wrapper + content classifier |
| `src/dungeonmaster/content/converter.py` | Book-to-adventure LLM conversion pipeline |

## Acceptance Criteria

1. A D&D adventure module ingested as .txt gets chunks correctly classified (encounters, NPCs, monsters, rules)
2. A novel processed through conversion produces structured adventure content with locations, NPCs, and encounters
3. Converted adventure chunks are auto-tagged correctly by the content classifier
4. Failed chapter conversions don't crash the pipeline
5. Content listing shows accurate per-book type breakdown
