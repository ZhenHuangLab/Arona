# RAG-Anything Validation Guide

This runbook walks operators through validating the full RAG-Anything stack —
Ollama GPU job, RAG worker job, and Open WebUI connector — after deploying the
Phase P2–P4 fixes. All commands must be executed on the cluster (not from this
login node session) and in the order presented. The checklist confirms that the
`ModuleNotFoundError` regression is gone and that Open WebUI can reach the RAG
backend end-to-end.

## 0. Scope and Prerequisites

- **Audience:** Cluster operators with Slurm access and write permission to
  `/ShareS/UserHome/user007/rag-data`.
- **Dependencies:**
  - `scripts/slurm/ollama_gpu_job.sh` deployed from latest `main`.
  - `scripts/slurm/rag_worker_job.sh` pointing at
    `scripts/cluster_rag_worker.py` (Phase P2 output).
  - Models cached: Qwen3 family under `${HOME}/.ollama`, FlagEmbedding reranker
    under `${HOME}/.huggingface/models/bge-v2-gemma`.
  - Shared directories defined (adjust paths if your deployment differs):
    ```bash
    export RAG_SHARED_ROOT=/ShareS/UserHome/user007/rag-data
    export RAG_RUNTIME_STATE=${RAG_SHARED_ROOT}/runtime
    export LOG_ROOT=$PWD/logs/slurm
    ```
- **Reference docs:** `docs/deployment/orchestration.md` (job orchestration) and
  `docs/deployment/webui.md` (Open WebUI integration).

> **Important:** Do not execute Slurm jobs from the login node used by this AI
> session. Run each command from your interactive shell on the cluster.

## 1. Preflight on the Login Node

1. **Syntax checks (no job submission):**
   ```bash
   bash -n scripts/slurm/ollama_gpu_job.sh
   bash -n scripts/slurm/rag_worker_job.sh
   python3 -m py_compile scripts/cluster_rag_worker.py
   python3 scripts/cluster_rag_worker.py --help
   ```
2. **Environment sanity:** confirm these variables resolve to real paths before
   proceeding:
   - `RAG_SHARED_ROOT`, `RAG_RUNTIME_STATE`
   - `RERANKER_MODEL_PATH`
   - `OLLAMA_GENERATE_MODEL`, `OLLAMA_EMBED_MODEL`
3. **Staging input artifact:** place a small PDF or text file at
   `${RAG_SHARED_ROOT}/samples/quickstart.pdf` (or update the ingestion command
   in §3 accordingly). Smaller documents reduce queue time during smoke testing.

Exit criteria: all four commands return `0`, required environment variables are
set, and the sample document exists.

## 2. Launch the Ollama GPU Job

1. Submit the GPU job:
   ```bash
   sbatch --partition=V100 --gres=gpu:1 scripts/slurm/ollama_gpu_job.sh
   ```
   Capture the job ID printed by `sbatch --parsable`.
2. Monitor startup logs until the health check passes:
   ```bash
   tail -f logs/slurm/ollama-<job-id>.out
   tail -f logs/slurm/ollama-serve.log
   ```
3. Verify `ollama_service.json` exists and contains a reachable host:port pair:
   ```bash
   cat ${RAG_RUNTIME_STATE}/ollama_service.json
   curl http://$(jq -r '.host + ":" + (.port|tostring)' \
     ${RAG_RUNTIME_STATE}/ollama_service.json)/api/tags
   ```

Exit criteria: the health check log shows `[INFO] Ollama is ready (attempt X)`, `curl …/api/tags`
returns model metadata, and the JSON file persists under
`${RAG_RUNTIME_STATE}`.

## 3. Validate Ingestion via RAG Worker

1. Export the minimal environment (override paths as needed):
   ```bash
   export RAG_INPUT_FILE=${RAG_SHARED_ROOT}/samples/quickstart.pdf
   export OLLAMA_GENERATE_MODEL=qwen3:235b
   export OLLAMA_EMBED_MODEL=qwen3-embedding:8b
   export WORKING_DIR=${RAG_SHARED_ROOT}/rag_storage
   ```
