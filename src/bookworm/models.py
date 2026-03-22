"""
Domain data models using plain Python dataclasses.

Why dataclasses instead of Pydantic models?
- Pydantic is great for VALIDATION (config, API input/output) — it parses and
  coerces data from untrusted sources.
- Dataclasses are better for DOMAIN OBJECTS — structured containers for data that
  our own code creates. No need for validation overhead when the data is already
  correct by construction.
- Using both teaches you when to reach for each tool.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class Chapter:
    """A chapter extracted from a book file."""

    number: int | None
    title: str | None
    content: str


@dataclass
class Chunk:
    """A segment of book text, ready to be embedded.

    Each chunk carries metadata about where it came from so we can
    cite sources when answering questions.
    """

    content: str
    chapter_title: str | None
    chapter_number: int | None
    chunk_index: int  # sequential position within the entire book
    start_char: int  # character offset in the original full text
    end_char: int


@dataclass
class BookMetadata:
    """A book record stored in the database."""

    id: UUID
    title: str
    file_path: str
    ingested_at: datetime


@dataclass
class ChunkResult:
    """A chunk returned from a similarity search, with its relevance score."""

    content: str
    chapter_title: str | None
    chapter_number: int | None
    chunk_index: int
    # Cosine similarity: 1.0 = identical direction, 0.0 = unrelated
    similarity_score: float


@dataclass
class QueryResult:
    """The complete answer from a RAG query."""

    answer: str
    sources: list[ChunkResult]
