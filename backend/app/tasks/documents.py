from __future__ import annotations

import uuid

from app.core.celery_app import celery_app
from app.core.logging import logger
from app.db.session import SessionLocal
from app.services.rag import DocumentProcessingService


@celery_app.task(name="app.tasks.documents.process_document")
def process_document_task(document_id: str) -> None:
    session = SessionLocal()
    try:
        service = DocumentProcessingService(session)
        service.process_document(uuid.UUID(document_id))
        logger.info("Documento %s processato con successo", document_id)
    except Exception:
        logger.exception("Errore durante il processing del documento %s", document_id)
        raise
    finally:
        session.close()


def enqueue_document_processing(document_id: uuid.UUID) -> None:
    process_document_task.delay(str(document_id))
