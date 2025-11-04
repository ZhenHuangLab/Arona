#!/usr/bin/env bash
# Quick fix script for MinerU network issues
# This script helps diagnose and fix MinerU model download problems

set -euo pipefail

echo "=========================================="
echo "MinerU Network Issue Quick Fix"
echo "=========================================="
echo ""

# Detect environment
echo "[1/5] Detecting environment..."
if [ -n "${SLURM_JOB_ID:-}" ]; then
    echo "  ✓ Running in SLURM job (HPC environment)"
    ENV_TYPE="hpc"
elif ping -c 1 huggingface.co &>/dev/null; then
    echo "  ✓ Can reach huggingface.co"
    ENV_TYPE="normal"
elif ping -c 1 modelscope.cn &>/dev/null; then
    echo "  ✓ Can reach modelscope.cn (China network detected)"
    ENV_TYPE="china"
else
    echo "  ⚠ No internet access detected"
    ENV_TYPE="offline"
fi

# Check existing models
echo ""
echo "[2/5] Checking for existing models..."
HF_HOME="${HF_HOME:-${HOME}/.huggingface}"
HF_HUB_CACHE="${HF_HUB_CACHE:-${HF_HOME}/hub}"
MODEL_DIR="${HF_HUB_CACHE}/models--opendatalab--PDF-Extract-Kit-1.0"

if [ -d "${MODEL_DIR}" ]; then
    echo "  ✓ Model directory found: ${MODEL_DIR}"
    MODEL_EXISTS=true
else
    echo "  ✗ Model directory not found: ${MODEL_DIR}"
    MODEL_EXISTS=false
fi

# Recommend solution
echo ""
echo "[3/5] Recommending solution..."
case "${ENV_TYPE}" in
    hpc)
        echo "  → Solution: Pre-download models on login node"
        RECOMMENDED_SOURCE="local"
        ;;
    china)
        echo "  → Solution: Use ModelScope mirror"
        RECOMMENDED_SOURCE="modelscope"
        ;;
    offline)
        echo "  → Solution: Use local models (must download elsewhere first)"
        RECOMMENDED_SOURCE="local"
        ;;
    *)
        echo "  → Solution: Use HuggingFace (default)"
        RECOMMENDED_SOURCE="huggingface"
        ;;
esac

# Apply fix
echo ""
echo "[4/5] Applying fix..."

# Create/update .env.backend
ENV_FILE=".env.backend"
if [ -f "${ENV_FILE}" ]; then
    echo "  ✓ Found ${ENV_FILE}"
else
    echo "  ⚠ ${ENV_FILE} not found, will create it"
fi

# Backup existing file
if [ -f "${ENV_FILE}" ]; then
    cp "${ENV_FILE}" "${ENV_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
    echo "  ✓ Backed up ${ENV_FILE}"
fi

# Add/update environment variables
echo ""
echo "  Setting environment variables..."
export HF_HOME="${HF_HOME}"
export HF_HUB_CACHE="${HF_HUB_CACHE}"
export MINERU_MODEL_SOURCE="${RECOMMENDED_SOURCE}"

# Add to .env.backend if not already there
if ! grep -q "MINERU_MODEL_SOURCE" "${ENV_FILE}" 2>/dev/null; then
    cat >> "${ENV_FILE}" << EOF

# MinerU Configuration (added by fix_mineru_network.sh)
HF_HOME=${HF_HOME}
HF_HUB_CACHE=${HF_HUB_CACHE}
MINERU_MODEL_SOURCE=${RECOMMENDED_SOURCE}
EOF
    echo "  ✓ Added configuration to ${ENV_FILE}"
else
    echo "  ℹ Configuration already exists in ${ENV_FILE}"
fi

# Download models if needed
echo ""
echo "[5/5] Downloading models (if needed)..."

if [ "${MODEL_EXISTS}" = false ] && [ "${ENV_TYPE}" != "offline" ]; then
    echo "  → Running download script..."
    
    case "${RECOMMENDED_SOURCE}" in
        modelscope)
            export MINERU_MODEL_SOURCE=modelscope
            ;;
        huggingface)
            # Check if we should use mirror
            read -p "  Use HuggingFace mirror (hf-mirror.com)? [y/N]: " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                export HF_ENDPOINT=https://hf-mirror.com
            fi
            ;;
        local)
            echo "  ℹ Skipping download (local mode)"
            echo "  ⚠ Make sure models are already downloaded!"
            ;;
    esac
    
    if [ "${RECOMMENDED_SOURCE}" != "local" ]; then
        bash scripts/download_mineru_models.sh
    fi
else
    echo "  ℹ Skipping download (models exist or offline)"
fi

# Summary
echo ""
echo "=========================================="
echo "Summary"
echo "=========================================="
echo ""
echo "Environment Type: ${ENV_TYPE}"
echo "Model Source: ${RECOMMENDED_SOURCE}"
echo "HF_HOME: ${HF_HOME}"
echo "HF_HUB_CACHE: ${HF_HUB_CACHE}"
echo "Models Exist: ${MODEL_EXISTS}"
echo ""

if [ "${MODEL_EXISTS}" = true ] || [ "${RECOMMENDED_SOURCE}" = "local" ]; then
    echo "✅ Fix applied successfully!"
    echo ""
    echo "Next steps:"
    echo "1. Restart your backend:"
    echo "   source .env.backend"
    echo "   python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000"
    echo ""
    echo "2. Test with a PDF document"
else
    echo "⚠ Models may not be fully downloaded"
    echo ""
    echo "Next steps:"
    echo "1. Verify models are downloaded:"
    echo "   ls -lh ${MODEL_DIR}"
    echo ""
    echo "2. If download failed, try manual download:"
    echo "   See docs/MINERU_NETWORK_ISSUES.md for instructions"
fi

echo ""
echo "For more help, see: docs/MINERU_NETWORK_ISSUES.md"
echo "=========================================="

