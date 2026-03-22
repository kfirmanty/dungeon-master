# API Reference

## Base URL

```
http://localhost:8000/api
```

---

## REST Endpoints

### Game Management

#### `POST /api/game/new`
Create a new game session.

**Request Body (JSON):**
```json
{
  "name": "Aelindra's Adventure",
  "rules_system": "dnd5e",
  "character": {
    "name": "Aelindra",
    "race": "elf",
    "character_class": "ranger",
    "is_player": true
  },
  "companions": [
    {
      "name": "Thorin",
      "race": "dwarf",
      "character_class": "fighter",
      "is_player": false,
      "personality": "Gruff but loyal dwarven warrior."
    }
  ],
  "adventure_book_id": "uuid-string-or-null",
  "rulebook_book_id": "uuid-string-or-null"
}
```

**Response:**
```json
{
  "session_id": "abc-123-...",
  "character": { ... },
  "companions": [ ... ]
}
```

#### `GET /api/game/{session_id}`
Get current game state.

**Response:**
```json
{
  "session_id": "abc-123",
  "name": "Aelindra's Adventure",
  "rules_system": "dnd5e",
  "character": { ... },
  "companions": [ ... ],
  "scene": {
    "type": "exploration",
    "description": "...",
    "location": "..."
  },
  "turn_count": 5,
  "in_combat": false,
  "history": [
    {"actor": "player", "content": "I look around", "action_type": "dialogue"},
    {"actor": "dm", "content": "You see...", "action_type": "narration"}
  ]
}
```

#### `DELETE /api/game/{session_id}`
Delete a game session and all its log entries.

#### `GET /api/game`
List all game sessions.

**Response:** Array of `GameSessionSummary`:
```json
[
  {
    "id": "abc-123",
    "name": "Adventure",
    "rules_system": "dnd5e",
    "character_name": "Aelindra",
    "character_class": "ranger",
    "hp_current": "24",
    "hp_max": "28",
    "turn_count": 5,
    "in_combat": false,
    "created_at": "2026-03-22T...",
    "updated_at": "2026-03-22T..."
  }
]
```

### Character

#### `GET /api/game/{session_id}/character`
Get the player character sheet and companion details.

#### `GET /api/rules/{system_id}/creation-options`
Get available character creation options for a rules system.

**Response (D&D 5e):**
```json
{
  "system": "D&D 5th Edition",
  "races": ["human", "elf", "dwarf", ...],
  "classes": ["fighter", "wizard", "rogue", ...],
  "race_details": {
    "elf": {"speed": 30, "bonuses": {"dexterity": 2}},
    "dwarf": {"speed": 25, "bonuses": {"constitution": 2}}
  }
}
```

### Saves

#### `GET /api/saves`
List all saved game sessions.

#### `POST /api/saves/{session_id}`
Save the current game state.

### Content

#### `GET /api/content`
List all ingested content with chunk type breakdown.

**Response:**
```json
[
  {
    "id": "book-uuid",
    "title": "D&D 5e Basic Rules",
    "file_path": "/tmp/...",
    "ingested_at": "2026-03-22T...",
    "total_chunks": 150,
    "content_types": {"rule": 120, "lore": 30},
    "category": "rulebook"
  }
]
```

#### `POST /api/content/ingest`
Upload and ingest a text file with content classification. **Returns SSE stream.**

**Request (multipart/form-data):**
- `file`: .txt or .md file
- `title`: Document title (string)
- `content_type`: Default type — `adventure`, `rule`, or `lore` (string)

**Response (text/event-stream):**
```
data: {"status": "reading", "message": "Reading 'file.txt'...", "progress": 0.0}
data: {"status": "chunking", "message": "Created 150 chunks", "progress": 0.2}
data: {"status": "embedding", "message": "Embedding batch 3/5", "progress": 0.6}
data: {"status": "storing", "message": "Storing in database...", "progress": 0.85}
data: {"status": "classifying", "message": "Classifying chunks...", "progress": 0.92}
data: {"status": "complete", "book_id": "uuid", "title": "...", "content_type_counts": {...}}
```

#### `POST /api/content/convert`
Convert a novel into a structured RPG adventure via LLM processing. **Returns SSE stream.**

**Request (multipart/form-data):**
- `file`: .txt or .md file (novel)
- `title`: Adventure title (string)

**Response (text/event-stream):**
```
data: {"status": "reading", "message": "Reading book: 27 chapters found", "progress": 0.0}
data: {"status": "converting", "chapter": 1, "total": 27, "title": "Chapter I", "progress": 0.037, "message": "Converting chapter 1/27: Chapter I"}
data: {"status": "converting", "chapter": 2, "total": 27, "title": "Chapter II", "progress": 0.074, "message": "..."}
...
data: {"status": "assembling", "message": "Assembling adventure document"}
data: {"status": "ingesting", "message": "Ingesting adventure content"}
data: {"status": "complete", "adventure_book_id": "uuid", "title": "...", "stats": {...}, "chapters_processed": 27}
```

---

## WebSocket Protocol

### Endpoint
```
ws://localhost:8000/api/game/{session_id}/play
```

### Connection Flow
1. Client connects
2. Server sends initial `GameStateUpdate` with full state
3. Client sends actions, server streams responses
4. On disconnect, client auto-reconnects with exponential backoff

### Client → Server Messages

#### PlayerAction
```json
{"type": "player_action", "text": "I search the chest for traps"}
```

#### CombatAction
```json
{"type": "combat_action", "action": "attack", "target": "Goblin", "details": null}
```

#### SystemCommand
```json
{"type": "system_command", "command": "save"}
```
Valid commands: `save`, `status`

### Server → Client Messages

#### NarrativeChunk
Streaming LLM tokens for real-time display.
```json
{"type": "narrative_chunk", "text": "The ", "is_final": false}
{"type": "narrative_chunk", "text": "torchlight ", "is_final": false}
{"type": "narrative_chunk", "text": "", "is_final": true}
```

#### DiceRollResult
```json
{
  "type": "dice_roll",
  "roller": "system",
  "description": "Skill check (Stealth): [14] + 6 = 20 vs DC 15 — Success",
  "dice": "1d20+6",
  "rolls": [14],
  "modifier": 6,
  "total": 20,
  "success": true,
  "dc": 15
}
```

#### GameStateUpdate
```json
{
  "type": "game_state_update",
  "character": { ... },
  "companions": [ ... ],
  "scene": { ... },
  "turn_count": 6,
  "in_combat": false
}
```

#### CombatUpdate
```json
{
  "type": "combat_update",
  "active": true,
  "round_number": 1,
  "initiative_order": [
    {"name": "Aelindra", "is_player": true, "hp_current": 24, "hp_max": 28, "conditions": [], "is_current": true}
  ],
  "current_turn": "Aelindra",
  "available_actions": ["attack", "cast_spell", "dash", "dodge"]
}
```

#### Thinking
```json
{"type": "thinking", "active": true}
```

#### ErrorMessage
```json
{"type": "error", "message": "Cannot connect to Ollama", "recoverable": true}
```
