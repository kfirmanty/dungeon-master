from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application configuration loaded from environment variables and .env file.

    pydantic-settings automatically maps UPPER_CASE env vars to lower_case fields.
    For example, DATABASE_URL in .env becomes settings.database_url in Python.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # PostgreSQL connection string (pgvector-enabled instance)
    database_url: str = "postgresql://bookworm:bookworm@localhost:5432/bookworm"

    # HuggingFace model ID for the embedding transformer
    # "sentence-transformers/" prefix is the HF org that hosts the model weights
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dimensions: int = 384

    # Ollama LLM settings
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"
    ollama_temperature: float = 0.7  # 0.0 = deterministic, 1.0 = creative

    # Chunking: how we split book text into embeddable segments
    chunk_size: int = 500
    chunk_overlap: int = 100

    # How many chunks to retrieve per query
    top_k: int = 5


@lru_cache
def get_settings() -> Settings:
    """Singleton settings instance — parsed once, cached forever."""
    return Settings()
