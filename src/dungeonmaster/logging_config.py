"""
Centralized logging configuration.

Provides timestamped, structured logging for the entire application.
Call setup_logging() once at server startup.
"""

import logging
import sys


def setup_logging(level: str = "INFO") -> None:
    """Configure logging with timestamps for all project modules.

    Format: [2026-03-22 14:30:05] INFO  module.name: Message
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    formatter = logging.Formatter(
        fmt="[%(asctime)s] %(levelname)-5s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(formatter)

    # Configure root logger for our packages
    for package in ("bookworm", "dungeonmaster"):
        logger = logging.getLogger(package)
        logger.setLevel(log_level)
        logger.handlers.clear()
        logger.addHandler(handler)
        logger.propagate = False
