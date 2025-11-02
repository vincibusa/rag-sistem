# Guida all'Hosting Cloud del Backend RAG

Questa guida descrive diverse opzioni per hostare il backend con tutti i servizi necessari.

## Architettura del Sistema

Il sistema richiede i seguenti servizi:
- **PostgreSQL**: Database relazionale per metadata dei documenti
- **Qdrant**: Database vettoriale per embeddings (1024 dimensioni)
- **Redis**: Message broker per Celery
- **Ollama** (opzionale): Per embeddings locali (può usare OpenAI invece)
- **Backend FastAPI**: Applicazione principale
- **Frontend Next.js**: Interfaccia utente

---

## Opzione 1: Platform as a Service (PaaS) - Raccomandata per Inizio 🚀

### Vercel (Frontend) + Railway/Render (Backend + Servizi)

**Pro:**
- Setup rapido, zero configurazione infrastruttura
- Deploy automatico da Git
- Scalabilità automatica
- Ottimo per MVP e piccole-medie applicazioni

**Contro:**
- Costi possono crescere con l'uso
- Meno controllo sulla configurazione

#### Configurazione

**1. Frontend su Vercel:**
```bash
# Nel frontend
npm install -g vercel
vercel login
vercel --prod
```

**2. Backend + Servizi su Railway:**

Railway offre tutti i servizi necessari:
- **PostgreSQL** (managed database)
- **Redis** (managed cache)
- **Qdrant** (deploy tramite Dockerfile)
- **Backend FastAPI** (deploy da Git)

**Setup Railway:**

1. **Installa Railway CLI:**
```bash
npm install -g @railway/cli
railway login
```

2. **Crea progetto:**
```bash
cd backend
railway init
```

3. **Aggiungi servizi:**
```bash
# PostgreSQL
railway add postgresql

# Redis  
railway add redis

# Qdrant (deploy da Docker Hub direttamente)
railway add
# Configura Qdrant manualmente dalla dashboard Railway
```

4. **Deploy backend:**
```bash
railway up
```

**3. Backend + Servizi su Render:**

Render è simile a Railway:
- PostgreSQL managed database
- Redis managed instance
- Web service per backend FastAPI
- Docker service per Qdrant

**Costi stimati:**
- Railway: ~$20-50/mese per setup completo
- Render: ~$25-60/mese per setup completo
- Vercel: Gratis per frontend (piano hobby)

---

## Opzione 2: Cloud Providers (Più Flessibile) 💪

### AWS (Amazon Web Services)

**Servizi necessari:**
- **RDS PostgreSQL**: Database managed
- **ElastiCache Redis**: Redis managed
- **EC2**: Per Qdrant e backend (o ECS/Fargate)
- **Lambda + API Gateway**: Alternative per backend serverless

**Setup minimo:**

1. **RDS PostgreSQL:**
```bash
# Usa AWS Console o Terraform
aws rds create-db-instance \
  --db-instance-identifier rag-postgres \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --allocated-storage 20
```

2. **ElastiCache Redis:**
```bash
aws elasticache create-cache-cluster \
  --cache-cluster-id rag-redis \
  --cache-node-type cache.t3.micro \
  --engine redis
```

3. **EC2 per Qdrant:**
```bash
# Usa AMI Ubuntu e installa Docker
sudo docker run -d -p 6333:6333 -p 6334:6334 qdrant/qdrant:v1.11.4
```

4. **Elastic Beanstalk o ECS per Backend:**
   - Usa il tuo `docker-compose.yml` come riferimento
   - Per ECS, crea task definition che usa immagine Python
   - Build e deploy backend come container separato

**Costi stimati:** ~$50-150/mese (dipende da traffico)

### Google Cloud Platform (GCP)

**Servizi:**
- **Cloud SQL (PostgreSQL)**: Database managed
- **Memorystore (Redis)**: Redis managed
- **Cloud Run**: Per backend (serverless)
- **Compute Engine**: Per Qdrant

**Setup:**

1. **Cloud SQL:**
```bash
gcloud sql instances create rag-postgres \
  --database-version=POSTGRES_16 \
  --tier=db-f1-micro \
  --region=europe-west1
```

