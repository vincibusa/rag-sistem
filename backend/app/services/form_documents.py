from __future__ import annotations

import io
import re
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4

import fitz  # PyMuPDF
from docx import Document as DocxDocument
from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.core.logging import logger
from app.models import FormDocument, FormField as FormFieldModel
from app.schemas.document import FormField, AutoFillRequest, AutoFillResponse
from app.services.rag import RagRetrievalService


class FormDocumentService:
    """Service per la gestione dei documenti form e l'auto-compilazione."""

    def __init__(self, session: Session):
        self.session = session
        self.rag_service = RagRetrievalService()
        self._field_counter = []  # Per tenere traccia dei nomi dei campi generati

    async def upload_form_document(self, file: UploadFile) -> FormDocument:
        """
        Carica un documento form senza processarlo nel sistema RAG.
        """
        try:
            # Leggi il file
            file_data = await file.read()
            
            # Determina il tipo di form
            form_type = self._detect_form_type(file.filename, file.content_type)
            
            # Crea il documento form nel database
            form_document = FormDocument(
                id=uuid4(),
                filename=file.filename or "unnamed",
                content_type=file.content_type or "application/octet-stream",
                data=file_data,
                form_type=form_type,
                size_bytes=len(file_data),
            )
            
            self.session.add(form_document)
            self.session.commit()
            
            logger.info(f"Documento form caricato: {form_document.id} ({form_type})")
            return form_document
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Errore durante l'upload del documento form: {e}")
            raise AppException(f"Errore durante l'upload del documento form: {str(e)}")

    def extract_form_fields(self, form_id: UUID) -> List[FormField]:
        """
        Estrae tutti i campi da un documento form.
        """
        form_document = self._get_form_document(form_id)
        
        try:
            if form_document.form_type == "pdf":
                fields = self._extract_pdf_form_fields(form_document)
            elif form_document.form_type == "word":
                fields = self._extract_word_form_fields(form_document)
            else:
                raise AppException(f"Tipo di form non supportato: {form_document.form_type}")
            
            # Salva i campi nel database
            self._save_form_fields(form_id, fields)
            
            logger.info(f"Estratti {len(fields)} campi dal documento form {form_id}")
            return fields
            
        except Exception as e:
            logger.error(f"Errore durante l'estrazione dei campi dal form {form_id}: {e}")
            raise AppException(f"Errore durante l'estrazione dei campi: {str(e)}")

    def auto_fill_form(self, form_id: UUID, request: AutoFillRequest) -> AutoFillResponse:
        """
        Auto-compila un documento form usando il sistema RAG.
        """
        form_document = self._get_form_document(form_id)
        fields = self._get_form_fields(form_id)
        
        if not fields:
            raise AppException("Nessun campo trovato nel documento form")
        
        logger.info(f"Iniziando auto-compilazione per form {form_id} con {len(fields)} campi")
        logger.info(f"Contesto di ricerca: {request.search_context}")
        logger.info(f"Campi specifici richiesti: {request.field_names}")
        
        # Filtra i campi se specificato
        if request.field_names:
            fields = [f for f in fields if f.name in request.field_names]
        
        filled_fields = []
        search_queries = []
        total_confidence = 0.0
        
        for field in fields:
            # Genera query di ricerca per il campo
            query = self._generate_field_query(field, request.search_context)
            search_queries.append(query)
            
            try:
                # Esegui ricerca RAG
                logger.info(f"Eseguendo ricerca RAG per campo '{field.name}' con query: '{query}'")
                result = self.rag_service.semantic_search(query=query, top_k=3)
                
                if result:
                    # Estrai il valore più rilevante
                    best_match = result[0]
                    field.value = best_match.text
                    field.confidence_score = best_match.score or 0.0
                    total_confidence += field.confidence_score
                    
                    logger.info(f"Campo '{field.name}' compilato con valore: '{field.value}' (confidenza: {field.confidence_score})")
                    
                    # Log dettagliato dei risultati
                    for i, match in enumerate(result):
                        logger.debug(f"  Risultato {i+1}: '{match.text}' (score: {match.score})")
                else:
                    field.confidence_score = 0.0
                    logger.warning(f"Nessun risultato trovato per il campo '{field.name}' con query: '{query}'")
                    
            except Exception as e:
                logger.error(f"Errore durante la ricerca per il campo '{field.name}' con query '{query}': {e}")
                field.confidence_score = 0.0
            
            filled_fields.append(field)
        
        # Calcola confidenza media
        average_confidence = total_confidence / len(filled_fields) if filled_fields else 0.0
        
        return AutoFillResponse(
            form_id=form_id,
            filled_fields=filled_fields,
            total_filled=len([f for f in filled_fields if f.value]),
            average_confidence=average_confidence,
            search_queries=search_queries
        )

    def get_filled_form(self, form_id: UUID) -> bytes:
        """
        Genera il documento form compilato.
        """
        form_document = self._get_form_document(form_id)
        fields = self._get_form_fields(form_id)
        
        try:
            if form_document.form_type == "pdf":
                return self._fill_pdf_form(form_document, fields)
            elif form_document.form_type == "word":
                return self._fill_word_form(form_document, fields)
            else:
                raise AppException(f"Tipo di form non supportato per il download: {form_document.form_type}")
                
        except Exception as e:
            logger.error(f"Errore durante la generazione del form compilato {form_id}: {e}")
            raise AppException(f"Errore durante la generazione del documento compilato: {str(e)}")

    def _detect_form_type(self, filename: Optional[str], content_type: Optional[str]) -> str:
        """Riconosce il tipo di documento form."""
        if filename and filename.lower().endswith('.pdf'):
            return "pdf"
        elif filename and filename.lower().endswith(('.docx', '.doc')):
            return "word"
        elif content_type:
            if 'pdf' in content_type:
                return "pdf"
            elif 'word' in content_type or 'officedocument' in content_type:
                return "word"
        
        return "unknown"

    def _extract_pdf_form_fields(self, form_document: FormDocument) -> List[FormField]:
        """Estrazione campi da PDF forms usando PyMuPDF."""
        fields = []
        
        with fitz.open(stream=form_document.data, filetype="pdf") as doc:
            logger.info(f"Analisi PDF con {len(doc)} pagine")
            
            for page_num, page in enumerate(doc):
                # 1. Cerca AcroForm fields (campi interattivi)
                widgets = list(page.widgets())
                logger.info(f"Pagina {page_num + 1}: trovati {len(widgets)} AcroForm widgets")
                
                for widget in widgets:
                    logger.debug(f"Widget trovato: {widget.field_name} (tipo: {widget.field_type})")
                    field = FormField(
                        name=widget.field_name or f"field_{len(fields)}",
                        field_type=self._map_pdf_field_type(widget.field_type),
                        value=widget.field_value,
                        placeholder=widget.field_label,
                        required=bool(widget.field_flags & 1),  # Bit 0 = required
                        position={
                            "page": page_num + 1,
                            "x": widget.rect.x0,
                            "y": widget.rect.y0,
                            "width": widget.rect.width,
                            "height": widget.rect.height
                        },
                        context=f"Pagina {page_num + 1}: {widget.field_label or widget.field_name}"
                    )
                    fields.append(field)
                
                # 2. Cerca placeholder testuali (come ____________)
                text_fields = self._extract_text_placeholders(page, page_num)
                logger.info(f"Pagina {page_num + 1}: trovati {len(text_fields)} placeholder testuali")
                fields.extend(text_fields)
        
        logger.info(f"Totale campi estratti: {len(fields)} (AcroForm: {len([f for f in fields if f.field_type != 'text_placeholder'])}, Placeholder: {len([f for f in fields if f.field_type == 'text_placeholder'])})")
        
        # Log dettagliato dei campi trovati
        for i, field in enumerate(fields):
            logger.debug(f"Campo {i+1}: {field.name} (tipo: {field.field_type}, placeholder: '{field.placeholder}', contesto: '{field.context}')")
        
        return fields

    def _extract_text_placeholders(self, page, page_num: int) -> List[FormField]:
        """
        Estrae placeholder testuali dal PDF (come ____________, _______, ecc.).
        """
        fields = []
        
        try:
            # Estrai tutto il testo dalla pagina
            text = page.get_text()
            logger.debug(f"Testo pagina {page_num + 1}: {text[:500]}...")
            
            # Pattern per placeholder comuni
            placeholder_patterns = [
                r'_{5,}',  # Underscores consecutivi (5+ caratteri) per ________________
                r'\s_{3,}\s',  # Underscores con spazi
                r'\(_{2,}\)',  # Parentesi con underscores come (___)
                r'\.{3,}',  # Punti consecutivi
                r'-{3,}',  # Trattini consecutivi
                r'\s{10,}',  # Spazi consecutivi (potrebbero essere campi vuoti)
            ]
            
            for pattern in placeholder_patterns:
                matches = list(re.finditer(pattern, text))
                for match in matches:
                    placeholder_text = match.group()
                    
                    # Estrai l'intera riga contenente il placeholder
                    line_start = text.rfind('\n', 0, match.start()) + 1
                    line_end = text.find('\n', match.end())
                    if line_end == -1:
                        line_end = len(text)
                    
                    full_line = text[line_start:line_end].strip()
                    
                    # Prova a trovare il contesto (testo prima del placeholder nella stessa riga)
                    context_start = max(line_start, match.start() - 50)
                    context_text = text[context_start:match.start()].strip()
                    
                    logger.debug(f"Placeholder trovato: '{placeholder_text}' in riga: '{full_line}'")
                    
                    # Crea un nome più significativo basato sul contesto
                    field_name = self._generate_field_name_from_context(full_line, context_text)
                    
                    field = FormField(
                        name=field_name,
                        field_type="text",  # Usiamo "text" invece di "text_placeholder" per compatibilità
                        value=None,
                        placeholder=placeholder_text,
                        required=False,
                        position={
                            "page": page_num + 1,
                            "text_position": match.start()
                        },
                        context=full_line if full_line else f"Pagina {page_num + 1}: campo da compilare"
                    )
                    fields.append(field)
                    
                    logger.debug(f"Placeholder trovato: '{placeholder_text}' con contesto: '{context}', nome campo: '{field_name}'")
            
        except Exception as e:
            logger.warning(f"Errore durante l'estrazione dei placeholder testuali dalla pagina {page_num + 1}: {e}")
        
        return fields

    def _generate_field_name_from_context(self, full_line: str, context_text: str) -> str:
        """
        Genera un nome significativo per il campo basato sul contesto.
        """
        
        # Cerca etichette di campo comuni nel testo completo
        field_labels = [
            'nato a', 'residente a', 'via/piazza', 'impresa', 'sede legale', 
            'sede operativa', 'codice fiscale', 'partita IVA', 'e-mail', 'PEC',
            'nome', 'cognome', 'data di nascita', 'indirizzo', 'città', 'provincia',
            'cap', 'telefono', 'fax', 'sito web', 'ragione sociale', 'forma giuridica'
        ]
        
        # Cerca etichette nel testo completo
        for label in field_labels:
            if label in full_line.lower():
                field_name = label.replace(' ', '_').replace('/', '_')
                logger.debug(f"Trovata etichetta campo: '{label}' -> '{field_name}'")
                return field_name
        
        # Se non trova etichette, usa le ultime parole del contesto
        if context_text:
            cleaned_context = re.sub(r'[^a-zA-Z0-9\s]', ' ', context_text)
            words = cleaned_context.strip().split()
            
            if len(words) >= 2:
                # Prendi le ultime 2-3 parole
                name_words = words[-3:] if len(words) >= 3 else words[-2:]
                field_name = '_'.join(name_words).lower()
                
                # Se il nome è troppo corto, usa un nome generico
                if len(field_name) >= 3:
                    return field_name
        
        # Usa un nome generico
        self._field_counter.append(1)
        return f"field_{len(self._field_counter)}"

    def _extract_word_form_fields(self, form_document: FormDocument) -> List[FormField]:
        """Estrazione campi da Word forms usando python-docx."""
        fields = []
        
        doc = DocxDocument(io.BytesIO(form_document.data))
        
        # TODO: Implementare estrazione Content Controls per Word forms
        # Per ora restituiamo campi placeholder
        field = FormField(
            name="placeholder_field",
            field_type="text",
            value=None,
            placeholder="Campo da compilare",
            required=False,
            context="Documento Word - implementazione in sviluppo"
        )
        fields.append(field)
        
        return fields

    def _fill_pdf_form(self, form_document: FormDocument, fields: List[FormField]) -> bytes:
        """Compila un PDF form con i valori trovati."""
        with fitz.open(stream=form_document.data, filetype="pdf") as doc:
            for page_num, page in enumerate(doc):
                widgets = list(page.widgets())
                
                for widget in widgets:
                    # Trova il campo corrispondente
                    matching_field = next(
                        (f for f in fields if f.name == widget.field_name and f.value),
                        None
                    )
                    
                    if matching_field:
                        widget.field_value = matching_field.value
                        widget.update()
            
            # Salva il PDF compilato
            output_buffer = io.BytesIO()
            doc.save(output_buffer)
            return output_buffer.getvalue()

    def _fill_word_form(self, form_document: FormDocument, fields: List[FormField]) -> bytes:
        """Compila un Word form con i valori trovati."""
        # TODO: Implementare compilazione Word forms
        # Per ora restituiamo il documento originale
        return form_document.data

    def _map_pdf_field_type(self, pdf_field_type: int) -> str:
        """Mappa i tipi di campo PDF a tipi generici."""
        type_mapping = {
            1: "button",    # Push button
            2: "checkbox",  # Check box
            3: "radio",     # Radio button
            4: "text",      # Text field
            5: "select",    # Choice field
            6: "signature", # Signature field
        }
        return type_mapping.get(pdf_field_type, "unknown")

    def _generate_field_query(self, field: FormField, search_context: Optional[str]) -> str:
        """Genera una query di ricerca per un campo specifico."""
        
        # Mappa dei campi comuni a query specifiche
        field_query_mapping = {
            'nato_a': ['luogo di nascita', 'nato a', 'città di nascita', 'comune di nascita'],
            'residente_a': ['residente a', 'città di residenza', 'comune di residenza', 'indirizzo di residenza'],
            'via_piazza': ['via', 'piazza', 'indirizzo', 'via/piazza', 'strada'],
            'impresa': ['nome impresa', 'ragione sociale', 'denominazione azienda', 'nome ditta'],
            'sede_legale': ['sede legale', 'indirizzo sede legale', 'ubicazione sede legale'],
            'sede_operativa': ['sede operativa', 'indirizzo sede operativa', 'ubicazione sede operativa'],
            'codice_fiscale': ['codice fiscale', 'tax code', 'CF', 'codice fiscale persona fisica'],
            'partita_IVA': ['partita IVA', 'VAT number', 'numero IVA', 'P.IVA'],
            'e_mail': ['email', 'indirizzo email', 'posta elettronica', 'e-mail'],
            'PEC': ['PEC', 'posta elettronica certificata', 'indirizzo PEC'],
            'nome': ['nome', 'nome persona', 'nome completo'],
            'cognome': ['cognome', 'cognome persona', 'cognome completo'],
            'data_di_nascita': ['data di nascita', 'giorno mese anno nascita', 'data nascita'],
            'indirizzo': ['indirizzo', 'via', 'civico', 'numero civico', 'cap'],
            'città': ['città', 'comune', 'località', 'paese'],
            'provincia': ['provincia', 'sigla provincia', 'provincia di residenza'],
            'cap': ['CAP', 'codice postale', 'codice avviamento postale'],
            'telefono': ['telefono', 'numero di telefono', 'cellulare', 'telefono fisso'],
            'fax': ['fax', 'numero fax', 'telefax'],
            'sito_web': ['sito web', 'website', 'indirizzo sito', 'URL'],
            'ragione_sociale': ['ragione sociale', 'denominazione sociale', 'nome azienda'],
            'forma_giuridica': ['forma giuridica', 'tipo società', 'tipologia azienda']
        }
        
        # Cerca se il nome del campo corrisponde a una mappatura
        for field_key, search_terms in field_query_mapping.items():
            if field_key in field.name:
                # Usa il primo termine di ricerca come query principale
                base_query = search_terms[0]
                logger.debug(f"Campo '{field.name}' mappato a query: '{base_query}'")
                
                # Aggiungi il contesto specifico del campo se disponibile
                if field.context:
                    base_query += f" {field.context}"
                
                # Aggiungi il contesto di ricerca dell'utente
                if search_context:
                    base_query += f" {search_context}"
                
                return base_query
        
        # Se non trova una mappatura specifica, usa l'approccio generico
        base_query = f"{field.name}"
        
        if field.context:
            base_query += f" {field.context}"
        
        if search_context:
            base_query += f" {search_context}"
        
        logger.debug(f"Query generica per campo '{field.name}': '{base_query}'")
        return base_query

    def _get_form_document(self, form_id: UUID) -> FormDocument:
        """Recupera un documento form dal database."""
        form_document = self.session.get(FormDocument, form_id)
        if not form_document:
            raise AppException(f"Documento form {form_id} non trovato")
        return form_document

    def _get_form_fields(self, form_id: UUID) -> List[FormField]:
        """Recupera i campi di un documento form dal database."""
        field_models = self.session.query(FormFieldModel).filter(
            FormFieldModel.form_document_id == form_id
        ).all()
        
        return [
            FormField(
                name=field.name,
                field_type=field.field_type,
                value=field.value,
                placeholder=field.placeholder,
                required=field.required,
                position=field.position,
                context=field.context,
                confidence_score=field.confidence_score
            )
            for field in field_models
        ]

    def _save_form_fields(self, form_id: UUID, fields: List[FormField]) -> None:
        """Salva i campi estratti nel database."""
        # Elimina campi esistenti
        self.session.query(FormFieldModel).filter(
            FormFieldModel.form_document_id == form_id
        ).delete()
        
        # Salva nuovi campi
        for field in fields:
            field_model = FormFieldModel(
                id=uuid4(),
                form_document_id=form_id,
                name=field.name,
                field_type=field.field_type,
                value=field.value,
                placeholder=field.placeholder,
                required=field.required,
                position=field.position,
                context=field.context,
                confidence_score=field.confidence_score
            )
            self.session.add(field_model)
        
        self.session.commit()