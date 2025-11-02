# Piano di Implementazione: Document Form Filling con RAG

## Overview
Implementare una feature che permetta agli utenti di caricare documenti con form fields, usare il sistema RAG per trovare automaticamente i dati con cui compilare i campi, e scaricare il documento compilato mantenendo il formato originale.

## Architettura a Doppio Percorso

### Documenti per Conoscenza (RAG)
- [ ] **Processo**: Docling parser → NodeSplitter → OllamaChunkEmbedder → Vector Store
- [ ] **Scopo**: Fornire conoscenza per compilare i form
- [ ] **Estensioni**: PDF, DOC, DOCX, XLS, XLSX, TXT

### Documenti da Compilare (Form Filling)
- [ ] **Processo**: Librerie specializzate per form field detection → Estrazione campi → Auto-compilazione → Download
- [ ] **Scopo**: Documenti che contengono form da compilare
- [ ] **Estensioni**: PDF (con AcroForm), DOCX (con Content Controls)
- [ ] **NON** vengono embedded nel vector store

---

## Fase 1: Setup e Dependencies

### Backend Dependencies
- [x] Aggiungere PyMuPDF>=1.23.0 per PDF form handling
- [x] Aggiungere python-docx>=1.1.0 per Word form handling  
- [x] Aggiungere openpyxl>=3.1.0 per Excel form handling (opzionale)

### Frontend Setup
- [ ] Verificare che i componenti UI esistenti supportino il nuovo flusso
- [ ] Preparare struttura per nuovi componenti form filling

---

## Fase 2: Backend - Schema e API

### Nuovi Schemas Pydantic
- [x] `FormField` - modello per singolo campo form
- [x] `FormDocumentUploadResponse` - response per upload form
- [x] `FormFieldExtractionResponse` - response con campi estratti
- [x] `AutoFillRequest` - request per auto-compilazione
- [x] `AutoFillResponse` - response con valori compilati

### Nuovi Endpoints API
- [x] `POST /documents/upload-form` - Upload documenti form (percorso separato)
- [x] `POST /documents/{form_id}/extract-fields` - Estrazione campi form
- [x] `POST /documents/{form_id}/auto-fill` - Auto-compilazione con RAG
- [x] `GET /documents/{form_id}/download-filled` - Download documento compilato

---

## Fase 3: Backend - Services

### Nuovo Service: FormDocumentService
- [x] `upload_form_document()` - Upload e riconoscimento documento form
- [x] `extract_form_fields()` - Estrazione campi usando PyMuPDF/python-docx
- [x] `detect_form_type()` - Riconoscimento tipo documento (PDF/Word/Excel)
- [x] `save_form_metadata()` - Salvare metadati campi separatamente

### Enhanced RagRetrievalService
- [x] `generate_field_queries()` - Generare query semantiche per campi specifici
- [x] `search_for_field_values()` - Ricerca RAG per valori campo
- [x] `calculate_confidence_scores()` - Calcolo punteggi confidenza

### Form Field Writers
- [x] `PDFFormWriter` - Scrittura valori in PDF forms con PyMuPDF
- [x] `WordFormWriter` - Scrittura valori in Word forms con python-docx
- [x] `preserve_formatting()` - Mantenimento layout originale

---

## Fase 4: Frontend - Componenti

### Nuovo Componente: DocumentFormFilling
- [x] Modal per upload documenti form
- [x] Visualizzazione lista campi estratti
- [x] Display valori auto-compilati con punteggi confidenza
- [x] Pulsante download documento compilato
- [x] Gestione stati loading/error/success

### Enhanced Chat Interface
- [x] Aggiungere pulsante "Carica documento da compilare"
- [x] Integrazione con flusso chat esistente
- [ ] Supporto per comandi vocali "aiutami a compilare questo documento"
- [ ] Visualizzazione progresso auto-compilazione

### API Client Extensions
- [x] `uploadFormDocument()` - Upload documento form
- [x] `extractFormFields()` - Estrazione campi
- [x] `autoFillForm()` - Auto-compilazione con RAG
- [x] `downloadFilledForm()` - Download documento compilato

---

## Fase 5: Workflow Implementation

