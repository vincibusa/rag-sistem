from __future__ import annotations

from datetime import datetime
from typing import List
from uuid import UUID

from pydantic import BaseModel

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
