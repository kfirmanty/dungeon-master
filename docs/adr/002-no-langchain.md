# ADR-002: Build RAG From Scratch (No LangChain)

## Status
Accepted

## Context
LangChain, LlamaIndex, and similar frameworks provide pre-built RAG pipelines. Using one would accelerate development but hide the mechanics of how RAG works.

## Decision
Build the entire RAG pipeline from scratch: manual tokenization, embedding, vector search, prompt construction, and LLM calls. No high-level RAG frameworks.

## Consequences

**Positive:**
- Every step is visible and auditable — no black-box abstractions
- Educational value: developers learn how embeddings, vector search, and prompt engineering actually work
- Full control over chunking strategy, prompt format, and retrieval logic
- Easier to customize for game-specific needs (content-type filtering, anti-spoiler retrieval)
- Fewer dependencies and smaller attack surface

**Negative:**
- More code to write and maintain
- No access to LangChain's ecosystem of pre-built tools (agents, memory, chains)
- Must handle edge cases (encoding, token limits, batching) manually
