# HPC Cluster Architecture for RAG-Anything / LightRAG

## 1. Topology Overview

```
[Developer / WebUI]
        |
        v (SSH)
  +--------------+        shared FS (e.g. /ShareS/UserHome)
  | Login Node   |-------------------------------+
  | (CPU only)   |                               |
  +--------------+                               |
        | salloc / sbatch                        |
        v                                        v
  +-------------------+               +-------------------+
  | GPU Service Nodes |<--->(RPC)---->|  RAG Workers      |
  | (Ollama Serve)    |               |  (Ingestion/Query)|
  +-------------------+               +-------------------+
```

- **Login node**: lightweight control plane. Submit Slurm jobs, manage OpenWebUI, run file ingestion CLI. Never runs Ollama.
- **GPU service node**: secured Slurm allocation hosting `ollama serve` for Qwen3-235B and Qwen3-Embedding:8B. RAG jobs load the FlagEmbedding reranker from the shared HuggingFace cache (`~/.huggingface/models/bge-v2-gemma`).
- **RAG worker nodes**: CPU or GPU jobs executing RAG-Anything / LightRAG ingestion, retrieval, and knowledge-graph updates. They call Ollama endpoints via internal network.

## 2. Shared Storage & Paths

| Path | Purpose | Owner | Notes |
| --- | --- | --- | --- |
| `/ShareS/UserHome/user007/software/RAG-Anything` | Repo checkout & uv env | login node | Mounted read-write on GPU nodes.
| `/ShareS/UserHome/user007/.ollama` | Model cache | GPU nodes | Bind into Ollama job to avoid redownloads.
| `/ShareS/UserHome/user007/rag-data` | RAG corpora, vector stores, KG snapshots | All nodes | Ensure POSIX ACLs match Slurm user account.
| `$SCRATCH/rag-temp` | Large transient outputs | GPU/RAG jobs | Auto-clean by scheduler; optional.

Always verify mounts with `ls` after Slurm allocation: cluster variants occasionally expose different prefixes (e.g., `/lustre`). Adjust paths in scripts accordingly.

## 3. Control & Data Flow

1. **Corpus ingestion (login node)**
   - Stage documents under `/ShareS/.../rag-data/input`.
   - Submit ingestion job (Phase P2 script) targeting CPU node. Job calls LightRAG graph builder & embedding pipeline.

2. **Embedding generation (GPU service node)**
   - Ollama host exposes `/api/embeddings` with `qwen3-embedding:8b`.
   - Ingestion job batches documents, hits embedding endpoint, writes vectors to FAISS or Milvus store under `rag-data/vector_store`.

3. **Knowledge graph update (RAG worker)**
   - LightRAG `kg_builder` consumes embeddings & metadata, updates graph DB (e.g., `kg.sqlite`).

4. **Query path (WebUI or CLI)**
   - User query enters OpenWebUI on login node.
   - UI calls backend retrieval service located on login node or CPU node.
   - Service fetches top-k chunks, optionally punts to reranker endpoint (see §5).
   - Final context forwarded to `qwen3:235b` via Ollama `/api/chat` for response; reply streamed back to UI/user.

## 4. Slurm Workflows

### 4.1 Persistent Ollama Service Job (Recommended)

Create a Slurm job (Phase P2 `ollama_gpu_job.sh`) that:
- Requests 1× V100 GPU, appropriate RAM (e.g., 80 GB), and walltime (e.g., 24h).
- Binds `${OLLAMA_HOME:-$HOME/.ollama}` as writable volume.
- Ensures `${HOME}/.huggingface/models/bge-v2-gemma` is readable on the GPU node so RAG workers can reuse the FlagEmbedding reranker without another download.
- Runs `source ~/setup/ollama.sh` then `ollama serve --host 0.0.0.0 --port 11434`.

Submit with `sbatch --parsable scripts/slurm/ollama_gpu_job.sh`. Capture job ID and publish host/port to shared file `rag-data/runtime/ollama_service.json` for RAG workers to consume.

### 4.2 Interactive Debug Session (Fallback)

When iterating:

```
$ salloc -p V100 -N 1 --time=02:00:00
$ ssh $SLURM_NODELIST
$ source ~/setup/ollama.sh
$ ollama serve --host 0.0.0.0 --port 11434
```

Launch a second terminal on login node to run tests against the temporary endpoint. Remember to `scancel` after experimentation.

### 4.3 RAG Worker Submission

Use P2 `rag_worker_job.sh` template to queue ingestion/query tasks. Export:

```
export OLLAMA_HOST="http://$(cat rag-data/runtime/ollama_service.json | jq -r .host):11434"
export OLLAMA_EMBED_MODEL="qwen3-embedding:8b"
export OLLAMA_GENERATE_MODEL="qwen3:235b"
export RERANKER_MODEL_PATH="$HOME/.huggingface/models/bge-v2-gemma"
export RERANKER_USE_FP16=1
```

