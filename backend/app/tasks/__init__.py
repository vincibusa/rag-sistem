"""Celery task registrations."""

from .documents import process_document_task, enqueue_document_processing

__all__ = ["process_document_task", "enqueue_document_processing"]
