from __future__ import annotations

from functools import lru_cache
from typing import Literal

from datapizza.clients.openai import OpenAIClient
from datapizza.modules.parsers import TextParser
from datapizza.modules.parsers.docling import DoclingParser
from datapizza.modules.prompt import ChatPromptTemplate
from datapizza.modules.rewriters import ToolRewriter
from datapizza.modules.splitters import NodeSplitter
from datapizza.pipeline import DagPipeline
from datapizza.pipeline.pipeline import IngestionPipeline

from app.core.config import settings
from app.core.exceptions import AppException
from app.core.logging import logger

from .components import OllamaChunkEmbedder, OllamaQueryEmbedder
from .vectorstore import ensure_collection, get_vectorstore

IngestionKind = Literal["docling", "text"]

_DEFAULT_REWRITER_PROMPT = (
    "Riscrivi il prompt dell'utente rendendolo più specifico per una ricerca semantica "
    "su documenti aziendali. Mantieni il significato originale e riduci riferimenti ambigui."
)


def create_ingestion_pipeline(kind: IngestionKind) -> IngestionPipeline:
    """Build ingestion pipeline for the requested parser strategy."""
    modules = [
        _resolve_parser(kind),
        NodeSplitter(max_char=settings.rag_chunk_size),
        OllamaChunkEmbedder(batch_size=8),
    ]
    return IngestionPipeline(modules=modules)


def _resolve_parser(kind: IngestionKind):
    if kind == "docling":
        return DoclingParser()
    if kind == "text":
        return TextParser()
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
    vector_module = (
        vectorstore.as_module_component()
        if hasattr(vectorstore, "as_module_component")
        else vectorstore
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
