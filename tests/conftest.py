"""Shared test fixtures."""

import pytest
from pathlib import Path
import tempfile


@pytest.fixture
def tmp_book(tmp_path: Path) -> Path:
    """A minimal book .txt file with two chapters."""
    text = """Chapter 1: The Beginning

This is the first paragraph of chapter one. It contains some text that
we can use for testing the reader and chunker components.

This is the second paragraph. It talks about something different but
is still part of chapter one.

Chapter 2: The Middle

This is chapter two. It has its own content that is separate from
chapter one. We use this to test chapter boundary detection.

Another paragraph in chapter two with more content.
"""
    file_path = tmp_path / "test_book.txt"
    file_path.write_text(text)
    return file_path


@pytest.fixture
def gutenberg_book(tmp_path: Path) -> Path:
    """A book file with Gutenberg header/footer markers."""
    text = """The Project Gutenberg eBook of Test Book

*** START OF THE PROJECT GUTENBERG EBOOK TEST BOOK ***

Chapter I

Content of the first chapter.

Second paragraph of chapter one.

Chapter II: The Return

Content of the second chapter.

*** END OF THE PROJECT GUTENBERG EBOOK TEST BOOK ***

End of the Project Gutenberg EBook of Test Book
"""
    file_path = tmp_path / "gutenberg_book.txt"
    file_path.write_text(text)
    return file_path
