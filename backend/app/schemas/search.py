from __future__ import annotations

from typing import Any, List

from pydantic import BaseModel, Field


class SearchChunk(BaseModel):
    id: str | None = None
    text: str
    score: float | None = None
    metadata: dict[str, Any] | None = None


class RagSearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int | None = Field(default=None, ge=1, le=20)


class RagSearchResponse(BaseModel):
    query: str
    rewritten_query: str | None
    answer: str | None
    chunks: List[SearchChunk]


class SemanticSearchResponse(BaseModel):
    query: str
    chunks: List[SearchChunk]
