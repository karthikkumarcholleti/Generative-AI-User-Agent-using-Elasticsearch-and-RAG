#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$ROOT_DIR/.env.local"

# Load environment variables if present
if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

log() {
  printf '\e[32m[%%s]\e[0m %%s\n' "$(date '+%H:%M:%S')" "$1"
}

start_elasticsearch() {
  if [[ -z "${ELASTICSEARCH_HOME:-}" ]]; then
    log "ELASTICSEARCH_HOME not set. Skipping ElasticSearch startup (assuming external instance)."
    return 0
  fi

  local es_bin="$ELASTICSEARCH_HOME/bin/elasticsearch"
  if [[ ! -x "$es_bin" ]]; then
    log "ElasticSearch binary not found at $es_bin"
    return 1
  fi

  local health_url="${ELASTICSEARCH_URL:-https://localhost:9200}"
  if curl -k -u "${ELASTICSEARCH_USERNAME:-elastic}:${ELASTICSEARCH_PASSWORD:-P@ssw0rd}" --silent --max-time 2 "$health_url" >/dev/null; then
    log "ElasticSearch already running at $health_url"
    return 0
  fi

  log "Starting ElasticSearch from $ELASTICSEARCH_HOME"
  "$es_bin" -d
  sleep 10

  if ! curl -k -u "${ELASTICSEARCH_USERNAME:-elastic}:${ELASTICSEARCH_PASSWORD:-P@ssw0rd}" --silent "$health_url" >/dev/null; then
    log "ElasticSearch did not respond at $health_url"
    return 1
  fi
  log "ElasticSearch is ready"
}

start_fastapi() {
  local backend_dir="$ROOT_DIR/llm_backend/backend"
  local venv_dir="$ROOT_DIR/llm_backend/venv"
  if [[ ! -d "$backend_dir" ]]; then
    log "FastAPI backend directory missing: $backend_dir"
    return 1
  fi

  if [[ -d "$venv_dir" && -f "$venv_dir/bin/activate" ]]; then
    # shellcheck disable=SC1091
    source "$venv_dir/bin/activate"
    log "Using Python virtual environment at $venv_dir"
  else
    log "Virtual environment not found at $venv_dir. Please create one before running (python -m venv llm_backend/venv && source llm_backend/venv/bin/activate && pip install -r backend/requirements.txt)."
    return 1
  fi

  pushd "$backend_dir" >/dev/null
  log "Starting FastAPI backend on ${FASTAPI_HOST:-0.0.0.0}:${FASTAPI_PORT:-8000}"
  python -m uvicorn app.main:app --reload --host "${FASTAPI_HOST:-0.0.0.0}" --port "${FASTAPI_PORT:-8000}" &
  FASTAPI_PID=$!
  popd >/dev/null
}

start_express() {
  local node_dir="$ROOT_DIR/dashboard/backend"
  pushd "$node_dir" >/dev/null
  if [[ ! -f package.json ]]; then
    log "package.json not found in $node_dir"
    return 1
  fi
  log "Starting Express API"
  node server.js &
  EXPRESS_PID=$!
  popd >/dev/null
}

start_next() {
  local frontend_dir="$ROOT_DIR/dashboard/backend/frontend"
  pushd "$frontend_dir" >/dev/null
  if [[ ! -f package.json ]]; then
    log "package.json not found in $frontend_dir"
    return 1
  fi
  log "Starting Next.js dev server"
  npm run dev &
  NEXT_PID=$!
  popd >/dev/null
}

cleanup() {
  log "Stopping services..."
  [[ -n "${NEXT_PID:-}" ]] && kill "$NEXT_PID" 2>/dev/null || true
  [[ -n "${EXPRESS_PID:-}" ]] && kill "$EXPRESS_PID" 2>/dev/null || true
  [[ -n "${FASTAPI_PID:-}" ]] && kill "$FASTAPI_PID" 2>/dev/null || true
  wait 2>/dev/null || true
  log "All services stopped"
}

trap cleanup EXIT INT TERM

start_elasticsearch
start_fastapi
start_express
start_next

deactivate 2>/dev/null || true

log "All services started. Press Ctrl+C to stop."
wait
