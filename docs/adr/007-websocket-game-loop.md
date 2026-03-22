# ADR-007: WebSocket for Game Loop

## Status
Accepted

## Context
The game UI needs to receive LLM output as it's generated (token streaming) and handle server-initiated events (NPC turns, dice animations). We need to choose the communication protocol.

Options:
1. **REST polling** — Client polls every N seconds for new content
2. **Server-Sent Events (SSE)** — Server pushes events, client sends via REST
3. **WebSocket** — Full-duplex bidirectional communication

## Decision
Use WebSocket for the main game loop. REST endpoints remain for stateless operations (save/load, content listing, character creation).

## Consequences

**Positive:**
- Full-duplex: server can push tokens, dice results, and NPC actions without client polling
- Token streaming: each LLM token can be forwarded immediately for typewriter effect
- Lower latency than polling — no wasted requests when nothing is happening
- Natural fit for the game loop pattern (send action, receive stream of events)

**Negative:**
- More complex than REST — connection management, reconnection logic, message routing
- The existing codebase is synchronous (psycopg, httpx) — needs `asyncio.to_thread()` bridge
- WebSocket connections are stateful — harder to load balance (not a concern for local-first)

**Implementation:**
- `ws://host/api/game/{session_id}/play` — main game WebSocket
- Client messages: `PlayerAction`, `CombatAction`, `SystemCommand`
- Server messages: `NarrativeChunk`, `DiceRollResult`, `GameStateUpdate`, `CombatUpdate`, `Thinking`, `ErrorMessage`
- All messages are JSON with a `type` discriminator field
- Auto-reconnect with exponential backoff (up to 5 attempts)
