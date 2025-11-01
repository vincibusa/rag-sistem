from __future__ import annotations

import logging
from logging.config import dictConfig

from .config import settings


def configure_logging() -> None:
    """Set up structured logging for the application."""
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "level": settings.log_level.upper(),
                },
            },
            "root": {
                "level": settings.log_level.upper(),
                "handlers": ["console"],
            },
            "loggers": {
                "uvicorn": {"level": settings.log_level.upper()},
                "uvicorn.access": {"level": "INFO"},
            },
        }
    )


logger = logging.getLogger("medit.backend")
