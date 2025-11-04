# Cluster Configuration Reference

This guide explains how Phase P3 wires the configuration knobs that control
Ollama-backed generation/embeddings and the local FlagEmbedding reranker. The
intent is to keep configuration deterministic so the login node, GPU nodes, and
worker jobs all agree on the same runtime values without editing code.

## 1. Environment Variables

Set these variables in your login shell **before** submitting Slurm jobs. They
are read by `RAGAnythingConfig`, which in turn drives the default Ollama client
and reranker instantiation inside `raganything/raganything.py`.

| Variable | Default | Purpose |
| --- | --- | --- |
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | Fully qualified URL for the running Ollama service (same as the JSON published by `ollama_gpu_job.sh`). |
| `OLLAMA_LLM_MODEL` / `OLLAMA_GENERATE_MODEL` | `qwen3:235b` | Model tag used for chat/generation requests. The legacy key is still honoured for backward compatibility. |
| `OLLAMA_EMBED_MODEL` / `OLLAMA_EMBEDDING_MODEL` | `qwen3-embedding:8b` | Model tag used for embeddings. |
| `OLLAMA_EMBED_DIM` | `8192` | Expected embedding dimensionality (used when constructing `EmbeddingFunc`). Override if you switch embedding models. |
| `OLLAMA_TIMEOUT_SECONDS` | `300` | HTTP timeout for each Ollama request. Increase for cold starts on slower disks. |
| `OLLAMA_MAX_RETRIES` | `2` | Number of retry attempts for network hiccups or `5xx` responses. |
| `OLLAMA_RETRY_BACKOFF` | `0.5` | Exponential backoff base (seconds) between retries. |
| `RERANKER_MODEL_PATH` | *(empty)* | Absolute path to the FlagEmbedding weight directory (e.g. `$HOME/.huggingface/models/bge-v2-gemma`). |
| `RERANKER_USE_FP16` | `false` | Enables fp16 mode when GPUs are available. Leave `false` on pure CPU workers. |
| `RERANKER_BATCH_SIZE` | `16` | Number of documents scored per rerank batch to balance memory use and throughput. |
| `ENABLE_RERANK` | `true` | Global toggle; when `true` and the model path exists, LightRAG reranks chunk candidates automatically. |

> **Tip:** the login node can export these variables and then call
> `sbatch --export=ALL` to pass them into the GPU and worker jobs. The scripts in
> Phase P2 expect the same variable names, so keeping them consistent avoids
> drift between documentation, environment, and code.

## 2. Default Model Wiring

When you instantiate `RAGAnything()` without manually supplying `llm_model_func`
or `embedding_func`, Phase P3 now constructs them automatically:

1. `raganything.clients.ollama.OllamaClient` is created using the values above.
   - Chat requests go through `/api/chat` with retries and timeout enforcement.
   - Embedding requests use `/api/embeddings` and convert the result into a
     NumPy array with the configured dimensionality.
2. The helper functions are wrapped in `asyncio.to_thread` so LightRAG’s async
   pipeline can await them without blocking the event loop.
3. If you provide custom callables when constructing `RAGAnything`, they take
   precedence—existing workflows are untouched.

### Verifying the Bindings

```bash
uv run python - <<'PY'
from raganything import RAGAnything
rag = RAGAnything()
print(rag.config.ollama_base_url)
print(rag.config.ollama_llm_model)
print(rag.embedding_func.embedding_dim)
PY
```

Run the snippet on the login node after exporting the env vars; it should print
the values you expect without launching any network calls. Submit an ingestion
worker afterwards to exercise the endpoints on the GPU node.

## 3. FlagEmbedding Reranker

`ENABLE_RERANK=true` and a valid `RERANKER_MODEL_PATH` trigger the lazy loader in
`raganything/rerankers/flagembedding.py`:

1. The wrapper checks that the path exists (use the shared home directory so all
   nodes can read the cached weights).
2. The first query loads `FlagLLMReranker` inside the worker process.
3. Scores are produced in batches to minimise per-request overhead, and the
   LightRAG `QueryParam.enable_rerank` flag is enabled automatically.

If `ENABLE_RERANK=true` but the weights directory is missing, the config module
logs a warning and disables reranking for the session so queries continue with
their prior behaviour.

### Smoke Test

```bash
uv run python - <<'PY'
from raganything.rerankers.flagembedding import FlagEmbeddingReranker
reranker = FlagEmbeddingReranker("$HOME/.huggingface/models/bge-v2-gemma", use_fp16=False)
scores = reranker.score("测试查询", ["候选文档 A", "候选文档 B"])
print(scores)
PY
```

The test can run on a login node as long as the HuggingFace cache was populated
earlier (mirrors the user-provided snippet). Expect two floats in descending
order—no Slurm allocation required.

## 4. Failure Modes & Mitigations

- **Ollama hostname mismatch:** ensure the JSON file dropped by the GPU job
  (`${RAG_RUNTIME_STATE}/ollama_service.json`) is readable and that
  `OLLAMA_BASE_URL` reuses the same host/IP.
- **Timeouts on cold start:** increase `OLLAMA_TIMEOUT_SECONDS` so the initial
  `ollama serve` warm-up completes before requests abort.
- **CPU-only reranker:** set `RERANKER_USE_FP16=0` when launching `rag_worker_job.sh`
  on CPU partitions; the adapter will fall back to fp32.
- **Model upgrades:** cancel the GPU job, pull the new models (`ollama pull …` or
  `hf download …`), and resubmit. The LightRAG clients pick up the changes on the
  next request because they read environment variables at startup.

With these settings in place, Phase P3 meets its exit criteria: the RAG pipeline
can run end-to-end using Ollama-hosted Qwen3 models, optionally reranks results
with FlagEmbedding, and keeps the configuration surface auditable for the whole
cluster team.
