#!/bin/bash
# Setup Environment Variables for Arona
#
# This script helps you set up the required environment variables
# for running Arona backend with MinerU.

set -e

echo "Arona Environment Setup"
echo "=============================="
echo ""

# Detect shell
SHELL_NAME=$(basename "$SHELL")
case "$SHELL_NAME" in
    bash)
        RC_FILE="$HOME/.bashrc"
        ;;
    zsh)
        RC_FILE="$HOME/.zshrc"
        ;;
    *)
        echo "⚠ Warning: Unknown shell ($SHELL_NAME). Defaulting to ~/.bashrc"
        RC_FILE="$HOME/.bashrc"
        ;;
esac

echo "Detected shell: $SHELL_NAME"
echo "RC file: $RC_FILE"
echo ""

# Check if variables are already set
echo "Checking current environment..."
echo ""

HF_HOME_SET=false
HF_HUB_CACHE_SET=false
MINERU_SOURCE_SET=false

if [ -n "$HF_HOME" ]; then
    echo "✓ HF_HOME is already set: $HF_HOME"
    HF_HOME_SET=true
else
    echo "✗ HF_HOME is not set"
fi

if [ -n "$HF_HUB_CACHE" ]; then
    echo "✓ HF_HUB_CACHE is already set: $HF_HUB_CACHE"
    HF_HUB_CACHE_SET=true
else
    echo "✗ HF_HUB_CACHE is not set"
fi

if [ -n "$MINERU_MODEL_SOURCE" ]; then
    echo "✓ MINERU_MODEL_SOURCE is already set: $MINERU_MODEL_SOURCE"
    MINERU_SOURCE_SET=true
else
    echo "✗ MINERU_MODEL_SOURCE is not set"
fi

echo ""

# If all are set, ask if user wants to reconfigure
if [ "$HF_HOME_SET" = true ] && [ "$HF_HUB_CACHE_SET" = true ] && [ "$MINERU_SOURCE_SET" = true ]; then
    echo "All required environment variables are already set."
    read -p "Do you want to reconfigure them? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Skipping configuration."
        exit 0
    fi
fi

# Determine default values
DEFAULT_HF_HOME="$HOME/.huggingface"
DEFAULT_HF_HUB_CACHE="$HOME/.huggingface/hub"

# Ask for HF_HOME
echo ""
echo "HuggingFace Cache Directory"
echo "---------------------------"
echo "This is where HuggingFace models and datasets are cached."
echo "Default: $DEFAULT_HF_HOME"
echo ""
read -p "Enter HF_HOME path (or press Enter for default): " HF_HOME_INPUT
HF_HOME_VALUE="${HF_HOME_INPUT:-$DEFAULT_HF_HOME}"

# Expand tilde
HF_HOME_VALUE="${HF_HOME_VALUE/#\~/$HOME}"

echo "Will set HF_HOME=$HF_HOME_VALUE"

# Ask for HF_HUB_CACHE
echo ""
echo "HuggingFace Hub Cache Directory"
echo "-------------------------------"
echo "This is where HuggingFace Hub models are cached."
echo "Default: $DEFAULT_HF_HUB_CACHE"
echo ""
read -p "Enter HF_HUB_CACHE path (or press Enter for default): " HF_HUB_CACHE_INPUT
HF_HUB_CACHE_VALUE="${HF_HUB_CACHE_INPUT:-$DEFAULT_HF_HUB_CACHE}"

# Expand tilde
HF_HUB_CACHE_VALUE="${HF_HUB_CACHE_VALUE/#\~/$HOME}"

echo "Will set HF_HUB_CACHE=$HF_HUB_CACHE_VALUE"

