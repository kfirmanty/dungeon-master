"""
Text file reader with chapter detection.

This module handles the first step of the RAG ingestion pipeline:
turning a raw .txt file into structured Chapter objects.
"""

import re
from pathlib import Path

from bookworm.models import Chapter


# Matches Project Gutenberg start/end markers so we can strip boilerplate
_GUTENBERG_START = re.compile(r"\*\*\* ?START OF .+?\*\*\*", re.IGNORECASE)
_GUTENBERG_END = re.compile(r"\*\*\* ?END OF .+?\*\*\*", re.IGNORECASE)

# Matches common chapter heading patterns:
#   "Chapter 1", "CHAPTER IV", "Chapter 3: The Title", "Chapter One — A Beginning"
# Also handles "Part I", "PART 2", etc.
_CHAPTER_HEADING = re.compile(
    r"^(?:CHAPTER|Chapter|PART|Part)\s+"  # keyword
    r"(\w+)"  # chapter number (digits, roman numerals, or words)
    r"(?:\s*[:\.\-\u2014]\s*(.+))?$",  # optional separator + title
)


def _strip_gutenberg(text: str) -> str:
    """Remove Project Gutenberg headers and footers.

    Gutenberg texts are wrapped with markers like:
        *** START OF THE PROJECT GUTENBERG EBOOK TITLE ***
        ... actual book content ...
        *** END OF THE PROJECT GUTENBERG EBOOK TITLE ***

    Everything outside these markers is license text we don't want to embed.
    """
    start_match = _GUTENBERG_START.search(text)
    if start_match:
        text = text[start_match.end() :]

    # Search for END marker AFTER stripping START, because character positions shift
    end_match = _GUTENBERG_END.search(text)
    if end_match:
        text = text[: end_match.start()]

    return text.strip()


def _parse_chapter_number(raw: str) -> int | None:
    """Convert chapter number strings to integers.

    Handles digits ("3"), roman numerals ("IV"), and common words ("One").
    Returns None if we can't parse it.
    """
    if raw.isdigit():
        return int(raw)

    # Roman numeral mapping (covers most books — up to ~40 chapters)
    roman = {
        "I": 1, "II": 2, "III": 3, "IV": 4, "V": 5,
        "VI": 6, "VII": 7, "VIII": 8, "IX": 9, "X": 10,
        "XI": 11, "XII": 12, "XIII": 13, "XIV": 14, "XV": 15,
        "XVI": 16, "XVII": 17, "XVIII": 18, "XIX": 19, "XX": 20,
        "XXI": 21, "XXII": 22, "XXIII": 23, "XXIV": 24, "XXV": 25,
        "XXVI": 26, "XXVII": 27, "XXVIII": 28, "XXIX": 29, "XXX": 30,
        "XXXI": 31, "XXXII": 32, "XXXIII": 33, "XXXIV": 34, "XXXV": 35,
        "XXXVI": 36, "XXXVII": 37, "XXXVIII": 38, "XXXIX": 39, "XL": 40,
    }
    if raw.upper() in roman:
        return roman[raw.upper()]

    # Word-based numbers
    words = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
        "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
        "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
        "nineteen": 19, "twenty": 20,
    }
    if raw.lower() in words:
        return words[raw.lower()]

    return None


def _detect_chapters(text: str) -> list[Chapter]:
    """Split text into chapters by scanning for heading patterns.

    Strategy: scan each line for a chapter heading regex match. When found,
    everything between this heading and the next one becomes the chapter content.
    """
    lines = text.split("\n")
    chapter_starts: list[tuple[int, int | None, str | None]] = []

    for i, line in enumerate(lines):
        match = _CHAPTER_HEADING.match(line.strip())
        if match:
            number = _parse_chapter_number(match.group(1))
            title = match.group(2).strip() if match.group(2) else None
            chapter_starts.append((i, number, title))

    if not chapter_starts:
        return []

    chapters = []
    for idx, (line_num, number, title) in enumerate(chapter_starts):
        # Chapter content goes from the line after the heading
        # to the line before the next heading (or end of file)
        start = line_num + 1
        end = chapter_starts[idx + 1][0] if idx + 1 < len(chapter_starts) else len(lines)
        content = "\n".join(lines[start:end]).strip()
        chapters.append(Chapter(number=number, title=title, content=content))

    return chapters


def read_book(file_path: Path) -> tuple[str, list[Chapter]]:
    """Read a .txt file and extract chapters.

    Returns:
        A tuple of (full_text, chapters).
        full_text is the cleaned text (Gutenberg markers stripped).
        If no chapters are detected, returns a single Chapter containing all text.
    """
    raw_text = file_path.read_text(encoding="utf-8")
    clean_text = _strip_gutenberg(raw_text)

    chapters = _detect_chapters(clean_text)

    # If no chapter structure is found, treat the whole book as one chapter
    if not chapters:
        chapters = [Chapter(number=None, title=None, content=clean_text)]

    return clean_text, chapters
