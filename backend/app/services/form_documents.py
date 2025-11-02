from __future__ import annotations

import io
import re
from typing import Any, Dict, Iterable, List, Optional
from uuid import UUID, uuid4

import fitz  # PyMuPDF
from datapizza.clients.openai import OpenAIClient
from docx import Document as DocxDocument
from fastapi import UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AppException
from app.core.logging import logger
from app.models import FormDocument, FormField as FormFieldModel
from app.schemas.document import AutoFillRequest, AutoFillResponse, FormField
from app.services.rag import RagRetrievalService


class AIPlaceholderFieldModel(BaseModel):
    """Structured response item describing a single placeholder discovered by the LLM."""

    type: str = Field(..., description="Categoria semantica del campo individuato")
    context: str = Field(..., description="Contesto testuale rilevante intorno al placeholder")
    query: str = Field(..., description="Query ottimizzata per il recupero via RAG")
    name: str = Field(..., description="Nome descrittivo del campo")
    placeholder_text: str = Field(..., description="Testo esatto del placeholder individuato")

    model_config = {"extra": "ignore", "populate_by_name": True}


class AIPlaceholderAnalysis(BaseModel):
    """Collezione di placeholder strutturati restituiti dal modello."""

    fields: List[AIPlaceholderFieldModel] = Field(default_factory=list)


def _build_ai_prompt(text: str, page_num: int) -> str:
    """Crea il prompt da inviare al modello per l'analisi dei placeholder."""
    return (
        "Analizza il seguente testo estratto da un documento form PDF (pagina {page_num}). "
        "Identifica tutti i placeholder (sequenze di underscore, trattini, spazi vuoti) "
        "e per ciascuno fornisci:\n\n"
        "1. Tipo di campo (es. nome, cognome, data_nascita, luogo_nascita, codice_fiscale, "
        "partita_iva, email, indirizzo, telefono, ecc.)\n"
        "2. Contesto significativo (testo prima o dopo il placeholder)\n"
        "3. Query ottimizzata per il sistema RAG\n"
        "4. Nome campo descrittivo\n"
        "5. Testo del placeholder rilevato\n\n"
        "Rispondi in formato JSON con chiave 'fields'.\n\n"
        "Testo da analizzare:\n"
        "{text}"
    ).format(page_num=page_num, text=text)


def _instantiate_openai_client() -> OpenAIClient:
    """Restituisce un client OpenAI configurato per l'analisi dei placeholder."""
    api_key = settings.openai_api_key or "ollama-placeholder"
    model_name = settings.openai_model_name
    client_kwargs: Dict[str, Any] = {"api_key": api_key, "model": model_name}

    base_url = settings.ollama_base_url if not settings.openai_api_key else None
    if base_url:
        # Supporta diversi parametri a seconda della versione del client datapizza.
        for parameter in ("base_url", "api_base", "api_url", "endpoint"):
            try:
                return OpenAIClient(**client_kwargs, **{parameter: base_url})
            except TypeError:
                continue
        logger.warning(
            "OpenAIClient non supporta la personalizzazione dell'endpoint; verrà usata la configurazione di default."
        )
        if not settings.openai_api_key:
            raise RuntimeError(
                "Impossibile configurare un client OpenAI per Ollama senza supporto base_url. "
                "Configura OPENAI_API_KEY oppure aggiorna datapizza-ai."
            )
    return OpenAIClient(**client_kwargs)


