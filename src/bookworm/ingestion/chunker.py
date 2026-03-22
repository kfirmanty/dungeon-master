"""
Text chunker: splits book content into overlapping segments for embedding.

WHY CHUNK?
Embedding models work best with short, focused text (a few sentences).
A full chapter is too long and too diffuse — the embedding would be an average
of many unrelated ideas, making similarity search imprecise.

WHY OVERLAP?
Imagine an important idea spans the boundary between two chunks. Without overlap,
chunk A has the first half and chunk B has the second — neither captures the full
idea. Overlap ensures at least one chunk contains the complete thought.
Think of overlapping tiles covering a floor: no gaps between them.

CHARACTER VS TOKEN LENGTH:
We chunk by characters (default 500), not tokens. For English text, 1 token is
roughly 4 characters, so 500 chars ≈ 125 tokens — well within MiniLM's 256-token
limit. If a chunk somehow exceeds the model's token limit, the tokenizer's
truncation=True will silently trim the excess (meaning the tail gets lost).
"""

import re

from bookworm.models import Chapter, Chunk


# Simple sentence boundary: split after . ! or ? followed by whitespace.
# This is imperfect (fails on "Dr. Smith" or "U.S.A.") but good enough for
# book text. A production system would use a proper sentence tokenizer.
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences using simple punctuation rules."""
    parts = _SENTENCE_BOUNDARY.split(text)
    return [s.strip() for s in parts if s.strip()]


def chunk_text(
    chapters: list[Chapter],
    full_text: str,
    chunk_size: int = 500,
    chunk_overlap: int = 100,
) -> list[Chunk]:
    """Split chapter content into overlapping chunks with metadata.

    Algorithm:
    1. For each chapter, split content into paragraphs (on double newlines).
    2. Accumulate paragraphs into a buffer until adding the next one would
       exceed chunk_size.
    3. Emit the buffer as a chunk, then start a new buffer with overlap
       from the end of the previous chunk.
    4. If a single paragraph exceeds chunk_size, fall back to sentence
       splitting within that paragraph.
    """
    chunks: list[Chunk] = []
    chunk_index = 0

    for chapter in chapters:
        paragraphs = [p.strip() for p in chapter.content.split("\n\n") if p.strip()]

        # Expand paragraphs that exceed chunk_size into individual sentences
        expanded: list[str] = []
        for para in paragraphs:
            if len(para) <= chunk_size:
                expanded.append(para)
            else:
                # Paragraph is too big — break into sentences
                expanded.extend(_split_sentences(para))

        if not expanded:
            continue

        buffer: list[str] = []
        buffer_len = 0

        for segment in expanded:
            segment_len = len(segment)

            # Would adding this segment overflow the chunk?
            # +1 accounts for the space/newline between segments
            new_len = buffer_len + segment_len + (1 if buffer else 0)

            if buffer and new_len > chunk_size:
                # Emit current buffer as a chunk
                chunk_text_str = " ".join(buffer)
                start_char = full_text.find(buffer[0], max(0, chunks[-1].start_char) if chunks else 0)
                if start_char == -1:
                    start_char = 0
                end_char = start_char + len(chunk_text_str)

                chunks.append(Chunk(
                    content=chunk_text_str,
                    chapter_title=chapter.title,
                    chapter_number=chapter.number,
                    chunk_index=chunk_index,
                    start_char=start_char,
                    end_char=end_char,
                ))
                chunk_index += 1

                # Overlap: keep text from the tail of the emitted chunk.
                # Walk backwards through the buffer to collect ~chunk_overlap chars.
                overlap_text = _build_overlap(buffer, chunk_overlap)
                buffer = [overlap_text] if overlap_text else []
                buffer_len = len(overlap_text) if overlap_text else 0

            buffer.append(segment)
            buffer_len += segment_len + (1 if len(buffer) > 1 else 0)

        # Emit remaining buffer
        if buffer:
            chunk_text_str = " ".join(buffer)
            start_char = full_text.find(buffer[0], max(0, chunks[-1].start_char) if chunks else 0)
            if start_char == -1:
                start_char = 0
            end_char = start_char + len(chunk_text_str)

            chunks.append(Chunk(
                content=chunk_text_str,
                chapter_title=chapter.title,
                chapter_number=chapter.number,
                chunk_index=chunk_index,
                start_char=start_char,
                end_char=end_char,
            ))
            chunk_index += 1

    return chunks


def _build_overlap(buffer: list[str], overlap_size: int) -> str:
    """Extract the last ~overlap_size characters from the buffer segments.

    We walk backwards through segments to avoid cutting words mid-segment.
    """
    if overlap_size <= 0:
        return ""

    collected: list[str] = []
    total = 0

    for segment in reversed(buffer):
        if total + len(segment) > overlap_size and collected:
            break
        collected.append(segment)
        total += len(segment) + 1  # +1 for the joining space

    collected.reverse()
    return " ".join(collected)
