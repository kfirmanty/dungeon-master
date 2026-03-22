# Dungeon Master — AI-Powered Solo Tabletop RPG

A local-first, single-player tabletop RPG powered by AI. An AI Game Master narrates your adventure, controls NPC companions, and enforces game rules through a deterministic rules engine — while you explore, fight, and role-play through text.

Built on top of **BookWorm**, a RAG (Retrieval-Augmented Generation) system that ingests rulebooks and adventure content to ground the AI's responses in source material. The rules engine is swappable — D&D 5e ships as default, but the system supports any RPG system via a Protocol interface.

Built from scratch for learning — no LangChain, no black-box frameworks. Every step is implemented manually with educational comments.

## How It Works

```mermaid
sequenceDiagram
    participant P as Player
    participant UI as Web UI
    participant DM as AI Dungeon Master
    participant RAG as RAG Pipeline
    participant RE as Rules Engine
    participant LLM as Ollama LLM

    P->>UI: "I sneak past the guards"
    UI->>DM: WebSocket message

    DM->>RAG: Retrieve rules + adventure context
    DM->>LLM: Generate narrative + [ROLL:...] tags
    LLM-->>UI: Streaming tokens ("The torchlight flickers...")
    LLM-->>DM: [ROLL:skill_check:stealth:DC12:Player]

    DM->>RE: roll_check(character, "skill_check", "stealth", 12)
    RE-->>DM: CheckResult(total=19, success=true)
    DM-->>UI: Dice roll animation

    DM->>LLM: Narrate the outcome
    LLM-->>UI: "You slip between the shadows..."
```

**Key design:** The AI never rolls dice or determines mechanical outcomes. It generates narrative and requests rolls via `[ROLL:...]` tags. The rules engine resolves them deterministically, then the AI narrates the result. This keeps the game fair while letting the AI focus on storytelling.

## Features

- **AI Game Master** — narrates scenes, controls NPCs, runs encounters
- **AI Companions** — 2 party members with distinct personalities controlled by the AI
- **Deterministic Rules Engine** — D&D 5e mechanics (dice, ability checks, combat, death saves)
- **Swappable RPG Systems** — Protocol-based engine supports D&D, WFRP, AD&D, or custom systems
- **RAG-Powered Knowledge** — ingest rulebooks and adventures for grounded responses
- **Book-to-Adventure Conversion** — upload a novel, LLM converts it to a playable RPG adventure
- **Streaming Narrative** — real-time token streaming via WebSocket
- **Dark Fantasy UI** — web-based game interface with character sheet, party panel, dice animations
- **Game Persistence** — save/load games, auto-save every N turns
- **100% Local** — runs on Ollama (local LLM) + PostgreSQL, no API keys needed

## Quick Start

```bash
# 1. Start PostgreSQL (pgvector) and Ollama
docker compose up -d

# 2. Pull an LLM model (first time only)
docker exec ollama ollama pull llama3.2:3b

# 3. Install Python dependencies
uv sync --extra dev

# 4. Start the Dungeon Master web server
uv run dungeonmaster
```

Open **http://localhost:8000** in your browser. You'll see:

1. **Start Screen** — resume a saved game or start new
2. **Adventure Selection** — pick an ingested adventure, upload new content, or play freeplay
3. **Character Creation** — choose name, race, class
4. **Game Screen** — play! Type actions, watch the AI narrate, see dice rolls resolve

## Game Flow

### Playing the Game

Type natural language actions like:
- "I search the chest for traps"
- "I try to persuade the guard to let us pass"
- "I attack the goblin with my longsword"

The AI DM will narrate the scene and request rolls when the outcome is uncertain. The rules engine resolves rolls fairly, then the AI continues the story based on success or failure.

### Adventure Content

Three ways to get adventure content:

1. **Freeplay** — no adventure selected, the DM improvises from LLM knowledge
2. **Upload & Ingest** — upload a pre-formatted adventure module (.txt) for direct RAG retrieval
3. **Convert Book to Adventure** — upload a novel (e.g. Dracula), the LLM extracts locations, NPCs, encounters, and creatures chapter by chapter

