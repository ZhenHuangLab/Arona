# Backend Orchestration Playbook

This guide explains how to submit and monitor the Slurm jobs introduced in Phase P2:

- `scripts/slurm/ollama_gpu_job.sh` boots a long-lived Ollama service that exposes `qwen3:235b` and `qwen3-embedding:8b`.
- `scripts/slurm/rag_worker_job.sh` runs ingestion/query workloads that depend on the Ollama endpoint and the local FlagEmbedding reranker.

The instructions assume you already followed the architecture guidance in `cluster_architecture.md` and that the repository lives under `/ShareS/UserHome/user007/software/RAG-Anything`.

## 1. Prerequisites

- Shared directories:
  - `RAG_SHARED_ROOT` → `/ShareS/UserHome/user007/rag-data`
  - `RAG_RUNTIME_STATE` → `${RAG_SHARED_ROOT}/runtime`
- Models cached ahead of time:
  - Ollama models (Qwen3) under `${HOME}/.ollama`
  - FlagEmbedding reranker under `${HOME}/.huggingface/models/bge-v2-gemma`
- Environment bootstrap script available at `~/setup/ollama.sh`
- `uv` available on `PATH` (the repo’s dependencies already installed via `uv pip install`)

Populate these variables in your shell (mirrors the additions in `env.example`):

```
export RAG_SHARED_ROOT=/ShareS/UserHome/user007/rag-data
export RAG_RUNTIME_STATE=${RAG_SHARED_ROOT}/runtime
export RERANKER_MODEL_PATH=$HOME/.huggingface/models/bge-v2-gemma
export RERANKER_USE_FP16=1
export LOG_ROOT=$PWD/logs/slurm
```

## 2. Starting the Ollama Service (GPU node)

1. Submit the job from the login node:
   ```
   sbatch --partition=V100 --gres=gpu:1 scripts/slurm/ollama_gpu_job.sh
   ```
   Override wall time or GPU count with standard `sbatch` overrides (the script defaults to 24 hours, 1× GPU).
2. The script performs the following automatically:
   - Sources `~/setup/ollama.sh`
   - Validates the FlagEmbedding cache at `$RERANKER_MODEL_PATH`
   - Launches `ollama serve --host 0.0.0.0 --port ${OLLAMA_PORT:-11434}` via `srun`
   - Writes `RAG_RUNTIME_STATE/ollama_service.json` containing `{host, port, job_id}`
3. Inspect logs on the login node:
   ```
   tail -f logs/slurm/ollama-<job-id>.out
   tail -f logs/slurm/ollama-serve.log
   ```
4. When the job exits (or is cancelled) the JSON file is removed by the script’s cleanup trap.

> **Health check:** the script waits up to 60 seconds for `http://127.0.0.1:11434/api/tags` to respond. If it never becomes ready the job terminates early; consult the log files for GPU allocation or model loading errors.

## 3. Running RAG Workloads

`scripts/slurm/rag_worker_job.sh` is flexible: submit it with a command to execute (`uv`, `python`, or a custom CLI). When `OLLAMA_HOST` is unset, the script reads `ollama_service.json` published by the GPU job.

### 3.1 Ingestion example (document processing)

The default command processes a document using the RAG pipeline:

```bash
export RAG_INPUT_FILE=/path/to/document.pdf
export OLLAMA_GENERATE_MODEL=qwen3:235b
export OLLAMA_EMBED_MODEL=qwen3-embedding:8b
sbatch --partition=cpu-long scripts/slurm/rag_worker_job.sh
```

To customize the ingestion command:

```bash
sbatch --partition=cpu-long scripts/slurm/rag_worker_job.sh -- \
  uv run python scripts/cluster_rag_worker.py \
    --mode ingest \
    --input-file /ShareS/UserHome/user007/rag-data/corpus/paper.pdf \
    --working-dir /ShareS/UserHome/user007/rag-data/rag_storage
```

### 3.2 Query example

```bash
export RAG_WORKER_MODE=query
sbatch --partition=cpu scripts/slurm/rag_worker_job.sh -- \
  uv run python scripts/cluster_rag_worker.py \
    --mode query \
    --query "What are the main findings?" \
    --working-dir /ShareS/UserHome/user007/rag-data/rag_storage
```

The worker script ensures:

- `OLLAMA_HOST` is resolved (`ollama_service.json` → `http://<gpu-host>:11434`)
- `RERANKER_MODEL_PATH` exists and `RERANKER_USE_FP16` is exported (so the retrieval code instantiates `FlagLLMReranker("~/.huggingface/models/bge-v2-gemma", use_fp16=True)`)
- `OMP_NUM_THREADS` is set to the allocated CPU count to avoid oversubscription
- `srun` launches the provided command with proper Slurm accounting

## 4. Coordinating Multiple Jobs

- Always start the Ollama GPU job first; the worker script hard fails if `ollama_service.json` is missing.
- Record the job ID printed by `sbatch --parsable` and share it with teammates so they can reuse the running service instead of launching duplicates.
- When updating models, cancel the running GPU job (`scancel <job-id>`), refresh the cache, then resubmit. The cleanup trap removes the stale JSON endpoint file.

