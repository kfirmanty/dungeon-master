# ADR-010: LLM-Powered Book-to-Adventure Conversion

## Status
Accepted

## Context
Users want to play RPG adventures based on novels (Dracula, Lord of the Rings). Raw novel text has no RPG structure — no encounters, DCs, stat blocks, or branching paths. Ingesting it directly results in all chunks tagged as "lore", giving the DM flavor text but no game-ready content.

Options:
1. **Raw ingestion + smarter prompt** — Ingest as-is, tell the DM to improvise mechanics
2. **LLM conversion pipeline** — Pre-process the novel into structured adventure content
3. **Manual conversion** — Require users to format content themselves

## Decision
Build an LLM-powered conversion pipeline that processes each chapter through the LLM to extract locations, NPCs, encounters, and creature stat blocks in a structured format. The output is ingested through the normal pipeline, where the content classifier auto-tags chunks correctly.

## Consequences

**Positive:**
- Produces game-ready content: locations with descriptions, NPCs with personality traits, encounters with specific DCs, creatures with stat blocks
- Automatic content classification works because the output format matches the classifier's regex patterns
- Chapter-by-chapter processing fits within LLM context windows
- Failed chapters don't crash the pipeline — error and continue
- Progress is trackable ("Converting chapter 3 of 27...")

**Negative:**
- Slow: one LLM call per chapter at 8-12 tok/s means a 27-chapter novel takes ~30-60 minutes
- Quality depends on the LLM — small models may produce inconsistent stat blocks
- Long chapters (>6000 chars) must be truncated, potentially losing content
- Extra LLM cost (tokens) compared to raw ingestion
- The conversion is one-shot — no way to regenerate individual chapters

**Mitigated by:**
- Conversion is a one-time cost per novel, not per game session
- The structured prompt with explicit format examples improves consistency
- Truncation warning is noted in the output ("[... chapter truncated for length ...]")
- Users can also use "Upload & Ingest" for pre-formatted content that doesn't need conversion

**Key design:**
- Process per-chapter (not whole book) to fit context windows and enable progress tracking
- Output format is intentionally designed to trigger the existing content classifier patterns
- Both the original book (for lore/flavor) and converted adventure (for game mechanics) can be linked to a game session
