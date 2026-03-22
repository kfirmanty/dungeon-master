"""
Text file reader with chapter detection.

Supports both plain text (.txt) and Markdown (.md) files.
This module handles the first step of the RAG ingestion pipeline:
turning a raw text file into structured Chapter objects.
"""

import re
from pathlib import Path

from bookworm.models import Chapter


# --- Plain text patterns ---

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

# --- Markdown patterns ---

# Matches Markdown H1/H2 headers: "# Title" or "## Title"
_MD_HEADING = re.compile(
    r"^(#{1,2})\s+(.+)$",
)

# Markdown formatting patterns for stripping
_MD_IMAGE = re.compile(r"!\[([^\]]*)\]\([^)]+\)")  # ![alt](url) → alt text
_MD_LINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")  # [text](url) → text
_MD_BOLD_ITALIC = re.compile(r"\*{1,3}(.+?)\*{1,3}")  # ***bold italic*** → text
_MD_UNDERLINE_BOLD = re.compile(r"_{1,3}(.+?)_{1,3}")  # ___bold___ → text
_MD_STRIKETHROUGH = re.compile(r"~~(.+?)~~")  # ~~text~~ → text
_MD_INLINE_CODE = re.compile(r"`([^`]+)`")  # `code` → code
_MD_CODE_BLOCK = re.compile(r"```[\s\S]*?```", re.MULTILINE)  # fenced code blocks
_MD_HTML_TAG = re.compile(r"<[^>]+>")  # <tag> → remove
_MD_HEADER_MARKER = re.compile(r"^#{1,6}\s+", re.MULTILINE)  # strip leading #'s


def _strip_gutenberg(text: str) -> str:
    """Remove Project Gutenberg headers and footers."""
    start_match = _GUTENBERG_START.search(text)
    if start_match:
        text = text[start_match.end():]

    end_match = _GUTENBERG_END.search(text)
    if end_match:
        text = text[:end_match.start()]

    return text.strip()


def _strip_markdown(text: str) -> str:
    """Convert Markdown to clean prose for embedding.

    Strips formatting while preserving the actual content:
    - Images → alt text (or removed if no alt)
    - Links → link text only
    - Bold/italic/strikethrough → plain text
    - Code blocks → content without fences
    - HTML tags → removed
    - Header markers → removed (headers detected separately for chapters)
    """
    # Remove fenced code blocks first (preserve content between fences)
    text = _MD_CODE_BLOCK.sub(lambda m: m.group(0).strip("`").strip(), text)

    # Images: keep alt text
    text = _MD_IMAGE.sub(r"\1", text)

    # Links: keep link text
    text = _MD_LINK.sub(r"\1", text)

    # Bold/italic/strikethrough: keep inner text
    text = _MD_BOLD_ITALIC.sub(r"\1", text)
    text = _MD_UNDERLINE_BOLD.sub(r"\1", text)
    text = _MD_STRIKETHROUGH.sub(r"\1", text)

    # Inline code: keep content
    text = _MD_INLINE_CODE.sub(r"\1", text)

    # HTML tags: remove
    text = _MD_HTML_TAG.sub("", text)

    # Strip header markers (# ## ### etc.) — we detect these separately
    text = _MD_HEADER_MARKER.sub("", text)

    # Clean up horizontal rules (--- or ***)
    text = re.sub(r"^[-*_]{3,}\s*$", "", text, flags=re.MULTILINE)

    # Clean up excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def _parse_chapter_number(raw: str) -> int | None:
    """Convert chapter number strings to integers.

    Handles digits ("3"), roman numerals ("IV"), and common words ("One").
    Returns None if we can't parse it.
    """
    if raw.isdigit():
        return int(raw)

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


def _detect_chapters_plaintext(text: str) -> list[Chapter]:
    """Detect chapters using plain text heading patterns (Chapter N, Part N)."""
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
        start = line_num + 1
        end = chapter_starts[idx + 1][0] if idx + 1 < len(chapter_starts) else len(lines)
        content = "\n".join(lines[start:end]).strip()
        chapters.append(Chapter(number=number, title=title, content=content))

    return chapters


def _detect_chapters_markdown(text: str) -> list[Chapter]:
    """Detect chapters using Markdown H1/H2 headers.

    H1 (# Title) and H2 (## Title) are treated as chapter boundaries.
    The title text is extracted and chapter numbers are parsed from it
    if present (e.g., "# Chapter 3: The Cave" → number=3, title="The Cave").
    """
    lines = text.split("\n")
    chapter_starts: list[tuple[int, int | None, str | None]] = []
    counter = 0

    for i, line in enumerate(lines):
        match = _MD_HEADING.match(line.strip())
        if match:
            level = len(match.group(1))  # 1 for #, 2 for ##
            raw_title = match.group(2).strip()

            # Try to extract a chapter number from the title
            # e.g., "Chapter 3: The Cave" or just "The Cave"
            chapter_match = _CHAPTER_HEADING.match(raw_title)
            if chapter_match:
                number = _parse_chapter_number(chapter_match.group(1))
                title = chapter_match.group(2).strip() if chapter_match.group(2) else raw_title
            else:
                counter += 1
                number = counter
                title = raw_title

            chapter_starts.append((i, number, title))

    if not chapter_starts:
        return []

    chapters = []
    for idx, (line_num, number, title) in enumerate(chapter_starts):
        start = line_num + 1
        end = chapter_starts[idx + 1][0] if idx + 1 < len(chapter_starts) else len(lines)
        content = "\n".join(lines[start:end]).strip()
        if content:  # skip empty sections
            chapters.append(Chapter(number=number, title=title, content=content))

    return chapters


def read_book(file_path: Path) -> tuple[str, list[Chapter]]:
    """Read a text or Markdown file and extract chapters.

    Auto-detects format from file extension:
    - .md: Markdown header detection + formatting stripped
    - .txt (or other): Gutenberg stripping + plain text chapter detection

    Returns:
        A tuple of (full_text, chapters).
        full_text is the cleaned text ready for chunking.
        If no chapters are detected, returns a single Chapter containing all text.
    """
    raw_text = file_path.read_text(encoding="utf-8")
    is_markdown = file_path.suffix.lower() in (".md", ".markdown")

    if is_markdown:
        # Detect chapters from Markdown headers BEFORE stripping formatting
        chapters = _detect_chapters_markdown(raw_text)

        # Strip Markdown formatting from the full text and chapter contents
        clean_text = _strip_markdown(raw_text)
        for chapter in chapters:
            chapter.content = _strip_markdown(chapter.content)
    else:
        # Plain text: strip Gutenberg boilerplate, detect chapters
        clean_text = _strip_gutenberg(raw_text)
        chapters = _detect_chapters_plaintext(clean_text)

    # If no chapter structure is found, treat the whole file as one chapter
    if not chapters:
        chapters = [Chapter(number=None, title=None, content=clean_text)]

    return clean_text, chapters