class AIPlaceholderAnalyzer:
    """Servizio che utilizza un LLM via datapizza-ai per individuare placeholder testuali."""

    def __init__(self, client: OpenAIClient | None = None, *, max_text_chars: int = 8000) -> None:
        self._client = client or _instantiate_openai_client()
        self._max_text_chars = max_text_chars

    def analyze_text_placeholders(self, text: str, page_num: int) -> List[AIPlaceholderFieldModel]:
        """Invoca il modello per ottenere i placeholder presenti nel testo fornito."""
        sanitized = text.strip()
        if not sanitized:
            return []

        if len(sanitized) > self._max_text_chars:
            logger.debug(
                "Testo pagina %s troppo lungo (%s caratteri): verrà troncato a %s caratteri per l'analisi AI.",
                page_num,
                len(sanitized),
                self._max_text_chars,
            )
            sanitized = sanitized[: self._max_text_chars]

        prompt = _build_ai_prompt(sanitized, page_num)
        logger.debug("Invio analisi AI placeholder per pagina %s (lunghezza testo: %s).", page_num, len(sanitized))

        try:
            response = self._client.structured_response(input=prompt, output_cls=AIPlaceholderAnalysis)
        except Exception as exc:  # pragma: no cover - dipendenza esterna
            logger.warning(
                "Chiamata structured_response fallita durante l'analisi placeholder (pagina %s): %s",
                page_num,
                exc,
            )
            raise
        analyses = list(response.structured_data or [])
        if not analyses:
            return []
        return analyses[0].fields


