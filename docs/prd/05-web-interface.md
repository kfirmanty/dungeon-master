# PRD-05: Web Interface

## Purpose

The web interface provides a browser-based game experience using FastAPI (backend) and vanilla HTML/CSS/JS (frontend). The design evokes a dark fantasy aesthetic and uses WebSocket for real-time narrative streaming.

## Functional Requirements

### FR-01: Game Flow (Screens)
1. **Start Screen** — Shows saved games (resume) and "New Game" button
2. **Adventure Selection** — Pick adventure/rulebook from ingested content, upload new content, or choose freeplay
3. **Character Creation** — Name, race, class selection with race info preview
4. **Game Screen** — Three-panel layout: character sheet | narrative | party panel

### FR-02: REST API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/game/new` | Create game session (character + companions + adventure) |
| GET | `/api/game/{id}` | Get game state |
| DELETE | `/api/game/{id}` | Delete session |
| GET | `/api/game` | List all sessions |
| GET | `/api/game/{id}/character` | Get character sheet |
| GET | `/api/rules/{system}/creation-options` | Get races/classes for character creation |
| GET | `/api/saves` | List saved games |
| POST | `/api/saves/{id}` | Save game |
| GET | `/api/content` | List ingested content with chunk type counts |
| POST | `/api/content/ingest` | Upload and ingest a .txt file |
| POST | `/api/content/convert` | Convert a novel to RPG adventure via LLM |

### FR-03: WebSocket Game Loop
- Endpoint: `/api/game/{session_id}/play`
- On connect: send initial `GameStateUpdate` with character, companions, scene
- Client sends: `PlayerAction`, `CombatAction`, `SystemCommand`
- Server sends: `NarrativeChunk` (streaming), `DiceRollResult`, `GameStateUpdate`, `CombatUpdate`, `Thinking`, `ErrorMessage`
- Auto-reconnect with exponential backoff (up to 5 attempts)

### FR-04: Frontend Layout (Desktop)
```
+------------------------------------------------------------------+
|  [Dungeon Master]                                  [Save] [Menu]  |
+------------------------------------------------------------------+
|                    |                                |              |
|   CHARACTER SHEET  |     MAIN NARRATIVE AREA        |   PARTY      |
|   (260px sidebar)  |     (flexible center)          |   (240px)    |
|                    |                                |              |
|   Name, Race,      |   DM narrative text            |   Companion  |
|   Class, Level     |   (streamed with typewriter)   |   HP bars    |
|   HP bar           |                                |              |
|   AC, Speed        |   Dice roll animations         |   Combat     |
|   Ability scores   |                                |   panel      |
|   Skills           |   [Thinking indicator]         |   (when      |
|   Inventory        |                                |   active)    |
|                    |   [What do you do?] [Send]     |              |
+------------------------------------------------------------------+
```

### FR-05: Frontend Layout (Mobile, < 768px)
- Single-column with tab navigation at bottom: Story | Character | Party
- Sidebars hidden by default, shown when tab selected
- Input stays fixed at bottom

### FR-06: Dark Fantasy Theme
- Background: `#0f0e17` (deep navy/charcoal)
- Text: `#e8d5b7` (parchment) for narrative, `#f5f0e8` (bright) for UI
- Accent: `#c9a43e` (gold) for headings and interactive elements
- Danger: `#8b1a1a` (deep red) for damage
- Success: `#2d6a2d` (green) for successful checks
- Typography: Crimson Text (serif) for narrative, system-ui for UI, JetBrains Mono for dice
- Dice roll animation: CSS scale + rotate keyframes

### FR-07: Content Upload & Conversion UI
- File upload form on adventure selection screen
- "Upload & Ingest" for pre-formatted adventure modules
- "Convert Book to Adventure" for novels (long-running LLM conversion)
- Progress/status display during conversion
- Auto-refresh adventure dropdown after successful upload

## Non-Functional Requirements

- **NFR-01**: No JavaScript framework — vanilla ES modules, no build step
- **NFR-02**: Static files served by FastAPI directly
- **NFR-03**: Sync DB/LLM operations wrapped with `asyncio.to_thread()` in async handlers
- **NFR-04**: Auto-save every N turns (configurable, default 10)

## Key Files

| File | Responsibility |
|------|---------------|
| `src/dungeonmaster/web/app.py` | FastAPI app factory, static file mounting |
| `src/dungeonmaster/web/schemas.py` | Pydantic request/response models |
| `src/dungeonmaster/web/routes/game.py` | Game endpoints + WebSocket handler |
| `src/dungeonmaster/web/routes/character.py` | Character endpoints |
| `src/dungeonmaster/web/routes/saves.py` | Save/load endpoints |
| `src/dungeonmaster/web/static/index.html` | Single-page HTML |
| `src/dungeonmaster/web/static/css/style.css` | Dark fantasy CSS theme |
| `src/dungeonmaster/web/static/js/app.js` | Screen routing, event wiring |
| `src/dungeonmaster/web/static/js/websocket.js` | WebSocket connection manager |
| `src/dungeonmaster/web/static/js/game.js` | Narrative rendering + streaming |
| `src/dungeonmaster/web/static/js/character.js` | Character sheet + creation |
| `src/dungeonmaster/web/static/js/combat.js` | Combat mode overlay |
| `src/dungeonmaster/web/static/js/dice.js` | Dice roll visualization |
