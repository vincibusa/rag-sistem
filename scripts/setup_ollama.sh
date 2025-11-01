#!/usr/bin/env bash

# Script to pull the required Ollama model for embeddings
# Assumes Ollama is running locally on localhost:11434

set -euo pipefail

if [[ ! -f ".env" ]]; then
  echo "Missing .env file. Copy .env.example to .env and adjust values." >&2
  exit 1
fi

set -a
source .env
set +a

MODEL_NAME=${OLLAMA_EMBED_MODEL:-mxbai-embed-large}
OLLAMA_PORT=${OLLAMA_PORT:-11434}

wait_for_ollama() {
  local attempt=0
  local max_attempts=30

  echo "Waiting for Ollama to be ready at localhost:${OLLAMA_PORT}..."
  until curl -fsS "http://localhost:${OLLAMA_PORT}/api/tags" >/dev/null 2>&1; do
    attempt=$((attempt + 1))
    if (( attempt >= max_attempts )); then
      echo "Ollama did not become ready in time." >&2
      echo "Make sure Ollama is installed and running: brew install ollama && ollama serve" >&2
      return 1
    fi
    sleep 3
  done
  echo "Ollama ready."
}

pull_model() {
  local model_name=$1
  echo "Pulling Ollama model: ${model_name}..."
  
  if ollama pull "${model_name}"; then
    echo "Successfully pulled model: ${model_name}"
    return 0
  else
    echo "Failed to pull model: ${model_name}" >&2
    return 1
  fi
}

check_model_exists() {
  local model_name=$1
  echo "Checking if model ${model_name} is already available..."
  
  if ollama list | grep -q "^${model_name}"; then
    echo "Model ${model_name} is already installed."
    return 0
  else
    echo "Model ${model_name} not found. Will pull it."
    return 1
  fi
}

main() {
  echo "Setting up Ollama for RAG embeddings..."
  
  wait_for_ollama
  
  if ! check_model_exists "${MODEL_NAME}"; then
    pull_model "${MODEL_NAME}"
  fi
  
  echo ""
  echo "Setup complete! Model ${MODEL_NAME} is ready for use."
  echo ""
  echo "You can verify the installation by running:"
  echo "  ollama list"
}

main "$@"