### Rules Engine

The D&D 5e engine handles:
- Ability checks, skill checks, saving throws (d20 + modifier vs DC)
- Attack rolls with critical hits (nat 20) and auto-miss (nat 1)
- Damage with resistance/immunity by type
- Death saving throws (nat 20 revives, nat 1 = 2 failures)
- Character creation (9 races + subraces, 12 classes with features)
- Expertise (Rogue/Bard double proficiency)
- Conditions (poisoned, paralyzed, etc. affect rolls automatically)
- Short/long rest (hit dice recovery, spell slot reset)
- Sneak Attack, Rage, Unarmored Defense

To add a different RPG system (WFRP, AD&D), implement the `RulesEngine` Protocol and register it. See `docs/reference/rules-engine-guide.md`.

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│  Frontend (Vanilla HTML/CSS/JS)                          │
│  ┌─────────────┐ ┌──────────┐ ┌─────────┐ ┌──────────┐ │
│  │ Narrative    │ │Character │ │ Party   │ │ Combat   │ │
│  │ Chat Area    │ │ Sheet    │ │ Panel   │ │ Overlay  │ │
│  └──────┬──────┘ └──────────┘ └─────────┘ └──────────┘ │
└─────────┼────────────────────────────────────────────────┘
          │ WebSocket (streaming)
┌─────────┼────────────────────────────────────────────────┐
│  FastAPI │ Backend                                        │
│  ┌──────┴──────┐                                         │
│  │ Game Loop   │──▶ RAG Retrieval (bookworm)             │
│  │ (turn.py)   │──▶ Rules Engine (rules/)                │
│  │             │──▶ AI DM (ai/dm.py → LLM)              │
│  └─────────────┘                                         │
│         │                                                │
│  ┌──────┴──────┐                                         │
│  │ PostgreSQL  │  books, chunks + pgvector,              │
│  │ + pgvector  │  game_sessions, game_log                │
│  └─────────────┘                                         │
└──────────────────────────────────────────────────────────┘
```

Two Python packages under `src/`:

- **`bookworm/`** — RAG foundation (ingestion, embeddings, LLM, retrieval, database)
- **`dungeonmaster/`** — Game layer (rules engine, AI DM, game loop, web UI, content conversion)

`dungeonmaster` imports from `bookworm` through Protocol interfaces — it is a consumer, not a child.

## Project Structure

```
src/
├── bookworm/                          # RAG system (CLI: bookworm)
│   ├── main.py                        # CLI: ingest, ask, list, remove
│   ├── config.py                      # Settings via pydantic-settings
│   ├── models.py                      # Chapter, Chunk, QueryResult
│   ├── ingestion/                     # .txt → chapters → chunks → embeddings → DB
│   ├── embeddings/                    # EmbeddingProvider Protocol + HuggingFace impl
│   ├── llm/                           # LLMProvider Protocol + Ollama impl
│   ├── retrieval/                     # Vector search + RAG query pipeline
│   └── db/                            # PostgreSQL + pgvector (raw SQL)
│
└── dungeonmaster/                     # Game engine (CLI: dungeonmaster)
    ├── config.py                      # GameSettings (extends BookWorm)
    ├── models.py                      # DiceResult, GameSession, Scene, etc.
    ├── rules/                         # Swappable rules engine
    │   ├── base.py                    # RulesEngine Protocol + factory
    │   ├── dice.py                    # Universal dice parser (2d6+3, d20, d100)
    │   └── dnd5e/                     # D&D 5e implementation
    │       ├── engine.py              # DnD5eEngine
    │       ├── abilities.py           # Checks, saves, expertise, conditions
    │       ├── combat.py              # Attacks, damage, initiative, death saves
    │       ├── characters.py          # Creation, rest, level-up
    │       ├── conditions.py          # 15 SRD conditions + mechanical effects
    │       └── data.py               # All SRD constants
    ├── ai/                            # AI Dungeon Master
    │   ├── dm.py                      # DungeonMasterAI orchestrator
    │   ├── prompts.py                 # System prompts (adapts to rules system)
    │   ├── actions.py                 # [ROLL:...] tag parser
    │   └── context.py                 # Conversation history management
    ├── game/                          # Session + turn orchestration
    │   ├── session.py                 # Create, save, load games
    │   └── turn.py                    # Turn resolution loop
    ├── content/                       # Content ingestion + conversion
    │   ├── ingest.py                  # Ingest with content_type tagging
    │   └── converter.py              # Novel → RPG adventure via LLM
    ├── db/                            # Game-specific DB (sessions, log)
    │   ├── migrations.py              # game_sessions, game_log tables
    │   └── repository.py              # Session CRUD, filtered search
    └── web/                           # FastAPI web server
        ├── app.py                     # App factory + entry point
        ├── schemas.py                 # API + WebSocket message types
        ├── routes/                    # REST + WebSocket endpoints
        └── static/                    # HTML/CSS/JS frontend

