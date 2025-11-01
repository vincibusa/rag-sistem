from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.core.exceptions import AppException
from app.schemas.search import (
    RagSearchRequest,
    RagSearchResponse,
    SearchChunk,
    SemanticSearchResponse,
)
from app.services.rag import RagRetrievalService

router = APIRouter(prefix="/search", tags=["search"])


@router.post("/rag", response_model=RagSearchResponse, summary="Esegue una ricerca RAG completa")
def rag_search(payload: RagSearchRequest) -> RagSearchResponse:
    service = RagRetrievalService()
    try:
        result = service.run(query=payload.query, top_k=payload.top_k)
    except AppException as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)

    chunks = [SearchChunk(**chunk) for chunk in result["chunks"]]
    return RagSearchResponse(
        query=result["query"],
        rewritten_query=result["rewritten_query"],
        answer=result["answer"],
        chunks=chunks,
    )


@router.post(
    "/semantic",
    response_model=SemanticSearchResponse,
    summary="Esegue una ricerca semantica (solo recupero dei chunk)",
)
def semantic_search(payload: RagSearchRequest) -> SemanticSearchResponse:
    service = RagRetrievalService()
    try:
        chunks = service.semantic_search(query=payload.query, top_k=payload.top_k)
    except AppException as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)

    items = [
        SearchChunk(
            id=getattr(chunk, "id", None),
            text=getattr(chunk, "text", ""),
            score=getattr(chunk, "score", None) or getattr(chunk, "distance", None),
            metadata=service._to_serialisable(getattr(chunk, "metadata", {})),
        )
        for chunk in chunks
    ]

    return SemanticSearchResponse(query=payload.query, chunks=items)
