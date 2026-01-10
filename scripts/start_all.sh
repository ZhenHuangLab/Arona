#!/usr/bin/env bash
# Start both Backend and Frontend (one command)
#
# Usage:
#   bash scripts/start_all.sh              # dev (default): backend --reload + vite dev server
#   bash scripts/start_all.sh dev          # same as default
#   bash scripts/start_all.sh prod         # production-like: backend + vite preview (build first)
#   bash scripts/start_all.sh dev --check  # forward args to backend

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

MODE="dev"
if [[ "${1:-}" == "dev" ]]; then
  MODE="dev"
  shift
elif [[ "${1:-}" == "prod" || "${1:-}" == "production" ]]; then
  MODE="prod"
  shift
fi

BACKEND_PID=""
FRONTEND_PID=""
USE_SETSID="false"
if command -v setsid >/dev/null 2>&1; then
  USE_SETSID="true"
fi

cleanup() {
  local code=$?

  # Best effort cleanup; do not fail on teardown.
  set +e
  trap - EXIT

  if [[ -n "${FRONTEND_PID}" ]] && kill -0 "${FRONTEND_PID}" 2>/dev/null; then
    if [[ "${USE_SETSID}" == "true" ]]; then
      # Negative PID targets the process group (created via `setsid`).
      kill -TERM -- "-${FRONTEND_PID}" 2>/dev/null || true
    else
      kill -TERM "${FRONTEND_PID}" 2>/dev/null || true
    fi
  fi

  if [[ -n "${BACKEND_PID}" ]] && kill -0 "${BACKEND_PID}" 2>/dev/null; then
    if [[ "${USE_SETSID}" == "true" ]]; then
      # Negative PID targets the process group (created via `setsid`).
      kill -TERM -- "-${BACKEND_PID}" 2>/dev/null || true
    else
      kill -TERM "${BACKEND_PID}" 2>/dev/null || true
    fi
  fi

  wait >/dev/null 2>&1 || true
  exit "${code}"
}

on_int() {
  echo ""
  echo "Interrupted (SIGINT)"
  exit 130
}

on_term() {
  echo ""
  echo "Terminated (SIGTERM)"
  exit 143
}

trap cleanup EXIT
trap on_int INT
trap on_term TERM

echo "Starting Arona (backend + frontend) [mode=${MODE}]"
echo ""

# Load environment from repo root (optional)
# Prefer `.env` (unified) and fall back to legacy `.env.backend`.
ENV_FILE=""
if [[ -f ".env" ]]; then
  ENV_FILE=".env"
elif [[ -f ".env.backend" ]]; then
  ENV_FILE=".env.backend"
fi

if [[ -n "${ENV_FILE}" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +a
  echo "✓ Loaded env from ${ENV_FILE}"
  echo ""
else
  echo "⚠ No .env or .env.backend found; using defaults/environment"
  echo "  Tip: cp env.example .env"
  echo ""
fi

# Reasonable defaults (can be overridden via env file)
API_PORT="${API_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
BACKEND_URL="${BACKEND_URL:-http://localhost:${API_PORT}}"
export BACKEND_URL

# Start backend in background
echo "Starting backend..."
BACKEND_ARGS=()
if [[ "${MODE}" == "dev" ]]; then
  BACKEND_ARGS+=(--reload)
fi
BACKEND_ARGS+=("$@")
if [[ "${USE_SETSID}" == "true" ]]; then
  setsid bash scripts/start_backend.sh "${BACKEND_ARGS[@]}" &
else
  bash scripts/start_backend.sh "${BACKEND_ARGS[@]}" &
fi
BACKEND_PID=$!

# This script only needs the backend HTTP server to be reachable before starting the frontend.
# RAG initialization can be lazy (and `/ready` may stay false until first query/index), so we
# prefer a quick `/health` check for startup orchestration.
BACKEND_HEALTH_URL="http://127.0.0.1:${API_PORT}/health"
BACKEND_WAIT_TIMEOUT_S="${BACKEND_READY_TIMEOUT_S:-${BACKEND_HEALTH_TIMEOUT_S:-30}}"
echo ""
echo "Waiting for backend HTTP (${BACKEND_HEALTH_URL})..."

backend_up=false
if ! command -v curl >/dev/null 2>&1; then
  echo "⚠ curl not found; skipping backend HTTP check"
  backend_up=true
else
  for ((i = 1; i <= BACKEND_WAIT_TIMEOUT_S; i++)); do
    if ! kill -0 "${BACKEND_PID}" 2>/dev/null; then
      echo "❌ Backend process exited while starting"
      wait "${BACKEND_PID}" || true
      exit 1
    fi

    # Bypass proxies for localhost checks. Many dev environments export http(s)_proxy without NO_PROXY,
    # which breaks curl -> 127.0.0.1 and makes startup appear stuck.
    if curl -fsS --noproxy '*' --connect-timeout 1 --max-time 2 "${BACKEND_HEALTH_URL}" >/dev/null 2>&1; then
      backend_up=true
      break
    fi

    sleep 1
  done
fi

if [[ "${backend_up}" != "true" ]]; then
  echo "⚠ Backend not reachable after ${BACKEND_WAIT_TIMEOUT_S}s; continuing anyway"
else
  echo "✓ Backend HTTP is up"
fi

echo ""
echo "Starting frontend..."
if [[ "${MODE}" == "dev" ]]; then
  export FRONTEND_MODE="${FRONTEND_MODE:-dev}"
else
  export FRONTEND_MODE="${FRONTEND_MODE:-production}"
fi

if [[ "${USE_SETSID}" == "true" ]]; then
  setsid bash scripts/start_frontend.sh &
else
  bash scripts/start_frontend.sh &
fi
FRONTEND_PID=$!

echo ""
echo "URLs:"
echo "  Frontend: http://localhost:${FRONTEND_PORT}"
echo "  Backend:  http://localhost:${API_PORT}"
echo "  API Docs: http://localhost:${API_PORT}/docs"
echo ""
echo "Press Ctrl-C to stop."
echo ""

# Exit if either process exits (cleanup will terminate the other one).
wait -n "${BACKEND_PID}" "${FRONTEND_PID}"
