"""Google Cloud Document AI parser adapter for the RAG pipeline."""
from __future__ import annotations

import asyncio
import os
from typing import Any

from datapizza.core.models import PipelineComponent
from datapizza.type import Node, NodeType
from google.api_core.client_options import ClientOptions
from google.cloud import documentai

from pathlib import Path

from app.core.config import BACKEND_DIR, BASE_DIR, settings
from app.core.logging import logger


class DocumentAIParser(PipelineComponent):
    """Parser che utilizza Google Cloud Document AI per l'estrazione testuale."""

    def __init__(self) -> None:
        super().__init__()

        if not settings.document_ai_processor_id:
            raise ValueError(
                "DOCUMENT_AI_PROCESSOR_ID non configurato nel file .env"
            )

        if not settings.google_cloud_project_id:
            raise ValueError("GOOGLE_CLOUD_PROJECT_ID non configurato nel file .env")

        if settings.google_application_credentials:
            configured_path = settings.google_application_credentials
            candidate_paths: list[Path] = []

            path_obj = Path(configured_path)

            if path_obj.is_absolute():
                candidate_paths.append(path_obj)
            else:
                # First try relative to backend directory
                candidate_paths.append((BACKEND_DIR / path_obj).resolve())
                # Then fallback to project root if needed
                candidate_paths.append((BASE_DIR / path_obj).resolve())

            credentials_path: Path | None = next(
                (p for p in candidate_paths if p.exists()),
                None,
            )

            if credentials_path is None:
                raise ValueError(
                    "File credenziali non trovato. Percorsi testati: "
                    + ", ".join(str(p) for p in candidate_paths)
                )

            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(credentials_path)

        options = ClientOptions(
            api_endpoint=f"{settings.document_ai_location}-documentai.googleapis.com"
        )
        self.client = documentai.DocumentProcessorServiceClient(client_options=options)
        self.processor_name = self.client.processor_path(
            settings.google_cloud_project_id,
            settings.document_ai_location,
            settings.document_ai_processor_id,
        )

        logger.info(
            "Document AI inizializzato: project=%s, location=%s, processor=%s",
            settings.google_cloud_project_id,
            settings.document_ai_location,
            settings.document_ai_processor_id,
        )

    def _run(self, text: str, metadata: dict | None = None) -> Node:
        try:
            with open(text, "rb") as file_obj:
                file_content = file_obj.read()

            mime_type = self._get_mime_type(text)

            request = documentai.ProcessRequest(
                name=self.processor_name,
                raw_document=documentai.RawDocument(
                    content=file_content,
                    mime_type=mime_type,
                ),
            )

            result = self.client.process_document(request=request)
            document = result.document

            table_count = sum(len(page.tables) for page in document.pages)

            logger.info(
                "Document AI ha processato %s: %s pagine, %s tabelle",
                text,
                len(document.pages),
                table_count,
            )

            return self._convert_to_nodes(document, metadata or {})
        except Exception as exc:  # pragma: no cover - dipendenza esterna
            logger.error("Errore durante il processing Document AI: %s", exc, exc_info=True)
            raise

    async def _a_run(self, text: str, metadata: dict | None = None) -> Node:
        return await asyncio.to_thread(self._run, text, metadata)

    def _get_mime_type(self, file_path: str) -> str:
        extension = file_path.lower().split(".")[-1]
        mime_types = {
            "pdf": "application/pdf",
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "tiff": "image/tiff",
            "tif": "image/tiff",
            "gif": "image/gif",
            "bmp": "image/bmp",
            "webp": "image/webp",
        }
        return mime_types.get(extension, "application/pdf")

    def _convert_to_nodes(
        self,
        document: documentai.Document,
        base_metadata: dict,
    ) -> Node:
        children: list[Node] = []

        for page_index, page in enumerate(document.pages):
            page_number = page_index + 1
            page_text = self._get_page_text(document.text, page)

            page_node = Node(
                content=page_text,
                metadata={
                    **base_metadata,
                    "page_number": page_number,
                    "element_type": "page",
                },
                node_type=NodeType.PAGE,
            )

            for table_index, table in enumerate(page.tables):
                table_text = self._extract_table_markdown(document.text, table)
                table_node = Node(
                    content=table_text,
                    metadata={
                        **base_metadata,
                        "page_number": page_number,
                        "element_type": "table",
                        "table_index": table_index,
                        "rows": len(table.body_rows),
                        "columns": len(table.header_rows[0].cells)
                        if table.header_rows
                        else 0,
                    },
                    node_type=NodeType.TABLE,
                )
                children.append(table_node)
                logger.debug(
                    "Estratta tabella dalla pagina %s: %s righe, %s caratteri",
                    page_number,
                    len(table.body_rows),
                    len(table_text),
                )

            for form_field in page.form_fields:
                field_name = self._get_text_from_layout(document.text, form_field.field_name)
                field_value = self._get_text_from_layout(document.text, form_field.field_value)
                field_node = Node(
                    content=f"{field_name}: {field_value}",
                    metadata={
                        **base_metadata,
                        "page_number": page_number,
                        "element_type": "form_field",
                        "field_name": field_name,
                        "field_value": field_value,
                    },
                    node_type=NodeType.PARAGRAPH,
                )
                children.append(field_node)

            children.append(page_node)

        parent_node = Node(
            content=document.text,
            metadata={
                **base_metadata,
                "total_pages": len(document.pages),
                "parser": "document_ai",
            },
            node_type=NodeType.DOCUMENT,
            children=children,
        )

        logger.info(
            "Creati %s nodi figli (%s tabelle)",
            len(children),
            sum(1 for node in children if node.metadata.get("element_type") == "table"),
        )
        return parent_node

    def _get_page_text(self, full_text: str, page: documentai.Document.Page) -> str:
        if not page.layout or not page.layout.text_anchor:
            return ""
        return self._get_text_from_layout(full_text, page.layout)

    def _get_text_from_layout(self, full_text: str, layout: Any) -> str:
        if not layout or not hasattr(layout, "text_anchor"):
            return ""

        text_anchor = layout.text_anchor
        if not text_anchor or not text_anchor.text_segments:
            return ""

        segments: list[str] = []
        for segment in text_anchor.text_segments:
            start = int(segment.start_index) if segment.start_index else 0
            end = int(segment.end_index) if segment.end_index else len(full_text)
            segments.append(full_text[start:end])

        return "".join(segments)

    def _extract_table_markdown(
        self,
        full_text: str,
        table: documentai.Document.Page.Table,
    ) -> str:
        lines: list[str] = []

        if table.header_rows:
            for header_row in table.header_rows:
                cells = [
                    self._get_text_from_layout(full_text, cell.layout).strip()
                    for cell in header_row.cells
                ]
                lines.append("| " + " | ".join(cells) + " |")
                lines.append("|" + "|".join(["---"] * len(cells)) + "|")

        for body_row in table.body_rows:
            cells = [
                self._get_text_from_layout(full_text, cell.layout).strip()
                for cell in body_row.cells
            ]
            lines.append("| " + " | ".join(cells) + " |")

        return "\n".join(lines)
