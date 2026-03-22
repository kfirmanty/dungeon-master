# PRD-01: Product Overview

## Vision

Dungeon Master is a local-first, single-player tabletop RPG powered by AI. A player creates a character, selects (or generates) an adventure, and plays through it with an AI Game Master that narrates the story, controls NPCs and companions, and enforces game rules through a deterministic rules engine.

## Goals

1. **Playable solo tabletop RPG** — full D&D 5e experience for one player with AI-controlled party members
2. **RPG-system-agnostic** — swappable rules engine supports D&D 5e, AD&D, WFRP, or custom systems
3. **Content-driven** — ingest any adventure module or novel and play through it
4. **Local-first** — runs entirely on local hardware (Ollama LLM, local embeddings, PostgreSQL)
5. **Educational** — every component built from scratch (no LangChain) with clear, documented code

## User Stories

### Core Gameplay
- As a player, I want to create a character with a name, race, and class so I can begin an adventure
- As a player, I want to type natural language actions ("I search the chest for traps") and receive narrative responses
- As a player, I want dice rolls to be fair and deterministic, handled by a programmatic engine rather than the AI
- As a player, I want AI-controlled companions who act in character and make tactical decisions

### Content
- As a player, I want to select from ingested adventure modules before starting a game
- As a player, I want to upload a novel and have it converted into a playable RPG adventure
- As a player, I want to play in "freeplay" mode where the DM improvises without source material

### Persistence
- As a player, I want to save my game and resume it later
- As a player, I want to see a list of my saved games on the start screen

## Scope

### In Scope
- Single-player gameplay with AI DM + AI companions
- D&D 5e rules (default), with Protocol for other systems
- Web-based UI (FastAPI + vanilla HTML/JS)
- RAG-powered context retrieval from ingested content
- Book-to-adventure conversion pipeline
- Game state persistence (PostgreSQL)
- Streaming narrative via WebSocket

### Out of Scope (Future)
- Multiplayer / shared sessions
- Voice input/output
- Image generation for scenes
- Mobile native app
- Cloud deployment / hosted service
- Character leveling across sessions
- Full spell system implementation

## Tech Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Language | Python 3.12+ | AI ecosystem, type hints, Protocol support |
| Package Manager | uv | Fast, reliable Python dependency management |
| LLM | Ollama (local) | Free, offline, no API keys |
| Embeddings | sentence-transformers/all-MiniLM-L6-v2 | Small (90MB), fast, 384-dim, local |
| Vector DB | PostgreSQL 16 + pgvector | Mature, combines relational + vector in one DB |
| Web Framework | FastAPI | Async-capable, WebSocket support, auto-docs |
| Frontend | Vanilla HTML/CSS/JS | No build step, no framework, educational simplicity |
| CLI | Typer | Type-safe CLI with minimal boilerplate |
| Config | pydantic-settings | Validated env vars with defaults |

## Project Structure

Two Python packages under `src/`:

- **`bookworm/`** — RAG foundation (ingestion, embeddings, LLM, retrieval, database)
- **`dungeonmaster/`** — Game layer (rules engine, AI DM, game loop, web UI, content conversion)

`dungeonmaster` imports from `bookworm` through Protocol interfaces — it is a consumer, not a child package.
