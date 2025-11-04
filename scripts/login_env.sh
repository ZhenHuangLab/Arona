#!/usr/bin/env bash
# Reason: Provide a single source of truth for the login node environment.

export OLLAMA_TIMEOUT_SECONDS="${OLLAMA_TIMEOUT_SECONDS:-540}"

# Prevent accidental execution; this script must be sourced.
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  echo "[ERROR] Source this script instead: source ${BASH_SOURCE[0]}" >&2
  exit 1
fi

# Resolve repository root so log paths stay portable across shells.
RAG_ANYTHING_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export RAG_ANYTHING_ROOT

# Shared storage layout (create lazily so sbatch finds it mounted).
export RAG_SHARED_ROOT="${RAG_SHARED_ROOT:-/ShareS/UserHome/user007/rag-data}"
export RAG_RUNTIME_STATE="${RAG_RUNTIME_STATE:-${RAG_SHARED_ROOT}/runtime}"
export LOG_ROOT="${LOG_ROOT:-${RAG_ANYTHING_ROOT}/logs/slurm}"

mkdir -p "${RAG_SHARED_ROOT}" "${RAG_RUNTIME_STATE}" "${LOG_ROOT}"

# Ollama defaults; leave host unset until the GPU job publishes the endpoint.
export OLLAMA_PORT="${OLLAMA_PORT:-11434}"
unset OLLAMA_HOST
unset OLLAMA_BASE_URL

export OLLAMA_GENERATE_MODEL="${OLLAMA_GENERATE_MODEL:-qwen3:235b}"
export OLLAMA_EMBED_MODEL="${OLLAMA_EMBED_MODEL:-qwen3-embedding:8b}"
export OLLAMA_EMBED_DIM="${OLLAMA_EMBED_DIM:-4096}"

export MAX_ASYNC="${MAX_ASYNC:-2}"
export MAX_GLEANING="${MAX_GLEANING:-0}"
export LLM_TIMEOUT="${LLM_TIMEOUT:-600}"
export OLLAMA_TIMEOUT_SECONDS="${OLLAMA_TIMEOUT_SECONDS:-540}"
export OLLAMA_MAX_RETRIES="${OLLAMA_MAX_RETRIES:-2}"
export OLLAMA_RETRY_BACKOFF="${OLLAMA_RETRY_BACKOFF:-0.5}"

# Reranker configuration shared across workers.
export RERANKER_MODEL_PATH="${RERANKER_MODEL_PATH:-${HOME}/.huggingface/models/bge-v2-gemma}"
export RERANKER_USE_FP16="${RERANKER_USE_FP16:-1}"

# Optional metadata; tweak per job as needed.
export RAG_WORKER_MODE="${RAG_WORKER_MODE:-ingest}"
export RAG_INPUT_FILE="${RAG_INPUT_FILE:-}" 
export HF_HOME="${HF_HOME:-${HOME}/.huggingface}"
export HF_HUB_CACHE="${HF_HUB_CACHE:-${HOME}/.huggingface/hub}"
export TIKTOKEN_CACHE_DIR="${TIKTOKEN_CACHE_DIR:-${HOME}/.cache/tiktoken}"

export ENABLE_IMAGE_PROCESSING="${ENABLE_IMAGE_PROCESSING:-false}"

echo "[INFO] RAG-Anything login environment configured."
echo "[INFO] Shared root: ${RAG_SHARED_ROOT}"
echo "[INFO] Runtime state: ${RAG_RUNTIME_STATE}"
echo "[INFO] Logs: ${LOG_ROOT}"
echo "[INFO] Ollama models: ${OLLAMA_GENERATE_MODEL} / ${OLLAMA_EMBED_MODEL}"
echo "[INFO] Reranker path: ${RERANKER_MODEL_PATH} (FP16=${RERANKER_USE_FP16})"
echo "[INFO] HF home: ${HF_HOME}"
echo "[INFO] HF hub cache: ${HF_HUB_CACHE}"
echo "[INFO] Tiktoken cache: ${TIKTOKEN_CACHE_DIR}"
echo "[INFO] Enable image processing: ${ENABLE_IMAGE_PROCESSING}"
echo "[INFO] Remember to launch Slurm jobs with --export=ALL."
