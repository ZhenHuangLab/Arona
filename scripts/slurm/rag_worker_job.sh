#!/bin/bash
#SBATCH --job-name=rag-worker
#SBATCH --partition=V100
#SBATCH --nodes=1
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --time=04:00:00
#SBATCH --output=logs/slurm/rag-worker-%j.out

# Purpose: Run ingestion, indexing, or query workloads that depend on an
#          Ollama endpoint plus the FlagEmbedding reranker.
# Usage:
#   # Default usage (uses RAG_INPUT_FILE environment variable):
#   export RAG_INPUT_FILE=/path/to/document.pdf
#   sbatch scripts/slurm/rag_worker_job.sh
#
#   # Custom command override:
#   sbatch scripts/slurm/rag_worker_job.sh -- uv run python scripts/cluster_rag_worker.py \
#     --mode ingest --input-file /path/to/document.pdf
#
# Override defaults via environment variables before submission, e.g.:
#   export OLLAMA_HOST=http://gpu123:11434
#   export RAG_INPUT_FILE=/data/paper.pdf
#   export OLLAMA_GENERATE_MODEL=qwen2.5:latest
#   sbatch --partition=V100 scripts/slurm/rag_worker_job.sh

set -euo pipefail

LOG_ROOT=${LOG_ROOT:-"${PWD}/logs/slurm"}
RAG_SHARED_ROOT=${RAG_SHARED_ROOT:-"${HOME}/rag-data"}
RAG_RUNTIME_STATE=${RAG_RUNTIME_STATE:-"${RAG_SHARED_ROOT}/runtime"}
SERVICE_FILE=${OLLAMA_SERVICE_FILE:-"${RAG_RUNTIME_STATE}/ollama_service.json"}
RERANKER_MODEL_PATH=${RERANKER_MODEL_PATH:-"${HOME}/.huggingface/models/bge-v2-gemma"}
RERANKER_USE_FP16=${RERANKER_USE_FP16:-1}
WORKER_MODE=${RAG_WORKER_MODE:-"ingest"}

# Ollama model configuration with defaults
OLLAMA_GENERATE_MODEL=${OLLAMA_GENERATE_MODEL:-"qwen3:32b"}
OLLAMA_EMBED_MODEL=${OLLAMA_EMBED_MODEL:-"qwen3-embedding:8b"}
OLLAMA_EMBED_DIM=${OLLAMA_EMBED_DIM:-4096}

# LightRAG concurrency and timeout defaults tuned for slower Ollama responses
# Reason: Avoid worker-level timeouts when the model latency spikes.
MAX_ASYNC=${MAX_ASYNC:-2}
MAX_GLEANING=${MAX_GLEANING:-0}
LLM_TIMEOUT=${LLM_TIMEOUT:-600}
OLLAMA_TIMEOUT_SECONDS=${OLLAMA_TIMEOUT_SECONDS:-540}

# HuggingFace cache directories
HF_HOME=${HF_HOME:-"${HOME}/.huggingface"}
HF_HUB_CACHE=${HF_HUB_CACHE:-"${HOME}/.huggingface/hub"}

mkdir -p "${LOG_ROOT}" "${RAG_RUNTIME_STATE}"

die() {
  echo "[FATAL] $*" >&2
  exit 1
}

resolve_ollama_host() {
  [[ -n "${OLLAMA_HOST:-}" ]] && return 0
  [[ -f "${SERVICE_FILE}" ]] || die "OLLAMA_HOST not set and service file ${SERVICE_FILE} missing."
  local host port
  read -r host port < <(
    python - <<'PY'
import json, os, sys
service_path = os.environ.get("SERVICE_FILE")
with open(service_path, "r", encoding="utf-8") as handle:
    payload = json.load(handle)
host = payload.get("host")
port = payload.get("port", 11434)
if not host:
    raise SystemExit("missing host in service file")
sys.stdout.write(f"{host} {port}\n")
PY
  ) || die "Failed to parse ${SERVICE_FILE}."
  export OLLAMA_HOST="http://${host}:${port}"
}

export SERVICE_FILE
resolve_ollama_host

[[ -d "${RERANKER_MODEL_PATH}" ]] || die "FlagEmbedding weights missing at ${RERANKER_MODEL_PATH}."

export RAG_SHARED_ROOT
export RAG_RUNTIME_STATE
export RERANKER_MODEL_PATH
export RERANKER_USE_FP16
export WORKER_MODE
export OLLAMA_HOST
export RAG_INPUT_FILE

# Export Ollama model configurations
export OLLAMA_GENERATE_MODEL
export OLLAMA_EMBED_MODEL
export OLLAMA_EMBED_DIM
export MAX_ASYNC
export MAX_GLEANING
export LLM_TIMEOUT
export OLLAMA_TIMEOUT_SECONDS
export HF_HOME
export HF_HUB_CACHE

# Reason: Compute nodes have no internet access. Point tiktoken to pre-cached encoding file
# in shared filesystem to avoid DNS resolution failures when initializing LightRAG.
export TIKTOKEN_CACHE_DIR="${HOME}/.cache/tiktoken"

DEFAULT_CMD=("uv" "run" "python" "scripts/cluster_rag_worker.py" "--mode" "ingest" "--input-file" "${RAG_INPUT_FILE:-/path/to/document.pdf}")

if [[ $# -gt 0 ]]; then
  CMD=("$@")
else
  CMD=("${DEFAULT_CMD[@]}")
fi

echo "[INFO] Running RAG worker mode='${WORKER_MODE}' via ${CMD[*]}"

command -v "${CMD[0]}" >/dev/null 2>&1 || die "Required executable ${CMD[0]} not found on PATH."

# Reason: Explicitly set CPU affinity to avoid oversubscription on shared nodes.
export OMP_NUM_THREADS=${OMP_NUM_THREADS:-${SLURM_CPUS_PER_TASK:-8}}

srun --cpu-bind=cores --ntasks=1 "${CMD[@]}"