## 5. Environment Variable Reference

| Variable | Producer | Consumer | Description |
| --- | --- | --- | --- |
| `RAG_SHARED_ROOT` | Operator | Both scripts | Shared corpus root (`/ShareS/.../rag-data`). |
| `RAG_RUNTIME_STATE` | Operator | Both scripts | Holds runtime metadata (`ollama_service.json`, logs). |
| `OLLAMA_PORT` | Operator | Ollama script | Override listener port (default `11434`). |
| `OLLAMA_HOST` | Ollama script (JSON) | Worker script, Web UI | Base URL to reach the running Ollama service. |
| `OLLAMA_GENERATE_MODEL` | Operator | RAG workloads | Default chat model (`qwen3:235b`). |
| `OLLAMA_EMBED_MODEL` | Operator | RAG workloads | Default embedding model (`qwen3-embedding:8b`). |
| `OLLAMA_GPUS` | Operator | Ollama script | Request additional GPUs (used in `srun`). |
| `RERANKER_MODEL_PATH` | Operator | Worker script | Absolute path to FlagEmbedding weights (e.g. `$HOME/.huggingface/models/bge-v2-gemma`). |
| `RERANKER_USE_FP16` | Operator | Worker script / pipeline | Toggle fp16 in `FlagLLMReranker`. |
| `RAG_WORKER_MODE` | Operator | Worker script | Free-form tag for logging (`ingest`, `query`, `kg-update`, …). |
| `LOG_ROOT` | Operator | Both scripts | Location for detailed logs (`logs/slurm` by default). |

## 6. Dry-Run Validation Checklist

Because this login node is not allowed to execute Slurm jobs, perform the following sanity checks manually on the cluster:

1. **Static validation (login node):**
   ```
   bash -n scripts/slurm/ollama_gpu_job.sh
   bash -n scripts/slurm/rag_worker_job.sh
   ```
2. **Slurm parser check (GPU queue):**
   ```
   sbatch --test-only scripts/slurm/ollama_gpu_job.sh
   sbatch --test-only scripts/slurm/rag_worker_job.sh
   ```
   Example output captured on 2025-10-04 from the login node:
   ```
   sbatch: Job 5837 to start at 2025-10-04T19:33:09 using 8 processors on nodes gpu01 in partition V100
   sbatch: Job 5838 to start at 2025-10-04T19:38:41 using 8 processors on nodes gpu01 in partition V100
   ```
   The `--test-only` flag validates directives without launching tasks; override partition/resources at submission time if you prefer CPU queues.
3. **Python script validation (login node):**
   ```bash
   python3 -m py_compile scripts/cluster_rag_worker.py
   python3 scripts/cluster_rag_worker.py --help
   ```
4. **Runtime smoke test (GPU node):**
   - Submit the Ollama job and wait for `ollama_service.json` to appear.
   - Submit a minimal worker job to test the cluster_rag_worker.py script:
     ```bash
     export RAG_INPUT_FILE=/path/to/test.pdf
     sbatch --partition=cpu-long scripts/slurm/rag_worker_job.sh
     ```
   - Check logs: `tail -f logs/slurm/rag-worker-<job-id>.out`
   - Issue `curl http://<host>:11434/api/tags` from the login node to confirm the service is reachable.

## 7. Troubleshooting

### Common Issues

**ModuleNotFoundError: No module named 'raganything.pipeline' or 'raganything.service'**
- **Cause:** These modules don't exist in the codebase. The RAG-Anything library uses a direct API pattern (see `examples/raganything_example.py`).
- **Solution:** Use `scripts/cluster_rag_worker.py` as the entry point (see examples in sections 3.1 and 3.2). The default job script command has been updated to use this wrapper.
- **Reference:** `configs/cluster.yaml.example` documents all available configuration options.

**Missing configuration file: configs/cluster.yaml**
- **Cause:** The cluster_rag_worker.py script is environment-driven and doesn't require a YAML file.
- **Solution:** Configure via environment variables (recommended) or CLI arguments. See `configs/cluster.yaml.example` for all available settings and `python scripts/cluster_rag_worker.py --help` for CLI usage.

**Worker script cannot load ollama_service.json**
- Confirm the JSON file exists under `${RAG_RUNTIME_STATE}` and that the login node can resolve the GPU hostname.

**Reranker import failures**
- Double-check the HuggingFace cache path; the script surfaces a fatal message before starting.
- Verify `RERANKER_MODEL_PATH` points to a valid model directory (e.g., `~/.huggingface/models/bge-v2-gemma`).

**GPU-specific errors**
- Tail `logs/slurm/ollama-serve.log` for OOM, CUDA driver problems, etc.

**Stuck jobs**
- Use `scancel <job-id>` to terminate; the cleanup trap removes stale endpoint files to avoid clients hitting defunct hosts.

---

These procedures satisfy Phase P2 exit criteria: both scripts are documented, environment variables are enumerated, and operators have a safe workflow to start/monitor/stop the services without executing Slurm commands from this login session.