2. Submit the worker job with the default command:
   ```bash
   sbatch --partition=cpu-long scripts/slurm/rag_worker_job.sh
   ```
3. Tail the worker log:
   ```bash
   tail -f logs/slurm/rag-worker-<job-id>.out
   ```
   Look for:
   - `Starting ingestion: …`
   - `Ollama host: http://<gpu-host>:11434`
   - `✓ Ingestion completed successfully`
   - **Absence** of `ModuleNotFoundError`
4. Inspect the storage directory for new artifacts:
   ```bash
   find ${WORKING_DIR}/parsed_output -maxdepth 1 -type f | head
   ```

Exit criteria: log shows the success checkmark line, no Python stack traces
appear, and parsed output files exist in `${WORKING_DIR}/parsed_output`.

## 4. Validate Query Workflow

1. Export query parameters (reuse the same working directory):
   ```bash
   export RAG_WORKER_MODE=query
   sbatch --partition=cpu scripts/slurm/rag_worker_job.sh -- \
     uv run python scripts/cluster_rag_worker.py \
       --mode query \
       --query "Summarize the quickstart document" \
       --working-dir ${WORKING_DIR}
   ```
2. Monitor the log for the query job:
   ```bash
   tail -f logs/slurm/rag-worker-<job-id>.out
   ```
   Look for the rendered answer block delimited by `========` plus the final
   `Answer:` section.

Exit criteria: job exits with status `0` and the log prints the formatted answer
section without raising `Operation failed`.

## 5. Confirm Open WebUI Connector End-to-End

1. Start Open WebUI following `docs/deployment/webui.md` (Docker or `uv`
   launcher). Ensure `RAG_API_BASE_URL` matches the ingress host for
   `scripts/cluster_rag_worker.py` (default `http://127.0.0.1:8001`).
2. Sign in to Open WebUI and enable the `rag_anything_connector` extension.
3. Use the extension tools to verify connectivity:
   - `/tools list_corpora` → Should list the corpus populated in §3.
   - `/tools preview_embedding` with a sample query → Should return reranked
     snippets referencing newly ingested content.
   - `/tools graph_snapshot` (optional) → Confirms LightRAG metadata is
     accessible.

Exit criteria: Open WebUI actions succeed, and the RAG backend responds within
the configured timeout (15 s default).

## 6. Success Checklist

- [ ] `ollama_gpu_job.sh` job is running (check `squeue -j <id>`).
- [ ] `${RAG_RUNTIME_STATE}/ollama_service.json` exists with valid host/port.
- [ ] Ingestion worker log shows `✓ Ingestion completed successfully`.
- [ ] Parsed artifacts created under `${WORKING_DIR}/parsed_output`.
- [ ] Query worker log prints an answer block without errors.
- [ ] Open WebUI `/tools list_corpora` and `/tools preview_embedding` succeed.
- [ ] No occurrence of `ModuleNotFoundError` across any log files.

## 7. Troubleshooting Reminders

- If Slurm submissions hang, rerun with `sbatch --test-only …` to validate
  directives and confirm partitions are spelled correctly.
- Missing HuggingFace weights trigger a fatal `FileNotFoundError` before the
  ingestion starts; rerun `huggingface-cli download …` or copy the cache.
- If `curl …/api/tags` fails, inspect `logs/slurm/ollama-serve.log` for GPU
  startup issues or port conflicts.
- Open WebUI failures usually stem from a mismatched `RAG_API_BASE_URL`; the
  value must reach the node running `scripts/cluster_rag_worker.py` (often the
  login node). Use `ssh -L` tunnelling to expose the port locally.
- After each run, clean up with `scancel <job-id>` and remove artifacts under
  `${RAG_RUNTIME_STATE}` if you need a fresh state.

Completing §§1–7 satisfies Acceptance Criterion AC4 (“Clear instructions provided
for user to test the connection between OpenWebUI and RAG backend”).