class FormDocumentService:
    """Service per la gestione dei documenti form e l'auto-compilazione."""

    def __init__(self, session: Session):
        self.session = session
        self.rag_service = RagRetrievalService()
        self._field_counter = 0
        self._registered_field_keys: set[str] = set()
        try:
            self._placeholder_analyzer: AIPlaceholderAnalyzer | None = AIPlaceholderAnalyzer()
        except Exception as exc:  # pragma: no cover - dipendenza esterna
            logger.warning(
                "Analizzatore AI dei placeholder non inizializzato (%s). Verrà usato il fallback regex.",
                exc,
            )
            self._placeholder_analyzer = None

    async def upload_form_document(self, file: UploadFile) -> FormDocument:
        """
        Carica un documento form senza processarlo nel sistema RAG.
        """
        try:
            # Leggi il file
            file_data = await file.read()
            
            # Determina il tipo di form
            form_type = self._detect_form_type(file.filename, file.content_type)
            
            # Crea il documento form nel database
            form_document = FormDocument(
                id=uuid4(),
                filename=file.filename or "unnamed",
                content_type=file.content_type or "application/octet-stream",
                data=file_data,
                form_type=form_type,
                size_bytes=len(file_data),
            )
            
            self.session.add(form_document)
            self.session.commit()
            
            logger.info(f"Documento form caricato: {form_document.id} ({form_type})")
            return form_document
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Errore durante l'upload del documento form: {e}")
            raise AppException(f"Errore durante l'upload del documento form: {str(e)}")

    def extract_form_fields(self, form_id: UUID) -> List[FormField]:
        """
        Estrae tutti i campi da un documento form.
        """
        form_document = self._get_form_document(form_id)
        self._registered_field_keys.clear()
        self._field_counter = 0
        
        try:
            if form_document.form_type == "pdf":
                fields = self._extract_pdf_form_fields(form_document)
            elif form_document.form_type == "word":
                fields = self._extract_word_form_fields(form_document)
            else:
                raise AppException(f"Tipo di form non supportato: {form_document.form_type}")
            
            # Salva i campi nel database
            self._save_form_fields(form_id, fields)
            
            logger.info(f"Estratti {len(fields)} campi dal documento form {form_id}")
            return fields
            
        except Exception as e:
            logger.error(f"Errore durante l'estrazione dei campi dal form {form_id}: {e}")
            raise AppException(f"Errore durante l'estrazione dei campi: {str(e)}")

    def auto_fill_form(self, form_id: UUID, request: AutoFillRequest) -> AutoFillResponse:
        """
        Auto-compila un documento form usando il sistema RAG.
        """
        form_document = self._get_form_document(form_id)
        fields = self._get_form_fields(form_id)
        
        if not fields:
            raise AppException("Nessun campo trovato nel documento form")
        
        logger.info(f"Iniziando auto-compilazione per form {form_id} con {len(fields)} campi")
        logger.info(f"Contesto di ricerca: {request.search_context}")
        logger.info(f"Campi specifici richiesti: {request.field_names}")
        
        # Filtra i campi se specificato
        if request.field_names:
            fields = [f for f in fields if f.name in request.field_names]
        
        filled_fields = []
        search_queries = []
        total_confidence = 0.0
        
        for field in fields:
            # Genera query di ricerca per il campo
            query = self._generate_field_query(field, request.search_context)
            search_queries.append(query)
            
            try:
                # Esegui ricerca RAG
                logger.info(f"Eseguendo ricerca RAG per campo '{field.name}' con query: '{query}'")
                result = list(self.rag_service.semantic_search(query=query, top_k=3))

                if result:
                    # Estrai il valore più rilevante
                    best_match = result[0]
                    field_value = self._extract_chunk_text(best_match).strip()
                    confidence = self._extract_chunk_score(best_match)

                    field.value = field_value or field.value
                    field.confidence_score = confidence
                    total_confidence += confidence

                    logger.info(
                        "Campo '%s' compilato con valore: '%s' (confidenza: %.3f)",
                        field.name,
                        field.value,
                        confidence,
                    )

                    # Log dettagliato dei risultati
                    for i, match in enumerate(result):
                        match_text = self._extract_chunk_text(match).strip()
                        match_score = self._extract_chunk_score(match)
                        logger.debug(
                            "  Risultato %s: '%s' (score: %.3f)",
                            i + 1,
                            match_text[:200],
                            match_score,
                        )
                else:
                    field.confidence_score = 0.0
                    logger.warning(f"Nessun risultato trovato per il campo '{field.name}' con query: '{query}'")
                    
            except Exception as e:
                logger.error(f"Errore durante la ricerca per il campo '{field.name}' con query '{query}': {e}")
                field.confidence_score = 0.0
            
            filled_fields.append(field)
        
        # Calcola confidenza media
        average_confidence = total_confidence / len(filled_fields) if filled_fields else 0.0
        
        return AutoFillResponse(
            form_id=form_id,
            filled_fields=filled_fields,
            total_filled=len([f for f in filled_fields if f.value]),
            average_confidence=average_confidence,
            search_queries=search_queries
        )

    def get_filled_form(self, form_id: UUID) -> bytes:
        """
        Genera il documento form compilato.
        """
        form_document = self._get_form_document(form_id)
        fields = self._get_form_fields(form_id)
        
        try:
            if form_document.form_type == "pdf":
                return self._fill_pdf_form(form_document, fields)
            elif form_document.form_type == "word":
                return self._fill_word_form(form_document, fields)
            else:
                raise AppException(f"Tipo di form non supportato per il download: {form_document.form_type}")
                
        except Exception as e:
            logger.error(f"Errore durante la generazione del form compilato {form_id}: {e}")
            raise AppException(f"Errore durante la generazione del documento compilato: {str(e)}")

    def _detect_form_type(self, filename: Optional[str], content_type: Optional[str]) -> str:
        """Riconosce il tipo di documento form."""
        if filename and filename.lower().endswith('.pdf'):
            return "pdf"
        elif filename and filename.lower().endswith(('.docx', '.doc')):
            return "word"
        elif content_type:
            if 'pdf' in content_type:
                return "pdf"
            elif 'word' in content_type or 'officedocument' in content_type:
                return "word"
        
        return "unknown"

    def _extract_pdf_form_fields(self, form_document: FormDocument) -> List[FormField]:
        """Estrazione campi da PDF forms usando PyMuPDF."""
        fields = []
        
        with fitz.open(stream=form_document.data, filetype="pdf") as doc:
            logger.info(f"Analisi PDF con {len(doc)} pagine")
            
            for page_num, page in enumerate(doc):
                # 1. Cerca AcroForm fields (campi interattivi)
                widgets = list(page.widgets())
                logger.info(f"Pagina {page_num + 1}: trovati {len(widgets)} AcroForm widgets")
                
                for widget in widgets:
                    logger.debug(f"Widget trovato: {widget.field_name} (tipo: {widget.field_type})")
                    field = FormField(
                        name=widget.field_name or f"field_{len(fields)}",
                        field_type=self._map_pdf_field_type(widget.field_type),
                        value=widget.field_value,
                        placeholder=widget.field_label,
                        required=bool(widget.field_flags & 1),  # Bit 0 = required
                        position={
                            "page": page_num + 1,
                            "x": widget.rect.x0,
                            "y": widget.rect.y0,
                            "width": widget.rect.width,
                            "height": widget.rect.height
                        },
                        context=f"Pagina {page_num + 1}: {widget.field_label or widget.field_name}"
                    )
                    fields.append(field)
                    self._register_field_name(field.name)
                
                # 2. Cerca placeholder testuali (come ____________)
                text_fields = self._extract_text_placeholders(page, page_num)
                logger.info(f"Pagina {page_num + 1}: trovati {len(text_fields)} placeholder testuali")
                fields.extend(text_fields)
        
        acroform_count = sum(
            1
            for f in fields
            if isinstance(f.position, dict)
            and {"x", "y", "width", "height"}.issubset(f.position.keys())
        )
        placeholder_count = len(fields) - acroform_count
        logger.info(
            "Totale campi estratti: %s (AcroForm: %s, Placeholder testuali: %s)",
            len(fields),
            acroform_count,
            placeholder_count,
        )
        
        # Log dettagliato dei campi trovati
        for i, field in enumerate(fields):
            logger.debug(f"Campo {i+1}: {field.name} (tipo: {field.field_type}, placeholder: '{field.placeholder}', contesto: '{field.context}')")
        
        return fields

    def _extract_text_placeholders(self, page, page_num: int) -> List[FormField]:
        """Estrae placeholder testuali sfruttando l'analisi AI con fallback regex."""
        if self._placeholder_analyzer:
            try:
                ai_fields = self._extract_text_placeholders_with_ai(page, page_num)
                if ai_fields:
                    return ai_fields
            except Exception as exc:  # pragma: no cover - dipendenza esterna
                logger.warning(
                    "Analisi AI placeholder fallita alla pagina %s: %s. Uso fallback regex.",
                    page_num + 1,
                    exc,
                )

        return self._extract_text_placeholders_with_regex(page, page_num)

    def _extract_text_placeholders_with_ai(self, page, page_num: int) -> List[FormField]:
        """Utilizza il modello LLM per individuare placeholder complessi."""
        if not self._placeholder_analyzer:
            return []

        text = page.get_text()
        logger.debug("Testo pagina %s (prime 500 chars): %s", page_num + 1, text[:500])
        ai_fields = self._placeholder_analyzer.analyze_text_placeholders(text, page_num + 1)
        if not ai_fields:
            return []
        return self._convert_ai_fields_to_form_fields(ai_fields, page_num, text)

    def _extract_text_placeholders_with_regex(self, page, page_num: int) -> List[FormField]:
        """Fallback basato su regex per individuare placeholder semplici."""
        fields: List[FormField] = []

        try:
            text = page.get_text()
            logger.debug("Fallback regex su pagina %s (prime 500 chars): %s", page_num + 1, text[:500])

            placeholder_patterns = [
                r"_{5,}",
                r"\s_{3,}\s",
                r"\(_{2,}\)",
                r"\.{3,}",
                r"-{3,}",
                r"\s{10,}",
            ]

            for pattern in placeholder_patterns:
                for match in re.finditer(pattern, text):
                    placeholder_text = match.group()
                    line_start = text.rfind("\n", 0, match.start()) + 1
                    line_end = text.find("\n", match.end())
                    if line_end == -1:
                        line_end = len(text)
                    full_line = text[line_start:line_end].strip()
                    context_start = max(line_start, match.start() - 80)
                    context_text = text[context_start:match.start()].strip()

                    field_name = self._generate_field_name_from_context(full_line, context_text)
                    field = FormField(
                        name=field_name,
                        field_type="text",
                        value=None,
                        placeholder=placeholder_text,
                        required=False,
                        position={
                            "page": page_num + 1,
                            "text_position": match.start(),
                        },
                        context=full_line or f"Pagina {page_num + 1}: campo da compilare",
                    )
                    fields.append(field)
                    self._register_field_name(field.name)

                    logger.debug(
                        "Placeholder regex '%s' rilevato alla pagina %s con contesto '%s' e campo '%s'",
                        placeholder_text,
                        page_num + 1,
                        context_text,
                        field_name,
                    )

        except Exception as exc:  # pragma: no cover - dipendenza esterna
            logger.warning(
                "Errore durante l'estrazione regex dei placeholder alla pagina %s: %s",
                page_num + 1,
                exc,
            )

        return fields

    def _convert_ai_fields_to_form_fields(
        self,
        ai_fields: Iterable[AIPlaceholderFieldModel],
        page_num: int,
        page_text: str,
    ) -> List[FormField]:
        """Converte la risposta AI in oggetti FormField pydantic."""
        fields: List[FormField] = []
        search_offset = 0

        for ai_field in ai_fields:
            placeholder = (ai_field.placeholder_text or "").strip()
            context = (ai_field.context or "").strip()
            query = self._normalize_ai_query(ai_field)
            name = self._ensure_unique_field_name(ai_field.name)
            text_position = None

            if not placeholder and not context:
                logger.debug(
                    "Risultato AI ignorato perché privo di placeholder e contesto (campo originale: %s)",
                    ai_field.model_dump(),
                )
                continue

            if placeholder:
                idx = page_text.find(placeholder, search_offset)
                if idx == -1:
                    idx = page_text.find(placeholder)
                if idx != -1:
                    text_position = idx
                    search_offset = idx + len(placeholder)

            position: Dict[str, Any] = {"page": page_num + 1}
            if text_position is not None:
                position["text_position"] = text_position
            position["ai"] = {
                "type": ai_field.type,
                "query": query,
                "raw_name": ai_field.name,
                "placeholder_text": ai_field.placeholder_text,
                "context": ai_field.context,
            }

            field = FormField(
                name=name,
                field_type=self._map_ai_field_type(ai_field.type),
                value=None,
                placeholder=placeholder or None,
                required=False,
                position=position,
                context=context or f"Pagina {page_num + 1}: campo da compilare",
            )
            fields.append(field)
            self._register_field_name(field.name)

            logger.debug(
                "Placeholder AI '%s' -> campo '%s' (tipo: %s, query: '%s')",
                placeholder,
                field.name,
                ai_field.type,
                query,
            )

        return fields

    def _generate_field_name_from_context(self, full_line: str, context_text: str) -> str:
        """
        Genera un nome significativo per il campo basato sul contesto.
        """
        
        # Cerca etichette di campo comuni nel testo completo
        field_labels = [
            'nato a', 'residente a', 'via/piazza', 'impresa', 'sede legale', 
            'sede operativa', 'codice fiscale', 'partita IVA', 'e-mail', 'PEC',
            'nome', 'cognome', 'data di nascita', 'indirizzo', 'città', 'provincia',
            'cap', 'telefono', 'fax', 'sito web', 'ragione sociale', 'forma giuridica'
        ]
        
        # Cerca etichette nel testo completo
        for label in field_labels:
            if label in full_line.lower():
                field_name = label.replace(' ', '_').replace('/', '_')
                logger.debug(f"Trovata etichetta campo: '{label}' -> '{field_name}'")
                return self._ensure_unique_field_name(field_name)
        
        # Se non trova etichette, usa le ultime parole del contesto
        if context_text:
            cleaned_context = re.sub(r'[^a-zA-Z0-9\s]', ' ', context_text)
            words = cleaned_context.strip().split()
            
            if len(words) >= 2:
                # Prendi le ultime 2-3 parole
                name_words = words[-3:] if len(words) >= 3 else words[-2:]
                field_name = '_'.join(name_words).lower()
                
                # Se il nome è troppo corto, usa un nome generico
                if len(field_name) >= 3:
                    return self._ensure_unique_field_name(field_name)
        
        # Usa un nome generico
        return self._next_generic_field_name()

    def _normalize_field_key(self, name: str | None) -> str:
        if not name:
            return ""
        return re.sub(r"[^a-zA-Z0-9_]+", "_", name.strip()).strip("_").lower()

    def _register_field_name(self, name: str | None) -> None:
        key = self._normalize_field_key(name)
        if key:
            self._registered_field_keys.add(key)

    def _ensure_unique_field_name(self, candidate: str | None) -> str:
        base_key = self._normalize_field_key(candidate)
        if not base_key:
            return self._next_generic_field_name()

        unique_key = base_key
        suffix = 1
        while unique_key in self._registered_field_keys:
            suffix += 1
            unique_key = f"{base_key}_{suffix}"

        self._registered_field_keys.add(unique_key)
        return unique_key

    def _next_generic_field_name(self) -> str:
        self._field_counter += 1
        generic_name = f"field_{self._field_counter}"
        self._registered_field_keys.add(generic_name)
        return generic_name

    def _normalize_ai_query(self, ai_field: AIPlaceholderFieldModel) -> str:
        query = (ai_field.query or "").strip()
        if query:
            return query

        type_hint = (ai_field.type or "").replace("_", " ").strip()
        context_hint = (ai_field.context or "").strip()
        name_hint = (ai_field.name or "").replace("_", " ").strip()
        fallback_parts = [part for part in (type_hint, context_hint or name_hint) if part]
        if fallback_parts:
            return " ".join(fallback_parts)
        return "informazioni per compilazione form"

    def _map_ai_field_type(self, ai_type: str) -> str:
        mapping = {
            "data_nascita": "date",
            "data_di_nascita": "date",
            "data": "date",
            "telefono": "tel",
            "cellulare": "tel",
            "email": "email",
            "pec": "email",
            "codice_fiscale": "text",
            "partita_iva": "text",
            "numero": "number",
            "quantita": "number",
            "firma": "signature",
        }
        key = (ai_type or "").lower()
        return mapping.get(key, "text")

    def _extract_chunk_text(self, chunk: Any) -> str:
        """Normalizza il testo del chunk indipendentemente dalla struttura restituita."""
        for attr in ("text", "content", "value"):
            value = getattr(chunk, attr, None)
            if isinstance(value, str) and value.strip():
                return value

        if isinstance(chunk, dict):
            for key in ("text", "content", "value"):
                value = chunk.get(key)
                if isinstance(value, str) and value.strip():
                    return value

        metadata = getattr(chunk, "metadata", None)
        if isinstance(metadata, dict):
            for key in ("text", "content", "value"):
                value = metadata.get(key)
                if isinstance(value, str) and value.strip():
                    return value

        payload = getattr(chunk, "payload", None)
        if isinstance(payload, dict):
            for key in ("text", "content"):
                value = payload.get(key)
                if isinstance(value, str) and value.strip():
                    return value

        return ""

    def _extract_chunk_score(self, chunk: Any) -> float:
        """Ricava un punteggio di confidenza dal chunk, normalizzando distanza -> similarità."""
        candidate = getattr(chunk, "score", None)
        if candidate is not None:
            try:
                return float(candidate)
            except (TypeError, ValueError):
                logger.debug("Impossibile convertire score '%s' in float.", candidate)

        distance = getattr(chunk, "distance", None)
        if distance is not None:
            try:
                distance_val = float(distance)
                return max(0.0, 1.0 - distance_val)
            except (TypeError, ValueError):
                logger.debug("Impossibile convertire distance '%s' in float.", distance)

        metadata = getattr(chunk, "metadata", None)
        if isinstance(metadata, dict):
            for key in ("score", "similarity", "confidence"):
                value = metadata.get(key)
                if value is not None:
                    try:
                        return float(value)
                    except (TypeError, ValueError):
                        continue

        if isinstance(chunk, dict):
            for key in ("score", "similarity", "confidence"):
                value = chunk.get(key)
                if value is not None:
                    try:
                        return float(value)
                    except (TypeError, ValueError):
                        continue

        return 0.0

    def _extract_word_form_fields(self, form_document: FormDocument) -> List[FormField]:
        """Estrazione campi da Word forms usando python-docx."""
        fields = []
        
        doc = DocxDocument(io.BytesIO(form_document.data))
        
        # TODO: Implementare estrazione Content Controls per Word forms
        # Per ora restituiamo campi placeholder
        field = FormField(
            name="placeholder_field",
            field_type="text",
            value=None,
            placeholder="Campo da compilare",
            required=False,
            context="Documento Word - implementazione in sviluppo"
        )
        fields.append(field)
        self._register_field_name(field.name)
        
        return fields

    def _fill_pdf_form(self, form_document: FormDocument, fields: List[FormField]) -> bytes:
        """Compila un PDF form con i valori trovati."""
        with fitz.open(stream=form_document.data, filetype="pdf") as doc:
            for page_num, page in enumerate(doc):
                widgets = list(page.widgets())
                
                for widget in widgets:
                    # Trova il campo corrispondente
                    matching_field = next(
                        (f for f in fields if f.name == widget.field_name and f.value),
                        None
                    )
                    
                    if matching_field:
                        widget.field_value = matching_field.value
                        widget.update()
            
            # Salva il PDF compilato
            output_buffer = io.BytesIO()
            doc.save(output_buffer)
            return output_buffer.getvalue()

    def _fill_word_form(self, form_document: FormDocument, fields: List[FormField]) -> bytes:
        """Compila un Word form con i valori trovati."""
        # TODO: Implementare compilazione Word forms
        # Per ora restituiamo il documento originale
        return form_document.data

    def _map_pdf_field_type(self, pdf_field_type: int) -> str:
        """Mappa i tipi di campo PDF a tipi generici."""
        type_mapping = {
            1: "button",    # Push button
            2: "checkbox",  # Check box
            3: "radio",     # Radio button
            4: "text",      # Text field
            5: "select",    # Choice field
            6: "signature", # Signature field
        }
        return type_mapping.get(pdf_field_type, "unknown")

    def _generate_field_query(self, field: FormField, search_context: Optional[str]) -> str:
        """Genera una query di ricerca per un campo specifico."""

        ai_metadata = None
        ai_type = ""
        if isinstance(field.position, dict):
            ai_metadata = field.position.get("ai")  # type: ignore[assignment]
        if isinstance(ai_metadata, dict):
            ai_query = (ai_metadata.get("query") or "").strip()
            if ai_query:
                enriched_query = ai_query
                if field.context:
                    enriched_query += f" {field.context}"
                if search_context:
                    enriched_query += f" {search_context}"
                logger.debug(
                    "Query AI per campo '%s': '%s' (contesto aggiuntivo: '%s')",
                    field.name,
                    enriched_query,
                    field.context,
                )
                return enriched_query
            ai_type = (ai_metadata.get("type") or "").lower()
        else:
            ai_metadata = None
        
        # Mappa dei campi comuni a query specifiche
        field_query_mapping = {
            'nato_a': ['luogo di nascita', 'nato a', 'città di nascita', 'comune di nascita'],
            'residente_a': ['residente a', 'città di residenza', 'comune di residenza', 'indirizzo di residenza'],
            'via_piazza': ['via', 'piazza', 'indirizzo', 'via/piazza', 'strada'],
            'impresa': ['nome impresa', 'ragione sociale', 'denominazione azienda', 'nome ditta'],
            'sede_legale': ['sede legale', 'indirizzo sede legale', 'ubicazione sede legale'],
            'sede_operativa': ['sede operativa', 'indirizzo sede operativa', 'ubicazione sede operativa'],
            'codice_fiscale': ['codice fiscale', 'tax code', 'CF', 'codice fiscale persona fisica'],
            'partita_IVA': ['partita IVA', 'VAT number', 'numero IVA', 'P.IVA'],
            'e_mail': ['email', 'indirizzo email', 'posta elettronica', 'e-mail'],
            'PEC': ['PEC', 'posta elettronica certificata', 'indirizzo PEC'],
            'nome': ['nome', 'nome persona', 'nome completo'],
            'cognome': ['cognome', 'cognome persona', 'cognome completo'],
            'data_di_nascita': ['data di nascita', 'giorno mese anno nascita', 'data nascita'],
            'indirizzo': ['indirizzo', 'via', 'civico', 'numero civico', 'cap'],
            'città': ['città', 'comune', 'località', 'paese'],
            'provincia': ['provincia', 'sigla provincia', 'provincia di residenza'],
            'cap': ['CAP', 'codice postale', 'codice avviamento postale'],
            'telefono': ['telefono', 'numero di telefono', 'cellulare', 'telefono fisso'],
            'fax': ['fax', 'numero fax', 'telefax'],
            'sito_web': ['sito web', 'website', 'indirizzo sito', 'URL'],
            'ragione_sociale': ['ragione sociale', 'denominazione sociale', 'nome azienda'],
            'forma_giuridica': ['forma giuridica', 'tipo società', 'tipologia azienda']
        }
        
        # Cerca se il nome del campo corrisponde a una mappatura
        candidate_keys = [field.name]
        if ai_type:
            candidate_keys.append(ai_type.replace(" ", "_"))

        for field_key, search_terms in field_query_mapping.items():
            if any(field_key in candidate for candidate in candidate_keys):
                # Usa il primo termine di ricerca come query principale
                base_query = search_terms[0]
                logger.debug(f"Campo '{field.name}' mappato a query: '{base_query}'")
                
                # Aggiungi il contesto specifico del campo se disponibile
                if field.context:
                    base_query += f" {field.context}"
                
                # Aggiungi il contesto di ricerca dell'utente
                if search_context:
                    base_query += f" {search_context}"
                
                return base_query
        
        # Se non trova una mappatura specifica, usa l'approccio generico
        base_query = f"{field.name}"
        
        if field.context:
            base_query += f" {field.context}"
        
        if search_context:
            base_query += f" {search_context}"
        
        logger.debug(f"Query generica per campo '{field.name}': '{base_query}'")
        return base_query

    def _get_form_document(self, form_id: UUID) -> FormDocument:
        """Recupera un documento form dal database."""
        form_document = self.session.get(FormDocument, form_id)
        if not form_document:
            raise AppException(f"Documento form {form_id} non trovato")
        return form_document

    def _get_form_fields(self, form_id: UUID) -> List[FormField]:
        """Recupera i campi di un documento form dal database."""
        field_models = self.session.query(FormFieldModel).filter(
            FormFieldModel.form_document_id == form_id
        ).all()
        
        return [
            FormField(
                name=field.name,
                field_type=field.field_type,
                value=field.value,
                placeholder=field.placeholder,
                required=field.required,
                position=field.position,
                context=field.context,
                confidence_score=field.confidence_score
            )
            for field in field_models
        ]

    def _save_form_fields(self, form_id: UUID, fields: List[FormField]) -> None:
        """Salva i campi estratti nel database."""
        # Elimina campi esistenti
        self.session.query(FormFieldModel).filter(
            FormFieldModel.form_document_id == form_id
        ).delete()
        
        # Salva nuovi campi
        for field in fields:
            field_model = FormFieldModel(
                id=uuid4(),
                form_document_id=form_id,
                name=field.name,
                field_type=field.field_type,
                value=field.value,
                placeholder=field.placeholder,
                required=field.required,
                position=field.position,
                context=field.context,
                confidence_score=field.confidence_score
            )
            self.session.add(field_model)
        
        self.session.commit()
