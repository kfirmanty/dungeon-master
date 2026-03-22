"""
Abstract interface for LLM providers.

Same structural typing approach as EmbeddingProvider — any class with a matching
generate() method is a valid LLMProvider without explicit inheritance.
"""

from typing import Iterator, Protocol


class LLMProvider(Protocol):
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Generate a response given system and user prompts.

        The system prompt sets the LLM's behavior and constraints.
        The user prompt contains the actual question with context.

        Returns the model's text response.
        """
        ...

    def generate_chat(self, messages: list[dict]) -> str:
        """Generate a response from a full message history.

        Messages format: [{"role": "system"|"user"|"assistant", "content": "..."}]
        This enables multi-turn conversation for the game loop.
        """
        ...

    def generate_stream(self, messages: list[dict]) -> Iterator[str]:
        """Stream a response token-by-token from a full message history.

        Yields individual text tokens as they are generated.
        Used by the WebSocket game loop for real-time narrative streaming.
        """
        ...
