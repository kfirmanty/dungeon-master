"""Tests for Markdown file reading and chapter detection."""

import tempfile
from pathlib import Path

import pytest

from bookworm.ingestion.reader import (
    _detect_chapters_markdown,
    _strip_markdown,
    read_book,
)


class TestStripMarkdown:
    def test_strip_bold(self):
        assert _strip_markdown("This is **bold** text") == "This is bold text"

    def test_strip_italic(self):
        assert _strip_markdown("This is *italic* text") == "This is italic text"

    def test_strip_bold_italic(self):
        assert _strip_markdown("This is ***bold italic*** text") == "This is bold italic text"

    def test_strip_underscore_bold(self):
        assert _strip_markdown("This is __bold__ text") == "This is bold text"

    def test_strip_strikethrough(self):
        assert _strip_markdown("This is ~~deleted~~ text") == "This is deleted text"

    def test_strip_link_keep_text(self):
        assert _strip_markdown("Click [here](https://example.com) now") == "Click here now"

    def test_strip_image_keep_alt(self):
        assert _strip_markdown("See ![a dragon](img.png) above") == "See a dragon above"

    def test_strip_image_no_alt(self):
        assert _strip_markdown("See ![](img.png) above") == "See  above"

    def test_strip_inline_code(self):
        assert _strip_markdown("Run `pip install` now") == "Run pip install now"

    def test_strip_code_block(self):
        text = "Before\n```python\ndef foo():\n    pass\n```\nAfter"
        result = _strip_markdown(text)
        assert "```" not in result
        assert "def foo():" in result

    def test_strip_html_tags(self):
        assert _strip_markdown("This is <b>bold</b> text") == "This is bold text"

    def test_strip_header_markers(self):
        result = _strip_markdown("# Title\n\nSome text\n\n## Section\n\nMore text")
        assert "#" not in result
        assert "Title" in result
        assert "Section" in result

    def test_strip_horizontal_rule(self):
        result = _strip_markdown("Above\n---\nBelow")
        assert "---" not in result
        assert "Above" in result
        assert "Below" in result

    def test_preserves_plain_text(self):
        text = "This is just plain text with no markdown."
        assert _strip_markdown(text) == text


class TestDetectChaptersMarkdown:
    def test_h1_chapters(self):
        text = "# Introduction\n\nSome intro text.\n\n# The Journey Begins\n\nChapter content here."
        chapters = _detect_chapters_markdown(text)
        assert len(chapters) == 2
        assert chapters[0].title == "Introduction"
        assert chapters[1].title == "The Journey Begins"
        assert "Some intro text" in chapters[0].content
        assert "Chapter content here" in chapters[1].content

    def test_h2_chapters(self):
        text = "## Part One\n\nFirst part.\n\n## Part Two\n\nSecond part."
        chapters = _detect_chapters_markdown(text)
        assert len(chapters) == 2
        assert chapters[0].title == "Part One"
        assert chapters[1].title == "Part Two"

    def test_mixed_h1_h2(self):
        text = "# Act I\n\nAct one content.\n\n## Scene 1\n\nScene content.\n\n# Act II\n\nAct two."
        chapters = _detect_chapters_markdown(text)
        assert len(chapters) == 3

    def test_chapter_numbering(self):
        """Headers without explicit chapter numbers get auto-numbered."""
        text = "# The Beginning\n\nStart.\n\n# The Middle\n\nMiddle.\n\n# The End\n\nEnd."
        chapters = _detect_chapters_markdown(text)
        assert chapters[0].number == 1
        assert chapters[1].number == 2
        assert chapters[2].number == 3

    def test_explicit_chapter_number_in_header(self):
        """'# Chapter 3: The Cave' should extract number=3, title='The Cave'."""
        text = "# Chapter 3: The Cave\n\nDark and damp.\n\n# Chapter 4: The Dragon\n\nFire!"
        chapters = _detect_chapters_markdown(text)
        assert chapters[0].number == 3
        assert chapters[0].title == "The Cave"
        assert chapters[1].number == 4
        assert chapters[1].title == "The Dragon"

    def test_no_headers_returns_empty(self):
        text = "Just some text without any markdown headers."
        chapters = _detect_chapters_markdown(text)
        assert chapters == []

    def test_h3_not_treated_as_chapter(self):
        """Only H1 and H2 are chapter boundaries, not H3+."""
        text = "# Main\n\nContent.\n\n### Subsection\n\nSub content."
        chapters = _detect_chapters_markdown(text)
        assert len(chapters) == 1
        assert "Sub content" in chapters[0].content

    def test_empty_sections_skipped(self):
        text = "# Title Only\n\n# Another with content\n\nSome text."
        chapters = _detect_chapters_markdown(text)
        # First section has no content, should be skipped
        assert all(c.content.strip() for c in chapters)


class TestReadBookMarkdown:
    def test_read_md_file(self):
        content = "# Chapter 1: Arrival\n\nYou arrive at the **dark castle**.\n\n# Chapter 2: Exploration\n\nThe halls are [cold](link) and empty."
        with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False, encoding="utf-8") as f:
            f.write(content)
            path = Path(f.name)

        try:
            full_text, chapters = read_book(path)
            assert len(chapters) == 2
            assert chapters[0].title == "Arrival"
            assert "dark castle" in chapters[0].content
            assert "**" not in chapters[0].content  # markdown stripped
            assert "[cold](link)" not in chapters[1].content  # link stripped
            assert "cold" in chapters[1].content  # text preserved
        finally:
            path.unlink()

    def test_read_txt_file_unchanged(self):
        """Plain text files should still work as before."""
        content = "CHAPTER I. The Beginning\n\nOnce upon a time.\n\nCHAPTER II. The End\n\nThey lived."
        with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False, encoding="utf-8") as f:
            f.write(content)
            path = Path(f.name)

        try:
            full_text, chapters = read_book(path)
            assert len(chapters) == 2
            assert chapters[0].number == 1
        finally:
            path.unlink()

    def test_md_without_headers_single_chapter(self):
        """Markdown without headers should fall back to single chapter."""
        content = "Just some **bold** text without headers."
        with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False, encoding="utf-8") as f:
            f.write(content)
            path = Path(f.name)

        try:
            full_text, chapters = read_book(path)
            assert len(chapters) == 1
            assert "bold" in chapters[0].content
            assert "**" not in chapters[0].content
        finally:
            path.unlink()
