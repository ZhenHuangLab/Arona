#!/bin/bash
# Start both Backend and Frontend

set -e

echo "Starting Arona (Backend + Frontend)..."

# Load environment
if [ -f .env.backend ]; then
    export $(cat .env.backend | grep -v '^#' | grep -v '^$' | sed 's/#.*$//' | xargs)
fi

# Start backend in background
echo "Starting backend..."
bash scripts/start_backend.sh &
BACKEND_PID=$!

# Wait for backend to be ready
echo "Waiting for backend to be ready..."
sleep 5

# Check if backend is running
if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo "Error: Backend failed to start"
    exit 1
fi

# Start frontend
echo "Starting frontend..."
bash scripts/start_frontend.sh

# Cleanup on exit
trap "kill $BACKEND_PID 2>/dev/null" EXIT

