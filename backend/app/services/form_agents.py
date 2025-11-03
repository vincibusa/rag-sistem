from __future__ import annotations

import json
from functools import lru_cache
from typing import Any, Iterable, List, Sequence

from datapizza.agents import Agent
from datapizza.clients.openai import OpenAIClient
from pydantic import BaseModel, Field, ValidationError

from app.core.config import settings
from app.core.logging import logger


class PlaceholderDescriptor(BaseModel):
    """Structured information about a placeholder detected on a page."""

    name: str
    type: str
    query: str
    context: str
    placeholder_text: str | None = Field(default=None)


class PlaceholderDetectionResponse(BaseModel):
    fields: List[PlaceholderDescriptor] = Field(default_factory=list)


class QueryPlan(BaseModel):
    query: str
    reasoning: str | None = None


class FieldCompletionDecision(BaseModel):
    value: str | None = None
    confidence: float = 0.0
    selected_chunk_index: int | None = None
    reason: str | None = None


def _get_agent_client() -> OpenAIClient:
    """Return an OpenAI-compatible client, using Ollama endpoint when OpenAI key is missing."""

    @lru_cache(maxsize=1)
    def _factory() -> OpenAIClient:
        api_key = settings.openai_api_key or "ollama-placeholder"
        client_kwargs: dict[str, Any] = {
            "api_key": api_key,
            "model": settings.openai_model_name,
        }

        # If we're in local dev without OpenAI key, reuse the Ollama endpoint if supported.
        if not settings.openai_api_key:
            base_url = settings.ollama_base_url.rstrip("/")
            for param in ("base_url", "api_base", "api_url", "endpoint"):
                try:
                    return OpenAIClient(**client_kwargs, **{param: base_url})
                except TypeError:
                    continue
            raise RuntimeError(
                "Impossibile configurare un client OpenAI compatibile. "
                "Configura OPENAI_API_KEY oppure aggiorna datapizza-ai."
            )

        return OpenAIClient(**client_kwargs)

    return _factory()


class PlaceholderDetectionAgent:
    """Specialised LLM agent that analyses page text and extracts placeholders metadata."""

    def __init__(self) -> None:
        self._agent = Agent(
            name="placeholder_detector",
            client=_get_agent_client(),
            system_prompt=(
                "Sei uno specialista nell'analizzare documenti PDF di tipo form. "
                "Ricevi il testo estratto da una pagina e devi individuare tutti i campi da compilare "
                "che sono rappresentati da placeholder (es. sequenze di underscore, trattini, "
                "spazi vuoti o caselle di firma). "
                "Per ogni placeholder devi fornire un JSON valido contenente: "
                "type, context, query, name, placeholder_text. "
                "Il campo 'query' deve essere una query ottimizzata da utilizzare in un sistema RAG."
            ),
        )

    def analyse(self, page_text: str, page_num: int) -> List[PlaceholderDescriptor]:
        trimmed = page_text.strip()
        if not trimmed:
            return []

        prompt = (
            "Pagina #: {page_num}\n"
            "Analizza il seguente testo e individua tutti i placeholder compresi eventuali aree vuote "
            "per l'inserimento di dati.\n"
            "Restituisci una risposta JSON con la forma {{\"fields\": [{{...}}]}}. "
            "Assicurati che il JSON sia valido.\n\n"
            "{text}"
        ).format(page_num=page_num, text=trimmed[:8000])

        result = self._agent.run(task_input=prompt)
        raw_text = result.text or ""

        try:
            payload = PlaceholderDetectionResponse.model_validate_json(raw_text)
        except ValidationError:
            logger.debug(
                "PlaceholderDetectionAgent ha fornito output non JSON, provo a ripulire: %s",
                raw_text[:2000],
            )
            try:
                payload = PlaceholderDetectionResponse.model_validate_json(
                    _extract_json_block(raw_text)
                )
            except Exception as exc:
                logger.warning("Impossibile interpretare la risposta dell'agente placeholder: %s", exc)
                return []

        return payload.fields