2. **Memorystore Redis:**
```bash
gcloud redis instances create rag-redis \
  --size=1 \
  --region=europe-west1
```

3. **Cloud Run per Backend:**
```bash
gcloud run deploy rag-backend \
  --source backend \
  --region=europe-west1 \
  --allow-unauthenticated
```

**Costi stimati:** ~$40-120/mese

### DigitalOcean

**Servizi:**
- **Managed PostgreSQL**
- **Managed Redis**
- **Droplet** per Qdrant e backend
- **App Platform** (alternativa PaaS)

**Setup:**

1. **Crea Droplet:**
```bash
# Usa DigitalOcean Console
# Ubuntu 22.04 LTS
# 2GB RAM minimo per Qdrant
```

2. **Installa Docker nel Droplet:**
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo docker run -d -p 6333:6333 -p 6334:6334 qdrant/qdrant:v1.11.4
```

3. **Deploy Backend:**
```bash
# Usa App Platform o deploy manuale
doctl apps create --spec app.yaml
```

**Costi stimati:** ~$30-80/mese

---

## Opzione 3: Soluzione All-in-One (Raccomandata per Produzione) 🎯

### Render.com - Setup Completo

**Vantaggi:**
- Tutto in un posto
- Deploy automatico da Git
- Free tier disponibile
- SSL incluso

**Configurazione:**

1. **Crea servizi da Render Dashboard:**
   - **PostgreSQL Database**: Crea da dashboard, piano starter ($7/mese)
   - **Redis**: Crea da dashboard, piano starter ($7/mese)
   - **Qdrant**: Crea Web Service usando immagine Docker `qdrant/qdrant:v1.11.4`
   - **Backend FastAPI**: Crea Web Service Python, build da `backend/`

2. **Configura Backend Service su Render:**
   - **Build Command**: `pip install --upgrade pip && pip install -e .`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Working Directory**: `backend/`

3. **Configura variabili d'ambiente su Render:**
   - `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` (dalle informazioni del database PostgreSQL)
   - `REDIS_HOST`, `REDIS_PORT` (dalle informazioni Redis)
   - `QDRANT_HOST`, `QDRANT_HTTP_PORT` (dalle informazioni Qdrant)
   - `OPENAI_API_KEY` (tua chiave OpenAI)
   - `ENVIRONMENT=production`
   - `BACKEND_CORS_ORIGINS` (URL del tuo frontend)

4. **Crea `.renderignore` (opzionale):**
```
.venv/
__pycache__/
*.pyc
.env
.git/
```

**Costi:** ~$21/mese (starter plans) per tutti i servizi

---

## Opzione 4: Self-Hosted con Docker Compose

### Deploy su VPS (Hetzner, OVH, DigitalOcean Droplet)

**Vantaggi:**
- Controllo completo
- Costi ridotti
- Buono per MVP

**Setup:**

1. **Crea VPS** (4GB RAM minimo, 2 CPU cores)

2. **Installa Docker e Docker Compose:**
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

3. **Usa il tuo `docker-compose.yml` esistente:**
   Il tuo `docker-compose.yml` già contiene postgres, qdrant e redis.
   
   **Per produzione, puoi:**
   - Usare `docker-compose.production.yml` che estende il tuo docker-compose con backend e celery
   - Oppure deployare backend separatamente (su PaaS) e usare i servizi dal docker-compose

4. **Deploy Backend su VPS:**
   Se vuoi deployare anche il backend sullo stesso VPS:
   ```bash
   # Opzione 1: Deploy come servizio Python
   cd backend
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -e .
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   
   # Opzione 2: Usa systemd per servizio permanente
   sudo nano /etc/systemd/system/rag-backend.service
   ```

5. **Setup Nginx come reverse proxy:**
```nginx
# /etc/nginx/sites-available/rag-backend
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

**Costi:** ~$5-10/mese (VPS)

---

## Raccomandazioni per Ambiente di Produzione

### Checklist Pre-Deploy

1. **Variabili d'Ambiente:**
   - [ ] Configurare `POSTGRES_*` per database cloud
   - [ ] Configurare `REDIS_*` per Redis cloud
   - [ ] Configurare `QDRANT_*` per Qdrant cloud
   - [ ] Aggiungere `OPENAI_API_KEY`
   - [ ] Configurare `CORS_ORIGINS` per frontend
   - [ ] Configurare `API_KEY` per autenticazione