docs/                                  # Project documentation
├── architecture.md                    # System diagrams (Mermaid)
├── prd/                               # Product requirements (6 PRDs)
├── adr/                               # Architecture decisions (11 ADRs)
└── reference/                         # API, data models, config, rules guide
```

## BookWorm CLI (RAG System)

The RAG system also works standalone for book Q&A:

```bash
# Ingest a book
uv run bookworm ingest --title "Dracula" dracula.txt

# Ask questions
uv run bookworm ask "Who is Count Dracula?"
uv run bookworm ask --book "Dracula" "What happens in Jonathan's journal?"

# Manage books
uv run bookworm list
uv run bookworm remove --title "Dracula"
```

## Configuration

All settings via environment variables or `.env` file:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://bookworm:bookworm@localhost:5632/bookworm` | PostgreSQL connection |
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | HuggingFace embedding model |
| `EMBEDDING_DIMENSIONS` | `384` | Vector dimensions |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API endpoint |
| `OLLAMA_MODEL` | `llama3.1:8b` | LLM model name |
| `CHUNK_SIZE` | `500` | Chunk size in characters |
| `CHUNK_OVERLAP` | `100` | Overlap between chunks |
| `TOP_K` | `5` | Chunks to retrieve per search |
| `RULES_SYSTEM` | `dnd5e` | Active RPG rules system |
| `WEB_HOST` | `127.0.0.1` | Web server bind address |
| `WEB_PORT` | `8000` | Web server port |
| `AUTO_SAVE_INTERVAL` | `10` | Auto-save every N turns |

## Running Tests

```bash
# BookWorm unit tests (no Docker needed)
uv run --extra dev pytest tests/test_reader.py tests/test_chunker.py tests/test_pipeline.py -v

# Rules engine tests (no Docker needed)
uv run --extra dev pytest tests/test_dice.py tests/test_dnd5e_abilities.py tests/test_dnd5e_combat.py tests/test_dnd5e_characters.py tests/test_dnd5e_engine.py tests/test_srd_mechanics.py -v

# Action parser tests
uv run --extra dev pytest tests/test_actions.py -v

# All tests
uv run --extra dev pytest -v
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.12+ |
| Package Manager | uv |
| LLM | Ollama (local, CPU or GPU) |
| Embeddings | sentence-transformers/all-MiniLM-L6-v2 (384-dim, local) |
| Vector DB | PostgreSQL 16 + pgvector |
| Web Framework | FastAPI + WebSocket |
| Frontend | Vanilla HTML/CSS/JS (no framework, no build step) |
| CLI | Typer |
| Config | pydantic-settings |
| Testing | pytest |

## Documentation

Comprehensive docs in `docs/`:

- **PRDs** — Product requirements for each subsystem
- **ADRs** — Architecture decision records (why Protocol over ABC, why no LangChain, etc.)
- **Reference** — API endpoints, data models, configuration, rules engine implementation guide
- **Architecture** — System diagrams with Mermaid

See `docs/reference/rules-engine-guide.md` for how to add a new RPG system (full WFRP example included).

## Prerequisites

- Python 3.12+
- Docker and Docker Compose
- ~5GB disk space (Ollama model + embedding model)
