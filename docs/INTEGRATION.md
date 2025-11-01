# Documentazione Integrazione Frontend-Backend

## Panoramica

Questo documento descrive l'integrazione completa tra il frontend Next.js e il backend FastAPI.

## Architettura API Client

### Configurazione

Il client API è centralizzato in `frontend/lib/api-client.ts` e utilizza **Axios** per tutte le chiamate HTTP.

**Vantaggi di Axios:**
- Interceptors per gestione errori centralizzata
- Supporto nativo per upload progress
- Timeout configurabili
- Cancellazione richieste
- Trasformazione automatica dati JSON

### File di Configurazione

```typescript
// frontend/lib/api-config.ts
- API_CONFIG: Configurazione base URL e timeout
- API_ENDPOINTS: Mapping degli endpoint
```

```typescript
// frontend/lib/types.ts
- Tipi TypeScript corrispondenti agli schemi Pydantic del backend
```

## Endpoint Implementati

### Documenti

#### Upload Documenti
```typescript
uploadDocuments(files: File[], onUploadProgress?: (event) => void)
```
- Supporta upload multipli
- Progress tracking in tempo reale
- Gestione errori automatica

#### Lista Documenti
```typescript
listDocuments(limit?: number, offset?: number)
```
- Paginazione integrata
- Filtri client-side (tipo, stato)
- Refresh automatico

#### Download Documento
```typescript
downloadDocument(id: string): Promise<Blob>
```
- Download diretto del file binario
- Gestione blob automatica

### Ricerca RAG

#### Ricerca Completa (RAG)
```typescript
ragSearch(request: RagSearchRequest)
```
- Pipeline completa: query rewriting + retrieval + generation
- Ritorna answer e chunks con score

#### Ricerca Semantica
```typescript
semanticSearch(request: RagSearchRequest)
```
- Solo retrieval, senza generazione risposta
- Utile per preview dei risultati

## Gestione Errori

### ApiClientError

Classe custom per errori API:
```typescript
class ApiClientError extends Error {
  status: number
  detail: string
  originalError?: unknown
}
```

### Interceptors

**Request Interceptor:**
- Possibilità di aggiungere token auth
- Logging richieste

**Response Interceptor:**
- Gestione centralizzata errori HTTP
- Mapping errori backend a ApiClientError
- Gestione errori di rete

## Integrazione nelle Pagine

### Upload Page (`/dashboard/upload`)

**Features:**
- Drag & drop support
- Upload multipli
- Progress tracking per file
- Validazione client-side
- Feedback visivo stati

**Flusso:**
1. Validazione file (tipo, dimensione)
2. Upload con progress tracking
3. Aggiornamento stato in tempo reale
4. Notifica successo/errore

### Search Page (`/dashboard/search`)

**Features:**
- Chat interface
- Streaming simulato risposte
- Visualizzazione chunks con score
- Storia conversazione
- Copy/delete/regenerate messaggi

**Flusso:**
1. Invio query
2. Chiamata API RAG
3. Formattazione risposta con chunks
4. Streaming simulato per UX
5. Visualizzazione markdown

### Documents Page (`/dashboard/documents`)

**Features:**
- Lista documenti con paginazione
- Filtri (tipo, stato)
- Ricerca testuale
- Download diretto
- Refresh manuale
- Stati documenti visibili

**Flusso:**
1. Caricamento lista iniziale
2. Applicazione filtri client-side
3. Paginazione
4. Download on-demand

## Configurazione Ambiente

### Variabili d'Ambiente

Crea `frontend/.env.local`:

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

### Development

1. Backend deve essere in esecuzione su `http://localhost:8000`
2. Frontend su `http://localhost:3000`
3. CORS configurato nel backend per permettere richieste dal frontend

## Best Practices

### Error Handling

Sempre gestire errori con try-catch:
```typescript
try {
  const response = await uploadDocuments(files)
  toast.success('Upload completato')
} catch (error) {
  if (error instanceof ApiClientError) {
    toast.error(error.detail)
  } else {
    toast.error('Errore sconosciuto')
  }
}
```

### Loading States

Gestire stati di caricamento:
```typescript
const [isLoading, setIsLoading] = useState(false)

try {
  setIsLoading(true)
  const response = await ragSearch({ query })
  // ...
} finally {
  setIsLoading(false)
}
```

### Progress Tracking

Per upload lunghi:
```typescript
const response = await uploadDocuments(
  files,
  (progressEvent) => {
    const progress = Math.round(
      (progressEvent.loaded * 100) / progressEvent.total
    )
    setProgress(progress)
  }
)
```

## Testing

### Test Manuali

1. **Upload:**
   - Testa tutti i formati supportati (PDF, DOC, DOCX, XLS, XLSX, TXT)
   - Verifica progress tracking
   - Testa file grandi (>10MB)
   - Verifica errori (file troppo grandi, formato non supportato)

2. **Ricerca:**
   - Testa query semplici
   - Testa query complesse
   - Verifica visualizzazione chunks
   - Testa errori (nessun documento caricato)

3. **Lista Documenti:**
   - Verifica paginazione
   - Testa filtri
   - Verifica download
   - Testa refresh

## Troubleshooting

### Errore CORS

Se vedi errori CORS, verifica:
- `BACKEND_CORS_ORIGINS` nel backend include `http://localhost:3000`
- Backend è in esecuzione

### Errori 404

Verifica:
- URL API corretto in `.env.local`
- Backend è accessibile su quella porta
- Endpoint path corretti

### Upload non funziona

Verifica:
- File size entro limiti backend (default 25MB)
- Content-Type corretto
- Backend ha spazio disco sufficiente

## Prossimi Passi

- [ ] Implementare streaming reale per risposte RAG
- [ ] Aggiungere caching per lista documenti
- [ ] Implementare retry automatico per errori di rete
- [ ] Aggiungere unit tests per API client
- [ ] Implementare WebSocket per notifiche real-time