# Ask for MINERU_MODEL_SOURCE
echo ""
echo "MinerU Model Source"
echo "-------------------"
echo "Options:"
echo "  huggingface - Download from HuggingFace (default, recommended for most users)"
echo "  modelscope  - Download from ModelScope (recommended for China/restricted networks)"
echo "  local       - Use pre-downloaded models (no network access)"
echo ""
read -p "Enter MINERU_MODEL_SOURCE (huggingface/modelscope/local) [huggingface]: " MINERU_SOURCE_INPUT
MINERU_SOURCE_VALUE="${MINERU_SOURCE_INPUT:-huggingface}"

# Validate input
case "$MINERU_SOURCE_VALUE" in
    huggingface|modelscope|local)
        echo "Will set MINERU_MODEL_SOURCE=$MINERU_SOURCE_VALUE"
        ;;
    *)
        echo "⚠ Invalid value. Using default: huggingface"
        MINERU_SOURCE_VALUE="huggingface"
        ;;
esac

# Optional: HF_ENDPOINT for China
echo ""
echo "HuggingFace Mirror (Optional)"
echo "-----------------------------"
echo "For users in China or restricted networks, you can use a mirror."
echo "Example: https://hf-mirror.com"
echo ""
read -p "Enter HF_ENDPOINT (or press Enter to skip): " HF_ENDPOINT_INPUT

# Summary
echo ""
echo "Summary of Changes"
echo "=================="
echo "The following will be added to $RC_FILE:"
echo ""
echo "export HF_HOME=\"$HF_HOME_VALUE\""
echo "export HF_HUB_CACHE=\"$HF_HUB_CACHE_VALUE\""
echo "export MINERU_MODEL_SOURCE=\"$MINERU_SOURCE_VALUE\""
if [ -n "$HF_ENDPOINT_INPUT" ]; then
    echo "export HF_ENDPOINT=\"$HF_ENDPOINT_INPUT\""
fi
echo ""

# Confirm
read -p "Do you want to proceed? (y/N): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

# Backup RC file
BACKUP_FILE="${RC_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
cp "$RC_FILE" "$BACKUP_FILE"
echo "✓ Backed up $RC_FILE to $BACKUP_FILE"

# Add to RC file
echo "" >> "$RC_FILE"
echo "# Arona Environment Variables (added by setup_env.sh)" >> "$RC_FILE"
echo "export HF_HOME=\"$HF_HOME_VALUE\"" >> "$RC_FILE"
echo "export HF_HUB_CACHE=\"$HF_HUB_CACHE_VALUE\"" >> "$RC_FILE"
echo "export MINERU_MODEL_SOURCE=\"$MINERU_SOURCE_VALUE\"" >> "$RC_FILE"

if [ -n "$HF_ENDPOINT_INPUT" ]; then
    echo "export HF_ENDPOINT=\"$HF_ENDPOINT_INPUT\"" >> "$RC_FILE"
fi

echo "✓ Added environment variables to $RC_FILE"

# Create directories if they don't exist
mkdir -p "$HF_HOME_VALUE"
mkdir -p "$HF_HUB_CACHE_VALUE"
echo "✓ Created cache directories"

# Export for current session
export HF_HOME="$HF_HOME_VALUE"
export HF_HUB_CACHE="$HF_HUB_CACHE_VALUE"
export MINERU_MODEL_SOURCE="$MINERU_SOURCE_VALUE"
if [ -n "$HF_ENDPOINT_INPUT" ]; then
    export HF_ENDPOINT="$HF_ENDPOINT_INPUT"
fi

echo ""
echo "✓ Setup completed successfully!"
echo ""
echo "The environment variables are now set for the current session."
echo "To use them in new terminal sessions, run:"
echo "  source $RC_FILE"
echo ""
echo "Or close and reopen your terminal."
echo ""

# Offer to source now
read -p "Do you want to source $RC_FILE now? (y/N): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    source "$RC_FILE"
    echo "✓ Sourced $RC_FILE"
fi

echo ""
echo "Next steps:"
echo "1. Verify configuration: python3 scripts/check_config.py"
echo "2. Start backend: bash scripts/start_backend.sh"
echo ""

