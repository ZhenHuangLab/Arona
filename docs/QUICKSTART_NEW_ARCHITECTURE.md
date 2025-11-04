# Quick Start: New RAG-Anything Architecture

This guide will help you get started with the redesigned RAG-Anything architecture in 5 minutes.

## Prerequisites

- Python 3.9+
- API key for your chosen LLM provider (OpenAI, Azure, etc.)
- (Optional) Local reranker model downloaded

## Step 1: Install Dependencies

```bash
# Install backend dependencies
pip install fastapi uvicorn pydantic pyyaml

# Install frontend dependencies
pip install gradio

# Install RAGAnything (if not already installed)
pip install -e .
```

## Step 2: Configure Environment

```bash
# Copy example environment file
cp .env.backend.example .env.backend

# Edit .env.backend with your configuration
nano .env.backend
```

### Minimal Configuration (OpenAI)

```bash
# LLM Configuration
LLM_PROVIDER=openai
LLM_MODEL_NAME=gpt-4o-mini
LLM_API_KEY=sk-your-api-key-here

# Embedding Configuration
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL_NAME=text-embedding-3-large
EMBEDDING_API_KEY=sk-your-api-key-here
EMBEDDING_EMBEDDING_DIM=3072

# Optional: Vision Model
VISION_PROVIDER=openai
VISION_MODEL_NAME=gpt-4o
VISION_API_KEY=sk-your-api-key-here

# Optional: Reranker (disable if not using)
RERANKER_ENABLED=false
```

## Step 3: Start the Backend

```bash
# Make scripts executable
chmod +x scripts/start_backend.sh scripts/start_frontend.sh scripts/start_all.sh

# Start backend server
bash scripts/start_backend.sh
```

You should see:

```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

## Step 4: Start the Frontend

In a new terminal:

```bash
# Start frontend
bash scripts/start_frontend.sh
```

You should see:

```
Starting RAG-Anything frontend on 0.0.0.0:7860
Backend URL: http://localhost:8000
Running on local URL:  http://0.0.0.0:7860
```

## Step 5: Use the Interface

1. **Open your browser** to `http://localhost:7860`

2. **Upload a document**:
   - Go to "Document Upload" tab
   - Select a PDF, DOCX, or other supported file
   - Click "Upload & Process"
   - Wait for processing to complete

3. **Ask questions**:
   - Go to "Query" tab
   - Select query mode (Hybrid recommended)
   - Type your question
   - Click "Ask" or press Enter

## Alternative: Start Both Together

```bash
# Start both backend and frontend
bash scripts/start_all.sh
```

## Testing the API Directly

### Health Check

```bash
curl http://localhost:8000/health
```

### Upload and Process Document

```bash
curl -X POST http://localhost:8000/api/documents/upload-and-process \
  -F "file=@/path/to/your/document.pdf" \
  -F "parse_method=auto"
```

### Query

```bash
curl -X POST http://localhost:8000/api/query/ \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the main topic of the document?",
    "mode": "hybrid"
  }'
```

## Configuration Examples

### Using Azure OpenAI

```bash
# .env.backend
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

### Using LM Studio (Local Models)

```bash
# 1. Start LM Studio server on port 1234

# 2. Configure .env.backend
LLM_PROVIDER=local
LLM_MODEL_NAME=local-model
LLM_API_KEY=not-needed
LLM_BASE_URL=http://localhost:1234/v1

EMBEDDING_PROVIDER=local
EMBEDDING_MODEL_NAME=nomic-embed-text
EMBEDDING_API_KEY=not-needed
EMBEDDING_BASE_URL=http://localhost:1234/v1
EMBEDDING_EMBEDDING_DIM=768

RERANKER_ENABLED=false
```

### Using Custom API (vLLM, TGI, etc.)

```bash
LLM_PROVIDER=custom
LLM_MODEL_NAME=Qwen/Qwen2.5-72B-Instruct
LLM_API_KEY=your-custom-key
LLM_BASE_URL=https://your-vllm-endpoint.com/v1

