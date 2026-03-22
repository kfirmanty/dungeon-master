# PRD-02: BookWorm RAG System

## Purpose

BookWorm is the RAG (Retrieval-Augmented Generation) foundation that powers the Dungeon Master's knowledge. It ingests text documents, creates vector embeddings, stores them in PostgreSQL with pgvector, and retrieves relevant passages to ground LLM responses in source material.

## Functional Requirements

### FR-01: Text Ingestion
- Accept `.txt` and `.md` (Markdown) files as input
- Auto-detect format from file extension
- **Plain text (.txt)**: Strip Project Gutenberg headers/footers, detect chapters via "Chapter N" / "Part N" regex
- **Markdown (.md)**: Detect chapters from H1/H2 headers (`# Title`, `## Section`), strip formatting (bold, italic, links, images, code blocks, HTML tags) while preserving content
- Fall back to treating the entire file as one chapter if no headings detected
- Split chapters into overlapping chunks respecting paragraph boundaries
- Default chunk size: 500 characters, overlap: 100 characters

### FR-02: Embedding Generation
- Generate 384-dimensional embeddings using `sentence-transformers/all-MiniLM-L6-v2`
- Manual transformer pipeline: tokenize, forward pass, mean pooling, L2 normalization
- Batch processing (32 chunks per batch) for efficiency
- Lazy model loading (first use, not import time)

### FR-03: Vector Storage
- Store embeddings in PostgreSQL using pgvector's `vector(384)` column type
- IVFFlat index with cosine distance operator (`<=>`) for approximate nearest neighbor search
- Each chunk stores: content, chapter metadata, character offsets, embedding, content_type

### FR-04: Similarity Search
- Embed user query with the same model used for chunks
- Find top-K chunks by cosine similarity (default K=5)
- Optional filtering by `book_id` and/or `content_type`
- Return results with similarity scores (0-1 range)

### FR-05: RAG Query Pipeline
- Assemble prompt: system instructions + retrieved context chunks + user question
- Question placed last in prompt (lost-in-the-middle effect mitigation)
- Context chunks labeled with chapter info for attribution
- LLM generates answer grounded in retrieved context

### FR-06: LLM Provider
- Protocol-based interface supporting multiple implementations
- Three methods: `generate()` (simple), `generate_chat()` (multi-turn), `generate_stream()` (token streaming)
- Default implementation: Ollama REST API (`/api/chat` endpoint)
- 300-second timeout for CPU-only inference
- Graceful error messages for connection issues and missing models

### FR-07: CLI Interface
- `bookworm ingest --title "Title" file.txt` — ingest a book
- `bookworm ask "question"` — query most recent book
- `bookworm ask --book "Title" "question"` — query specific book
- `bookworm list` — list ingested books
- `bookworm remove --title "Title"` — delete a book and its chunks

## Non-Functional Requirements

- **NFR-01**: No LangChain or high-level RAG frameworks — built from scratch for learning
- **NFR-02**: All provider interfaces use Python Protocols (structural typing)
- **NFR-03**: Database operations use raw SQL (no ORM)
- **NFR-04**: Fail gracefully with actionable error messages

## Key Files

| File | Responsibility |
|------|---------------|
| `src/bookworm/ingestion/reader.py` | .txt parsing, Gutenberg stripping, chapter detection |
| `src/bookworm/ingestion/chunker.py` | Paragraph-aware text splitting with overlap |
| `src/bookworm/ingestion/pipeline.py` | Orchestrate: read, chunk, embed, store |
| `src/bookworm/embeddings/base.py` | `EmbeddingProvider` Protocol |
| `src/bookworm/embeddings/local.py` | HuggingFace transformer implementation |
| `src/bookworm/llm/base.py` | `LLMProvider` Protocol |
| `src/bookworm/llm/ollama.py` | Ollama HTTP implementation |
| `src/bookworm/retrieval/search.py` | pgvector similarity search wrapper |
| `src/bookworm/retrieval/pipeline.py` | Full RAG query: embed, search, prompt, generate |
| `src/bookworm/db/connection.py` | PostgreSQL connection management |
| `src/bookworm/db/migrations.py` | Schema creation (books, chunks, IVFFlat index) |
| `src/bookworm/db/repository.py` | Raw SQL CRUD operations |
| `src/bookworm/config.py` | Settings via pydantic-settings |
| `src/bookworm/models.py` | Domain dataclasses (Chapter, Chunk, ChunkResult, QueryResult) |

## Acceptance Criteria

1. A .txt file can be ingested and queried within one pipeline run
2. Queries return relevant passages with chapter attribution
3. Embedding model loads lazily and produces consistent 384-dim vectors
4. pgvector cosine search returns results ordered by relevance
5. System handles missing Docker services with clear error messages
