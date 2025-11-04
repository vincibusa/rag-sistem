from __future__ import annotations

from functools import lru_cache
from typing import Literal

from datapizza.clients.openai import OpenAIClient
from datapizza.core.models import PipelineComponent
from datapizza.modules.parsers import TextParser
from datapizza.modules.prompt import ChatPromptTemplate
from datapizza.modules.rewriters import ToolRewriter
from datapizza.modules.splitters import NodeSplitter
from datapizza.pipeline import DagPipeline
from datapizza.pipeline.pipeline import IngestionPipeline

from app.core.config import settings
from app.core.exceptions import AppException
from app.core.logging import logger

from .components import OllamaChunkEmbedder, OllamaQueryEmbedder
from .document_ai_parser import DocumentAIParser
from .table_processor import TableEnhancer
from .vectorstore import ensure_collection, get_vectorstore

IngestionKind = Literal["document_ai", "text"]

_DEFAULT_REWRITER_PROMPT = (
    "Riscrivi il prompt dell'utente rendendolo più specifico per una ricerca semantica "
    "su documenti aziendali. Mantieni il significato originale e riduci riferimenti ambigui."
)


def create_ingestion_pipeline(kind: IngestionKind) -> IngestionPipeline:
    """Build ingestion pipeline for the requested parser strategy."""
    modules = [
        _resolve_parser(kind),
        TableEnhancer(),  # Arricchisce e formatta le tabelle
        NodeSplitter(max_char=settings.rag_chunk_size),
        OllamaChunkEmbedder(batch_size=8),
    ]
    
    return IngestionPipeline(modules=modules)


def _resolve_parser(kind: IngestionKind):
    if kind == "text":
        return TextParser()
    if kind == "document_ai":
        return DocumentAIParser()
    raise ValueError(f"Parser non supportato: {kind}")


def create_retrieval_pipeline() -> DagPipeline:
    """Build the retrieval pipeline (rewriter -> embedder -> vectorstore -> prompt -> generator)."""
    if not settings.openai_api_key:
        raise AppException(
            "OPENAI_API_KEY non configurata: impossibile creare la pipeline di retrieval.",
            status_code=500,
        )

    client = _get_openai_client()
    query_rewriter = ToolRewriter(
        client=client,
        system_prompt=_DEFAULT_REWRITER_PROMPT,
    )
    query_embedder = OllamaQueryEmbedder()

    vectorstore = get_vectorstore()
    ensure_collection(vectorstore)
    vector_module: PipelineComponent
    vector_module = _VectorSearchModule(
        vectorstore,
        default_vector_name=settings.rag_embedding_name,
        expected_dimensions=settings.rag_embedding_dimensions,
    )

    prompt_template = ChatPromptTemplate(
        user_prompt_template=(
            "Sei un assistente specializzato nell'analizzare i documenti caricati dal gestionale. "
            "Rispondi utilizzando esclusivamente le informazioni fornite nei chunk recuperati. "
            "Quando non trovi una risposta nelle fonti indicate, comunica chiaramente che l'informazione non è disponibile.\n\n"
            "Domanda utente: {{ user_prompt }}"
        ),
        retrieval_prompt_template=(
            "Contenuto recuperato:\n"
            "{% for chunk in chunks %}- {{ chunk.text }}\n{% endfor %}\n"
        ),
    )

    pipeline = DagPipeline()
    pipeline.add_module("rewriter", query_rewriter)
    pipeline.add_module("embedder", query_embedder)
    pipeline.add_module("retriever", vector_module)
    pipeline.add_module("prompt", prompt_template)
    pipeline.add_module("generator", client)

    pipeline.connect("rewriter", "embedder", target_key="text")
    pipeline.connect("embedder", "retriever", target_key="query_vector")
    pipeline.connect("retriever", "prompt", target_key="chunks")
    pipeline.connect("prompt", "generator", target_key="memory")

    logger.debug("Pipeline di retrieval creata con successo")
    return pipeline


@lru_cache(maxsize=1)
def _get_openai_client() -> OpenAIClient:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY non configurata.")
    return OpenAIClient(
        api_key=settings.openai_api_key,
        model=settings.openai_model_name,
    )
class _VectorSearchModule(PipelineComponent):
    """Ensure search requests always include the configured dense vector name."""

    def __init__(self, vectorstore, *, default_vector_name: str, expected_dimensions: int) -> None:
        self._vectorstore = vectorstore
        self._default_vector_name = default_vector_name
        self._expected_dimensions = expected_dimensions

    def _run(
        self,
        collection_name: str,
        query_vector: list[float] | None = None,
        k: int = 10,
        **kwargs: object,
    ) -> list:
        vector_payload = query_vector

        if isinstance(vector_payload, dict):
            extracted = vector_payload.get("query_vector")
            if isinstance(extracted, list):
                logger.warning("Query vector delivered as mapping; extracting 'query_vector' key.")
                vector_payload = extracted
            else:
                logger.warning(
                    "RAG retriever received a dict query vector without a valid 'query_vector' list: %s",
                    vector_payload,
                )
                raise ValueError("Query vector mapping must contain a 'query_vector' list.")

        if not isinstance(vector_payload, list) or not vector_payload:
            logger.warning(
                "RAG retriever received an invalid query vector (type=%s).",
                type(vector_payload).__name__,
            )
            raise ValueError("Query vector must be a non-empty list of floats.")

        if len(vector_payload) != self._expected_dimensions:
            logger.warning(
                "Query vector length mismatch (expected=%s, got=%s) for collection %s.",
                self._expected_dimensions,
                len(vector_payload),
                collection_name,
            )

        vector_name = kwargs.get("vector_name")  # type: ignore[assignment]
        if not isinstance(vector_name, str):
            kwargs["vector_name"] = self._default_vector_name
            logger.warning(
                "vector_name missing for Qdrant search; defaulting to '%s'.",
                self._default_vector_name,
            )
        elif vector_name != self._default_vector_name:
            logger.warning(
                "vector_name override detected: expected '%s', received '%s'.",
                self._default_vector_name,
                vector_name,
            )

        try:
            return self._vectorstore.search(
                collection_name=collection_name,
                query_vector=vector_payload,
                k=k,
                **kwargs,
            )
        except Exception as exc:  # pragma: no cover - delegated to vectorstore
            logger.warning(
                "Qdrant search failed (collection=%s, vector_name=%s, k=%s): %s",
                collection_name,
                kwargs.get("vector_name"),
                k,
                exc,
            )
            raise
