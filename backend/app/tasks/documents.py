from __future__ import annotations

import uuid

from app.core.celery_app import celery_app
from app.core.logging import logger
from app.db.session import SessionLocal
from app.services.rag import DocumentProcessingService


@celery_app.task(
    name="app.tasks.documents.process_document",
    max_retries=3,
    default_retry_delay=60,  # 60 secondi tra un retry e l'altro
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,  # massimo 10 minuti di delay
    retry_jitter=True,  # aggiunge random jitter per evitare thundering herd
)
def process_document_task(document_id: str) -> None:
    session = SessionLocal()
    try:
        service = DocumentProcessingService(session)
        service.process_document(uuid.UUID(document_id))
        logger.info("Documento %s processato con successo", document_id)
    except Exception as exc:
        logger.exception("Errore durante il processing del documento %s", document_id)
        raise process_document_task.retry(exc=exc)  # type: ignore
    finally:
        session.close()


def enqueue_document_processing(document_id: uuid.UUID) -> None:
    process_document_task.delay(str(document_id))
