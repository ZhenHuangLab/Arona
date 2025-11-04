# MinerU Network Issues - Troubleshooting Guide

## Problem

MinerU fails with network timeout when trying to download models from HuggingFace:

```
huggingface_hub.errors.LocalEntryNotFoundError: An error happened while trying to locate 
the files on the Hub and we cannot find the appropriate snapshot folder for the specified 
revision on the local disk. Please check your internet connection and try again.
```

**Root Cause**: MinerU needs to download the `opendatalab/PDF-Extract-Kit-1.0` model from HuggingFace Hub, but the connection times out due to:
- No internet access on compute nodes (HPC environments)
- Firewall restrictions
- Network restrictions in China
- Slow/unstable connection to HuggingFace

---

## Solutions

### Solution 1: Pre-download Models (Recommended for HPC)

**Best for**: HPC environments where compute nodes have no internet access.

#### Step 1: Download on Login Node

Run this on a node with internet access:

```bash
# Activate your virtual environment
source .venv/bin/activate

# Run the download script
bash scripts/download_mineru_models.sh
```

This will download models to `~/.huggingface/hub/models--opendatalab--PDF-Extract-Kit-1.0/`

#### Step 2: Verify Download

```bash
# Check if models are downloaded
ls -lh ~/.huggingface/hub/models--opendatalab--PDF-Extract-Kit-1.0/

# You should see snapshots directory
ls -lh ~/.huggingface/hub/models--opendatalab--PDF-Extract-Kit-1.0/snapshots/
```

#### Step 3: Configure Environment Variables

Add to your `.env.backend` or shell environment:

```bash
export HF_HOME="${HOME}/.huggingface"
export HF_HUB_CACHE="${HOME}/.huggingface/hub"
export HF_DATASETS_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export MINERU_MODEL_SOURCE=local
```

#### Step 4: Restart Backend

```bash
# Stop the backend
pkill -f "uvicorn backend.main:app"

# Restart with new environment
source .env.backend
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

---

### Solution 2: Use ModelScope Mirror (For China)

**Best for**: Users in China or behind restrictive firewalls.

#### Step 1: Configure ModelScope

Add to `.env.backend`:

```bash
# Use ModelScope instead of HuggingFace
export MINERU_MODEL_SOURCE=modelscope
```

#### Step 2: Install ModelScope SDK (Optional)

```bash
pip install modelscope
```

#### Step 3: Restart Backend

```bash
source .env.backend
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

---

### Solution 3: Use HuggingFace Mirror

**Best for**: Users with slow/unstable connection to HuggingFace.

#### Step 1: Configure Mirror

Add to `.env.backend`:

```bash
# Use HuggingFace mirror
export HF_ENDPOINT=https://hf-mirror.com
export MINERU_MODEL_SOURCE=huggingface
```

#### Step 2: Download Models via Mirror

```bash
# Set mirror endpoint
export HF_ENDPOINT=https://hf-mirror.com

# Download models
bash scripts/download_mineru_models.sh
```

#### Step 3: Restart Backend

```bash
source .env.backend
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

---

### Solution 4: Manual Download

**Best for**: When automated methods fail.

#### Step 1: Download from Browser

1. Visit: https://huggingface.co/opendatalab/PDF-Extract-Kit-1.0
2. Click "Files and versions"
3. Download all files to a local directory

Or use `git-lfs`:

```bash
# Install git-lfs
git lfs install

# Clone the repository
cd ~/.huggingface/hub
git clone https://huggingface.co/opendatalab/PDF-Extract-Kit-1.0 \
    models--opendatalab--PDF-Extract-Kit-1.0
```

#### Step 2: Organize Files

The directory structure should be:

```
~/.huggingface/hub/
└── models--opendatalab--PDF-Extract-Kit-1.0/
    ├── refs/
    │   └── main
    └── snapshots/
        └── <commit-hash>/
            ├── config.json
            ├── model.safetensors
            └── ... (other model files)
```

#### Step 3: Configure Environment

```bash
export HF_HOME="${HOME}/.huggingface"
export HF_HUB_CACHE="${HOME}/.huggingface/hub"
export HF_DATASETS_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export MINERU_MODEL_SOURCE=local
```

---

## Verification

### Check Model Cache

```bash
# List cached models
ls -lh ~/.huggingface/hub/

