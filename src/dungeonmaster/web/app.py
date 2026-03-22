"""
FastAPI application factory — the web server entry point.

Serves:
- WebSocket endpoint for the real-time game loop
- REST endpoints for game management
- Static files for the frontend
"""

import logging
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from dungeonmaster.logging_config import setup_logging
from dungeonmaster.web.routes import character, game, saves

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    from dungeonmaster.config import get_game_settings
    settings = get_game_settings()
    setup_logging(level=settings.log_level)
    logger.info("Starting Dungeon Master server")

    app = FastAPI(
        title="Dungeon Master",
        description="Single-player tabletop RPG powered by AI",
        version="0.1.0",
    )

    # Include API routes
    app.include_router(game.router, prefix="/api")
    app.include_router(character.router, prefix="/api")
    app.include_router(saves.router, prefix="/api")

    # Serve static frontend files
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

    return app


app = create_app()


def main():
    """Entry point for the `dungeonmaster` CLI command."""
    from dungeonmaster.config import get_game_settings

    settings = get_game_settings()
    uvicorn.run(
        "dungeonmaster.web.app:app",
        host=settings.web_host,
        port=settings.web_port,
        reload=True,
    )


if __name__ == "__main__":
    main()
