"""
Abstract interface for embedding providers.

Using Python's Protocol (structural subtyping) instead of ABC:
- With ABC, a class must explicitly inherit from the base (nominal typing).
- With Protocol, any class with matching methods is compatible (structural typing).
- This is like TypeScript interfaces or Go interfaces — "if it quacks like a duck."

The benefit: you can swap embedding providers (local transformer, OpenAI API,
Cohere API) without changing any calling code, as long as they implement
embed_texts() and embed_query().
"""

from typing import Protocol


class EmbeddingProvider(Protocol):
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a batch of texts.

        Returns a list of vectors, one per input text.
        Each vector has `embedding_dimensions` floats (384 for MiniLM).
        """
        ...

    def embed_query(self, query: str) -> list[float]:
        """Generate embedding for a single query string.

        Convenience method — semantically identical to embed_texts([query])[0],
        but makes calling code more readable.
        """
        ...
