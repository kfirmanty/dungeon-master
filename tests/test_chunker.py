"""Tests for the text chunker module."""

from bookworm.ingestion.chunker import chunk_text
from bookworm.models import Chapter


def _make_chapter(content: str, number: int = 1, title: str = "Test") -> Chapter:
    return Chapter(number=number, title=title, content=content)


class TestBasicChunking:
    def test_short_text_produces_single_chunk(self):
        chapter = _make_chapter("A short paragraph.")
        chunks = chunk_text([chapter], "A short paragraph.", chunk_size=500)
        assert len(chunks) == 1
        assert chunks[0].content == "A short paragraph."

    def test_long_text_produces_multiple_chunks(self):
        # 5 paragraphs, each ~60 chars -> total ~300 chars
        # With chunk_size=150, should produce at least 2 chunks
        paras = ["Paragraph number {i} has some content here.".format(i=i) for i in range(5)]
        content = "\n\n".join(paras)
        chapter = _make_chapter(content)
        chunks = chunk_text([chapter], content, chunk_size=150, chunk_overlap=0)
        assert len(chunks) >= 2

    def test_chunk_indices_are_sequential(self):
        paras = ["Paragraph {i} with enough text to fill a chunk.".format(i=i) for i in range(10)]
        content = "\n\n".join(paras)
        chapter = _make_chapter(content)
        chunks = chunk_text([chapter], content, chunk_size=100, chunk_overlap=0)
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i


class TestMetadataPreservation:
    def test_chapter_metadata_propagated(self):
        chapter = _make_chapter("Some content.", number=3, title="The Title")
        chunks = chunk_text([chapter], "Some content.", chunk_size=500)
        assert chunks[0].chapter_number == 3
        assert chunks[0].chapter_title == "The Title"

    def test_multiple_chapters_have_correct_metadata(self):
        ch1 = _make_chapter("Content of chapter one.", number=1, title="First")
        ch2 = _make_chapter("Content of chapter two.", number=2, title="Second")
        full_text = "Content of chapter one.\n\nContent of chapter two."
        chunks = chunk_text([ch1, ch2], full_text, chunk_size=500)
        assert chunks[0].chapter_number == 1
        assert chunks[-1].chapter_number == 2


class TestOverlap:
    def test_overlap_produces_more_chunks(self):
        """Overlap means each chunk "rewinds", so we get more chunks total."""
        paras = ["This is paragraph number {i} with text.".format(i=i) for i in range(10)]
        content = "\n\n".join(paras)
        chapter = _make_chapter(content)

        no_overlap = chunk_text([chapter], content, chunk_size=120, chunk_overlap=0)
        with_overlap = chunk_text([chapter], content, chunk_size=120, chunk_overlap=40)
        assert len(with_overlap) >= len(no_overlap)


class TestEdgeCases:
    def test_empty_text(self):
        chapter = _make_chapter("")
        chunks = chunk_text([chapter], "", chunk_size=500)
        assert len(chunks) == 0

    def test_single_paragraph(self):
        text = "Just one paragraph with no double newlines."
        chapter = _make_chapter(text)
        chunks = chunk_text([chapter], text, chunk_size=500)
        assert len(chunks) == 1

    def test_paragraph_exceeding_chunk_size(self):
        """A single very long paragraph should be split by sentences."""
        sentences = ["Sentence number {i} is here.".format(i=i) for i in range(20)]
        long_para = " ".join(sentences)  # one paragraph, ~500+ chars
        chapter = _make_chapter(long_para)
        chunks = chunk_text([chapter], long_para, chunk_size=100, chunk_overlap=0)
        assert len(chunks) >= 2
