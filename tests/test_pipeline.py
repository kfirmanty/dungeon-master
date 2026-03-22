"""Tests for the ingestion and retrieval pipelines.

Uses a mock LLM provider for deterministic, fast testing.
"""

import pytest
from pathlib import Path

from bookworm.ingestion.reader import read_book
from bookworm.ingestion.chunker import chunk_text
from bookworm.config import Settings


class MockLLMProvider:
    """A fake LLM that echoes back the question — useful for testing the
    pipeline plumbing without needing a real Ollama instance."""

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        return f"Mock answer. System prompt length: {len(system_prompt)}, User prompt length: {len(user_prompt)}"


class TestIngestionPipelineUnit:
    """Test the ingestion pipeline components without a database."""

    def test_full_read_and_chunk_flow(self, tmp_book: Path):
        """Verify that reader + chunker produce meaningful chunks."""
        full_text, chapters = read_book(tmp_book)
        assert len(chapters) >= 1

        chunks = chunk_text(chapters, full_text, chunk_size=200, chunk_overlap=50)
        assert len(chunks) >= 1
        assert all(c.content for c in chunks)
        assert all(c.chunk_index >= 0 for c in chunks)

    def test_chunk_metadata_traces_back_to_chapters(self, tmp_book: Path):
        full_text, chapters = read_book(tmp_book)
        chunks = chunk_text(chapters, full_text, chunk_size=200, chunk_overlap=50)

        # Every chunk should have chapter metadata from the source chapter
        for chunk in chunks:
            assert chunk.chapter_number is not None or chunk.chapter_title is not None


class TestRetrievalPipelineUnit:
    """Test prompt construction logic without external services."""

    def test_build_user_prompt_format(self):
        from bookworm.retrieval.pipeline import _build_user_prompt
        from bookworm.models import ChunkResult

        sources = [
            ChunkResult(
                content="Elizabeth found Darcy proud and disagreeable.",
                chapter_title="The Assembly",
                chapter_number=3,
                chunk_index=5,
                similarity_score=0.89,
            ),
        ]

        prompt = _build_user_prompt("What did Elizabeth think of Darcy?", sources, "Pride and Prejudice")

        assert "Pride and Prejudice" in prompt
        assert "Chapter 3: The Assembly" in prompt
        assert "Elizabeth found Darcy" in prompt
        assert "What did Elizabeth think of Darcy?" in prompt
        # Question should come after the context
        context_pos = prompt.index("Elizabeth found Darcy")
        question_pos = prompt.index("What did Elizabeth think")
        assert question_pos > context_pos, "Question should come after context (lost-in-the-middle effect)"
