from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from io import BytesIO
import mimetypes
from pathlib import Path
from typing import Iterable
import zipfile

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import exceptions
from app.core.config import settings
from app.core.logging import logger
from app.models import Document, DocumentStatus
from app.rag import ensure_collection, get_vectorstore


@dataclass
class UploadedFileData:
    filename: str
    content_type: str
    data: bytes


class DocumentService:
    def __init__(self, session: Session):
        self.session = session

    def _validate_filename(self, filename: str) -> str:
        name = filename.strip()
        if not name:
            raise exceptions.AppException("Il nome del file non può essere vuoto.")
        return name

    def _validate_extension(self, filename: str) -> None:
        extension = Path(filename).suffix.lower().lstrip(".")
        if extension not in settings.allowed_file_extensions:
            raise exceptions.AppException(
                message=f"Formato non supportato: .{extension or 'unknown'}",
                status_code=415,
            )

    def _validate_size(self, size_bytes: int) -> None:
        if size_bytes == 0:
            raise exceptions.AppException("Il file caricato è vuoto.")
        if size_bytes > settings.max_upload_bytes:
            raise exceptions.AppException(
                message="Il file supera la dimensione massima consentita.",
                status_code=413,
                extra={"max_bytes": settings.max_upload_bytes},
            )

    def create_documents(self, files: Iterable[UploadedFileData]) -> list[Document]:
        documents: list[Document] = []

        for file in files:
            filename = self._validate_filename(file.filename)
            extension = Path(filename).suffix.lower().lstrip(".")

            if extension == "zip":
                documents.extend(self._create_documents_from_zip(file, filename))
                continue

            self._validate_extension(filename)
            self._validate_size(len(file.data))

            document = self._create_document_record(
                filename=filename,
                content_type=file.content_type or "application/octet-stream",
                data=file.data,
                extra_metadata={
                    "source": "upload",
                    "original_filename": filename,
                },
            )
            documents.append(document)

        self.session.commit()

        for document in documents:
            self.session.refresh(document)

        return documents

    def list_documents(self, limit: int, offset: int) -> tuple[list[Document], int]:
        stmt = (
            select(Document)
            .order_by(Document.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = self.session.execute(stmt).scalars().all()

        total = self.session.execute(select(func.count()).select_from(Document)).scalar_one()

        return result, total

    def get_document(self, document_id: uuid.UUID) -> Document:
        document = self.session.get(Document, document_id)
        if document is None:
            raise exceptions.AppException("Documento non trovato", status_code=404)
        return document

    def delete_document(self, document_id: uuid.UUID) -> None:
        document = self.session.get(Document, document_id)
        if document is None:
            raise exceptions.AppException("Documento non trovato", status_code=404)

        ensure_collection()
        vectorstore = get_vectorstore()
        point_ids = [chunk.qdrant_point_id for chunk in document.chunks if chunk.qdrant_point_id]
        if point_ids:
            try:
                vectorstore.remove(
                    collection_name=settings.qdrant_collection_name,
                    ids=point_ids,
                )
            except Exception as exc:  # pragma: no cover - qdrant failure surfaces upstream
                logger.warning(
                    "Impossibile rimuovere i punti Qdrant per il documento %s: %s",
                    document_id,
                    exc,
                )

        self.session.delete(document)
        self.session.commit()

    def mark_document_for_reprocessing(self, document_id: uuid.UUID) -> Document:
        document = self.session.get(Document, document_id)
        if document is None:
            raise exceptions.AppException("Documento non trovato", status_code=404)

        document.status = DocumentStatus.PROCESSING
        extra = dict(document.extra_metadata or {})
        extra.pop("last_error", None)
        document.extra_metadata = extra or None

        self.session.commit()
        self.session.refresh(document)
        return document

    def _create_document_record(
        self,
        *,
        filename: str,
        content_type: str,
        data: bytes,
        extra_metadata: dict[str, str] | None = None,
    ) -> Document:
        checksum = hashlib.sha256(data).hexdigest()

        document = Document(
            filename=filename,
            content_type=content_type,
            size_bytes=len(data),
            checksum_sha256=checksum,
            data=data,
            status=DocumentStatus.NEW,
            extra_metadata=extra_metadata,
        )

        self.session.add(document)
        return document

    def _create_documents_from_zip(
        self, file: UploadedFileData, archive_name: str
    ) -> list[Document]:
        documents: list[Document] = []

        try:
            archive = zipfile.ZipFile(BytesIO(file.data))
        except zipfile.BadZipFile as exc:  # pragma: no cover - defensive guard
            raise exceptions.AppException(
                "Archivio zip non valido o corrotto.", status_code=400
            ) from exc

        with archive:
            members = [info for info in archive.infolist() if not info.is_dir()]
            if not members:
                raise exceptions.AppException(
                    "L'archivio zip non contiene file supportati.", status_code=400
                )

            archive_stem = Path(archive_name).stem

            for member in members:
                inner_path = Path(member.filename)
                if any(part.startswith("__MACOSX") for part in inner_path.parts):
                    continue
                if inner_path.name.startswith("."):
                    continue
                extension = inner_path.suffix.lower().lstrip(".")
                if extension not in settings.allowed_file_extensions:
                    logger.debug(
                        "Ignoro il file %s nell'archivio %s: estensione non supportata",  # pragma: no cover - informational
                        member.filename,
                        archive_name,
                    )
                    continue

                data = archive.read(member)
                if not data:
                    continue

                self._validate_size(len(data))

                relative_name = f"{archive_stem}/{member.filename}".strip()
                filename = self._validate_filename(relative_name)
                content_type = (
                    mimetypes.guess_type(inner_path.name)[0]
                    or file.content_type
                    or "application/octet-stream"
                )

                extra_metadata = {
                    "source": "upload",
                    "original_filename": inner_path.name,
                    "archive_name": archive_name,
                    "archive_path": str(inner_path),
                }

                document = self._create_document_record(
                    filename=filename,
                    content_type=content_type,
                    data=data,
                    extra_metadata=extra_metadata,
                )
                documents.append(document)

        if not documents:
            raise exceptions.AppException(
                "Nessun file con estensione supportata trovato nell'archivio.",
                status_code=415,
            )

        return documents
