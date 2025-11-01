#!/usr/bin/env bash

# Quick bootstrap script to start the local stack defined in docker-compose.yml.

set -euo pipefail

COMPOSE_CMD=${COMPOSE_CMD:-"docker compose"}

if [[ ! -f ".env" ]]; then
  echo "Missing .env file. Copy .env.example to .env and adjust values." >&2
  exit 1
fi

echo "Starting infrastructure services (PostgreSQL, Qdrant, Redis)..."
$COMPOSE_CMD --env-file .env up -d postgres qdrant redis

echo "Running health checks..."
"$(dirname "$0")/check_infrastructure.sh"

echo "Infrastructure up and healthy."
