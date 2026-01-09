# RAG-Anything Architecture Redesign

## Overview

This document describes the redesigned RAG-Anything architecture that replaces OpenWebUI with a custom frontend/backend solution.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (Gradio)                        │
│  - Document Upload UI                                        │
│  - Chat Interface                                            │
│  - Configuration Panel                                       │
│  - Results Visualization                                     │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP/REST API
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  Backend (FastAPI)                           │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  API Layer (Routers)                                 │   │
│  │  - /api/documents  (upload, process, batch)          │   │
│  │  - /api/query      (query, multimodal, conversation) │   │
│  │  - /health         (status, readiness)               │   │
│  └──────────────────────┬──────────────────────────────┘   │
│                         │                                    │
│  ┌──────────────────────▼──────────────────────────────┐   │
│  │  Service Layer                                       │   │
│  │  - RAGService (manages RAGAnything instances)        │   │
│  │  - ModelFactory (creates model providers)            │   │
│  └──────────────────────┬──────────────────────────────┘   │
│                         │                                    │
│  ┌──────────────────────▼──────────────────────────────┐   │
│  │  Model Providers (Abstraction Layer)                 │   │
│  │  - OpenAI/Azure/Custom API providers                 │   │
│  │  - Unified interface for LLM/Vision/Embedding        │   │
│  └──────────────────────┬──────────────────────────────┘   │
└─────────────────────────┼────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              RAGAnything Core Library                        │
│  - Document Processing (MineRU/Docling)                     │
│  - Multimodal Processing (Images/Tables/Equations)          │
│  - LightRAG Integration (Knowledge Graph)                   │
│  - Query Engine (Naive/Local/Global/Hybrid)                 │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              External Services                               │
│  - LLM API (OpenAI/Azure/Custom)                            │
│  - Embedding API (OpenAI/Azure/Custom)                      │
│  - Vision API (OpenAI/Azure/Custom)                         │
│  - Local Reranker (FlagEmbedding)                           │
└─────────────────────────────────────────────────────────────┘
```

## Key Design Decisions

### 1. **Separation of Concerns**

- **Frontend**: Pure UI layer, no business logic
- **Backend**: API layer + business logic + model abstraction
- **Core**: RAGAnything library remains unchanged

### 2. **Model Provider Abstraction**

**Problem**: Current code is tightly coupled to Ollama.

**Solution**: Abstract provider interface supporting multiple backends:

```python
# Before (Ollama-specific)
from raganything.clients.ollama import OllamaClient
client = OllamaClient(base_url="http://localhost:11434")

# After (Provider-agnostic)
from backend.config import ModelConfig, ProviderType
config = ModelConfig(
    provider=ProviderType.OPENAI,
    model_name="gpt-4o-mini",
    api_key="sk-...",
    base_url="https://api.openai.com/v1"
)
llm_func = ModelFactory.create_llm_func(config)
```

### 3. **Configuration Management**

**Unified configuration** via environment variables or YAML:

- **Environment variables**: For production deployment
- **YAML files**: For development and testing
- **Backward compatible**: Existing Ollama configs still work

### 4. **Technology Stack**

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Backend | FastAPI | Async-native, excellent for RAG workloads, already in use |
| Frontend | Gradio | Fastest to implement, built for ML/AI apps, auto-generates API |
| Model Abstraction | Custom providers | Flexibility to support any OpenAI-compatible API |
| Configuration | Pydantic + YAML | Type-safe, validated, easy to use |

## Project Structure

```
RAG-Anything/
├── backend/                  # NEW: Backend API service
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Unified model provider config
│   ├── models/              # Pydantic request/response models
│   ├── routers/             # API route handlers
│   ├── services/            # Business logic
│   └── providers/           # Model provider adapters
├── frontend/                # NEW: Gradio frontend
│   └── app.py              # Gradio UI definition
├── raganything/            # UNCHANGED: Core library
├── configs/                # Configuration files
│   └── model_providers.yaml
├── scripts/                # Deployment scripts
│   ├── start_backend.sh
│   ├── start_frontend.sh
│   └── start_all.sh
└── .env.backend.example    # Environment template
```

## Migration Path

### Phase 1: Backend Setup ✅ (Completed)

- [x] Create unified configuration system
- [x] Implement model provider abstraction
- [x] Build FastAPI backend with REST API
- [x] Create RAG service wrapper

### Phase 2: Frontend Development ✅ (Completed)

- [x] Create Gradio UI
- [x] Implement document upload interface
- [x] Implement chat interface
- [x] Add configuration panel

### Phase 3: Testing & Deployment (Next Steps)

- [ ] Test with different model providers
- [ ] Add error handling and validation
- [ ] Create Docker deployment
- [ ] Write integration tests
- [ ] Update documentation

### Phase 4: Deprecation (Future)

- [ ] Mark OpenWebUI integration as deprecated
- [ ] Provide migration guide
- [ ] Remove Ollama-specific code (optional)

## Configuration Examples

### Example 1: OpenAI

```bash
# .env.backend
LLM_PROVIDER=openai
LLM_MODEL_NAME=gpt-4o-mini
LLM_API_KEY=sk-...
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL_NAME=text-embedding-3-large
EMBEDDING_API_KEY=sk-...
EMBEDDING_EMBEDDING_DIM=3072
```

### Example 2: Azure OpenAI

```bash
LLM_PROVIDER=azure
LLM_MODEL_NAME=gpt-4o-mini
LLM_API_KEY=your-azure-key
LLM_BASE_URL=https://your-resource.openai.azure.com/
EMBEDDING_PROVIDER=azure
EMBEDDING_MODEL_NAME=text-embedding-3-large
EMBEDDING_API_KEY=your-azure-key
EMBEDDING_BASE_URL=https://your-resource.openai.azure.com/
EMBEDDING_EMBEDDING_DIM=3072
```

### Example 3: LM Studio (Local)

```bash
LLM_PROVIDER=local
LLM_MODEL_NAME=local-model
LLM_API_KEY=not-needed
LLM_BASE_URL=http://localhost:1234/v1
EMBEDDING_PROVIDER=local
EMBEDDING_MODEL_NAME=nomic-embed-text
EMBEDDING_API_KEY=not-needed
EMBEDDING_BASE_URL=http://localhost:1234/v1
EMBEDDING_EMBEDDING_DIM=768
```

### Example 4: Mixed Providers

```bash
# Use OpenAI for LLM, local for embedding
LLM_PROVIDER=openai
LLM_MODEL_NAME=gpt-4o-mini
LLM_API_KEY=sk-...
EMBEDDING_PROVIDER=local
EMBEDDING_MODEL_NAME=bge-m3
EMBEDDING_BASE_URL=http://localhost:11434/v1
EMBEDDING_EMBEDDING_DIM=1024
```

### Example 5: Local GPU Embedding (Task 7)

```bash
# NOTE:
# - EMBEDDING_PROVIDER=local means an OpenAI-compatible HTTP server (LM Studio, Ollama, vLLM, etc.)
# - EMBEDDING_PROVIDER=local_gpu means in-process GPU inference (HuggingFace / sentence-transformers)

