from __future__ import annotations

from typing import Iterable, Sequence, cast

import httpx
from datapizza.core.models import PipelineComponent
from datapizza.type import Chunk, DenseEmbedding

from app.core.config import settings
from app.core.logging import logger


def _ensure_embeddings_list(chunk: Chunk) -> None:
    if getattr(chunk, "embeddings", None) is None:
        chunk.embeddings = []


class OllamaChunkEmbedder(PipelineComponent):
    """Embed batches of chunks using an Ollama OpenAI-compatible endpoint."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        model: str | None = None,
        embedding_name: str | None = None,
        batch_size: int = 16,
        timeout: float = 60.0,
    ) -> None:
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.model = model or settings.ollama_embed_model
        self.embedding_name = embedding_name or settings.rag_embedding_name
        self.batch_size = max(1, batch_size)
        self.timeout = timeout

    def _run(self, nodes: Sequence[Chunk] | None = None, **_: object) -> list[Chunk]:
        if not nodes:
            return []
        return self._embed_sync(list(nodes))

    async def _a_run(self, nodes: Sequence[Chunk] | None = None, **_: object) -> list[Chunk]:
        if not nodes:
            return []
        return await self._embed_async(list(nodes))

    def _embed_sync(self, nodes: list[Chunk]) -> list[Chunk]:
        endpoint = f"{self.base_url}/embeddings"
        with httpx.Client(timeout=self.timeout) as client:
            for batch in _batched(nodes, self.batch_size):
                texts = [chunk.text for chunk in batch]
                payload = {"model": self.model, "input": texts}
                response = client.post(endpoint, json=payload)
                response.raise_for_status()
                data = response.json().get("data", [])
                if len(data) != len(batch):
                    raise RuntimeError(
                        "La risposta di Ollama contiene un numero di embedding diverso dai chunk elaborati."
                    )
                for chunk, item in zip(batch, data, strict=True):
                    vector = _extract_vector(item)
                    _ensure_embeddings_list(chunk)
                    chunk.embeddings.append(
                        DenseEmbedding(name=self.embedding_name, vector=vector)
                    )
        return nodes

    async def _embed_async(self, nodes: list[Chunk]) -> list[Chunk]:
        endpoint = f"{self.base_url}/embeddings"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for batch in _batched(nodes, self.batch_size):
                texts = [chunk.text for chunk in batch]
                payload = {"model": self.model, "input": texts}
                response = await client.post(endpoint, json=payload)
                response.raise_for_status()
                data = response.json().get("data", [])
                if len(data) != len(batch):
                    raise RuntimeError(
                        "La risposta di Ollama contiene un numero di embedding diverso dai chunk elaborati."
                    )
                for chunk, item in zip(batch, data, strict=True):
                    vector = _extract_vector(item)
                    _ensure_embeddings_list(chunk)
                    chunk.embeddings.append(
                        DenseEmbedding(name=self.embedding_name, vector=vector)
                    )
        return nodes


class OllamaQueryEmbedder(PipelineComponent):
    """Embed user queries using the same Ollama endpoint employed for document chunks."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.model = model or settings.ollama_embed_model
        self.timeout = timeout

    def _run(self, text: str | None = None, **kwargs: object) -> dict[str, list[float]]:
        query = self._resolve_text(text, **kwargs)
        vector = self._embed_sync(query)
        return {"query_vector": vector}

    async def _a_run(self, text: str | None = None, **kwargs: object) -> dict[str, list[float]]:
        query = self._resolve_text(text, **kwargs)
        vector = await self._embed_async(query)
        return {"query_vector": vector}

    def _resolve_text(self, text: str | None, **kwargs: object) -> str:
        if text:
            return text
        for key in ("input", "prompt", "user_prompt", "query"):
            value = cast(str | None, kwargs.get(key))
            if value:
                return value
        raise ValueError("Nessun testo fornito per generare l'embedding della query.")

    def _embed_sync(self, text: str) -> list[float]:
        endpoint = f"{self.base_url}/embeddings"
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(endpoint, json={"model": self.model, "input": [text]})
            response.raise_for_status()
            data = response.json().get("data", [])
            if not data:
                raise RuntimeError("Ollama non ha restituito alcun embedding per la query.")
            return _extract_vector(data[0])

    async def _embed_async(self, text: str) -> list[float]:
        endpoint = f"{self.base_url}/embeddings"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(endpoint, json={"model": self.model, "input": [text]})
            response.raise_for_status()
            data = response.json().get("data", [])
            if not data:
                raise RuntimeError("Ollama non ha restituito alcun embedding per la query.")
            return _extract_vector(data[0])


def _extract_vector(item: dict) -> list[float]:
    vector: Iterable[float] | None = item.get("embedding") or item.get("vector")
    if vector is None:
        logger.error("Embedding mancante nella risposta di Ollama: %s", item)
        raise RuntimeError("Embedding mancante nella risposta di Ollama.")
    return list(vector)


def _batched(items: Sequence[Chunk], batch_size: int) -> Iterable[list[Chunk]]:
    batch: list[Chunk] = []
    for item in items:
        batch.append(item)
        if len(batch) >= batch_size:
            yield batch
            batch = []
    if batch:
        yield batch
