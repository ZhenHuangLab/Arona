# RAG-Anything v2.0 - New Architecture

> **Custom Frontend/Backend Architecture** replacing OpenWebUI integration

> ⚠️ Note: This file is kept as a historical design note. The current, maintained
> startup/config instructions are in `README.md` (React/Vite frontend + FastAPI backend).

## 🎯 What's New

- ✅ **Custom React Frontend** - Clean, simple UI for document upload and queries
- ✅ **FastAPI Backend** - Production-ready REST API
- ✅ **Flexible Model Providers** - Support for OpenAI, Azure, LM Studio, vLLM, and any OpenAI-compatible API
- ✅ **No Ollama Dependency** - Use any LLM provider via base_url + api_key
- ✅ **Unified Configuration** - Environment variables or YAML files
- ✅ **Type-Safe** - Pydantic validation throughout
- ✅ **Async-Native** - High performance with async/await

## 🚀 Quick Start (5 Minutes)

### 1. Install Dependencies

```bash
# Backend (recommended)
uv sync

# Frontend
cd frontend
npm install
cd ..
```

### 2. Configure Environment

**Unified Configuration (Recommended):**
```bash
cp env.example .env
```

Edit `.env` with your API keys:

```bash
# Minimal OpenAI configuration
LLM_PROVIDER=openai
LLM_MODEL_NAME=gpt-4o-mini
LLM_API_KEY=sk-your-api-key-here

EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL_NAME=text-embedding-3-large
EMBEDDING_API_KEY=sk-your-api-key-here
EMBEDDING_EMBEDDING_DIM=3072
```

**Frontend Configuration (Optional):** see `frontend/env.example` (only `VITE_` vars are exposed to the browser)

> Tip: dev 模式下前端默认走 Vite proxy，一般无需配置 `VITE_BACKEND_URL`。

### 3. Start Services

```bash
# Start both backend and frontend
bash scripts/start_all.sh
```

### 4. Open Browser

- **Frontend**: http://localhost:5173
- **API Docs**: http://localhost:8000/docs

## 📁 Project Structure

```
RAG-Anything/
├── backend/              # FastAPI backend
│   ├── config.py        # Unified configuration
│   ├── main.py          # API server
│   ├── models/          # Pydantic models
│   ├── providers/       # Model provider adapters
│   ├── routers/         # API endpoints
│   └── services/        # Business logic
├── frontend/            # React + Vite UI
├── configs/             # Configuration examples
├── docs/                # Documentation
└── scripts/             # Deployment scripts
```

## 🔧 Supported Providers

### OpenAI

```bash
LLM_PROVIDER=openai
LLM_MODEL_NAME=gpt-4o-mini
LLM_API_KEY=sk-...
```

### Azure OpenAI

```bash
LLM_PROVIDER=azure
LLM_MODEL_NAME=gpt-4o-mini
LLM_API_KEY=your-azure-key
LLM_BASE_URL=https://your-resource.openai.azure.com/
```

### LM Studio (Local)

```bash
LLM_PROVIDER=local
LLM_MODEL_NAME=local-model
LLM_BASE_URL=http://localhost:1234/v1
```

### Custom API (vLLM, TGI, etc.)

```bash
LLM_PROVIDER=custom
LLM_MODEL_NAME=Qwen/Qwen2.5-72B-Instruct
LLM_API_KEY=your-key
LLM_BASE_URL=https://your-endpoint.com/v1
```

## 📚 Documentation

- **[Quick Start Guide](docs/QUICKSTART_NEW_ARCHITECTURE.md)** - Get started in 5 minutes
- **[Architecture Details](docs/ARCHITECTURE_REDESIGN.md)** - Detailed architecture documentation
- **[Implementation Summary](docs/IMPLEMENTATION_SUMMARY.md)** - What was built and why

## 🎨 Features

### Frontend (Gradio)

- 📄 **Document Upload** - Upload PDF, DOCX, PPTX, XLSX, TXT, MD, HTML
- 💬 **Chat Interface** - Ask questions with conversation history
- ⚙️ **Configuration Panel** - View backend configuration
- 🔍 **Query Modes** - Naive, Local, Global, Hybrid

### Backend (FastAPI)

- 📤 **Document Management** - Upload, process, batch processing
- 🔍 **Query API** - Standard, multimodal, conversational queries
- 🏥 **Health Checks** - Status and readiness endpoints
- 📖 **Auto-Generated Docs** - OpenAPI/Swagger at `/docs`

## 🔌 API Endpoints

### Documents

- `POST /api/documents/upload` - Upload document
- `POST /api/documents/process` - Process document
- `POST /api/documents/upload-and-process` - Upload and process
- `POST /api/documents/batch-process` - Batch process folder
- `GET /api/documents/list` - List documents

### Query

- `POST /api/query/` - Execute RAG query
- `POST /api/query/multimodal` - Multimodal query
- `POST /api/query/conversation` - Conversational query

### Health

- `GET /health` - Health check
- `GET /ready` - Readiness check

## 🏗️ Architecture

```
┌─────────────────┐
│  React UI       │  Frontend (Port 5173)
└────────┬────────┘
         │ HTTP/REST
         ▼
┌─────────────────┐
│  FastAPI        │  Backend (Port 8000)
│  - Routers      │
│  - Services     │
│  - Providers    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  RAGAnything    │  Core Library
│  - LightRAG     │
│  - MineRU       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  LLM APIs       │  External Services
│  - OpenAI       │
│  - Azure        │
│  - Custom       │
└─────────────────┘
```

## 🔄 Migration from Old Architecture

### What Changed

- ❌ Removed OpenWebUI integration
- ❌ Removed Ollama-specific code
- ✅ Added FastAPI backend
- ✅ Added React frontend (migrated from Gradio)
- ✅ Added unified configuration

### What Stayed the Same

- ✅ Core RAGAnything library
- ✅ Document processing (MineRU/Docling)
- ✅ LightRAG integration
- ✅ Query modes (Naive/Local/Global/Hybrid)

## 🛠️ Development

### Start Backend Only

```bash
bash scripts/start_backend.sh
```

### Start Frontend Only

```bash
bash scripts/start_frontend.sh
```

### Enable Auto-Reload (Development)

```bash
python -m backend.main --reload
```

## 🧪 Testing

### Test Backend Health

```bash
curl http://localhost:8000/health
```

### Test Document Upload

```bash
curl -X POST http://localhost:8000/api/documents/upload-and-process \
  -F "file=@document.pdf"
```

### Test Query

```bash
curl -X POST http://localhost:8000/api/query/ \
  -H "Content-Type: application/json" \
  -d '{"query": "What is this about?", "mode": "hybrid"}'
```

## 📝 Configuration Examples

See `configs/model_providers.yaml` for complete examples:

- OpenAI configuration
- Azure OpenAI configuration
- LM Studio (local) configuration
- Mixed providers configuration
- Custom API configuration

## 🤝 Contributing

The new architecture is designed to be extensible:

1. **Add new providers**: Implement `BaseLLMProvider` in `backend/providers/`
2. **Add new endpoints**: Create routers in `backend/routers/`
3. **Customize frontend**: Edit `frontend/app.py`

## 📄 License

Same as RAG-Anything main project.

## 🙏 Acknowledgments

- **RAGAnything** - Core multimodal RAG library
- **LightRAG** - Knowledge graph RAG framework
- **FastAPI** - Modern async web framework
- **Gradio** - ML/AI web interface framework

---

**Ready to get started?** See [Quick Start Guide](docs/QUICKSTART_NEW_ARCHITECTURE.md)
