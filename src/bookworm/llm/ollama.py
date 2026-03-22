"""
Ollama LLM provider — direct REST API calls, no SDK.

Ollama exposes a simple REST API for inference. We use the /api/chat endpoint
which accepts a list of messages (system + user) and returns the model's response.

This is the same pattern used by OpenAI, Anthropic, and other LLM APIs — learning
this teaches you the universal chat completion interface.
"""

import json
from typing import Iterator

import httpx


class OllamaProvider:
    """LLM provider that calls a local Ollama instance via HTTP."""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3.1:8b"):
        self._base_url = base_url.rstrip("/")
        self._model = model

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Send a chat completion request to Ollama.

        The /api/chat endpoint expects:
        {
            "model": "llama3.1:8b",
            "messages": [
                {"role": "system", "content": "..."},  ← sets behavior
                {"role": "user", "content": "..."}     ← the actual request
            ],
            "stream": false  ← return the complete response at once
        }

        With stream=false, the response is a single JSON object with the full
        generated text. With stream=true, you'd get token-by-token Server-Sent
        Events (useful for real-time UIs, but overkill for a CLI in Phase 1).
        """
        url = f"{self._base_url}/api/chat"

        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
        }

        try:
            # 300s timeout: CPU-only Ollama in Docker on macOS is slow (~8-12 tok/s).
            # A 500-token response could take ~60 seconds. 300s gives plenty of margin.
            response = httpx.post(url, json=payload, timeout=300.0)
            response.raise_for_status()
        except httpx.ConnectError:
            raise ConnectionError(
                "Cannot connect to Ollama. Is the container running?\n"
                "  Try: docker compose up -d"
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ConnectionError(
                    f"Model '{self._model}' not found in Ollama.\n"
                    f"  Try: docker exec ollama ollama pull {self._model}"
                )
            raise

        data = response.json()

        # The chat endpoint returns {"message": {"role": "assistant", "content": "..."}}
        return data["message"]["content"]

    def _send_chat(self, messages: list[dict], stream: bool = False) -> httpx.Response:
        """Shared helper for chat requests."""
        url = f"{self._base_url}/api/chat"
        payload = {"model": self._model, "messages": messages, "stream": stream}

        try:
            if stream:
                # For streaming, return the response object for the caller to iterate
                return httpx.stream("POST", url, json=payload, timeout=300.0)
            response = httpx.post(url, json=payload, timeout=300.0)
            response.raise_for_status()
            return response
        except httpx.ConnectError:
            raise ConnectionError(
                "Cannot connect to Ollama. Is the container running?\n"
                "  Try: docker compose up -d"
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ConnectionError(
                    f"Model '{self._model}' not found in Ollama.\n"
                    f"  Try: docker exec ollama ollama pull {self._model}"
                )
            raise

    def generate_chat(self, messages: list[dict]) -> str:
        """Generate a response from a full message history.

        Messages: [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}, ...]
        Enables multi-turn conversation for the game loop.
        """
        response = self._send_chat(messages, stream=False)
        data = response.json()
        return data["message"]["content"]

    def generate_stream(self, messages: list[dict]) -> Iterator[str]:
        """Stream tokens from Ollama's /api/chat endpoint.

        Ollama's streaming response is newline-delimited JSON:
            {"message": {"content": "The"}, "done": false}
            {"message": {"content": " goblin"}, "done": false}
            ...
            {"message": {"content": ""}, "done": true}

        Yields individual text tokens as they arrive.
        """
        url = f"{self._base_url}/api/chat"
        payload = {"model": self._model, "messages": messages, "stream": True}

        try:
            with httpx.stream("POST", url, json=payload, timeout=300.0) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if line:
                        data = json.loads(line)
                        token = data.get("message", {}).get("content", "")
                        if token:
                            yield token
                        if data.get("done", False):
                            return
        except httpx.ConnectError:
            raise ConnectionError(
                "Cannot connect to Ollama. Is the container running?\n"
                "  Try: docker compose up -d"
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ConnectionError(
                    f"Model '{self._model}' not found in Ollama.\n"
                    f"  Try: docker exec ollama ollama pull {self._model}"
                )
            raise