EMBEDDING_PROVIDER=custom
EMBEDDING_MODEL_NAME=BAAI/bge-large-en-v1.5
EMBEDDING_API_KEY=your-custom-key
EMBEDDING_BASE_URL=https://your-embedding-endpoint.com/v1
EMBEDDING_EMBEDDING_DIM=1024
```

## Enabling Reranker

RAG-Anything supports both local and API-based rerankers to improve retrieval quality.

### Option 1: Local Reranker (FlagEmbedding)

Use a local reranker model for offline deployment:

```bash
# 1. Download reranker model
mkdir -p ~/.huggingface/models
cd ~/.huggingface/models
git clone https://huggingface.co/BAAI/bge-reranker-v2-gemma

# 2. Configure in .env.backend
RERANKER_ENABLED=true
RERANKER_PROVIDER=local
RERANKER_MODEL_PATH=~/.huggingface/models/bge-reranker-v2-gemma
RERANKER_USE_FP16=false
RERANKER_BATCH_SIZE=16
```

### Option 2: API-based Reranker

Use cloud-based reranker APIs for better performance and no local GPU requirements.

#### Jina AI Reranker

```bash
# Configure in .env.backend
RERANKER_ENABLED=true
RERANKER_PROVIDER=api
RERANKER_MODEL_NAME=jina-reranker-v2-base-multilingual
RERANKER_API_KEY=jina_xxxxxxxxxxxxx
RERANKER_BASE_URL=https://api.jina.ai/v1/rerank  # Optional: auto-detected
RERANKER_BATCH_SIZE=16
```

**Get API Key**: [https://jina.ai/](https://jina.ai/)

#### Cohere Reranker

```bash
# Configure in .env.backend
RERANKER_ENABLED=true
RERANKER_PROVIDER=api
RERANKER_MODEL_NAME=rerank-english-v3.0
RERANKER_API_KEY=your-cohere-api-key
RERANKER_BASE_URL=https://api.cohere.ai/v1/rerank  # Optional: auto-detected
RERANKER_BATCH_SIZE=16
```

**Get API Key**: [https://cohere.com/](https://cohere.com/)

**Available Models**:
- `rerank-english-v3.0` - Best for English
- `rerank-multilingual-v3.0` - Supports 100+ languages

#### Voyage AI Reranker

```bash
# Configure in .env.backend
RERANKER_ENABLED=true
RERANKER_PROVIDER=api
RERANKER_MODEL_NAME=rerank-lite-1
RERANKER_API_KEY=your-voyage-api-key
RERANKER_BASE_URL=https://api.voyageai.com/v1/rerank  # Optional: auto-detected
RERANKER_BATCH_SIZE=16
```

**Get API Key**: [https://www.voyageai.com/](https://www.voyageai.com/)

**Available Models**:
- `rerank-lite-1` - Fast and cost-effective
- `rerank-1` - Higher accuracy

### Comparison: Local vs API Reranker

| Feature | Local Reranker | API Reranker |
|---------|---------------|--------------|
| **Setup** | Download model (~2-5GB) | Just API key |
| **Cost** | Free (after download) | Pay per request |
| **Speed** | Depends on GPU | Usually faster |
| **Privacy** | Data stays local | Data sent to API |
| **GPU Required** | Yes (recommended) | No |
| **Offline** | Yes | No |

### Disabling Reranker

To disable reranking entirely:

```bash
RERANKER_ENABLED=false
```

## Troubleshooting

### Backend won't start

**Error**: `ModuleNotFoundError: No module named 'backend'`

**Solution**: Make sure you're running from the project root directory.

### Frontend can't connect to backend

**Error**: `❌ Cannot connect to backend at http://localhost:8000`

**Solution**: 
1. Check backend is running: `curl http://localhost:8000/health`
2. Check `BACKEND_URL` environment variable
3. Check firewall settings

### Document processing fails

**Error**: `Failed to process document`

**Solution**:
1. Check document format is supported
2. Check MineRU/Docling is installed correctly
3. Check backend logs for detailed error

### Query returns error

**Error**: `Query failed with status 500`

**Solution**:
1. Check API keys are correct
2. Check model names are valid
3. Check backend logs for detailed error
4. Verify you have processed at least one document

## Next Steps

- Read [ARCHITECTURE_REDESIGN.md](./ARCHITECTURE_REDESIGN.md) for detailed architecture
- Explore API documentation at `http://localhost:8000/docs`
- Customize frontend in `frontend/app.py`
- Add custom model providers in `backend/providers/`

## Getting Help

- Check backend logs for errors
- Visit API docs: `http://localhost:8000/docs`
- Check configuration: `http://localhost:8000/health`

