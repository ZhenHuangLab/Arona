# Arona Configuration Guide

This document explains the configuration file structure and environment variable setup for Arona.

---

## 📁 Configuration File Structure

Arona uses separate configuration files for backend and frontend to maintain security and deployment flexibility:

```
Arona/
├── .env.backend              # Backend actual configuration (DO NOT commit to Git)
├── env.backend.example       # Backend configuration template (commit to Git)
└── frontend/
    ├── .env                  # Frontend actual configuration (DO NOT commit to Git)
    └── .env.example          # Frontend configuration template (commit to Git)
```

### Why Separate Configuration Files?

1. **Security Isolation**: Backend configuration contains sensitive API keys and credentials that should never be exposed to the client
2. **Deployment Flexibility**: Backend and frontend can be deployed independently with different configurations
3. **Environment-Specific Settings**: Different environments (dev/staging/prod) may require different configurations
4. **Vite Requirements**: Frontend environment variables must be prefixed with `VITE_` to be accessible in the browser

---

## 🔧 Backend Configuration

### Setup

1. **Copy the example file**:
   ```bash
   cp env.backend.example .env.backend
   ```

2. **Edit `.env.backend`** with your actual configuration:
   ```bash
   nano .env.backend  # or use your preferred editor
   ```

### Configuration Sections

#### 1. LLM Configuration (Required)
```env
LLM_PROVIDER=openai                    # openai, azure, anthropic, custom, local
LLM_MODEL_NAME=gpt-4o-mini             # Model identifier
LLM_API_KEY=your-api-key-here          # API key for the provider
LLM_BASE_URL=https://api.openai.com/v1 # Optional: Custom base URL
LLM_TEMPERATURE=0.7                    # Optional: Sampling temperature
LLM_MAX_TOKENS=4096                    # Optional: Max tokens in response
```

#### 2. Embedding Configuration (Required)
```env
EMBEDDING_PROVIDER=openai              # openai, azure, custom, local
EMBEDDING_MODEL_NAME=text-embedding-3-large
EMBEDDING_API_KEY=your-api-key-here
EMBEDDING_BASE_URL=https://api.openai.com/v1
EMBEDDING_EMBEDDING_DIM=3072           # Required: Embedding dimension
```

#### 3. Vision Model Configuration (Optional)
```env
VISION_PROVIDER=openai                 # openai, azure, custom, local
VISION_MODEL_NAME=gpt-4o               # Vision-capable model
VISION_API_KEY=your-api-key-here
VISION_BASE_URL=https://api.openai.com/v1
```

#### 4. Reranker Configuration (Optional)
```env
RERANKER_ENABLED=true                  # Enable/disable reranking
RERANKER_PROVIDER=local                # local or api
RERANKER_MODEL_PATH=~/.huggingface/models/bge-reranker-v2-gemma
RERANKER_USE_FP16=false                # Use FP16 for local reranker
RERANKER_BATCH_SIZE=16                 # Batch size for reranking
```

#### 5. Storage Configuration
```env
WORKING_DIR=./rag_storage              # RAG storage directory
UPLOAD_DIR=./uploads                   # Upload directory for documents
```

#### 6. RAGAnything Configuration
```env
PARSER=mineru                          # Parser: mineru or docling
ENABLE_IMAGE_PROCESSING=true           # Process images in documents
ENABLE_TABLE_PROCESSING=true           # Process tables in documents
ENABLE_EQUATION_PROCESSING=true        # Process equations in documents
```

#### 7. API Server Configuration
```env
API_HOST=0.0.0.0                       # Host to bind to
API_PORT=8000                          # Port to bind to
CORS_ORIGINS=*                         # CORS allowed origins (comma-separated)
```

### Loading Mechanism

The backend automatically loads `.env.backend` on startup:

```python
# backend/main.py
env_file = PROJECT_ROOT / ".env.backend"
if env_file.exists():
    load_dotenv(dotenv_path=env_file, override=False)
```

---

## 🎨 Frontend Configuration

### Setup

1. **Copy the example file**:
   ```bash
   cd frontend
   cp .env.example .env
   ```

2. **Edit `frontend/.env`** with your configuration:
   ```bash
   nano .env  # or use your preferred editor
   ```

### Configuration Variables

