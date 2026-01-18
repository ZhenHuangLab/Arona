# API-based Reranker Examples

This directory contains examples for using API-based rerankers with RAG-Anything.

## Overview

RAG-Anything supports multiple reranker providers:

- **Jina AI** - Multilingual reranker with excellent performance
- **Cohere** - Industry-leading reranker with English and multilingual models
- **Voyage AI** - Fast and cost-effective reranker
- **OpenAI-compatible** - Any API following OpenAI's format

## Quick Start

### 1. Install Dependencies

```bash
pip install httpx  # Required for API rerankers
```

### 2. Get API Keys

- **Jina AI**: [https://jina.ai/](https://jina.ai/)
- **Cohere**: [https://cohere.com/](https://cohere.com/)
- **Voyage AI**: [https://www.voyageai.com/](https://www.voyageai.com/)

### 3. Set Environment Variables

```bash
export JINA_API_KEY="jina_xxxxxxxxxxxxx"
export COHERE_API_KEY="your-cohere-key"
export VOYAGE_API_KEY="your-voyage-key"
```

### 4. Run Test Script

```bash
python examples/test_api_reranker.py
```

## Configuration Examples

### Using with Backend (.env.backend)

#### Jina AI Reranker

```bash
RERANKER_ENABLED=true
RERANKER_PROVIDER=api
RERANKER_MODEL_NAME=jina-reranker-v2-base-multilingual
RERANKER_API_KEY=jina_xxxxxxxxxxxxx
RERANKER_BATCH_SIZE=16
```

#### Cohere Reranker

```bash
RERANKER_ENABLED=true
RERANKER_PROVIDER=api
RERANKER_MODEL_NAME=rerank-english-v3.0
RERANKER_API_KEY=your-cohere-key
RERANKER_BATCH_SIZE=16
```

#### Voyage AI Reranker

```bash
RERANKER_ENABLED=true
RERANKER_PROVIDER=api
RERANKER_MODEL_NAME=rerank-lite-1
RERANKER_API_KEY=your-voyage-key
RERANKER_BATCH_SIZE=16
```

### Using Programmatically

```python
from raganything.rerankers.api_reranker import APIReranker

# Create reranker
reranker = APIReranker(
    provider="jina",
    model_name="jina-reranker-v2-base-multilingual",
    api_key="jina_xxxxxxxxxxxxx",
    batch_size=16,
)

# Rerank documents
query = "What is machine learning?"
documents = [
    "Machine learning is a subset of AI.",
    "Python is a programming language.",
    "Deep learning uses neural networks.",
]

scores = await reranker.score_async(query, documents)

# Clean up
await reranker.close()
```

## Available Models

### Jina AI

| Model | Description | Languages |
|-------|-------------|-----------|
| `jina-reranker-v2-base-multilingual` | Base multilingual model | 100+ |
| `jina-reranker-v1-base-en` | English-only model | English |

**Pricing**: ~$0.02 per 1K rerank requests

### Cohere

| Model | Description | Languages |
|-------|-------------|-----------|
| `rerank-english-v3.0` | Latest English model | English |
| `rerank-multilingual-v3.0` | Latest multilingual model | 100+ |
| `rerank-english-v2.0` | Previous English model | English |

**Pricing**: ~$1.00 per 1K searches (1K documents)

### Voyage AI

| Model | Description | Use Case |
|-------|-------------|----------|
| `rerank-1` | High accuracy model | Production |
| `rerank-lite-1` | Fast, cost-effective | Development |

**Pricing**: ~$0.05 per 1K rerank requests

## Performance Comparison

| Provider | Speed | Accuracy | Cost | Best For |
|----------|-------|----------|------|----------|
| Jina AI | Fast | High | Low | Multilingual, Budget |
| Cohere | Medium | Very High | Medium | English, Quality |
| Voyage AI | Very Fast | High | Low | Speed, Cost |
| Local (FlagEmbedding) | Depends on GPU | High | Free* | Privacy, Offline |

*Free after model download, but requires GPU

## Troubleshooting

### API Key Not Working

Make sure your API key is valid and has sufficient credits:

```bash
# Test Jina API key
curl -X POST https://api.jina.ai/v1/rerank \
  -H "Authorization: Bearer $JINA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "jina-reranker-v2-base-multilingual",
    "query": "test",
    "documents": ["test document"]
  }'
```

### Rate Limiting

If you hit rate limits, reduce `RERANKER_BATCH_SIZE`:

```bash
RERANKER_BATCH_SIZE=8  # Reduce from default 16
```

### Timeout Errors

Increase timeout in code:

```python
reranker = APIReranker(
    provider="jina",
    model_name="jina-reranker-v2-base-multilingual",
    api_key="your-key",
    timeout=60.0,  # Increase from default 30.0
)
```

## Best Practices

1. **Choose the right provider**:
   - Use Jina for multilingual content
   - Use Cohere for highest quality English results
   - Use Voyage for speed and cost optimization

2. **Batch size optimization**:
   - Larger batches = fewer API calls = lower cost
   - But larger batches may timeout on slow connections
   - Recommended: 16-32 for most use cases

3. **Error handling**:
   - API rerankers have built-in retry logic (3 attempts)
   - Always use `try/except` for production code
   - Consider fallback to no reranking on persistent failures

4. **Cost optimization**:
   - Cache reranking results when possible
   - Use cheaper models for development/testing
   - Monitor API usage and costs

## Migration from Local Reranker

To migrate from local FlagEmbedding reranker to API:

1. **Backup your config**:
   ```bash
   cp .env.backend .env.backend.backup
   ```

2. **Update configuration**:
   ```bash
   # Change from:
   RERANKER_PROVIDER=local
   RERANKER_MODEL_PATH=~/.huggingface/models/bge-reranker-v2-gemma

   # To:
   RERANKER_PROVIDER=api
   RERANKER_MODEL_NAME=jina-reranker-v2-base-multilingual
   RERANKER_API_KEY=your-api-key
   ```

3. **Test the change**:
   ```bash
   python examples/test_api_reranker.py
   ```

4. **Restart backend**:
   ```bash
   python -m backend.main
   ```

## Support

For issues or questions:
- Check the main documentation: `docs/QUICKSTART_NEW_ARCHITECTURE.md`
- Open an issue on GitHub
- Review API provider documentation

## License

Same as RAG-Anything main project.
