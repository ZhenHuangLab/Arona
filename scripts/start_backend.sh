#!/bin/bash
# Start RAG-Anything Backend Server

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Change to project root
cd "$PROJECT_ROOT"

# Detect execution method: prefer uv, fallback to direct Python
USE_UV=false
PYTHON_CMD=""

# Check if uv is available and .venv exists (preferred method)
if command -v uv &> /dev/null && [ -d ".venv" ]; then
    echo "✓ Detected uv package manager with .venv"
    USE_UV=true
    PYTHON_CMD="uv run python"

    # Get Python version from uv environment
    PYTHON_VERSION=$(uv run python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")')
    PYTHON_MAJOR=$(uv run python -c 'import sys; print(sys.version_info.major)')
    PYTHON_MINOR=$(uv run python -c 'import sys; print(sys.version_info.minor)')
    PYTHON_PATH=$(uv run python -c 'import sys; print(sys.executable)')

    echo "Using uv-managed Python"
    echo "Python version: $PYTHON_VERSION"
    echo "Python path: $PYTHON_PATH"
    echo ""
else
    # Fallback: Detect Python executable (prefer python3, fallback to python)
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        echo "❌ Error: Neither 'uv' nor 'python3/python' command found."
        echo ""
        echo "This project uses uv for package management. Please either:"
        echo ""
        echo "Option 1 (Recommended): Install and use uv"
        echo "  1. Install uv:"
        echo "     curl -LsSf https://astral.sh/uv/install.sh | sh"
        echo "  2. Install dependencies:"
        echo "     uv sync"
        echo "  3. Run this script again"
        echo ""
        echo "Option 2: Use system Python 3.10+"
        echo "  1. Ensure Python 3.10+ is installed and in PATH"
        echo "  2. Install dependencies:"
        echo "     pip install -r requirements-backend.txt"
        echo "  3. Run this script again"
        exit 1
    fi

    # Get Python version
    PYTHON_VERSION=$(${PYTHON_CMD} -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")')
    PYTHON_MAJOR=$(${PYTHON_CMD} -c 'import sys; print(sys.version_info.major)')
    PYTHON_MINOR=$(${PYTHON_CMD} -c 'import sys; print(sys.version_info.minor)')

    echo "⚠️  Warning: uv not detected or .venv not found"
    echo "   Using system Python (not recommended for production)"
    echo ""
    echo "Detected Python: $PYTHON_CMD"
    echo "Python version: $PYTHON_VERSION"
    echo "Python path: $(which ${PYTHON_CMD})"
    echo ""
fi

# Check Python version (requires 3.10+)
if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]); then
    echo "❌ Error: Python 3.10+ is required, but found Python $PYTHON_VERSION"
    echo ""
    echo "This project requires Python 3.10 or higher due to:"
    echo "  - Modern type hints (PEP 604, PEP 612)"
    echo "  - Structural pattern matching"
    echo "  - Other Python 3.10+ features"
    echo ""

    if [ "$USE_UV" = true ]; then
        echo "⚠️  Your .venv has Python $PYTHON_VERSION, which is too old."
        echo ""
        echo "To fix this:"
        echo "  1. Remove the old virtual environment:"
        echo "     rm -rf .venv"
        echo ""
        echo "  2. Ensure you have Python 3.10+ available on your system"
        echo "     (uv will use the system Python to create the venv)"
        echo ""
        echo "  3. Recreate the virtual environment:"
        echo "     uv sync"
        echo ""
        echo "  4. Run this script again"
    else
        # Check if uv is available but .venv doesn't exist
        if command -v uv &> /dev/null; then
            echo "💡 Tip: This project is designed to use uv package manager."
            echo ""
            echo "Recommended fix:"
            echo "  1. Install dependencies with uv:"
            echo "     uv sync"
            echo "  2. Run this script again (it will automatically use uv)"
            echo ""
            echo "Alternative fix (not recommended):"
        fi

        # Check if conda is available
        if command -v conda &> /dev/null; then
            echo "🔍 Conda detected. Checking conda environment..."
            echo ""

            # Check if conda environment is activated
            if [ -n "$CONDA_DEFAULT_ENV" ]; then
                echo "Current conda environment: $CONDA_DEFAULT_ENV"
                echo ""
                echo "⚠️  WARNING: Your conda environment is activated, but Python $PYTHON_VERSION was detected."
                echo "   This suggests the conda environment doesn't have Python 3.10+ installed."
                echo ""
                echo "To fix this:"
                echo "  1. Create a new conda environment with Python 3.10+:"
                echo "     conda create -n raganything python=3.10"
                echo "     conda activate raganything"
                echo ""
                echo "  2. Or update your current environment:"
                echo "     conda install python=3.10"
                echo ""
                echo "  3. Then install the project dependencies:"
                echo "     pip install -r requirements-backend.txt"
            else
                echo "⚠️  No conda environment is currently activated."
                echo ""
                echo "To fix this:"
                echo "  1. Create and activate a conda environment with Python 3.10+:"
                echo "     conda create -n raganything python=3.10"
                echo "     conda activate raganything"
                echo ""
                echo "  2. Install the project dependencies:"
                echo "     pip install -r requirements-backend.txt"
                echo ""
                echo "  3. Run this script again"
            fi
        else
            echo "To fix this:"
            echo "  1. Install Python 3.10+ from https://www.python.org/downloads/"
            echo "  2. Or use a version manager like pyenv:"
            echo "     pyenv install 3.10"
            echo "     pyenv local 3.10"
            echo ""
            echo "  3. Or create a virtual environment with Python 3.10+:"
            echo "     python3.10 -m venv venv"
            echo "     source venv/bin/activate"
            echo ""
            echo "  4. Install the project dependencies:"
            echo "     pip install -r requirements-backend.txt"
        fi
    fi

    exit 1
fi

echo "✓ Python version check passed (>= 3.10)"
echo ""

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
    ${PYTHON_CMD} scripts/check_config.py
    exit $?
fi

echo "Starting backend server..."
echo ""

# Start backend server
# Note: Backend will load .env.backend automatically
${PYTHON_CMD} -m backend.main --host "$HOST" --port "$PORT" "$@"