```env
# Backend API Configuration (Required)
VITE_BACKEND_URL=http://localhost:8000

# Application Configuration
VITE_APP_NAME=Arona
VITE_APP_VERSION=0.1.0

# Development Configuration (Optional)
# VITE_DEV_PORT=5173
```

### Important Notes

1. **VITE_ Prefix Required**: All environment variables must be prefixed with `VITE_` to be accessible in the frontend code
2. **Build-Time Injection**: These variables are replaced at build time, not runtime
3. **No Sensitive Data**: Never put API keys or secrets in frontend configuration (they will be visible in the browser)

### Usage in Code

```typescript
// frontend/src/api/client.ts
const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';
```

### Loading Mechanism

Vite automatically loads `.env` files in the following order:
1. `.env` - Loaded in all cases
2. `.env.local` - Loaded in all cases, ignored by git
3. `.env.[mode]` - Only loaded in specified mode (e.g., `.env.production`)
4. `.env.[mode].local` - Only loaded in specified mode, ignored by git

---

## 🔒 Security Best Practices

### 1. Git Ignore Configuration

The `.gitignore` file is already configured to ignore actual configuration files:

```gitignore
*.env*          # Ignore all .env files
!env.*.example  # But keep example files
```

### 2. Never Commit Secrets

- ❌ **DO NOT** commit `.env.backend` or `frontend/.env` to Git
- ✅ **DO** commit `env.backend.example` and `frontend/.env.example` as templates
- ✅ **DO** use placeholder values in example files (e.g., `your-api-key-here`)

### 3. Environment-Specific Configurations

For different environments, use separate configuration files:

```bash
# Development
.env.backend

# Staging
.env.backend.staging

# Production
.env.backend.production
```

Then load the appropriate file based on your deployment environment.

---

## 🚀 Quick Start

### For Development

1. **Setup Backend Configuration**:
   ```bash
   cp env.backend.example .env.backend
   # Edit .env.backend with your API keys
   ```

2. **Setup Frontend Configuration**:
   ```bash
   cd frontend
   cp .env.example .env
   # Edit .env if needed (default values usually work for local development)
   ```

3. **Start the Application**:
   ```bash
   # From project root
   bash scripts/start_all.sh
   ```

### For Production

1. **Backend**: Set environment variables directly on the server or use a secrets management service
2. **Frontend**: Create `.env.production` with production API endpoint:
   ```env
   VITE_BACKEND_URL=https://api.your-domain.com
   ```

---

## 🔍 Troubleshooting

### Backend Configuration Issues

**Problem**: Backend can't find configuration file
```
Warning: .env.backend not found
```

**Solution**: 
```bash
cp env.backend.example .env.backend
```

**Problem**: Environment variables not loaded
```
ValueError: Missing required env var: LLM_MODEL_NAME
```

**Solution**: Check that `.env.backend` exists and contains the required variables

### Frontend Configuration Issues

**Problem**: Frontend can't connect to backend
```
Network Error: Failed to fetch
```

**Solution**: Check `VITE_BACKEND_URL` in `frontend/.env`:
```env
VITE_BACKEND_URL=http://localhost:8000
```

**Problem**: Environment variable is `undefined` in code

**Solution**: Ensure the variable is prefixed with `VITE_` and restart the dev server:
```bash
# Wrong
API_URL=http://localhost:8000

# Correct
VITE_API_URL=http://localhost:8000
```

---

## 📚 Related Documentation

- [Quick Start Guide](./QUICKSTART_NEW_ARCHITECTURE.md)
- [Deployment Guide](./deployment/REACT_DEPLOYMENT.md)
- [Troubleshooting](./TROUBLESHOOTING.md)
- [Architecture Overview](./REACT_ARCHITECTURE.md)

---

## 🔄 Migration from Old Configuration

If you're upgrading from an older version that used `env.example`:

1. **Delete the old file** (already done in latest version):
   ```bash
   rm env.example  # This file is obsolete
   ```

2. **Use the new structure**:
   - Backend: `env.backend.example` → `.env.backend`
   - Frontend: `frontend/.env.example` → `frontend/.env`

3. **Update your deployment scripts** to use `.env.backend` instead of `.env`

---

**Last Updated**: 2025-11-07  
**Version**: 0.1.0

