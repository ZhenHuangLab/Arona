#!/bin/bash
#SBATCH --job-name=ollama-serve
#SBATCH --partition=V100
#SBATCH --nodes=1
#SBATCH --gres=gpu:4
#SBATCH --cpus-per-task=8
#SBATCH --time=24:00:00
#SBATCH --output=logs/slurm/ollama-%j.out

# Purpose: Launch a long-lived Ollama service on a GPU node.
# Notes:
#   * Override resources at submission time (e.g. `sbatch --partition=A100 --gres=gpu:2`).
#   * Script assumes shared storage mounted at the same location on login and GPU nodes.
#   * Do NOT run directly on the login node; always submit through `sbatch`.

set -euo pipefail

LOG_ROOT=${LOG_ROOT:-"${PWD}/logs/slurm"}
RAG_SHARED_ROOT=${RAG_SHARED_ROOT:-"${HOME}/rag-data"}
RAG_RUNTIME_STATE=${RAG_RUNTIME_STATE:-"${RAG_SHARED_ROOT}/runtime"}
OLLAMA_PORT=${OLLAMA_PORT:-11434}
OLLAMA_HOST_FILE="${RAG_RUNTIME_STATE}/ollama_service.json"
OLLAMA_CACHE=${OLLAMA_CACHE:-"${HOME}/.ollama/models"}
RERANKER_MODEL_PATH=${RERANKER_MODEL_PATH:-"${HOME}/.huggingface/models/bge-v2-gemma"}
OLLAMA_GPUS=${OLLAMA_GPUS:-${SLURM_GPUS_ON_NODE:-1}}

mkdir -p "${LOG_ROOT}" "${RAG_RUNTIME_STATE}" "${OLLAMA_CACHE}"

die() {
  echo "[FATAL] $*" >&2
  exit 1
}

cleanup() {
  rm -f "${OLLAMA_HOST_FILE}"
}
trap cleanup EXIT

[[ -f "${HOME}/setup/ollama.sh" ]] || die "Expected Ollama environment script at ~/setup/ollama.sh"
[[ -d "${RERANKER_MODEL_PATH}" ]] || die "FlagEmbedding weights missing at ${RERANKER_MODEL_PATH}. Sync before submitting the job."

source "${HOME}/setup/ollama.sh"

command -v ollama >/dev/null 2>&1 || die "ollama binary not found after sourcing environment."

HOSTNAME_VALUE=${SLURMD_NODENAME:-$(hostname -s)}

cat >"${OLLAMA_HOST_FILE}.tmp" <<JSON
{
  "host": "${HOSTNAME_VALUE}",
  "port": ${OLLAMA_PORT},
  "job_id": "${SLURM_JOB_ID:-unknown}",
  "cache": "${OLLAMA_CACHE}",
  "updated_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
}
JSON
mv "${OLLAMA_HOST_FILE}.tmp" "${OLLAMA_HOST_FILE}"

echo "[INFO] Starting ollama serve on ${HOSTNAME_VALUE}:${OLLAMA_PORT}"

# Reason: Older Ollama builds on the cluster ignore CLI flags; use env vars instead.
srun --ntasks=1 --gres="gpu:${OLLAMA_GPUS}" --unbuffered \
  env \
  OLLAMA_HOST="0.0.0.0:${OLLAMA_PORT}" \
  OLLAMA_KEEP_ALIVE=0 \
  OLLAMA_MODELS="${OLLAMA_CACHE}" \
  ollama serve >>"${LOG_ROOT}/ollama-serve.log" 2>&1 &

SERVER_PID=$!

health_check() {
  if command -v curl >/dev/null 2>&1; then
    curl --silent --fail "http://127.0.0.1:${OLLAMA_PORT}/api/tags" >/dev/null
    return $?
  fi
  python - <<PY
import json, urllib.request
urllib.request.urlopen("http://127.0.0.1:${OLLAMA_PORT}/api/tags", timeout=5)
PY
}

READY=0
for attempt in $(seq 1 30); do
  if health_check; then
    echo "[INFO] Ollama is ready (attempt ${attempt})."
    READY=1
    break
  fi
  echo "[WARN] Waiting for Ollama to become ready (attempt ${attempt})."
  sleep 2
done

if [[ ${READY} -ne 1 ]]; then
  echo "[ERROR] Ollama failed to respond after 60 seconds. Check logs under ${LOG_ROOT}." >&2
  kill ${SERVER_PID} 2>/dev/null || true
  wait ${SERVER_PID} || true
  exit 1
fi

wait ${SERVER_PID}
