# Troubleshooting Guide

This document provides solutions to common issues you may encounter when using RAG-Anything.

## Table of Contents

- [Reranker Warnings](#reranker-warnings)
- [MinerU Errors](#mineru-errors)
- [Environment Variable Issues](#environment-variable-issues)

---

## Reranker Warnings

### Issue: "ENABLE_RERANK is true but RERANKER_MODEL_PATH is empty"

**Symptom:**
```
<string>:32: RuntimeWarning: ENABLE_RERANK is true but RERANKER_MODEL_PATH is empty; disabling reranker stage.
```

**Cause:**
This warning appears when you're using an API-based reranker (e.g., Jina, Cohere, Voyage) but the legacy `RAGAnythingConfig` is still checking for `RERANKER_MODEL_PATH`, which is only needed for local FlagEmbedding rerankers.

**Solution:**

The warning is harmless and can be ignored when using API rerankers. The backend correctly uses the API reranker through the `rerank_model_func` parameter.

To suppress the warning, ensure your `.env.backend` has:

```bash
RERANKER_ENABLED=true
RERANKER_PROVIDER=api  # This tells RAGAnythingConfig to skip the warning

# API Reranker settings
RERANKER_MODEL_NAME=jina-reranker-v2-base-multilingual
RERANKER_API_KEY=your-api-key
RERANKER_BASE_URL=https://api.jina.ai/v1/rerank  # Optional
```

**Technical Details:**

The backend architecture separates concerns:
- `backend/config.py` - Handles both local and API reranker configuration
- `backend/services/model_factory.py` - Creates appropriate reranker instances
- `raganything/config.py` - Legacy config for direct RAGAnything usage

When using the backend API, the reranker is passed as a function to RAGAnything, so the `RERANKER_MODEL_PATH` check is not needed.

---

## MinerU Errors

### Issue: "'NoneType' object has no attribute 'get'"

**Symptom:**
```
2025-11-02 16:04:19,478 - root - ERROR - [MinerU] 2025-11-02 16:04:19.464 | ERROR    | mineru.cli.client:parse_doc:201 - 'NoneType' object has no attribute 'get'
```

**Cause:**
This error occurs when MinerU cannot access its configuration, usually due to:
1. Missing or incorrectly set HuggingFace environment variables
2. Environment variables not being properly expanded (e.g., `${HOME}` in `.env` files)
3. Missing model files when using `MINERU_MODEL_SOURCE=local`

**Solution:**

#### Option 1: Set environment variables in your shell (Recommended)

Add to your `~/.bashrc` or `~/.zshrc`:

```bash
# HuggingFace configuration
export HF_HOME="$HOME/.huggingface"
export HF_HUB_CACHE="$HOME/.huggingface/hub"

# For China/restricted networks
# export HF_ENDPOINT="https://hf-mirror.com"
# export HF_DATASETS_OFFLINE=1
# export TRANSFORMERS_OFFLINE=1

# MinerU model source
export MINERU_MODEL_SOURCE=huggingface  # or modelscope for China
```

Then reload your shell:
```bash
source ~/.bashrc  # or source ~/.zshrc
```

#### Option 2: Set before running the backend

```bash
export HF_HOME="$HOME/.huggingface"
export HF_HUB_CACHE="$HOME/.huggingface/hub"
export MINERU_MODEL_SOURCE=huggingface

python -m backend.main
```

#### Option 3: Use the startup script

The `scripts/start_backend.sh` script will load `.env.backend`, but shell variables like `${HOME}` won't be expanded in `.env` files. Set them in your shell environment instead.

**Verification:**

Check that MinerU can access its models:

```bash
python -c "import os; print('HF_HOME:', os.getenv('HF_HOME')); print('MINERU_MODEL_SOURCE:', os.getenv('MINERU_MODEL_SOURCE'))"
```

---

## Environment Variable Issues

### Issue: Shell variables not expanded in .env files

**Problem:**
Variables like `${HOME}` in `.env.backend` are not automatically expanded by Python's `dotenv` library.

**Example of what doesn't work:**
```bash
# .env.backend
HF_HOME="${HOME}/.huggingface"  # This will be literal "${HOME}", not expanded!
```

**Solution:**

1. **Use absolute paths in .env files:**
   ```bash
   HF_HOME=/home/username/.huggingface
   ```

2. **Or set in shell environment** (recommended):
   ```bash
   export HF_HOME="$HOME/.huggingface"
   ```

3. **Or use the tilde (~) expansion** (works in some contexts):
   ```bash
   HF_HOME=~/.huggingface
   ```

### Issue: Environment variables not loaded

**Symptom:**
Backend doesn't see environment variables from `.env.backend`.

**Solution:**

The backend now automatically loads `.env.backend` on startup (as of the latest update). If you're using an older version:

1. **Update backend/main.py** to include:
   ```python
   from dotenv import load_dotenv
   
   # Load .env.backend
   env_file = Path(__file__).parent.parent / ".env.backend"
   if env_file.exists():
       load_dotenv(dotenv_path=env_file, override=False)
   ```

2. **Or use the startup script:**
   ```bash
   bash scripts/start_backend.sh
   ```

---

## Configuration Validation

### Check your configuration

Run this script to validate your environment:

```python
import os
from backend.config import BackendConfig

# Load config
config = BackendConfig.from_env()

# Print configuration
print("=== Backend Configuration ===")
print(f"LLM: {config.llm.provider.value}/{config.llm.model_name}")
print(f"Embedding: {config.embedding.provider.value}/{config.embedding.model_name}")
print(f"Embedding Dim: {config.embedding.embedding_dim}")

if config.vision:
    print(f"Vision: {config.vision.provider.value}/{config.vision.model_name}")

if config.reranker and config.reranker.enabled:
    print(f"Reranker: {config.reranker.provider}")
    if config.reranker.provider == "api":
        print(f"  Model: {config.reranker.model_name}")
        print(f"  Base URL: {config.reranker.base_url}")
    else:
        print(f"  Model Path: {config.reranker.model_path}")

print(f"\nWorking Dir: {config.working_dir}")
print(f"Upload Dir: {config.upload_dir}")
print(f"Parser: {config.parser}")

# Check HuggingFace environment
print("\n=== HuggingFace Environment ===")
print(f"HF_HOME: {os.getenv('HF_HOME', 'Not set')}")
print(f"HF_HUB_CACHE: {os.getenv('HF_HUB_CACHE', 'Not set')}")
print(f"MINERU_MODEL_SOURCE: {os.getenv('MINERU_MODEL_SOURCE', 'Not set')}")
```

Save as `check_config.py` and run:
```bash
python check_config.py
```

---

## Getting Help

If you encounter issues not covered here:

1. **Check the logs** - Backend logs provide detailed error messages
2. **Verify environment variables** - Use `printenv | grep -E "(LLM|EMBEDDING|RERANKER|HF_|MINERU)"` to check
3. **Test components individually** - Test LLM, embedding, and reranker separately
4. **Check model availability** - Ensure API keys are valid and models are accessible

For API-based services:
- Verify API keys are correct
- Check network connectivity to API endpoints
- Ensure base URLs are correct

For local models:
- Verify model files exist in the specified paths
- Check file permissions
- Ensure sufficient disk space

