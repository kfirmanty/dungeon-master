"""Tests for the text reader module."""

from pathlib import Path

from bookworm.ingestion.reader import read_book


class TestChapterDetection:
    def test_detects_numbered_chapters(self, tmp_book: Path):
        _, chapters = read_book(tmp_book)
        assert len(chapters) == 2
        assert chapters[0].number == 1
        assert chapters[0].title == "The Beginning"
        assert chapters[1].number == 2
        assert chapters[1].title == "The Middle"

    def test_chapter_content_is_extracted(self, tmp_book: Path):
        _, chapters = read_book(tmp_book)
        assert "first paragraph" in chapters[0].content
        assert "chapter two" in chapters[1].content

    def test_chapters_dont_leak_content(self, tmp_book: Path):
        """Chapter 1 should NOT contain chapter 2's text and vice versa."""
        _, chapters = read_book(tmp_book)
        assert "chapter two" not in chapters[0].content
        assert "first paragraph" not in chapters[1].content

    def test_roman_numeral_chapters(self, gutenberg_book: Path):
        _, chapters = read_book(gutenberg_book)
        assert len(chapters) == 2
        assert chapters[0].number == 1
        assert chapters[1].number == 2
        assert chapters[1].title == "The Return"

    def test_no_chapters_fallback(self, tmp_path: Path):
        """When no chapter headings are found, treat entire text as one chapter."""
        file_path = tmp_path / "no_chapters.txt"
        file_path.write_text("Just some text without any chapter headings.\n\nAnother paragraph.")
        _, chapters = read_book(file_path)
        assert len(chapters) == 1
        assert chapters[0].number is None
        assert chapters[0].title is None
        assert "Just some text" in chapters[0].content


class TestGutenbergStripping:
    def test_strips_gutenberg_markers(self, gutenberg_book: Path):
        full_text, _ = read_book(gutenberg_book)
        assert "Project Gutenberg" not in full_text
        assert "*** START" not in full_text
        assert "*** END" not in full_text

    def test_preserves_book_content(self, gutenberg_book: Path):
        full_text, _ = read_book(gutenberg_book)
        assert "Content of the first chapter" in full_text

    def test_no_gutenberg_markers_passthrough(self, tmp_book: Path):
        """Files without Gutenberg markers are returned as-is."""
        full_text, _ = read_book(tmp_book)
        assert "first paragraph" in full_text