class RagQueryAgent:
    """Agent dedicated to crafting focused RAG queries for form fields."""

    def __init__(self) -> None:
        self._agent = Agent(
            name="rag_query_planner",
            client=_get_agent_client(),
            system_prompt=(
                "Sei un assistente che riceve le informazioni di un campo di un formulario "
                "e deve costruire una query molto specifica per un sistema di ricerca semantica. "
                "La query deve essere breve ma precisa, includendo gli elementi rilevanti. "
                "Restituisci un JSON valido con le chiavi 'query' e 'reasoning'."
            ),
        )

    def build_query(self, field: dict[str, Any], *, user_context: str | None = None) -> QueryPlan:
        prompt = (
            "Campo: {name}\n"
            "Tipo: {type}\n"
            "Placeholder: {placeholder}\n"
            "Contesto: {context}\n"
            "Informazioni aggiuntive utente: {user_context}\n\n"
            "Genera una query specializzata per trovare il valore corretto."
        ).format(
            name=field.get("name"),
            type=field.get("type"),
            placeholder=field.get("placeholder"),
            context=field.get("context"),
            user_context=user_context or "N/A",
        )

        response = self._agent.run(task_input=prompt)
        raw_text = response.text or ""

        try:
            return QueryPlan.model_validate_json(raw_text)
        except ValidationError:
            logger.debug("RagQueryAgent output non JSON, fallback parsing: %s", raw_text[:1000])
            cleaned = _extract_json_block(raw_text)
            try:
                return QueryPlan.model_validate_json(cleaned)
            except ValidationError:
                return QueryPlan(query=(raw_text or field.get("name") or "").strip())


class DocumentCompletionAgent:
    """Agent that inspects retrieved chunks and decides the best value for a form field."""

    def __init__(self) -> None:
        self._agent = Agent(
            name="form_completion_agent",
            client=_get_agent_client(),
            system_prompt=(
                "Ricevi una lista di estratti testuali recuperati dal sistema RAG e devi scegliere "
                "il testo più adatto da inserire in un campo di un form. "
                "Restituisci un JSON con le chiavi: value (stringa), confidence (0-1), "
                "selected_chunk_index (int o null) e reason (stringa breve). "
                "Se nessun risultato è adatto, lascia value vuoto e confidence 0."
            ),
        )

    def decide(
        self,
        *,
        field: dict[str, Any],
        query: str,
        chunks: Sequence[dict[str, Any]],
        guidance: str | None = None,
    ) -> FieldCompletionDecision:
        formatted_chunks = "\n".join(
            f"- [{idx}] score={chunk.get('score')} source={chunk.get('metadata', {}).get('document_name')} "
            f"text={_truncate(chunk.get('text', ''), 600)}"
            for idx, chunk in enumerate(chunks)
        )

        prompt = (
            "Campo: {field_name}\n"
            "Tipo: {field_type}\n"
            "Query usata: {query}\n"
            "Placeholder: {placeholder}\n"
            "Contesto: {context}\n"
            "Istruzioni utente: {guidance}\n"
            "Risultati RAG:\n{chunks}\n\n"
            "Scegli il miglior testo e rispondi in JSON."
        ).format(
            field_name=field.get("name"),
            field_type=field.get("type"),
            query=query,
            placeholder=field.get("placeholder"),
            context=_truncate(field.get("context", ""), 400),
            guidance=_truncate(guidance, 400) or "N/A",
            chunks=formatted_chunks or "- Nessun risultato",
        )

        result = self._agent.run(task_input=prompt)
        raw_text = result.text or ""

        try:
            decision = FieldCompletionDecision.model_validate_json(raw_text)
        except ValidationError:
            logger.debug("DocumentCompletionAgent output non JSON, cerco blocco JSON: %s", raw_text[:2000])
            try:
                decision = FieldCompletionDecision.model_validate_json(_extract_json_block(raw_text))
            except ValidationError:
                decision = FieldCompletionDecision(value=None, confidence=0.0)

        if decision.selected_chunk_index is not None and (
            decision.selected_chunk_index < 0 or decision.selected_chunk_index >= len(chunks)
        ):
            decision.selected_chunk_index = None
        decision.confidence = max(0.0, min(1.0, decision.confidence))
        return decision


def _truncate(value: str | None, limit: int) -> str:
    if not value:
        return ""
    if len(value) <= limit:
        return value
    return value[: limit - 3] + "..."


def _extract_json_block(text: str) -> str:
    """Extract the first JSON object or array from the LLM response."""
    start_idx = text.find("{")
    if start_idx == -1:
        start_idx = text.find("[")
    if start_idx == -1:
        raise ValueError("Nessun JSON trovato nell'output dell'agente.")

    stack = []
    for idx in range(start_idx, len(text)):
        char = text[idx]
        if char in "{[":
            stack.append("{" if char == "{" else "[")
        elif char in "}]":
            if not stack:
                continue
            opening = stack.pop()
            if not stack:
                return text[start_idx : idx + 1]

    # In caso di JSON tagliato, proviamo comunque a parse con json.loads
    candidate = text[start_idx:]
    json.loads(candidate)  # may raise, leaving to caller
    return candidate
