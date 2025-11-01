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

Lo script `scripts/check_infrastructure.sh` può essere rieseguito in qualsiasi momento per verificare che i servizi siano raggiungibili.
