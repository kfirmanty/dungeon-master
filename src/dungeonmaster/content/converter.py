"""
Book-to-adventure conversion pipeline.

Takes a novel (e.g. Dracula) and uses the LLM to convert it chapter-by-chapter
into structured RPG adventure content: locations, NPCs, encounters, creatures.

The output is formatted so the content classifier (ingest.py) automatically
tags chunks correctly for filtered RAG retrieval during gameplay.
"""

import logging
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

logger = logging.getLogger(__name__)

from bookworm.config import Settings
from bookworm.embeddings.base import EmbeddingProvider
from bookworm.ingestion.reader import read_book
from bookworm.llm.base import LLMProvider

from dungeonmaster.content.ingest import ingest_game_content


CONVERSION_SYSTEM_PROMPT = """You are an expert RPG adventure designer. Your task is to convert \
a novel chapter into structured tabletop RPG adventure content.

Extract game-relevant elements and format them EXACTLY as shown below. \
Only include sections that have content — skip empty sections entirely.

Use the novel's actual characters, locations, and events. Invent appropriate \
game mechanics (DCs, stats, abilities) that fit the tone and danger level."""


CONVERSION_USER_PROMPT = """Convert this chapter into RPG adventure content.

Book: "{book_title}"
Chapter {chapter_num}: {chapter_title}

--- CHAPTER TEXT ---
{chapter_text}
--- END ---

Format your output EXACTLY like this (skip sections with nothing to extract):

## LOCATIONS

Area 1: [Location Name]
Description: [2-3 vivid sentences a DM would read aloud to players]
Features: [Notable interactive elements, hidden items, environmental hazards]
When the characters arrive: [What happens, who they meet, what they notice]

## NPCs

NPC: [Character Name]
Personality: [2 key traits], Ideal: [1 ideal], Bond: [1 bond], Flaw: [1 flaw]
Roleplaying: [Speech patterns, mannerisms, how to portray them at the table]
Is a [race/class approximation] who [brief role in the story]

## ENCOUNTERS

Encounter: [Descriptive Title]
Trigger: When the characters [specific condition]
Challenge: [Skill checks with specific DCs, combat details, or puzzle description]
Development: [What happens on success vs failure, consequences]
Treasure: [Rewards if applicable]

## CREATURES

[Creature Name]
Armor Class [number] | Hit Points [number] ([dice expression]) | Speed [number] ft
STR [number] DEX [number] CON [number] INT [number] WIS [number] CHA [number]
Challenge [number]
Special: [Unique abilities inspired by the source material]

## LORE

[Any important world-building details, historical events, or setting information
from this chapter that the DM should know but doesn't fit the above categories.]
"""


@dataclass
class ConversionProgress:
    """Tracks progress of a book-to-adventure conversion."""

    total_chapters: int = 0
    current_chapter: int = 0
    current_chapter_title: str = ""
    status: str = "pending"  # pending, converting, ingesting, complete, error
    error: str = ""
    stats: dict = field(default_factory=lambda: {
        "locations": 0,
        "npcs": 0,
        "encounters": 0,
        "creatures": 0,
    })


def convert_book_to_adventure(
    file_path: Path,
    title: str,
    llm: LLMProvider,
    settings: Settings,
    conn,
    embedding_provider: EmbeddingProvider,
    on_progress: Callable[[ConversionProgress], None] | None = None,
) -> dict:
    """Convert a novel into a structured RPG adventure.

    Process:
    1. Read the book and split into chapters
    2. Send each chapter to the LLM with the conversion prompt
    3. Assemble all chapter outputs into one adventure document
    4. Ingest the adventure document through the normal pipeline

    Args:
        file_path: Path to the .txt novel
        title: Adventure title (e.g. "Dracula Adventure")
        llm: LLM provider for conversion
        settings: BookWorm settings
        conn: Database connection
        embedding_provider: For embedding the final adventure
        on_progress: Optional callback for progress updates

    Returns:
        Dict with source_book_id, adventure_book_id, and stats.
    """
    progress = ConversionProgress()

    def _update(status=None, chapter=None, chapter_title=None, error=None):
        if status:
            progress.status = status
        if chapter is not None:
            progress.current_chapter = chapter
        if chapter_title:
            progress.current_chapter_title = chapter_title
        if error:
            progress.error = error
        # Log with timestamp
        msg = f"[{title}] status={progress.status}"
        if progress.current_chapter:
            msg += f" chapter={progress.current_chapter}/{progress.total_chapters}"
        if chapter_title:
            msg += f" ({chapter_title})"
        if error:
            msg += f" error={error}"
        logger.info(msg)
        if on_progress:
            on_progress(progress)

    # Step 1: Read and split into chapters
    _update(status="reading")
    _full_text, chapters = read_book(file_path)
    progress.total_chapters = len(chapters)

    if not chapters:
        _update(status="error", error="No chapters found in the book.")
        return {"error": "No chapters found"}

    # Step 2: Convert each chapter via LLM
    _update(status="converting")
    chapter_outputs: list[str] = []

    for i, chapter in enumerate(chapters):
        chapter_title = chapter.title or f"Chapter {chapter.number or i + 1}"
        _update(chapter=i + 1, chapter_title=chapter_title)

        # Truncate very long chapters to fit in context window
        chapter_text = chapter.content
        if len(chapter_text) > 6000:
            chapter_text = chapter_text[:6000] + "\n\n[... chapter truncated for length ...]"

        prompt = CONVERSION_USER_PROMPT.format(
            book_title=title,
            chapter_num=chapter.number or i + 1,
            chapter_title=chapter_title,
            chapter_text=chapter_text,
        )

        try:
            result = llm.generate_chat([
                {"role": "system", "content": CONVERSION_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ])
            chapter_outputs.append(
                f"# Chapter {chapter.number or i + 1}: {chapter_title}\n\n{result}"
            )

            # Count extracted elements
            progress.stats["locations"] += result.count("Area ")
            progress.stats["npcs"] += result.count("NPC: ")
            progress.stats["encounters"] += result.count("Encounter: ")
            progress.stats["creatures"] += result.count("Armor Class")

        except Exception as e:
            # Log error but continue with other chapters
            chapter_outputs.append(
                f"# Chapter {chapter.number or i + 1}: {chapter_title}\n\n"
                f"[Conversion failed: {e}]\n"
            )

    # Step 3: Assemble into adventure document
    _update(status="assembling")
    adventure_text = f"# {title}\n\nAdventure converted from novel.\n\n"
    adventure_text += "\n\n---\n\n".join(chapter_outputs)

    # Step 4: Write to temp file and ingest
    _update(status="ingesting")
    with tempfile.NamedTemporaryFile(
        suffix=".txt", delete=False, mode="w", encoding="utf-8"
    ) as tmp:
        tmp.write(adventure_text)
        tmp_path = Path(tmp.name)

    try:
        result = ingest_game_content(
            file_path=tmp_path,
            title=title,
            content_type="adventure",
            settings=settings,
            conn=conn,
            embedding_provider=embedding_provider,
        )
    finally:
        tmp_path.unlink(missing_ok=True)

    _update(status="complete")

    return {
        "adventure_book_id": str(result["book_id"]),
        "title": title,
        "content_type_counts": result["content_type_counts"],
        "stats": progress.stats,
        "chapters_processed": len(chapter_outputs),
    }
