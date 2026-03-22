"""
Game-specific configuration — extends BookWorm settings.

All BookWorm settings (database, embeddings, LLM) are inherited.
Game-specific settings are added on top.
"""

from functools import lru_cache

from bookworm.config import Settings as BookwormSettings


class GameSettings(BookwormSettings):
    """Extends BookWorm settings with game-specific configuration."""

    # Rules system selection
    rules_system: str = "dnd5e"

    # Web server
    web_host: str = "127.0.0.1"
    web_port: int = 8000

    # Game defaults
    max_companions: int = 2
    max_conversation_history: int = 50
    auto_save_interval: int = 10  # auto-save every N turns


@lru_cache
def get_game_settings() -> GameSettings:
    """Singleton game settings instance."""
    return GameSettings()
