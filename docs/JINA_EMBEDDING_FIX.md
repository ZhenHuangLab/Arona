# Jina Embeddings API Compatibility Fix

## Problem Summary

When using Jina AI embeddings (`jina-embeddings-v4`), the system encountered two critical errors:

### Error 1: API Validation Error (422)
```
'body -> jina-embeddings-v4 -> encoding_format' Extra inputs are not permitted
```

**Root Cause**: The LightRAG library's `openai_embed` function hardcodes `encoding_format="base64"` parameter, which is not supported by Jina AI's API. Jina AI only accepts standard OpenAI embedding parameters and rejects the `encoding_format` field.

### Error 2: TypeError - NoneType
```python
TypeError: expected string or bytes-like object, got 'NoneType'
at raganything/query.py:567 in _process_image_paths_for_vlm
```

**Root Cause**: When the embedding API call fails (due to Error 1), the LightRAG query returns `None` instead of a valid prompt string. This `None` value is then passed to `_process_image_paths_for_vlm`, which attempts to use `re.findall()` on it, causing a TypeError.

## Solution

### 1. Created Custom Jina Embedding Provider

**File**: `backend/providers/jina.py`

A new provider that:
- Implements the `BaseEmbeddingProvider` interface
- Makes direct HTTP requests to Jina AI API using `httpx`
- **Does NOT include** the `encoding_format` parameter
- Supports Jina-specific parameters: `task`, `dimensions`, `late_chunking`, `embedding_type`
- Properly handles Jina's response format: `{"data": [{"embedding": [...], "index": 0}, ...]}`

**Key Features**:
```python
# Does NOT include encoding_format (unlike LightRAG's openai_embed)
payload = {
    "model": self.model_name,
    "input": texts,
    # Note: Do NOT include encoding_format - Jina doesn't support it
}
```

### 2. Updated Model Factory

**File**: `backend/services/model_factory.py`

Modified `create_embedding_provider()` to:
- Detect Jina models by checking:
  - Model name contains "jina" (case-insensitive)
  - Base URL contains "jina.ai" (case-insensitive)
- Route to `JinaEmbeddingProvider` for Jina models
- Continue using `OpenAIEmbeddingProvider` for other providers

```python
# Check if this is a Jina model (by model name or base URL)
is_jina = (
    "jina" in config.model_name.lower() or 
    (config.base_url and "jina.ai" in config.base_url.lower())
)

if is_jina:
    from backend.providers.jina import JinaEmbeddingProvider
    return JinaEmbeddingProvider(config)
```

### 3. Added Null Check for Prompt

**File**: `raganything/query.py`

Added defensive check in `_process_image_paths_for_vlm()`:
```python
# Handle None or empty prompt
if not prompt:
    self.logger.warning("Received None or empty prompt in _process_image_paths_for_vlm")
    return "", 0
```

This prevents the TypeError and allows the system to gracefully handle embedding failures by returning 0 images found, which triggers the fallback to normal query mode.

## Configuration

To use Jina embeddings, configure your `model_providers.yaml`:

```yaml
jina_example:
  models:
    llm:
      provider: openai
      model_name: gpt-4o-mini
      api_key: ${OPENAI_API_KEY}
      base_url: https://api.openai.com/v1

    embedding:
      provider: custom  # or openai, local - doesn't matter, auto-detected
      model_name: jina-embeddings-v4
      api_key: ${JINA_API_KEY}
      base_url: https://api.jina.ai/v1/embeddings
      embedding_dim: 2048  # or 1024, 512 depending on your needs

  reranker:
    enabled: true
    provider: api
    model_name: jina-reranker-v2-base-multilingual
    api_key: ${JINA_API_KEY}
    base_url: https://api.jina.ai/v1/rerank
```

## Testing

After applying these fixes:

1. **Embedding requests** will use the custom Jina provider
2. **No `encoding_format` parameter** will be sent to Jina API
3. **Failed embeddings** will be handled gracefully without crashing
4. **Query flow** will fallback to normal mode if embedding fails

## Files Modified

1. ✅ `backend/providers/jina.py` - **NEW** - Custom Jina embedding provider
2. ✅ `backend/providers/__init__.py` - Export JinaEmbeddingProvider
3. ✅ `backend/services/model_factory.py` - Auto-detect and route Jina models
4. ✅ `raganything/query.py` - Add null check for prompt parameter

## Backward Compatibility

- ✅ Existing OpenAI embeddings continue to work unchanged
- ✅ Existing Ollama embeddings continue to work unchanged
- ✅ Existing Azure embeddings continue to work unchanged
- ✅ Only Jina models are routed to the new provider

## Additional Notes

### Jina API Differences from OpenAI

1. **No `encoding_format` support** - Jina always returns embeddings as float arrays
2. **Different response structure** - Uses `data[].embedding` format
3. **Jina-specific parameters**:
   - `task`: "retrieval.query" or "retrieval.passage" or "text-matching"
   - `dimensions`: Output dimension (512, 1024, 2048, etc.)
   - `late_chunking`: Boolean for late chunking optimization
   - `embedding_type`: "float" or "binary"

### Future Improvements

Consider adding:
- Retry logic with exponential backoff
- Batch size optimization for large text lists
- Caching layer for frequently embedded texts
- Support for Jina's `task` parameter to optimize retrieval vs. passage embeddings

