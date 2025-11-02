from __future__ import annotations

from io import BytesIO
from typing import Annotated, List
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile, status
from fastapi.responses import StreamingResponse

from app.api.deps import get_db_session
from app.core import exceptions
from app.schemas.document import DocumentListResponse, DocumentSummary, DocumentUploadResponse
from app.services.documents import DocumentService, UploadedFileData
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
