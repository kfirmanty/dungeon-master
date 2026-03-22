"""
D&D content ingestion — wraps the bookworm ingestion pipeline and adds
content_type tagging to chunks for filtered RAG retrieval.

Content types:
- "rule": Game mechanics, ability descriptions, spell rules
- "encounter": Adventure encounters, room descriptions, plot events
- "npc": NPC descriptions, personalities, dialogue
- "monster": Monster stat blocks
- "lore": World-building, history, setting descriptions
- "book": Default (regular book content, not game-specific)
"""

import re
from pathlib import Path

import psycopg

from bookworm.config import Settings
from bookworm.embeddings.base import EmbeddingProvider
from bookworm.ingestion.pipeline import ingest_book


# ---------------------------------------------------------------------------
# Content type classification
# ---------------------------------------------------------------------------

# Patterns that indicate rules content
_RULE_PATTERNS = [
    re.compile(r"\b(ability score|saving throw|hit points?|armor class|spell slot|proficiency bonus)\b", re.I),
    re.compile(r"\b(difficulty class|DC \d+|attack roll|damage roll)\b", re.I),
    re.compile(r"\b(short rest|long rest|concentration|bonus action|reaction)\b", re.I),
    re.compile(r"\b(advantage|disadvantage|ability check|skill check)\b", re.I),
]

# Patterns that indicate encounter/adventure content
_ENCOUNTER_PATTERNS = [
    re.compile(r"^Area \d+", re.I | re.M),
    re.compile(r"\b(read or paraphrase|read aloud|boxed text)\b", re.I),
    re.compile(r"\b(encounter|treasure|development|tactics)\b", re.I),
    re.compile(r"\b(when the (characters|players|party))\b", re.I),
]

# Patterns that indicate monster stat blocks
_MONSTER_PATTERNS = [
    re.compile(r"Armor Class \d+", re.I),
    re.compile(r"Hit Points \d+\s*\(\d+d\d+", re.I),
    re.compile(r"Challenge \d+", re.I),
    re.compile(r"STR\s+DEX\s+CON\s+INT\s+WIS\s+CHA", re.I),
]

# Patterns that indicate NPC content
_NPC_PATTERNS = [
    re.compile(r"\b(personality|ideal|bond|flaw|trait)\b", re.I),
    re.compile(r"\b(roleplaying|speaks? with|appears? as|is a .{3,30} who)\b", re.I),
]


def classify_chunk(content: str, chapter_title: str | None = None) -> str:
    """Determine the content_type for a chunk based on text patterns.

    Returns one of: "rule", "encounter", "monster", "npc", "lore", "book"
    Priority: monster > npc > encounter > rule > lore
    """
    # Check chapter title hints first
    if chapter_title:
        title_lower = chapter_title.lower()
        if any(kw in title_lower for kw in ["monster", "bestiary", "creature", "appendix: monster"]):
            return "monster"
        if any(kw in title_lower for kw in ["rule", "combat", "spell", "ability", "equipment", "class", "race"]):
            return "rule"
        if any(kw in title_lower for kw in ["appendix: npc", "dramatis personae", "cast of characters"]):
            return "npc"

    # Check content patterns
    monster_score = sum(1 for p in _MONSTER_PATTERNS if p.search(content))
    if monster_score >= 2:
        return "monster"

    npc_score = sum(1 for p in _NPC_PATTERNS if p.search(content))
    if npc_score >= 2:
        return "npc"

    encounter_score = sum(1 for p in _ENCOUNTER_PATTERNS if p.search(content))
    if encounter_score >= 2:
        return "encounter"

    rule_score = sum(1 for p in _RULE_PATTERNS if p.search(content))
    if rule_score >= 2:
        return "rule"

    # Default to "lore" for game content that doesn't match specific patterns
    return "lore"


def tag_chunks(
    conn: psycopg.Connection,
    book_id: str,
    default_type: str = "lore",
) -> dict[str, int]:
    """Tag all chunks for a book with content_type based on their content.

    Returns a dict of {content_type: count} showing how many chunks got each tag.
    """
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, content, chapter_title FROM chunks WHERE book_id = %s",
            (book_id,),
        )
        rows = cur.fetchall()

    counts: dict[str, int] = {}
    with conn.cursor() as cur:
        for row in rows:
            content_type = classify_chunk(row["content"], row["chapter_title"])
            # Fall back to default_type if classification returns generic "lore"
            # and caller specified something different
            if content_type == "lore" and default_type != "lore":
                content_type = default_type

            cur.execute(
                "UPDATE chunks SET content_type = %s WHERE id = %s",
                (content_type, row["id"]),
            )
            counts[content_type] = counts.get(content_type, 0) + 1

    conn.commit()
    return counts


def ingest_game_content(
    file_path: Path,
    title: str,
    content_type: str,
    settings: Settings,
    conn: psycopg.Connection,
    embedding_provider: EmbeddingProvider,
) -> dict:
    """Ingest a game document (rulebook, adventure, etc.) with content tagging.

    This wraps the bookworm ingestion pipeline and then runs the content
    tagger to classify each chunk.

    Args:
        file_path: Path to the .txt file
        title: Document title (e.g. "D&D 5e Basic Rules")
        content_type: Default content type ("rule", "encounter", "lore", etc.)
        settings: BookWorm settings
        conn: Database connection
        embedding_provider: Embedding provider

    Returns:
        Dict with book_id and content_type counts.
    """
    # Step 1: Use existing bookworm ingestion pipeline
    book_meta = ingest_book(file_path, title, settings, conn, embedding_provider)
    book_id = book_meta.id

    # Step 2: Tag chunks with content_type
    counts = tag_chunks(conn, book_id, default_type=content_type)

    return {
        "book_id": book_id,
        "title": title,
        "content_type_counts": counts,
    }
