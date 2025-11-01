#!/usr/bin/env bash

# Basic readiness checks for the Docker infrastructure services.

set -euo pipefail

COMPOSE_CMD=${COMPOSE_CMD:-"docker compose"}

if [[ ! -f ".env" ]]; then
  echo "Missing .env file. Copy .env.example to .env and adjust values." >&2
  exit 1
fi

if ! command -v curl >/dev/null 2>&1; then
  echo "curl command not available. Install curl to run Qdrant health checks." >&2
  exit 1
fi

set -a
source .env
set +a

wait_for_postgres() {
  local attempt=0
  local max_attempts=15

  echo "Waiting for PostgreSQL..."
  until $COMPOSE_CMD exec -T postgres pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1; do
    attempt=$((attempt + 1))
    if (( attempt >= max_attempts )); then
      echo "PostgreSQL did not become ready in time." >&2
      return 1
    fi
    sleep 2
  done
  echo "PostgreSQL ready."
}

wait_for_redis() {
  local attempt=0
  local max_attempts=15

  echo "Waiting for Redis..."
  until $COMPOSE_CMD exec -T redis redis-cli ping >/dev/null 2>&1; do
    attempt=$((attempt + 1))
    if (( attempt >= max_attempts )); then
      echo "Redis did not become ready in time." >&2
      return 1
    fi
    sleep 2
  done
  echo "Redis ready."
}

wait_for_qdrant() {
  local attempt=0
  local max_attempts=15
  local health_url="http://${QDRANT_HOST_EXTERNAL:-localhost}:${QDRANT_HTTP_PORT:-6333}/healthz"

  echo "Waiting for Qdrant..."
  until curl -fsS "$health_url" >/dev/null 2>&1; do
    attempt=$((attempt + 1))
    if (( attempt >= max_attempts )); then
      echo "Qdrant did not become ready in time." >&2
      return 1
    fi
    sleep 2
  done
  echo "Qdrant ready."
}

wait_for_postgres
wait_for_redis
wait_for_qdrant

echo "All Docker services are reachable."
echo ""
echo "Note: Ollama should be running locally on localhost:11434"
echo "Run: ollama serve (or ensure it's running in the background)"