2. **Sicurezza:**
   - [ ] Usare HTTPS (SSL/TLS)
   - [ ] Configurare firewall
   - [ ] Usare password forti per database
   - [ ] Abilitare autenticazione API
   - [ ] Configurare rate limiting

3. **Monitoring:**
   - [ ] Setup logging centralizzato
   - [ ] Monitoring errori (Sentry)
   - [ ] Health checks
   - [ ] Alerting

4. **Backup:**
   - [ ] Backup automatico PostgreSQL
   - [ ] Backup Qdrant collections
   - [ ] Disaster recovery plan

### Setup Ollama (Opzionale)

Se vuoi usare Ollama invece di OpenAI per embeddings:

1. **Deploy Ollama:**
```bash
# Su VPS o cloud instance
docker run -d -p 11434:11434 --name ollama ollama/ollama
docker exec -it ollama ollama pull mxbai-embed-large
```

2. **Configura variabili:**
```bash
OLLAMA_HOST=your-ollama-host
OLLAMA_PORT=11434
OLLAMA_EMBED_MODEL=mxbai-embed-large
```

---

## Comparazione Rapida

| Soluzione | Costo/mese | Complessità | Scalabilità | Raccomandato per |
|-----------|------------|-------------|-------------|------------------|
| **Render/Railway** | $20-50 | Bassa | Media | MVP, Startup |
| **AWS/GCP** | $50-150 | Alta | Alta | Enterprise |
| **DigitalOcean** | $30-80 | Media | Media | SMB |
| **VPS Self-hosted** | $5-10 | Media | Bassa | Progetti personali |

---

## Quick Start - Render.com (Raccomandato)

Per iniziare rapidamente:

1. **Vai su [render.com](https://render.com)**
2. **Crea account e connetti repository GitHub**
3. **Crea servizi dalla dashboard:**
   - **PostgreSQL Database** (starter plan, ~$7/mese)
     - Nome: `rag-postgres`
     - Copia hostname, porta, user, password, database name
   - **Redis** (starter plan, ~$7/mese)
     - Nome: `rag-redis`
     - Copia hostname e porta
   - **Web Service per Qdrant** (starter plan, ~$7/mese)
     - Nome: `rag-qdrant`
     - Docker Image: `qdrant/qdrant:v1.11.4`
     - Port: `6333`
   - **Web Service per Backend** (starter plan, ~$7/mese)
     - Nome: `rag-backend`
     - Environment: `Python 3`
     - Root Directory: `backend`
     - Build Command: `pip install --upgrade pip && pip install -e .`
     - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. **Configura variabili d'ambiente per Backend:**
   - Database: Usa i valori del servizio PostgreSQL creato
   - Redis: Usa i valori del servizio Redis creato
   - Qdrant: Usa l'URL del servizio Qdrant creato
   - OpenAI: Aggiungi `OPENAI_API_KEY`
   - CORS: Aggiungi `BACKEND_CORS_ORIGINS` con URL frontend
5. **Deploy!**

**Nota:** Render creerà automaticamente URL interni per comunicazione tra servizi.

**Link utili:**
- [Render Docs](https://render.com/docs)
- [Railway Docs](https://docs.railway.app)
- [Vercel Docs](https://vercel.com/docs)

---

## Note Finali

- **Per sviluppo**: Usa il tuo `docker-compose.yml` esistente localmente
- **Per produzione**: Usa managed services (Render/Railway) per semplicità
- **Per enterprise**: Considera AWS/GCP con configurazione dedicata
- **Per budget limitato**: VPS self-hosted con `docker-compose.production.yml` o servizi separati

### File esistenti nel progetto:
- `docker-compose.yml` - Per sviluppo locale (postgres, qdrant, redis)
- `docker-compose.production.yml` - Per produzione (include anche backend e celery)

### Setup consigliato:
1. **Sviluppo**: Usa `docker-compose up` con il tuo file esistente
2. **Produzione PaaS**: **Render.com** o **Railway** - setup più semplice, deploy automatico
3. **Produzione Self-hosted**: VPS con `docker-compose.production.yml` - più controllo, costi ridotti

