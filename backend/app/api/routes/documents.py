from __future__ import annotations

from io import BytesIO
from typing import Annotated, List
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile, status
from fastapi.responses import StreamingResponse

from app.api.deps import get_db_session
from app.core import exceptions
from app.schemas.document import (
    DocumentListResponse, 
    DocumentSummary, 
    DocumentUploadResponse,
    FormDocumentUploadResponse,
    FormFieldExtractionResponse,
    AutoFillRequest,
    AutoFillResponse
)
from app.services.documents import DocumentService, UploadedFileData
from app.services.form_documents import FormDocumentService
from app.tasks import enqueue_document_processing

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Carica documenti originali",
)
async def upload_documents(
    files: Annotated[List[UploadFile], File(description="Documenti da caricare")],
    session=Depends(get_db_session),
) -> DocumentUploadResponse:
    if not files:
        raise exceptions.AppException("Nessun file fornito per l'upload.")

    # we read synchronously to ensure full validation before saving
    uploads: list[UploadedFileData] = []
    for upload in files:
        data = await upload.read()
        uploads.append(
            UploadedFileData(
                filename=upload.filename or "unnamed",
                content_type=upload.content_type or "application/octet-stream",
                data=data,
            )
        )
        await upload.close()

    service = DocumentService(session)
    documents = service.create_documents(uploads)

    for document in documents:
        enqueue_document_processing(document.id)

    return DocumentUploadResponse(
        documents=[DocumentSummary.model_validate(doc) for doc in documents]
    )


@router.get(
    "/list",
    response_model=DocumentListResponse,
    summary="Lista documenti caricati",
)
def list_documents(
    limit: Annotated[int, Query(ge=1, le=100, description="Numero massimo di elementi")] = 20,
    offset: Annotated[int, Query(ge=0, description="Offset per la paginazione")] = 0,
    session=Depends(get_db_session),
) -> DocumentListResponse:
    service = DocumentService(session)
    documents, total = service.list_documents(limit=limit, offset=offset)

    return DocumentListResponse(
        items=[DocumentSummary.model_validate(doc) for doc in documents],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{document_id}/download",
    summary="Scarica documento originale",
    responses={200: {"content": {"application/octet-stream": {}}, "description": "File"}},
)
def download_document(
    document_id: UUID,
    session=Depends(get_db_session),
) -> Response:
    service = DocumentService(session)
    document = service.get_document(document_id)

    return StreamingResponse(
        BytesIO(document.data),
        media_type=document.content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{document.filename}"',
            "X-Checksum-SHA256": document.checksum_sha256,
        },
    )


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Elimina documento",
)
def delete_document(
    document_id: UUID,
    session=Depends(get_db_session),
) -> Response:
    service = DocumentService(session)
    service.delete_document(document_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{document_id}/reprocess",
    response_model=DocumentSummary,
    summary="Rielabora documento",
)
def reprocess_document(
    document_id: UUID,
    session=Depends(get_db_session),
) -> DocumentSummary:
    service = DocumentService(session)
    document = service.mark_document_for_reprocessing(document_id)
    enqueue_document_processing(document.id)
    return DocumentSummary.model_validate(document)


# Form Filling Endpoints

@router.post(
    "/upload-form",
    response_model=FormDocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Carica documento form per compilazione",
)
async def upload_form_document(
    file: Annotated[UploadFile, File(description="Documento form da caricare")],
    session=Depends(get_db_session),
) -> FormDocumentUploadResponse:
    """
    Carica un documento form (PDF, Word) per la compilazione automatica.
    Il documento NON viene processato dal sistema RAG.
    """
    if not file:
        raise exceptions.AppException("Nessun file fornito per l'upload.")

    service = FormDocumentService(session)
    form_document = await service.upload_form_document(file)
    
    return FormDocumentUploadResponse(
        form_id=form_document.id,
        filename=form_document.filename,
        content_type=form_document.content_type,
        size_bytes=form_document.size_bytes,
        form_type=form_document.form_type
    )


@router.post(
    "/{form_id}/extract-fields",
    response_model=FormFieldExtractionResponse,
    summary="Estrai campi da documento form",
)
def extract_form_fields(
    form_id: UUID,
    session=Depends(get_db_session),
) -> FormFieldExtractionResponse:
    """
    Estrae tutti i campi da un documento form caricato.
    """
    service = FormDocumentService(session)
    fields = service.extract_form_fields(form_id)
    
    return FormFieldExtractionResponse(
        form_id=form_id,
        fields=fields,
        total_fields=len(fields)
    )


@router.post(
    "/{form_id}/auto-fill",
    response_model=AutoFillResponse,
    summary="Auto-compila documento form con RAG",
)
def auto_fill_form(
    form_id: UUID,
    request: AutoFillRequest,
    session=Depends(get_db_session),
) -> AutoFillResponse:
    """
    Auto-compila un documento form usando il sistema RAG per trovare i valori.
    """
    service = FormDocumentService(session)
    response = service.auto_fill_form(form_id, request)
    
    return response


@router.get(
    "/{form_id}/download-filled",
    summary="Scarica documento form compilato",
    responses={200: {"content": {"application/octet-stream": {}}, "description": "File compilato"}},
)
def download_filled_form(
    form_id: UUID,
    session=Depends(get_db_session),
) -> Response:
    """
    Scarica il documento form compilato con i valori trovati dal RAG.
    """
    service = FormDocumentService(session)
    filled_document = service.get_filled_form(form_id)
    
    # Determina il media type in base al tipo di form
    form_document = service._get_form_document(form_id)
    media_type = "application/pdf" if form_document.form_type == "pdf" else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    
    return Response(
        content=filled_document,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="filled_{form_document.filename}"',
        },
    )
