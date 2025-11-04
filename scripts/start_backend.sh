#!/bin/bash
# Start RAG-Anything Backend Server

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Change to project root
cd "$PROJECT_ROOT"

echo "RAG-Anything Backend Server"
echo "============================"
echo ""

# Check if .env.backend exists
if [ -f .env.backend ]; then
    echo "✓ Found .env.backend"
    echo ""
    echo "Note: Backend will load .env.backend automatically via Python's dotenv."
    echo "      Shell variables like \${HOME} should be set in your shell environment,"
    echo "      not in .env.backend, as they won't be expanded in .env files."
    echo ""
else
    echo "⚠ Warning: .env.backend not found."
    echo "   Using default configuration and environment variables."
    echo ""
fi

# Check for HuggingFace environment variables (needed for MinerU)
if [ -z "$HF_HOME" ]; then
    echo "⚠ Warning: HF_HOME not set. MinerU may fail."
    echo "   Set it in your shell: export HF_HOME=\"\$HOME/.huggingface\""
    echo ""
fi

# Default values
HOST=${API_HOST:-0.0.0.0}
PORT=${API_PORT:-8000}

echo "Configuration:"
echo "  Host: $HOST"
echo "  Port: $PORT"
echo "  Working Directory: ${WORKING_DIR:-./rag_storage}"
echo ""

# Optional: Run configuration check
if [ "$1" = "--check" ]; then
    echo "Running configuration check..."
    python scripts/check_config.py
    exit $?
fi

echo "Starting backend server..."
echo ""

# Start backend server
# Note: Backend will load .env.backend automatically
python -m backend.main --host "$HOST" --port "$PORT" "$@"

