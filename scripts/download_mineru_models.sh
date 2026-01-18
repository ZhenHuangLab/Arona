#!/usr/bin/env bash
# Purpose: Pre-download MinerU models on the login node (which has internet access)
# Usage: bash scripts/download_mineru_models.sh
#
# Environment Variables:
#   MINERU_MODEL_SOURCE - Model source: huggingface (default), modelscope, or local
#   HF_ENDPOINT - HuggingFace mirror endpoint (e.g., https://hf-mirror.com for China)
#   HF_HOME - HuggingFace cache directory
#   HF_HUB_CACHE - HuggingFace Hub cache directory

set -euo pipefail

# Ensure HuggingFace cache directory exists
HF_HOME="${HF_HOME:-${HOME}/.huggingface}"
HF_HUB_CACHE="${HF_HUB_CACHE:-${HF_HOME}/hub}"
MINERU_MODEL_SOURCE="${MINERU_MODEL_SOURCE:-huggingface}"

export HF_HOME
export HF_HUB_CACHE

mkdir -p "${HF_HOME}" "${HF_HUB_CACHE}"

echo "[INFO] HuggingFace cache: ${HF_HOME}"
echo "[INFO] Model source: ${MINERU_MODEL_SOURCE}"
if [ -n "${HF_ENDPOINT:-}" ]; then
    echo "[INFO] Using HuggingFace mirror: ${HF_ENDPOINT}"
    export HF_ENDPOINT
fi
echo "[INFO] Downloading MinerU models..."

# Download based on source
if [ "${MINERU_MODEL_SOURCE}" = "modelscope" ]; then
    echo "[INFO] Using ModelScope to download models..."

    # Method: Use Python with ModelScope
    python3 << 'PYTHON_SCRIPT'
import os
try:
    from modelscope import snapshot_download

    cache_dir = snapshot_download(
        model_id="opendatalab/PDF-Extract-Kit-1.0",
        cache_dir=os.environ.get("HF_HUB_CACHE", os.path.expanduser("~/.huggingface/hub"))
    )
    print(f"✅ Models downloaded successfully to: {cache_dir}")
except ImportError:
    print("❌ ModelScope not installed. Installing...")
    import subprocess
    subprocess.check_call(["pip", "install", "modelscope"])
    print("✅ ModelScope installed. Please re-run this script.")
    exit(1)
except Exception as e:
    print(f"❌ Download failed: {e}")
    print("[HELP] Make sure you have internet access on this node")
    exit(1)
PYTHON_SCRIPT

elif [ "${MINERU_MODEL_SOURCE}" = "local" ]; then
    echo "[INFO] Using local models (skipping download)"
    echo "[INFO] Make sure models are already in: ${HF_HUB_CACHE}/models--opendatalab--PDF-Extract-Kit-1.0/"

else
    # Default: Use HuggingFace
    # Method 1: Use huggingface-cli to pre-download models
    if command -v huggingface-cli &> /dev/null; then
        echo "[INFO] Using huggingface-cli to download models..."

        # Download PDF-Extract-Kit models
        huggingface-cli download opendatalab/PDF-Extract-Kit-1.0 \
            --repo-type model \
            --cache-dir "${HF_HUB_CACHE}" \
            --resume-download

        echo "✅ Models downloaded successfully to ${HF_HUB_CACHE}"

    else
        echo "[WARN] huggingface-cli not found, trying Python method..."

        # Method 2: Use Python to download
        python3 << 'PYTHON_SCRIPT'
import os
from huggingface_hub import snapshot_download

hf_hub_cache = os.environ.get("HF_HUB_CACHE", os.path.expanduser("~/.huggingface/hub"))
hf_endpoint = os.environ.get("HF_ENDPOINT", None)

if hf_endpoint:
    print(f"[INFO] Using HuggingFace mirror: {hf_endpoint}")

print(f"[INFO] Downloading to: {hf_hub_cache}")

try:
    cache_dir = snapshot_download(
        repo_id="opendatalab/PDF-Extract-Kit-1.0",
        repo_type="model",
        cache_dir=hf_hub_cache,
        resume_download=True
    )
    print(f"✅ Models downloaded successfully to: {cache_dir}")
except Exception as e:
    print(f"❌ Download failed: {e}")
    print("[HELP] Make sure you have internet access on this node")
    print("[HELP] You can also manually download from: https://huggingface.co/opendatalab/PDF-Extract-Kit-1.0")
    print("[HELP] Or try using ModelScope: export MINERU_MODEL_SOURCE=modelscope")
    print("[HELP] Or use HuggingFace mirror: export HF_ENDPOINT=https://hf-mirror.com")
    exit(1)
PYTHON_SCRIPT
    fi
fi

echo ""
echo "[INFO] Verifying downloaded models..."
if ls -lh "${HF_HUB_CACHE}/models--opendatalab--PDF-Extract-Kit-1.0/" 2>/dev/null; then
    echo "✅ Model directory found"
else
    echo "[WARN] Model directory not found at: ${HF_HUB_CACHE}/models--opendatalab--PDF-Extract-Kit-1.0/"
    echo "[HELP] This might be normal if using ModelScope or if download is still in progress"
fi

echo ""
echo "✅ Done! Models are ready for offline use on compute nodes."
echo ""
echo "[INFO] Make sure to set these environment variables in your jobs/backend:"
echo "       export HF_HOME=${HF_HOME}"
echo "       export HF_HUB_CACHE=${HF_HUB_CACHE}"
echo "       export MINERU_MODEL_SOURCE=${MINERU_MODEL_SOURCE}"
if [ -n "${HF_ENDPOINT:-}" ]; then
    echo "       export HF_ENDPOINT=${HF_ENDPOINT}"
fi
echo ""
echo "[INFO] For offline use, also set:"
echo "       export HF_DATASETS_OFFLINE=1"
echo "       export TRANSFORMERS_OFFLINE=1"
