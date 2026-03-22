# Configuration Reference

All settings are loaded from environment variables or a `.env` file via `pydantic-settings`. Case-insensitive (env vars are UPPER_CASE, Python fields are lower_case).

## BookWorm Settings (`src/bookworm/config.py`)

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://bookworm:bookworm@localhost:5432/bookworm` | PostgreSQL connection string (pgvector-enabled) |
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | HuggingFace model ID for embeddings |
| `EMBEDDING_DIMENSIONS` | `384` | Embedding vector dimensions (must match model) |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama REST API base URL |
| `OLLAMA_MODEL` | `llama3.1:8b` | Ollama model name for LLM generation |
| `OLLAMA_TEMPERATURE` | `0.7` | LLM temperature (0.0 = deterministic, 1.0 = creative) |
| `CHUNK_SIZE` | `500` | Maximum characters per chunk |
| `CHUNK_OVERLAP` | `100` | Character overlap between consecutive chunks |
| `TOP_K` | `5` | Number of chunks to retrieve per similarity search |

## Game Settings (`src/dungeonmaster/config.py`)

Inherits all BookWorm settings and adds:

| Variable | Default | Description |
|----------|---------|-------------|
| `RULES_SYSTEM` | `dnd5e` | Active RPG rules system (maps to engine registry) |
| `WEB_HOST` | `127.0.0.1` | FastAPI server bind address |
| `WEB_PORT` | `8000` | FastAPI server port |
| `MAX_COMPANIONS` | `2` | Maximum AI companion NPCs per session |
| `MAX_CONVERSATION_HISTORY` | `50` | Max narrative entries to retain in memory |
| `AUTO_SAVE_INTERVAL` | `10` | Auto-save game every N turns |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |

## .env Example

```bash
# Database
DATABASE_URL=postgresql://bookworm:bookworm@localhost:5632/bookworm

# Embeddings
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_DIMENSIONS=384

# LLM
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b

# RAG
CHUNK_SIZE=500
CHUNK_OVERLAP=100
TOP_K=5

# Game
RULES_SYSTEM=dnd5e
WEB_HOST=127.0.0.1
WEB_PORT=8000
```

## Docker Compose Services

| Service | Image | Port | Volume | Purpose |
|---------|-------|------|--------|---------|
| `postgres` | `pgvector/pgvector:pg16` | `5632:5432` | `pgdata` | PostgreSQL with pgvector extension |
| `ollama` | `ollama/ollama` | `11434:11434` | `ollama_models` | Local LLM inference |

**Note:** The PostgreSQL port is `5632` (not the default `5432`) to avoid conflicts with local PostgreSQL installations.

## CLI Entry Points

Defined in `pyproject.toml`:

| Command | Module | Purpose |
|---------|--------|---------|
| `bookworm` | `bookworm.main:app` | BookWorm CLI (ingest, ask, list, remove) |
| `dungeonmaster` | `dungeonmaster.web.app:main` | Start FastAPI web server |

## Running

```bash
# Start infrastructure
docker compose up -d

# Pull an LLM model (first time only)
docker exec ollama ollama pull llama3.2:3b

# Install dependencies
uv sync --extra dev

# Run BookWorm CLI
uv run bookworm ingest --title "Dracula" dracula.txt
uv run bookworm ask "Who is Count Dracula?"

# Run Dungeon Master web server
uv run dungeonmaster
# → http://localhost:8000

# Run tests
uv run --extra dev pytest tests/ -v
```
