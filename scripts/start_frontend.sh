#!/usr/bin/env bash
# Start Arona React Frontend

set -euo pipefail

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

# Load environment (optional)
# Prefer `.env` (unified) and fall back to legacy `.env.backend`.
ENV_FILE=""
if [[ -f "$PROJECT_ROOT/.env" ]]; then
    ENV_FILE="$PROJECT_ROOT/.env"
elif [[ -f "$PROJECT_ROOT/.env.backend" ]]; then
    ENV_FILE="$PROJECT_ROOT/.env.backend"
fi

if [[ -n "$ENV_FILE" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    set +a
fi

# Change to frontend directory
cd "$FRONTEND_DIR"

echo "Arona React Frontend"
echo "============================"
echo ""

# Default values
HOST=${FRONTEND_HOST:-0.0.0.0}
PORT=${FRONTEND_PORT:-5173}
FRONTEND_MODE=${FRONTEND_MODE:-production}

# Backend URL (mainly used for production build/preview).
# In dev mode we prefer Vite proxy (see `frontend/vite.config.ts`), so a backend URL is optional.
DEFAULT_BACKEND_URL="http://localhost:${API_PORT:-8000}"
BACKEND_URL=${BACKEND_URL:-$DEFAULT_BACKEND_URL}

echo "Configuration:"
echo "  Mode: $FRONTEND_MODE"
echo "  Host: $HOST"
echo "  Port: $PORT"
echo "  Backend URL: $BACKEND_URL"
echo ""

# Export backend URL for Vite only when needed.
# - dev: prefer proxy unless user explicitly sets VITE_BACKEND_URL
# - production/preview: ensure VITE_BACKEND_URL is set so built assets can call the backend
if [[ "$FRONTEND_MODE" != "dev" ]]; then
    export VITE_BACKEND_URL="${VITE_BACKEND_URL:-$BACKEND_URL}"
fi

# Check if node_modules exists, install dependencies if not
if [ ! -d "node_modules" ]; then
    echo "📦 Installing npm dependencies..."
    npm install
    echo ""
fi

# Start frontend based on mode
if [ "$FRONTEND_MODE" = "dev" ]; then
    echo "🚀 Starting React frontend in DEVELOPMENT mode..."
    echo "   Hot reload enabled"
    echo "   Frontend will be available at: http://$HOST:$PORT"
    echo "   API requests: Vite proxy (/api -> $BACKEND_URL)"
    echo ""
    npm run dev -- --host "$HOST" --port "$PORT"
else
    echo "🏗️  Building React frontend for PRODUCTION..."
    npm run build
    echo ""
    echo "🚀 Starting React frontend in PRODUCTION mode..."
    echo "   Serving optimized build"
    echo "   Frontend will be available at: http://$HOST:$PORT"
    echo ""
    npm run preview -- --host "$HOST" --port "$PORT"
fi
