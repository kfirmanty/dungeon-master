# ADR-001: Protocol-Based Provider Interfaces

## Status
Accepted

## Context
The system needs swappable implementations for three core concerns: embeddings, LLM generation, and RPG rules. We need to decide how to define the interfaces that allow swapping implementations without changing calling code.

Options considered:
1. **Abstract Base Classes (ABC)** — traditional Python inheritance
2. **Python Protocols** — structural typing (duck typing with type checker support)
3. **No interface** — just swap concrete classes directly

## Decision
Use Python `Protocol` (from `typing`) for all provider interfaces: `EmbeddingProvider`, `LLMProvider`, and `RulesEngine`.

## Consequences

**Positive:**
- No inheritance required — any class with matching methods is automatically valid
- Implementations don't need to import the interface (zero coupling)
- Works naturally with Python's duck typing tradition
- Type checkers (mypy, pyright) validate compliance at static analysis time
- Easy to create test mocks — just define an object with the right methods

**Negative:**
- Less discoverable than ABC — new developers might not realize there's an interface to conform to
- No runtime `isinstance()` checks by default (though `runtime_checkable` is available)
- IDE "find implementations" may not work as well as with inheritance

**Files:**
- `src/bookworm/embeddings/base.py` — `EmbeddingProvider` Protocol
- `src/bookworm/llm/base.py` — `LLMProvider` Protocol
- `src/dungeonmaster/rules/base.py` — `RulesEngine` Protocol
