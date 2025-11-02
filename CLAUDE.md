# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a full-stack RAG (Retrieval-Augmented Generation) document management system with:
- **Backend**: FastAPI Python application using DataPizza AI framework
- **Frontend**: Next.js React application with TypeScript and Tailwind CSS
- **Database**: PostgreSQL for document metadata and chunk storage
- **Vector Store**: Qdrant for semantic search and embeddings
- **Embeddings**: Ollama with mxbai-embed-large model
- **Task Queue**: Celery with Redis for background document processing

## Development Commands

### Infrastructure Setup
```bash
# Start database, Qdrant, and Redis
./scripts/dev.sh

# Check infrastructure health
./scripts/check_infrastructure.sh

# Setup Ollama embeddings
./scripts/setup_ollama.sh
```

### Backend Development
```bash
cd backend

# Setup virtual environment
python -m venv .venv
source .venv/bin/activate
pip install -e .

# Database migrations
alembic -c alembic.ini upgrade head

# Run development server
uvicorn app.main:app --reload

# Run Celery worker
celery -A app.core.celery_app worker --loglevel=info

# Code quality
ruff check .
ruff format .
```

### Frontend Development
```bash
cd frontend

# Install dependencies
npm install

# Development server
npm run dev

# Build
npm run build

# Lint
npm run lint
```

## Architecture

### Backend Structure
- `app/main.py` - FastAPI application factory
- `app/core/config.py` - Settings management with Pydantic
- `app/models/` - SQLAlchemy models for documents and chunks
- `app/services/` - Business logic layer
- `app/api/routes/` - HTTP endpoints
- `app/rag/` - RAG pipeline components using DataPizza
- `app/tasks/` - Celery background tasks

### RAG Pipeline Components
- **Ingestion Pipeline** (`app/rag/pipelines.py`): Docling/Text Parser → NodeSplitter → OllamaChunkEmbedder
- **Retrieval Pipeline**: ToolRewriter → OllamaQueryEmbedder → VectorSearch → ChatPromptTemplate → OpenAI Generator
- **Vector Store**: Qdrant with dense embeddings (1024 dimensions, cosine distance)
- **Embedding Model**: Ollama with mxbai-embed-large

### Document Processing Flow
1. Upload via `/api/documents/upload` → stored in PostgreSQL
2. Background task processes document → creates chunks with embeddings
3. Chunks stored in Qdrant vector store with metadata linking to PostgreSQL
4. Search queries use semantic search in Qdrant → retrieve relevant chunks → generate responses

### Key Configuration
- **Embedding Dimensions**: 1024 (configured in `RAG_EMBED_DIMENSIONS`)
- **Chunk Size**: 1000 characters with 100 overlap
- **Vector Name**: "default" (configured in `RAG_EMBED_NAME`)
- **Collection Name**: "rag_documents" (configured in `QDRANT_COLLECTION_NAME`)

## Important Notes

### Vector Store Configuration
The Qdrant collection is configured for **dense embeddings only** using `EmbeddingFormat.DENSE`. The error "Conversion between sparse and regular vectors failed" indicates a mismatch between the configured vector format and the embedding type being used.

### DataPizza Integration
The project uses DataPizza 0.0.7 with custom components for Ollama integration. Key custom components:
- `OllamaChunkEmbedder` - Batch embedding of document chunks
- `OllamaQueryEmbedder` - Embedding of user queries
- `_VectorSearchModule` - Wrapper to ensure proper vector configuration

### File Processing
Supported file types: PDF, DOC, DOCX, XLS, XLSX, TXT
- Text files processed directly
- Spreadsheets converted to text format before processing
- Documents processed using Docling parser

### Environment Variables
Required services: PostgreSQL, Qdrant, Redis, Ollama
Key environment variables in `.env`:
- Database: `POSTGRES_*`
- Vector store: `QDRANT_*`
- Embeddings: `OLLAMA_*`
- OpenAI: `OPENAI_API_KEY` for generation

## Common Development Tasks

### Adding New Document Types
1. Add extension to `SUPPORTED_EXTENSIONS` in `DocumentProcessingService`
2. Implement parser in `_prepare_document_file` method
3. Add dependencies to `pyproject.toml`

### Modifying RAG Pipeline
1. Update pipeline components in `app/rag/pipelines.py`
2. Modify embedding configuration in `app/rag/vectorstore.py`
3. Update vector search parameters in `_VectorSearchModule`

### Debugging Vector Search Issues
- Check Qdrant collection configuration matches embedding dimensions
- Verify Ollama model returns correct vector dimensions
- Ensure `vector_name` parameter is consistently used in search requests