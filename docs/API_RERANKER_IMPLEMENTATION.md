# API-based Reranker Implementation

## Overview

This document describes the implementation of API-based reranker support in RAG-Anything, enabling users to use cloud-based reranking services instead of local models.

## Implementation Summary

### Files Created

1. **`raganything/rerankers/api_reranker.py`** (300 lines)
   - Core implementation of API-based reranker
   - Supports multiple providers: Jina AI, Cohere, Voyage AI, OpenAI-compatible
   - Features:
     - Async HTTP client with connection pooling
     - Automatic retry logic with exponential backoff
     - Batch processing support
     - Provider auto-detection from model name or base URL
     - Comprehensive error handling

2. **`examples/test_api_reranker.py`** (180 lines)
   - Test script for all supported API rerankers
   - Demonstrates usage patterns
   - Validates configuration

3. **`examples/README_API_RERANKER.md`** (250 lines)
   - Comprehensive guide for API reranker usage
   - Configuration examples for all providers
   - Pricing and performance comparison
   - Troubleshooting guide
   - Migration guide from local reranker

4. **`docs/API_RERANKER_IMPLEMENTATION.md`** (this file)
   - Technical implementation details
   - Architecture overview

### Files Modified

1. **`raganything/rerankers/__init__.py`**
   - Added `APIReranker` to exports

2. **`backend/services/model_factory.py`**
   - Implemented `create_reranker()` for API provider
   - Added `_detect_reranker_provider()` helper method
   - Removed "TODO" placeholder

3. **`backend/services/rag_service.py`**
   - Fixed: Now passes `rerank_model_func` to RAGAnything instance

4. **`.env.backend`**
   - Added API reranker configuration section
   - Added examples for Jina, Cohere, Voyage providers

5. **`configs/model_providers.yaml`**
   - Added 3 new examples:
     - `jina_reranker_example`
     - `cohere_reranker_example`
     - `voyage_reranker_example`

6. **`docs/QUICKSTART_NEW_ARCHITECTURE.md`**
   - Expanded "Enabling Reranker" section
   - Added detailed API reranker configuration guide
   - Added comparison table: Local vs API reranker

## Architecture

### Class Hierarchy

```
APIReranker
├── provider: str (jina, cohere, voyage, openai)
├── model_name: str
├── api_key: str
├── base_url: Optional[str]
├── batch_size: int
├── timeout: float
├── max_retries: int
└── _client: httpx.AsyncClient
```

### Request Flow

```
User Query
    ↓
RAGAnything.aquery()
    ↓
LightRAG (retrieval)
    ↓
rerank_model_func(query, documents)
    ↓
APIReranker.score_async(query, documents)
    ↓
[Batch Processing]
    ↓
_score_batch() for each batch
    ↓
HTTP POST to API endpoint
    ↓
[Retry Logic if needed]
    ↓
_parse_response()
    ↓
Return scores: List[float]
```

### Provider-Specific Implementations

#### Jina AI

- **Endpoint**: `https://api.jina.ai/v1/rerank`
- **Request Format**:
  ```json
  {
    "model": "jina-reranker-v2-base-multilingual",
    "query": "search query",
    "documents": ["doc1", "doc2"],
    "top_n": 5
  }
  ```
- **Response Format**:
  ```json
  {
    "results": [
      {"index": 0, "relevance_score": 0.95},
      {"index": 1, "relevance_score": 0.87}
    ]
  }
  ```

#### Cohere

- **Endpoint**: `https://api.cohere.ai/v1/rerank`
- **Request Format**:
  ```json
  {
    "model": "rerank-english-v3.0",
    "query": "search query",
    "documents": ["doc1", "doc2"],
    "top_n": 5,
    "return_documents": false
  }
  ```
- **Response Format**: Same as Jina

#### Voyage AI

- **Endpoint**: `https://api.voyageai.com/v1/rerank`
- **Request Format**:
  ```json
  {
    "model": "rerank-lite-1",
    "query": "search query",
    "documents": ["doc1", "doc2"],
    "top_k": 5
  }
  ```
- **Response Format**:
  ```json
  {
    "data": [
      {"index": 0, "relevance_score": 0.95},
      {"index": 1, "relevance_score": 0.87}
    ]
  }
  ```

## Configuration

### Environment Variables

```bash
# Enable API reranker
RERANKER_ENABLED=true
RERANKER_PROVIDER=api

# Provider-specific settings
RERANKER_MODEL_NAME=jina-reranker-v2-base-multilingual
RERANKER_API_KEY=jina_xxxxxxxxxxxxx
RERANKER_BASE_URL=https://api.jina.ai/v1/rerank  # Optional

# Performance tuning
RERANKER_BATCH_SIZE=16  # Process 16 documents per API call
```

### Programmatic Usage

