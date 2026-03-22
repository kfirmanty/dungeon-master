# Data Models Reference

## Python Dataclasses

All domain models use plain Python `dataclasses`. API schemas use Pydantic.

### BookWorm Models (`src/bookworm/models.py`)

| Class | Fields | Purpose |
|-------|--------|---------|
| `Chapter` | `number: int\|None`, `title: str\|None`, `content: str` | A chapter extracted from a book file |
| `Chunk` | `content`, `chapter_title`, `chapter_number`, `chunk_index`, `start_char`, `end_char` | A segment of text ready to be embedded |
| `BookMetadata` | `id: UUID`, `title`, `file_path`, `ingested_at` | A book record from the database |
| `ChunkResult` | `content`, `chapter_title`, `chapter_number`, `chunk_index`, `similarity_score: float` | A chunk returned from similarity search |
| `QueryResult` | `answer: str`, `sources: list[ChunkResult]` | Complete RAG query response |

### DungeonMaster Models (`src/dungeonmaster/models.py`)

#### Mechanical Results (shared across all RPG systems)

| Class | Key Fields | Purpose |
|-------|-----------|---------|
| `DiceResult` | `expression`, `rolls: list[int]`, `modifier: int`, `total: int`, `natural_max: bool`, `natural_min: bool` | Complete dice roll record |
| `CheckResult` | `dice_result: DiceResult`, `success: bool`, `target_number: int`, `check_type`, `detail`, `actor`, `description` | Outcome of any check |
| `AttackResult` | `attack_roll: DiceResult`, `hit: bool`, `critical: bool`, `damage_roll: DiceResult\|None`, `total_damage: int` | Full attack resolution |
| `DamageResult` | `damage_dealt: int`, `target_unconscious: bool`, `target_dead: bool`, `target`, `description` | Damage application outcome |

#### Game Objects

| Class | Key Fields | Purpose |
|-------|-----------|---------|
| `Item` | `name`, `description`, `weight`, `quantity`, `equipped: bool`, `properties: dict` | Any game item |
| `CombatantState` | `character_id`, `initiative: int`, `has_acted: bool`, `position`, `is_player`, `is_enemy` | A combatant in an encounter |
| `CombatState` | `combatants: list`, `turn_order: list[str]`, `current_turn_index: int`, `round_number: int` | Active combat state |
| `Scene` | `scene_type: SceneType`, `description`, `location`, `npcs_present`, `enemies: list[dict]`, `combat_state` | Current narrative scene |
| `NarrativeEntry` | `actor`, `content`, `action_type`, `dice_results: list[dict]`, `metadata: dict`, `timestamp` | Game log entry |
| `GameSession` | `id`, `name`, `rules_system`, `player_character: dict`, `companions: list[dict]`, `current_scene`, `narrative_history`, `adventure_book_id`, `rulebook_book_id`, `turn_count`, `in_combat` | Root aggregate |

#### Enums

| Enum | Values |
|------|--------|
| `SceneType` | `exploration`, `combat`, `social`, `rest`, `puzzle` |

---

## Database Schema

### BookWorm Tables

#### `books`
```sql
CREATE TABLE books (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    file_path TEXT NOT NULL,
    ingested_at TIMESTAMPTZ DEFAULT now()
);
```

#### `chunks`
```sql
CREATE TABLE chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    book_id UUID NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    chapter_title TEXT,
    chapter_number INTEGER,
    chunk_index INTEGER NOT NULL,
    start_char INTEGER NOT NULL,
    end_char INTEGER NOT NULL,
    embedding vector(384) NOT NULL,
    content_type TEXT DEFAULT 'book',  -- added by game migrations
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX chunks_embedding_idx ON chunks
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX chunks_content_type_idx ON chunks(content_type);
```

### DungeonMaster Tables

#### `game_sessions`
```sql
CREATE TABLE game_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    rules_system TEXT NOT NULL DEFAULT 'dnd5e',
    player_character JSONB NOT NULL,
    companions JSONB NOT NULL DEFAULT '[]',
    current_scene JSONB NOT NULL DEFAULT '{}',
    adventure_book_id UUID REFERENCES books(id),
    rulebook_book_id UUID REFERENCES books(id),
    turn_count INTEGER DEFAULT 0,
    in_combat BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
```

#### `game_log`
```sql
CREATE TABLE game_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES game_sessions(id) ON DELETE CASCADE,
    sequence_number INTEGER NOT NULL,
    actor TEXT NOT NULL,
    content TEXT NOT NULL,
    action_type TEXT NOT NULL DEFAULT 'narration',
    dice_results JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(session_id, sequence_number)
);

CREATE INDEX game_log_session_idx ON game_log(session_id, sequence_number);
```

---

## D&D 5e Character Dict Schema

This is the JSONB structure stored in `game_sessions.player_character`:

```json
{
  "name": "Aelindra",
  "race": "elf",
  "subrace": "wood_elf",
  "character_class": "ranger",
  "level": 1,
  "abilities": {
    "strength": 12, "dexterity": 18, "constitution": 14,
    "intelligence": 10, "wisdom": 15, "charisma": 8
  },
  "hp": {"current": 12, "max": 12, "temp": 0},
  "ac": 14,
  "proficiency_bonus": 2,
  "speed": 35,
  "proficiencies": ["stealth", "perception", "survival"],
  "save_proficiencies": ["strength", "dexterity"],
  "expertise": [],
  "traits": ["darkvision_60", "keen_senses", "fey_ancestry", "trance", "fleet_of_foot", "mask_of_the_wild"],
  "resistances": [],
  "class_features": [
    {"name": "Favored Enemy", "description": "..."},
    {"name": "Natural Explorer", "description": "..."}
  ],
  "inventory": [
    {
      "name": "Longbow", "description": "", "weight": 0.0,
      "quantity": 1, "equipped": true,
      "properties": {"damage": "1d8", "type": "piercing", "range": "150/600"}
    }
  ],
  "spells_known": [],
  "spell_slots": {"max": [0,0,0,0,0,0,0,0,0,0], "current": [0,0,0,0,0,0,0,0,0,0]},
  "conditions": [],
  "death_saves": {"successes": 0, "failures": 0},
  "hit_dice": {"size": 10, "total": 1, "current": 1},
  "is_player": true,
  "personality": "",
  "backstory": "",
  "gold": 50,
  "xp": 0
}
```

**Rogue-specific fields:**
```json
{
  "sneak_attack_dice": "1d6",
  "expertise": ["stealth", "thieves_tools"]
}
```

**Barbarian-specific fields:**
```json
{
  "rage_uses": {"max": 2, "current": 2},
  "rage_bonus_damage": 2
}
```

**Bard-specific fields:**
```json
{
  "jack_of_all_trades": true,
  "expertise": ["persuasion", "deception"]
}
```

Different RPG systems will have entirely different schemas. The game engine treats this as an opaque `dict` and passes it to the active `RulesEngine` for interpretation.