# Text embedding on GPU 0
EMBEDDING_PROVIDER=local_gpu
EMBEDDING_MODEL_NAME=Qwen/Qwen3-Embedding-4B
EMBEDDING_EMBEDDING_DIM=2560
EMBEDDING_DEVICE=cuda:0
EMBEDDING_DTYPE=float16
EMBEDDING_ATTN_IMPLEMENTATION=sdpa

# Optional: dynamic batching
EMBEDDING_MAX_BATCH_SIZE=32
EMBEDDING_MAX_WAIT_TIME=0.1
EMBEDDING_MAX_BATCH_TOKENS=16384
EMBEDDING_ENCODE_BATCH_SIZE=128

# Local GPU reranker on GPU 1
RERANKER_ENABLED=true
RERANKER_PROVIDER=local_gpu
RERANKER_MODEL_NAME=Qwen/Qwen3-Reranker-4B
RERANKER_DEVICE=cuda:1
RERANKER_DTYPE=float16
RERANKER_ATTN_IMPLEMENTATION=sdpa
RERANKER_BATCH_SIZE=16
```

## API Endpoints

### Document Management

- `POST /api/documents/upload` - Upload a document
- `POST /api/documents/process` - Process uploaded document
- `POST /api/documents/upload-and-process` - Upload and process in one step
- `POST /api/documents/batch-process` - Process multiple documents
- `GET /api/documents/list` - List uploaded documents

### Query

- `POST /api/query/` - Execute RAG query
- `POST /api/query/multimodal` - Execute multimodal query
- `POST /api/query/conversation` - Conversational query with history

### Health

- `GET /health` - Health check with configuration
- `GET /ready` - Readiness check

## Deployment

### Development

```bash
# 1. Configure environment
cp .env.backend.example .env.backend
# Edit .env.backend with your API keys

# 2. Start backend
bash scripts/start_backend.sh

# 3. Start frontend (in another terminal)
bash scripts/start_frontend.sh

# Or start both together
bash scripts/start_all.sh
```

### Production

See `docker/docker-compose.yml` for containerized deployment.

## Benefits of New Architecture

1. **Flexibility**: Support any OpenAI-compatible API
2. **Simplicity**: No Ollama dependency, cleaner code
3. **Maintainability**: Clear separation of concerns
4. **Extensibility**: Easy to add new providers
5. **Testability**: Each layer can be tested independently
6. **Performance**: Async-native throughout the stack

## Backward Compatibility

The core `raganything` library remains unchanged. Existing scripts using RAGAnything directly will continue to work.

## Next Steps

1. **Test the implementation** with your preferred model providers
2. **Customize the frontend** to match your requirements
3. **Deploy to production** using the provided scripts
4. **Provide feedback** for improvements