### Step 1: Upload e Riconoscimento
- [ ] Utente clicca "Carica documento da compilare"
- [ ] Frontend invia a `/documents/upload-form`
- [ ] Backend riconosce tipo documento (PDF/Word)
- [ ] Salva documento senza processing RAG

### Step 2: Estrazione Campi
- [ ] Backend usa PyMuPDF per PDF forms (analisi AcroForm)
- [ ] Backend usa python-docx per Word forms (analisi Content Controls)
- [ ] Estrai metadati: nome, tipo, posizione, contesto
- [ ] Restituisce lista campi al frontend

### Step 3: Auto-Compilazione
- [ ] Utente scrive "aiutami a compilare questo documento"
- [ ] Per ogni campo vuoto, generare query RAG specifica
- [ ] Eseguire ricerca RAG sui documenti conoscenza
- [ ] Compilare campi con valori trovati + punteggio confidenza
- [ ] Aggiornare UI con valori compilati

### Step 4: Download
- [ ] Backend usa PyMuPDF/python-docx per scrivere valori nei campi
- [ ] Generare documento compilato mantenendo formato
- [ ] Frontend fornisce download all'utente

---

## Fase 6: Testing e Quality

### Test Backend
- [ ] Test unitari per FormDocumentService
- [ ] Test integrazione API endpoints
- [ ] Test PyMuPDF/python-docx integration
- [ ] Test RAG query generation per form fields

### Test Frontend
- [ ] Test componenti DocumentFormFilling
- [ ] Test integrazione con chat esistente
- [ ] Test upload/download documenti
- [ ] Test responsive design

### End-to-End Testing
- [ ] Test completo flusso: upload → estrazione → auto-fill → download
- [ ] Test con diversi tipi di documenti (PDF, Word)
- [ ] Test con diversi scenari di dati RAG

---

## Fase 7: Deployment e Documentazione

### Deployment
- [ ] Aggiornare requirements.txt con nuove dependencies
- [ ] Verificare compatibilità con infrastruttura esistente
- [ ] Deploy in ambiente di sviluppo
- [ ] Deploy in produzione

### Documentazione
- [ ] Documentazione API nuovi endpoints
- [ ] Guida utente per feature form filling
- [ ] Esempi di utilizzo
- [ ] Troubleshooting guide

---

## File Structure

### Backend
```
backend/
├── app/
│   ├── api/
│   │   └── routes/
│   │       └── documents.py              # Modifica: aggiungere endpoints form
│   ├── schemas/
│   │   └── document.py                   # Modifica: aggiungere schemi form
│   ├── services/
│   │   ├── documents.py                  # Modifica: routing doppio percorso
│   │   ├── form_documents.py             # NUOVO: service form documents
│   │   └── rag.py                        # Modifica: enhance per form queries
│   └── utils/
│       └── form_writers.py               # NUOVO: PDF/Word form writers
```

### Frontend
```
frontend/
├── app/
│   └── dashboard/
│       └── search/
│           ├── page.tsx                  # Modifica: integrare form filling
│           └── components/
│               └── DocumentFormFilling.tsx  # NUOVO: componente form filling
├── lib/
│   ├── api-client.ts                     # Modifica: aggiungere endpoints form
│   └── types.ts                          # Modifica: aggiungere tipi form
```

---

## Timeline Stimata

- **Fase 1-2**: 2-3 giorni (Setup e API)
- **Fase 3**: 3-4 giorni (Services backend)
- **Fase 4**: 2-3 giorni (Componenti frontend)
- **Fase 5**: 2 giorni (Workflow integration)
- **Fase 6**: 2 giorni (Testing)
- **Fase 7**: 1 giorno (Deployment)

**Totale**: ~12-15 giorni di sviluppo

---

## Note Importanti

1. **Separazione Netta**: I documenti form NON devono mai entrare nel vector store RAG
2. **Format Preservation**: Mantenere sempre il formato originale per il download
3. **Error Handling**: Gestire casi edge (documenti senza form fields, form fields non riconosciuti)
4. **Performance**: Ottimizzare l'analisi di documenti grandi
5. **Security**: Validare input e sanitizzare output per prevenire injection