Jobs call the cluster RAG worker script:

```bash
# Ingestion mode
uv run python scripts/cluster_rag_worker.py --mode ingest --input-file /path/to/document.pdf

# Query mode
uv run python scripts/cluster_rag_worker.py --mode query --query "What are the findings?"
```

See `configs/cluster.yaml.example` for all configuration options and `orchestration.md` for detailed submission examples.

## 5. Reranker Implementation (FlagEmbedding)

- Use FlagEmbedding's `FlagLLMReranker` with the locally cached HuggingFace model at `~/.huggingface/models/bge-v2-gemma` (downloaded via `hf download BAAI/bge-reranker-v2-gemma --local-dir ~/.huggingface/models/bge-v2-gemma`).
- Keep the path on the shared filesystem so every RAG worker sees the same weights without re-downloading.
- Sample Python bootstrap (inside the `raganything` uv/venv):

```
from FlagEmbedding import FlagLLMReranker

reranker = FlagLLMReranker("~/.huggingface/models/bge-v2-gemma", use_fp16=True)
score = reranker.compute_score(["查询", "候选文档"])
```

- Expose `RERANKER_MODEL_PATH` and `RERANKER_USE_FP16` via environment or config so retrieval code can instantiate the reranker lazily. Default to FP16 on GPU nodes; fall back to CPU if GPUs busy.
- Retrieval pipeline should call the FlagEmbedding reranker directly rather than `/api/rerank`. Maintain compatibility by bypassing rerank stage when `RERANKER_MODEL_PATH` is unset.

## 6. Environment Variables & Secrets

| Variable | Scope | Description |
| --- | --- | --- |
| `OLLAMA_HOST` | RAG workers | Base URL to GPU service node (`http://gpu123:11434`). |
| `OLLAMA_GENERATE_MODEL` | RAG workers / UI | Default LLM (`qwen3:235b`). |
| `OLLAMA_EMBED_MODEL` | Ingestion jobs | Embedding model (`qwen3-embedding:8b`). |
| `RERANKER_MODEL_PATH` | Retrieval jobs | HuggingFace path (e.g., `$HOME/.huggingface/models/bge-v2-gemma`). |
| `RERANKER_USE_FP16` | Retrieval jobs | `1` to enable fp16 execution when GPU available; unset to force fp32. |
| `RAG_SHARED_ROOT` | All nodes | Root path for corpora and caches (e.g., `/ShareS/.../rag-data`). |
| `RAG_RUNTIME_STATE` | All nodes | Directory storing `ollama_service.json`, lock files, metrics. |
| `LIGHTRAG_GRAPH_PATH` | RAG workers | Location of graph database. |

Store sensitive API keys (for fallback online models) in `~/.config/raganything/secrets.env` and source inside jobs. Do **not** bake secrets into scripts.

## 7. Networking & Security Guardrails

- Ensure cluster firewall allows HTTP between GPU nodes and login node subnet; restrict to cluster CIDR via `--host 0.0.0.0 --allowed-origins <cidr>` once supported.
- Use reverse SSH tunnel when exposing to OpenWebUI running on login node: `ssh -L 11434:localhost:11434 gpu-node`.
- Rotate job tokens stored under `rag-data/runtime` each time job restarts to avoid stale endpoints.
- Avoid binding Ollama to 127.0.0.1 on GPU node; login node must connect remotely.

## 8. Operational Checklist

1. Validate model cache exists on shared storage before submitting job.
2. Run `sbatch --test-only scripts/slurm/ollama_gpu_job.sh` (Phase P2) to verify parameters.
3. Update OpenWebUI backend env with fresh `OLLAMA_HOST` plus `RERANKER_MODEL_PATH`.
4. Confirm LightRAG graph syncs after ingestion by checking `rag-data/runtime/graph.log`.
5. Document reranker availability to end-users (UI toggle, CLI flag).

## 9. Rollback & Recovery

- If GPU job fails, `scancel <job-id>` and delete `rag-data/runtime/ollama_service.json`.
- Maintain previous configs in Git; revert doc or scripts via `git checkout HEAD~1 -- <file>` if misconfiguration is introduced.
- Always provide temporary fallback to base retrieval (skip reranker) by unsetting `RERANKER_MODEL_PATH`.

## 10. Open Questions / Follow-ups

- Confirm cluster policy on long-lived jobs; may require QoS or reservation.
- Monitor FlagEmbedding memory footprint; adjust FP16/FP32 settings per node capacity.
- Evaluate whether LightRAG graph storage should move to dedicated database service under `/ShareS` or remain SQLite.

---

This blueprint satisfies Phase P1 exit criteria: clear control/data flow, HPC constraints, concrete FlagEmbedding reranker guidance, and step-by-step Slurm guidance.