```python
from raganything.rerankers.api_reranker import APIReranker

# Create reranker
reranker = APIReranker(
    provider="jina",
    model_name="jina-reranker-v2-base-multilingual",
    api_key="jina_xxxxxxxxxxxxx",
    batch_size=16,
    timeout=30.0,
    max_retries=3,
)

# Use reranker
scores = await reranker.score_async(query, documents)

# Clean up
await reranker.close()
```

## Features

### 1. Automatic Provider Detection

The system automatically detects the provider from:
1. Base URL (e.g., "jina" in URL → Jina provider)
2. Model name (e.g., "jina-reranker" → Jina provider)
3. Falls back to OpenAI-compatible format

### 2. Retry Logic

- Automatic retry on transient failures (5xx errors)
- Exponential backoff: 1s, 2s, 4s
- No retry on client errors (4xx)
- Configurable max retries (default: 3)

### 3. Batch Processing

- Splits large document lists into batches
- Configurable batch size (default: 16)
- Reduces API calls and costs
- Prevents timeout on large batches

### 4. Connection Pooling

- Reuses HTTP connections via `httpx.AsyncClient`
- Configurable connection limits
- Automatic cleanup on close

### 5. Error Handling

- Validates API responses
- Handles missing or malformed scores
- Pads/truncates scores to match document count
- Provides detailed error messages

## Testing

### Unit Tests

Run the test script:

```bash
# Set API keys
export JINA_API_KEY="jina_xxxxxxxxxxxxx"
export COHERE_API_KEY="your-cohere-key"
export VOYAGE_API_KEY="your-voyage-key"

# Run tests
python examples/test_api_reranker.py
```

### Integration Tests

Test with backend:

```bash
# Configure .env.backend
RERANKER_ENABLED=true
RERANKER_PROVIDER=api
RERANKER_MODEL_NAME=jina-reranker-v2-base-multilingual
RERANKER_API_KEY=jina_xxxxxxxxxxxxx

# Start backend
python -m backend.main

# Test query endpoint
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is machine learning?", "mode": "hybrid"}'
```

## Performance Considerations

### Latency

- API rerankers add network latency (~100-500ms)
- Batch processing reduces total latency
- Consider using local reranker for latency-sensitive applications

### Cost

- Jina: ~$0.02 per 1K rerank requests
- Cohere: ~$1.00 per 1K searches (1K documents)
- Voyage: ~$0.05 per 1K rerank requests
- Local: Free (after model download)

### Throughput

- API rerankers scale automatically
- No GPU required
- Limited by API rate limits
- Batch processing improves throughput

## Limitations

1. **Network Dependency**: Requires internet connection
2. **Privacy**: Documents sent to third-party API
3. **Rate Limits**: Subject to provider rate limits
4. **Cost**: Pay-per-use pricing
5. **Latency**: Higher than local reranker

## Future Enhancements

1. **Caching**: Cache reranking results to reduce API calls
2. **Fallback**: Automatic fallback to local reranker on API failure
3. **More Providers**: Support for additional reranker APIs
4. **Streaming**: Stream reranking results for large batches
5. **Metrics**: Track API usage and costs

## Migration Guide

### From Local to API Reranker

1. **Backup configuration**:
   ```bash
   cp .env.backend .env.backend.backup
   ```

2. **Update configuration**:
   ```bash
   # Change RERANKER_PROVIDER from "local" to "api"
   # Add RERANKER_MODEL_NAME and RERANKER_API_KEY
   # Remove RERANKER_MODEL_PATH and RERANKER_USE_FP16
   ```

3. **Test configuration**:
   ```bash
   python examples/test_api_reranker.py
   ```

4. **Restart backend**:
   ```bash
   python -m backend.main
   ```

### From API to Local Reranker

1. **Download model**:
   ```bash
   mkdir -p ~/.huggingface/models
   cd ~/.huggingface/models
   git clone https://huggingface.co/BAAI/bge-reranker-v2-gemma
   ```

2. **Update configuration**:
   ```bash
   RERANKER_PROVIDER=local
   RERANKER_MODEL_PATH=~/.huggingface/models/bge-reranker-v2-gemma
   RERANKER_USE_FP16=false
   ```

3. **Restart backend**

## Troubleshooting

### API Key Invalid

**Error**: `HTTP 401 Unauthorized`

**Solution**: Verify API key is correct and has sufficient credits

### Timeout Errors

**Error**: `Request timeout after 30s`

**Solution**: Increase timeout or reduce batch size:
```python
reranker = APIReranker(..., timeout=60.0, batch_size=8)
```

### Rate Limiting

**Error**: `HTTP 429 Too Many Requests`

**Solution**: Reduce batch size or add delay between requests

### Unexpected Response Format

**Error**: `Failed to parse reranker response`

**Solution**: Check provider documentation for API changes

## References

- [Jina AI Documentation](https://jina.ai/reranker/)
- [Cohere Rerank API](https://docs.cohere.com/reference/rerank)
- [Voyage AI Documentation](https://docs.voyageai.com/docs/reranker)
- [RAG-Anything Documentation](../README.md)

