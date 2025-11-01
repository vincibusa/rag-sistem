from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette import status

from .logging import logger


class AppException(Exception):
    def __init__(self, message: str, status_code: int = status.HTTP_400_BAD_REQUEST, extra: dict[str, Any] | None = None):
        self.message = message
        self.status_code = status_code
        self.extra = extra or {}
        super().__init__(message)


def _app_exception_handler(_: Request, exc: AppException) -> JSONResponse:
    payload = {"detail": exc.message, **exc.extra}
    return JSONResponse(status_code=exc.status_code, content=payload)


def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception", extra={"path": request.url.path})
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppException, _app_exception_handler)
    app.add_exception_handler(Exception, _unhandled_exception_handler)
