# System Architecture

## Overview

Dungeon Master is a single-player AI-powered tabletop RPG built on top of BookWorm, a local-first RAG (Retrieval-Augmented Generation) system. The system ingests rulebooks and adventure content, then uses an AI Game Master to run interactive narrative gameplay with deterministic mechanical resolution.

## High-Level Architecture

```mermaid
graph TB
    subgraph Frontend["Frontend (Vanilla HTML/CSS/JS)"]
        UI[Game UI]
        CS[Character Sheet]
        PP[Party Panel]
        CP[Combat Panel]
    end

    subgraph Backend["FastAPI Backend"]
        WS[WebSocket Handler]
        REST[REST Endpoints]
        TL[Turn Loop]
    end

    subgraph GameEngine["Game Engine"]
        DM[DungeonMasterAI]
        RE[Rules Engine]
        AC[Action Parser]
    end

    subgraph RAG["RAG Pipeline (BookWorm)"]
        EP[Embedding Provider]
        VS[Vector Search]
        RP[Retrieval Pipeline]
    end

    subgraph Storage["PostgreSQL + pgvector"]
        BT[(books)]
        CT[(chunks + embeddings)]
        GS[(game_sessions)]
        GL[(game_log)]
    end

    subgraph External["External Services"]
        OL[Ollama LLM]
        HF[HuggingFace Model]
    end

    UI -->|WebSocket| WS
    UI -->|HTTP| REST
    WS --> TL
    TL --> DM
    DM --> RE
    DM --> AC
    DM --> RP
    DM -->|generate_chat/stream| OL
    RP --> EP
    EP -->|embeddings| HF
    RP --> VS
    VS --> CT
    RE -.->|pure Python, no I/O| RE
    REST --> GS
    TL --> GL
    TL --> GS
```

## Package Relationship

```mermaid
graph LR
    subgraph bookworm["bookworm (RAG foundation)"]
        ing[ingestion/]
        emb[embeddings/]
        llm[llm/]
        ret[retrieval/]
        bdb[db/]
    end

    subgraph dungeonmaster["dungeonmaster (game layer)"]
        rul[rules/]
        ai[ai/]
        gam[game/]
        con[content/]
        ddb[db/]
        web[web/]
    end

    ai -->|uses| llm
    ai -->|uses| ret
    ai -->|uses| emb
    con -->|wraps| ing
    ddb -->|extends| bdb
    web -->|serves| gam
    gam -->|orchestrates| ai
    gam -->|orchestrates| rul
```

`dungeonmaster` is a **consumer** of `bookworm`, not a child. It imports bookworm's providers and pipelines through their public Protocol interfaces.

## Turn Resolution Flow

```mermaid
sequenceDiagram
    participant P as Player (Browser)
    participant WS as WebSocket
    participant DM as DungeonMasterAI
    participant RAG as RAG Pipeline
    participant LLM as Ollama LLM
    participant RE as Rules Engine
    participant DB as PostgreSQL

    P->>WS: {type: "player_action", text: "I sneak past the guards"}
    WS->>DM: process_player_input_stream()

    DM->>RAG: retrieve rules (content_type=rule)
    RAG->>DB: pgvector cosine search
    DB-->>RAG: relevant rule chunks
    DM->>RAG: retrieve adventure (content_type=encounter,npc,monster)
    RAG->>DB: pgvector cosine search
    DB-->>RAG: relevant adventure chunks

    DM->>LLM: generate_stream(system + history + context + input)
    LLM-->>WS: streaming tokens ("The torchlight flickers...")
    WS-->>P: NarrativeChunk tokens
    LLM-->>DM: [ROLL:skill_check:stealth:DC12:Player]

    DM->>RE: roll_check(character, "skill_check", "stealth", 12)
    RE-->>DM: CheckResult(total=19, success=true)
    DM-->>WS: DiceRollResult
    WS-->>P: dice animation

    DM->>LLM: generate_stream(narrate outcome: stealth 19 vs DC 12 success)
    LLM-->>WS: streaming tokens ("You slip between the shadows...")
    WS-->>P: NarrativeChunk tokens

    DM->>DB: append to game_log
    DM->>DB: save session state
    WS-->>P: GameStateUpdate
```

## Data Flow: Content Ingestion

```mermaid
flowchart LR
    TXT[".txt file"] --> R[Reader]
    R -->|chapters| C[Chunker]
    C -->|chunks| E[Embedding Provider]
    E -->|384-dim vectors| DB[(PostgreSQL + pgvector)]
    C -->|chunks| TAG[Content Tagger]
    TAG -->|content_type labels| DB
```

## Data Flow: Book-to-Adventure Conversion

```mermaid
flowchart TB
    NOVEL[Novel .txt] --> READ[Read & split chapters]
    READ --> LOOP{For each chapter}
    LOOP --> LLM[LLM: extract locations, NPCs, encounters, creatures]
    LLM --> ASM[Assemble adventure document]
    ASM --> INGEST[Ingest through RAG pipeline]
    INGEST --> TAG[Auto-classify chunks]
    TAG --> DB[(Tagged chunks in pgvector)]
```

## Database Schema

```mermaid
erDiagram
    books ||--o{ chunks : contains
    books ||--o{ game_sessions : "adventure/rulebook for"
    game_sessions ||--o{ game_log : records

    books {
        uuid id PK
        text title
        text file_path
        timestamptz ingested_at
    }

    chunks {
        uuid id PK
        uuid book_id FK
        text content
        text chapter_title
        int chapter_number
        int chunk_index
        int start_char
        int end_char
        vector384 embedding
        text content_type
        timestamptz created_at
    }

    game_sessions {
        uuid id PK
        text name
        text rules_system
        jsonb player_character
        jsonb companions
        jsonb current_scene
        uuid adventure_book_id FK
        uuid rulebook_book_id FK
        int turn_count
        bool in_combat
        timestamptz created_at
        timestamptz updated_at
    }

    game_log {
        uuid id PK
        uuid session_id FK
        int sequence_number
        text actor
        text content
        text action_type
        jsonb dice_results
        jsonb metadata
        timestamptz created_at
    }
```

## Deployment

```mermaid
graph TB
    subgraph Docker["Docker Compose"]
        PG["PostgreSQL 16 + pgvector<br/>Port 5632"]
        OL["Ollama<br/>Port 11434"]
    end

    subgraph Local["Local Process"]
        UV["uvicorn (FastAPI)<br/>Port 8000"]
    end

    Browser -->|HTTP/WS| UV
    UV -->|psycopg| PG
    UV -->|httpx| OL
    OL -->|loads| MODEL["llama3.1:8b / llama3.2:3b"]
    UV -->|loads| EMB["all-MiniLM-L6-v2<br/>(HuggingFace, cached locally)"]
```

## Key Interfaces (Protocols)

All three core abstractions use Python's `Protocol` for structural typing — no inheritance required.

| Protocol | File | Methods | Implementations |
|----------|------|---------|----------------|
| `EmbeddingProvider` | `bookworm/embeddings/base.py` | `embed_texts()`, `embed_query()` | `TransformerEmbeddingProvider` (local HuggingFace) |
| `LLMProvider` | `bookworm/llm/base.py` | `generate()`, `generate_chat()`, `generate_stream()` | `OllamaProvider` (HTTP REST) |
| `RulesEngine` | `dungeonmaster/rules/base.py` | `roll_check()`, `resolve_attack()`, `create_character()`, `get_rules_summary()`, ... | `DnD5eEngine` (D&D 5th Edition) |
