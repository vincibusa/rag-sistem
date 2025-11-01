from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader

from .config import settings


api_key_header = APIKeyHeader(
    name=settings.api_key_header_name,
    auto_error=False,
)


def verify_api_key(api_key: str | None = Depends(api_key_header)) -> None:
    """Simple API key guard; disabled when no key is configured."""
    if settings.api_key is None:
        return

    if api_key is None or api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
