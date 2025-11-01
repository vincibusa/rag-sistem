from __future__ import annotations

from typing import Iterable

from datapizza.core.vectorstore import Distance, VectorConfig
from datapizza.type import EmbeddingFormat
from datapizza.vectorstores.qdrant import QdrantVectorstore

from app.core.config import settings
from app.core.logging import logger

_VECTORSTORE: QdrantVectorstore | None = None
_COLLECTION_ENSURED = False


def get_vectorstore() -> QdrantVectorstore:
    global _VECTORSTORE
    if _VECTORSTORE is None:
        _VECTORSTORE = QdrantVectorstore(**settings.qdrant_client_kwargs)
    return _VECTORSTORE


def ensure_collection(vectorstore: QdrantVectorstore | None = None) -> None:
    global _COLLECTION_ENSURED
    if _COLLECTION_ENSURED:
        return

    vs = vectorstore or get_vectorstore()
    collection_name = settings.qdrant_collection_name

    if not _collection_exists(vs, collection_name):
        vector_config = [
            VectorConfig(
                name=settings.rag_embedding_name,
                dimensions=settings.rag_embedding_dimensions,
                distance=Distance.COSINE,
                format=EmbeddingFormat.DENSE,
            )
        ]
        vs.create_collection(collection_name=collection_name, vector_config=vector_config)
        logger.info("Creata collezione Qdrant %s", collection_name)
    else:
        logger.debug("Collezione Qdrant %s già esistente", collection_name)

    _COLLECTION_ENSURED = True


def _collection_exists(vectorstore: QdrantVectorstore, name: str) -> bool:
    try:
        collections = vectorstore.get_collections()  # type: ignore[assignment]
    except Exception as exc:  # pragma: no cover - qdrant failure surfaces upstream
        logger.warning("Impossibile recuperare le collezioni Qdrant: %s", exc)
        return False

    names: set[str] = set()
    if isinstance(collections, Iterable):
        for item in collections:
            candidate = getattr(item, "name", None)
            if candidate:
                names.add(candidate)
            elif isinstance(item, dict):
                candidate = item.get("name")
                if candidate:
                    names.add(str(candidate))
    elif hasattr(collections, "collections"):
        for item in collections.collections:
            candidate = getattr(item, "name", None)
            if candidate:
                names.add(candidate)

    return name in names
