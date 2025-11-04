from __future__ import annotations

from typing import Sequence

from datapizza.core.models import PipelineComponent
from datapizza.type import Node

from app.core.logging import logger


class TableEnhancer(PipelineComponent):
    """
    Arricchisce i nodi contenenti tabelle con formato strutturato e metadati.
    
    Questo componente:
    - Identifica i nodi che contengono tabelle dal parsing Docling
    - Converte le tabelle in formato markdown/testo strutturato
    - Arricchisce i metadati per identificare chunk tabulari
    - Migliora la leggibilità delle tabelle per l'embedding
    """

    def _run(self, node: Node | None = None, **_: object) -> Node:
        if not node:
            logger.warning("TableEnhancer ricevuto nodo vuoto")
            return Node(text="", metadata={})
        
        logger.info("TableEnhancer - Nodo ricevuto: tipo=%s, ha children=%s", 
                   type(node).__name__, hasattr(node, 'children'))
        
        if hasattr(node, 'children') and node.children:
            logger.info("TableEnhancer - Numero di children: %s", len(node.children))
            
            # Log di tutti i docling_type per vedere la distribuzione
            docling_types = []
            for child in node.children:
                child_metadata = getattr(child, 'metadata', {})
                dt = child_metadata.get('docling_type', 'unknown')
                dl = child_metadata.get('docling_label', 'unknown')
                docling_types.append(f"{dt}/{dl}")
            logger.info("TableEnhancer - Tutti i docling_type/label: %s", docling_types)
        
        # Se il nodo ha children, processa i children
        if hasattr(node, 'children') and node.children:
            enhanced_children = []
            table_count = 0
            
            for idx, child in enumerate(node.children):
                is_table = self._is_table_node(child)
                child_metadata = getattr(child, 'metadata', {})
                
                docling_type = child_metadata.get('docling_type', 'unknown')
                docling_label = child_metadata.get('docling_label', 'unknown')
                logger.info("TableEnhancer - Child %s: docling_type=%s, docling_label=%s, is_table=%s", 
                           idx, docling_type, docling_label, is_table)
                
                if is_table:
                    table_count += 1
                    enhanced_child = self._enhance_table_node(child)
                    enhanced_children.append(enhanced_child)
                    logger.info(
                        "Tabella rilevata e arricchita: %s caratteri",
                        len(enhanced_child.text) if hasattr(enhanced_child, 'text') else 0
                    )
                else:
                    enhanced_children.append(child)
            
            if table_count > 0:
                logger.info("Arricchite %s tabelle su %s nodi children", table_count, len(node.children))
            
            # Restituisci il nodo principale con i children arricchiti
            node.children = enhanced_children
            return node
        else:
            # Se il nodo non ha children, controlla se è una tabella
            logger.info("TableEnhancer - Nodo senza children, controllo se è tabella")
            is_table = self._is_table_node(node)
            logger.info("TableEnhancer - Nodo principale è tabella: %s", is_table)
            
            if is_table:
                logger.info("Tabella rilevata nel nodo principale")
                return self._enhance_table_node(node)
            
            logger.info("TableEnhancer - Nessuna tabella rilevata, restituisco nodo originale")
            return node

    async def _a_run(self, node: Node | None = None, **_: object) -> Node:
        # Per ora implementazione sincrona anche in modalità async
        return self._run(node=node)

    def _is_table_node(self, node: Node) -> bool:
        """Determina se un nodo contiene una tabella."""
        # Verifica nei metadati se Docling ha identificato questo come tabella
        metadata = getattr(node, "metadata", {}) or {}
        
        # Docling usa 'docling_type' per il tipo principale
        # e 'docling_label' per il sottotipo
        docling_type = metadata.get("docling_type", "")
        docling_label = metadata.get("docling_label", "")
        
        # Una tabella può essere identificata da:
        # - docling_type == 'tables' (tipo principale)
        # - docling_label == 'table' (sottotipo)
        if docling_type == "tables" or docling_label == "table":
            return True
        
        # Fallback: cerca pattern tipici delle tabelle nel testo
        text = getattr(node, "text", "")
        if not text:
            return False
        
        # Cerca pattern di separatori comuni nelle tabelle
        has_pipes = "|" in text and text.count("|") >= 4
        has_tabs = "\t" in text and text.count("\t") >= 3
        has_multiple_lines = text.count("\n") >= 2
        
        # Una tabella tipicamente ha più righe con separatori
        return has_multiple_lines and (has_pipes or has_tabs)

    def _enhance_table_node(self, node: Node) -> Node:
        """Arricchisce un nodo tabella con formato strutturato."""
        # Aggiungi metadati per identificare questo come tabella
        metadata = dict(getattr(node, "metadata", {}) or {})
        metadata["is_table"] = True
        metadata["content_type"] = "table"
        
        # Se il nodo ha già un formato markdown ben strutturato, mantienilo
        text = getattr(node, "text", "")
        
        # Migliora la formattazione se necessario
        enhanced_text = self._format_table_text(text)
        
        # Aggiungi un prefisso per rendere chiaro che è una tabella
        if not enhanced_text.strip().startswith(("# Tabella", "## Tabella", "**Tabella")):
            enhanced_text = f"**Tabella:**\n\n{enhanced_text}"
        
        # Crea un nuovo nodo con i dati arricchiti
        enhanced_node = Node(
            text=enhanced_text,
            metadata=metadata,
            id=getattr(node, "id", None),
        )
        
        # Preserva altri attributi se presenti
        if hasattr(node, "embeddings"):
            enhanced_node.embeddings = node.embeddings
        
        return enhanced_node

    def _format_table_text(self, text: str) -> str:
        """Formatta il testo della tabella per renderlo più leggibile."""
        if not text:
            return text
        
        lines = text.split("\n")
        
        # Se il testo usa pipe (|) come separatori, è già in formato markdown
        if "|" in text:
            # Assicurati che le righe siano ben separate
            formatted_lines = []
            for line in lines:
                line = line.strip()
                if line:
                    formatted_lines.append(line)
            return "\n".join(formatted_lines)
        
        # Se usa tab, converti in formato markdown
        if "\t" in text:
            formatted_lines = []
            for line in lines:
                if "\t" in line:
                    # Converti tab in pipe-separated
                    cells = [cell.strip() for cell in line.split("\t")]
                    formatted_lines.append(" | ".join(cells))
                elif line.strip():
                    formatted_lines.append(line.strip())
            
            # Aggiungi separator dopo la prima riga (header)
            if len(formatted_lines) > 1:
                # Conta il numero di celle
                first_row_pipes = formatted_lines[0].count("|")
                separator = "|" + "---|" * (first_row_pipes + 1)
                formatted_lines.insert(1, separator)
            
            return "\n".join(formatted_lines)
        
        # Altrimenti restituisci il testo originale
        return text

