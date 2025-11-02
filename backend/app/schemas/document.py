from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.models import DocumentStatus


class DocumentSummary(BaseModel):
    id: UUID
    filename: str
    content_type: str
    size_bytes: int
    status: DocumentStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentUploadResponse(BaseModel):
    documents: List[DocumentSummary]


class DocumentListResponse(BaseModel):
    items: List[DocumentSummary]
    total: int
    limit: int
    offset: int


# Form Filling Schemas

class FormField(BaseModel):
    """Modello per un singolo campo di un form."""
    name: str = Field(..., description="Nome del campo")
    field_type: str = Field(..., description="Tipo di campo (text, date, number, checkbox, etc.)")
    value: Optional[str] = Field(None, description="Valore corrente del campo")
    placeholder: Optional[str] = Field(None, description="Testo placeholder del campo")
    required: bool = Field(False, description="Se il campo è obbligatorio")
    position: Optional[Dict[str, Any]] = Field(None, description="Posizione del campo nel documento")
    context: Optional[str] = Field(None, description="Contesto semantico del campo")
    confidence_score: Optional[float] = Field(None, description="Punteggio di confidenza per valore auto-compilato")


class FormDocumentUploadResponse(BaseModel):
    """Response per l'upload di un documento form."""
    form_id: UUID = Field(..., description="ID del documento form")
    filename: str = Field(..., description="Nome del file")
    content_type: str = Field(..., description="Tipo di contenuto")
    size_bytes: int = Field(..., description="Dimensione in bytes")
    form_type: str = Field(..., description="Tipo di form (pdf, word, excel)")


class FormFieldExtractionResponse(BaseModel):
    """Response per l'estrazione dei campi form."""
    form_id: UUID = Field(..., description="ID del documento form")
    fields: List[FormField] = Field(..., description="Lista dei campi estratti")
    total_fields: int = Field(..., description="Numero totale di campi estratti")


class AutoFillRequest(BaseModel):
    """Request per l'auto-compilazione di un form."""
    form_id: UUID = Field(..., description="ID del documento form")
    field_names: Optional[List[str]] = Field(None, description="Campi specifici da compilare (se None, tutti i campi)")
    search_context: Optional[str] = Field(None, description="Contesto aggiuntivo per la ricerca")


class AutoFillResponse(BaseModel):
    """Response per l'auto-compilazione di un form."""
    form_id: UUID = Field(..., description="ID del documento form")
    filled_fields: List[FormField] = Field(..., description="Campi compilati con valori")
    total_filled: int = Field(..., description="Numero di campi compilati")
    average_confidence: float = Field(..., description="Punteggio di confidenza medio")
    search_queries: List[str] = Field(..., description="Query di ricerca utilizzate")