# Check specific model
ls -lh ~/.huggingface/hub/models--opendatalab--PDF-Extract-Kit-1.0/
```

### Test MinerU

```bash
# Test with a sample PDF
source .venv/bin/activate
python -c "
from raganything.parser import MineruParser
parser = MineruParser()
result = parser.parse_pdf('test.pdf', 'output')
print('✅ MinerU is working!')
"
```

### Check Environment Variables

```bash
# Verify environment
echo "HF_HOME: $HF_HOME"
echo "HF_HUB_CACHE: $HF_HUB_CACHE"
echo "MINERU_MODEL_SOURCE: $MINERU_MODEL_SOURCE"
echo "HF_ENDPOINT: $HF_ENDPOINT"
```

---

## Common Issues

### Issue 1: Models Not Found After Download

**Symptom**: Models downloaded but MinerU still tries to download

**Solution**:
```bash
# Ensure environment variables are set
export HF_HOME="${HOME}/.huggingface"
export HF_HUB_CACHE="${HOME}/.huggingface/hub"

# Restart backend with environment
source .env.backend
python -m uvicorn backend.main:app --reload
```

### Issue 2: Permission Denied

**Symptom**: Cannot write to `~/.huggingface/`

**Solution**:
```bash
# Fix permissions
chmod -R u+w ~/.huggingface/

# Or use custom directory
export HF_HOME="/path/to/writable/dir/.huggingface"
export HF_HUB_CACHE="${HF_HOME}/hub"
```

### Issue 3: Disk Space

**Symptom**: Download fails due to insufficient space

**Solution**:
```bash
# Check space
df -h ~/.huggingface/

# Use different directory with more space
export HF_HOME="/mnt/large-disk/.huggingface"
export HF_HUB_CACHE="${HF_HOME}/hub"
mkdir -p "${HF_HOME}" "${HF_HUB_CACHE}"
```

### Issue 4: Proxy Settings

**Symptom**: Connection fails due to proxy

**Solution**:
```bash
# Set proxy
export HTTP_PROXY=http://proxy.example.com:8080
export HTTPS_PROXY=http://proxy.example.com:8080
export NO_PROXY=localhost,127.0.0.1

# Download models
bash scripts/download_mineru_models.sh
```

---

## Environment Variable Reference

| Variable | Description | Example |
|----------|-------------|---------|
| `HF_HOME` | HuggingFace cache root | `~/.huggingface` |
| `HF_HUB_CACHE` | HuggingFace Hub cache | `~/.huggingface/hub` |
| `HF_ENDPOINT` | HuggingFace mirror endpoint | `https://hf-mirror.com` |
| `HF_DATASETS_OFFLINE` | Enable offline mode | `1` |
| `TRANSFORMERS_OFFLINE` | Enable offline mode | `1` |
| `MINERU_MODEL_SOURCE` | Model source | `huggingface`, `modelscope`, `local` |
| `HTTP_PROXY` | HTTP proxy | `http://proxy:8080` |
| `HTTPS_PROXY` | HTTPS proxy | `http://proxy:8080` |

---

## Quick Fix Commands

```bash
# Quick fix for HPC (run on login node)
bash scripts/download_mineru_models.sh
export HF_HOME="${HOME}/.huggingface"
export HF_HUB_CACHE="${HOME}/.huggingface/hub"
export MINERU_MODEL_SOURCE=local

# Quick fix for China
export MINERU_MODEL_SOURCE=modelscope
export HF_ENDPOINT=https://hf-mirror.com

# Quick fix for proxy
export HTTP_PROXY=http://proxy:8080
export HTTPS_PROXY=http://proxy:8080
bash scripts/download_mineru_models.sh
```

---

## Additional Resources

- MinerU Documentation: https://github.com/opendatalab/MinerU
- HuggingFace Hub: https://huggingface.co/opendatalab/PDF-Extract-Kit-1.0
- ModelScope: https://modelscope.cn/
- HuggingFace Mirror (China): https://hf-mirror.com

