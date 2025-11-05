#!/bin/bash
# Start Arona React Frontend

set -e

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

# Change to frontend directory
cd "$FRONTEND_DIR"

echo "Arona React Frontend"
echo "============================"
echo ""

# Default values
HOST=${FRONTEND_HOST:-0.0.0.0}
PORT=${FRONTEND_PORT:-5173}
BACKEND_URL=${BACKEND_URL:-http://localhost:8000}
FRONTEND_MODE=${FRONTEND_MODE:-production}

echo "Configuration:"
echo "  Mode: $FRONTEND_MODE"
echo "  Host: $HOST"
echo "  Port: $PORT"
echo "  Backend URL: $BACKEND_URL"
echo ""

# Export backend URL for Vite
export VITE_BACKEND_URL="$BACKEND_URL"

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

