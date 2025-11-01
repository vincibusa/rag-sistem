# Medit RAG Fullstack

Stack fullstack per la gestione documentale con RAG.

## Avvio Infrastruttura Locale

1. Copia il file di configurazione di esempio.
   ```bash
   cp .env.example .env
   ```
2. Assicurati di avere `docker` e `docker compose` installati.
3. Avvia i servizi di base (PostgreSQL, Qdrant, Redis) ed esegui i check di salute.
   ```bash
   ./scripts/dev.sh
   ```

4. **Installa e configura Ollama per gli embeddings:**
   ```bash
   # Installazione Ollama (macOS con Homebrew)
   brew install ollama
   
   # Avvia il server Ollama in background
   ollama serve
   
   # Pull del modello per embeddings
   ./scripts/setup_ollama.sh
   ```

Lo script `scripts/check_infrastructure.sh` può essere rieseguito in qualsiasi momento per verificare che i servizi siano raggiungibili.

### Troubleshooting Docker

Se incontri errori di I/O con Docker (es: `input/output error` su containerd):

1. **Riavvia Docker Desktop:**
   ```bash
   killall Docker && open -a Docker
   ```

2. **Se il problema persiste, resetta Docker completamente:**
   - Apri Docker Desktop
   - Vai su "Troubleshoot" → "Clean / Purge data"
   - Riavvia Docker Desktop

3. **Verifica che Docker funzioni:**
   ```bash
   docker info
   ```

## Backend FastAPI

### Setup ambiente sviluppo

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

> Puoi impostare la variabile `API_KEY` nel file `.env` per richiedere un header `X-API-Key` su tutti gli endpoint protetti.

### Migrazioni database

```bash
alembic -c alembic.ini upgrade head
```

### Avvio server

```bash
uvicorn app.main:app --reload
```

### Endpoints disponibili

- `GET /api/health` – verifica stato applicazione.
- `POST /api/documents/upload` – upload multiplo con validazione formati.
- `GET /api/documents/list` – metadati documenti con paginazione.
- `GET /api/documents/{id}/download` – scarica il file originale.
