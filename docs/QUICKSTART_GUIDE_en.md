# RAG-Anything Quickstart Guide for Beginners

> **About**: This comprehensive guide covers everything you need to know to get started with RAG-Anything, from basic concepts to advanced deployment scenarios.

## 📖 Table of Contents

1. [What is RAG-Anything?](#1-what-is-rag-anything)
2. [Core Features](#2-core-features)
3. [System Architecture](#3-system-architecture)
4. [Quick Start](#4-quick-start)
5. [Usage Scenarios & Examples](#5-usage-scenarios--examples)
6. [HPC Cluster Deployment (SLURM)](#6-hpc-cluster-deployment-slurm)
7. [Configuration Guide](#7-configuration-guide)
8. [FAQ](#8-faq)
9. [Advanced Usage](#9-advanced-usage)

---

## 1. What is RAG-Anything?

**RAG-Anything** is an **All-in-One Multimodal Document Processing RAG (Retrieval-Augmented Generation) System** built on [LightRAG](https://github.com/HKUDS/LightRAG).

### Why RAG-Anything?

Traditional RAG systems only handle plain text, but modern documents contain:
- 📊 **Tabular Data**
- 🖼️ **Images, Charts, Diagrams**  
- 📐 **Mathematical Equations**
- 📄 **Complex PDFs and Office Documents**

RAG-Anything solves this challenge with **unified processing for all content types**.

### Core Advantages

| Feature | Description |
|---------|-------------|
| 🔄 End-to-End Multimodal Pipeline | Complete workflow from parsing to intelligent Q&A |
| 📄 Universal Document Support | PDF, Word, PPT, Excel, Images, Markdown, etc. |
| 🧠 Specialized Content Analysis | Dedicated processors for images, tables, equations |
| 🔗 Multimodal Knowledge Graph | Auto entity extraction and cross-modal relationships |
| ⚡ Flexible Processing Modes | Support for MinerU, Docling, and more parsers |
| 🎯 Hybrid Intelligent Retrieval | Context-aware search across text and multimodal content |

---

## 2. Core Features

### 2.1 Document Parsing Stage

**Supported Parsers:**
- **MinerU**: Powerful OCR and table extraction with GPU acceleration
- **Docling**: Optimized for Office documents with better structure preservation

**Supported Formats:**
```
PDF, DOC/DOCX, PPT/PPTX, XLS/XLSX
JPG/PNG/BMP/TIFF/GIF/WebP
TXT, Markdown
```

### 2.2 Multimodal Content Understanding

The system automatically identifies and processes:
- 🔍 **Images**: VLM-powered caption generation
- 📊 **Tables**: Structured data interpretation and statistics
- 📐 **Equations**: LaTeX support with concept mapping
- 🔧 **Custom Content**: Extensible processor framework

### 2.3 Knowledge Graph Indexing

- Multi-modal entity extraction
- Cross-modal relationship mapping
- Document hierarchy preservation
- Weighted relationship scoring

### 2.4 Intelligent Retrieval

Three query types:
1. **Pure Text Query**: Direct knowledge base search
2. **VLM Enhanced Query**: Automatic image analysis in retrieved context
3. **Multimodal Query**: Analysis with specific multimodal content

---

## 3. System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    RAG-Anything Architecture                     │
└─────────────────────────────────────────────────────────────────┘

    Document Input (PDF/Office/Images)
         ↓
    ┌────────────┐
    │  Parser    │  MinerU / Docling
    └────────────┘
         ↓
    ┌────────────┐
    │  Content   │  Auto-routing to processors
    │  Classifier│
    └────────────┘
         ↓
    ┌─────────────────────────────────────┐
    │   Multimodal Processors (Parallel)  │
    │  • ImageModalProcessor              │
    │  • TableModalProcessor              │
    │  • EquationModalProcessor           │
    │  • GenericModalProcessor            │
    └─────────────────────────────────────┘
         ↓
    ┌────────────┐
    │ LightRAG   │  Knowledge Graph
    │ Knowledge  │  • Entity extraction
    │ Graph      │  • Relationship building
    └────────────┘
         ↓
    ┌────────────┐
    │ Intelligent│  • Vector similarity
    │ Retrieval  │  • Graph traversal
    │            │  • Context-aware
    └────────────┘
         ↓
    Query Results
```

---

## 4. Quick Start

### 4.1 Requirements

- **Python**: 3.10+
- **OS**: Linux/macOS/Windows
- **Optional**: LibreOffice (for Office documents)

### 4.2 Installation

#### Option 1: Install from PyPI (Recommended)

```bash
# Basic installation
pip install raganything

# Full installation (all optional dependencies)
pip install 'raganything[all]'

# Install specific features
pip install 'raganything[image]'        # Image format support
pip install 'raganything[text]'         # Text file support
pip install 'raganything[image,text]'   # Multiple features
```

#### Option 2: Install from Source

```bash
# Install uv package manager
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone the repository
git clone https://github.com/HKUDS/RAG-Anything.git
cd RAG-Anything

# Install dependencies
uv sync

# If network timeout (especially for opencv):
UV_HTTP_TIMEOUT=120 uv sync

# Run examples with uv
uv run python examples/raganything_example.py --help

# Install all optional dependencies
uv sync --all-extras
```

### 4.3 Install Optional Dependencies

#### LibreOffice (Office Document Support)

```bash
# macOS
brew install --cask libreoffice

# Ubuntu/Debian
sudo apt-get install libreoffice

# CentOS/RHEL
sudo yum install libreoffice

# Windows
# Download from: https://www.libreoffice.org/download/download/
```

#### Verify MinerU Installation

```bash
# Check version
mineru --version

# Check configuration
python -c "from raganything import RAGAnything; rag = RAGAnything(); print('✅ MinerU OK' if rag.check_parser_installation() else '❌ MinerU Issue')"
```

### 4.4 Configure API Keys

Create `.env` file (refer to `env.example`):

```bash
# OpenAI Configuration
LLM_BINDING=openai
LLM_MODEL=gpt-4o-mini
LLM_BINDING_HOST=https://api.openai.com/v1
LLM_BINDING_API_KEY=your_api_key_here

# Embedding Model
EMBEDDING_BINDING=openai
EMBEDDING_MODEL=text-embedding-3-large
EMBEDDING_DIM=3072
EMBEDDING_BINDING_API_KEY=your_api_key_here

# Or use local Ollama
# EMBEDDING_BINDING=ollama
# EMBEDDING_MODEL=bge-m3:latest
# EMBEDDING_DIM=1024
# EMBEDDING_BINDING_HOST=http://localhost:11434

# Document Processing
PARSER=mineru                    # or docling
PARSE_METHOD=auto                # auto/ocr/txt
ENABLE_IMAGE_PROCESSING=true
ENABLE_TABLE_PROCESSING=true
ENABLE_EQUATION_PROCESSING=true
```

---

## 5. Usage Scenarios & Examples

### 5.1 Scenario 1: Process Academic Papers (End-to-End)

**Use Case**: Analyze a PDF paper with figures, tables, and equations

```python
import asyncio
from raganything import RAGAnything, RAGAnythingConfig
from lightrag.llm.openai import openai_complete_if_cache, openai_embed
from lightrag.utils import EmbeddingFunc

async def main():
    # Configuration
    api_key = "your-api-key"
    base_url = "https://api.openai.com/v1"  # Optional
    
    # Create config
    config = RAGAnythingConfig(
        working_dir="./rag_storage",
        parser="mineru",
        parse_method="auto",
        enable_image_processing=True,
        enable_table_processing=True,
        enable_equation_processing=True,
    )
    
    # LLM function
    def llm_model_func(prompt, system_prompt=None, history_messages=[], **kwargs):
        return openai_complete_if_cache(
            "gpt-4o-mini", prompt,
            system_prompt=system_prompt,
            history_messages=history_messages,
            api_key=api_key, base_url=base_url, **kwargs
        )
    
    # Vision model function (for image analysis)
    def vision_model_func(prompt, system_prompt=None, history_messages=[], 
                         image_data=None, messages=None, **kwargs):
        if messages:  # VLM enhanced query mode
            return openai_complete_if_cache(
                "gpt-4o", "", system_prompt=None, history_messages=[],
                messages=messages, api_key=api_key, base_url=base_url, **kwargs
            )
        elif image_data:  # Single image mode
            return openai_complete_if_cache(
                "gpt-4o", "", system_prompt=None, history_messages=[],
                messages=[
                    {"role": "system", "content": system_prompt} if system_prompt else None,
                    {"role": "user", "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
                    ]} if image_data else {"role": "user", "content": prompt}
                ],
                api_key=api_key, base_url=base_url, **kwargs
            )
        else:  # Pure text
            return llm_model_func(prompt, system_prompt, history_messages, **kwargs)
    
    # Embedding function
    embedding_func = EmbeddingFunc(
        embedding_dim=3072, max_token_size=8192,
        func=lambda texts: openai_embed(
            texts, model="text-embedding-3-large",
            api_key=api_key, base_url=base_url
        ),
    )
    
    # Initialize RAGAnything
    rag = RAGAnything(
        config=config,
        llm_model_func=llm_model_func,
        vision_model_func=vision_model_func,
        embedding_func=embedding_func,
    )
    
    # Process document
    print("📄 Processing paper...")
    await rag.process_document_complete(
        file_path="path/to/research_paper.pdf",
        output_dir="./output",
        parse_method="auto"
    )
    print("✅ Document processed!")
    
    # Query 1: Pure text query
    print("\n🔍 Text query...")
    result = await rag.aquery(
        "What are the main findings?",
        mode="hybrid"
    )
    print(f"Answer: {result}\n")
    
    # Query 2: VLM enhanced query (auto image analysis)
    print("🔍 VLM enhanced query...")
    result = await rag.aquery(
        "What trends are shown in the charts?",
        mode="hybrid"
        # vlm_enhanced=True automatically when vision_model_func provided
    )
    print(f"Answer: {result}\n")
    
    # Query 3: Multimodal query with specific equation
    print("🔍 Multimodal query...")
    result = await rag.aquery_with_multimodal(
        "Explain this formula and its relevance",
        multimodal_content=[{
            "type": "equation",
            "latex": r"E = mc^2",
            "equation_caption": "Mass-energy equivalence"
        }],
        mode="hybrid"
    )
    print(f"Answer: {result}")

if __name__ == "__main__":
    asyncio.run(main())
```

### 5.2 Scenario 2: Batch Processing Multiple Documents

```python
import asyncio
from raganything import RAGAnything

async def batch_process():
    # ... initialization code same as above ...
    
    # Batch process entire folder
    await rag.process_folder_complete(
        folder_path="./documents",
        output_dir="./output",
        file_extensions=[".pdf", ".docx", ".pptx"],
        recursive=True,          # Process subfolders
        max_workers=4            # Parallel processing
    )
    
    print("✅ All documents processed!")

asyncio.run(batch_process())
```

### 5.3 Scenario 3: Direct Content List Insertion

**Use Case**: You already have parsed content, skip re-parsing

```python
import asyncio
from raganything import RAGAnything

async def insert_parsed_content():
    # ... initialize RAGAnything ...
    
    # Pre-parsed content list
    content_list = [
        {
            "type": "text",
            "text": "This is the introduction section.",
            "page_idx": 0
        },
        {
            "type": "image",
            "img_path": "/absolute/path/to/figure1.jpg",  # Must be absolute path
            "image_caption": ["Figure 1: System Architecture"],
            "image_footnote": ["Source: Authors"],
            "page_idx": 1
        },
        {
            "type": "table",
            "table_body": "| Method | Accuracy | F1 |\n|--------|----------|----|\n| Ours | 95.2% | 0.94 |\n| Baseline | 87.3% | 0.85 |",
            "table_caption": ["Table 1: Performance"],
            "table_footnote": ["Test set results"],
            "page_idx": 2
        },
        {
            "type": "equation",
            "latex": r"P(d|q) = \frac{P(q|d) \cdot P(d)}{P(q)}",
            "text": "Document relevance probability",
            "page_idx": 3
        }
    ]
    
    # Insert content list directly
    await rag.insert_content_list(
        content_list=content_list,
        file_path="research_paper.pdf",
        display_stats=True
    )
    
    # Query
    result = await rag.aquery(
        "What are the key performance metrics?",
        mode="hybrid"
    )
    print(f"Answer: {result}")

asyncio.run(insert_parsed_content())
```

### 5.4 Scenario 4: Load Existing LightRAG Instance

**Use Case**: Add multimodal capabilities to existing LightRAG knowledge base

```python
import asyncio
from raganything import RAGAnything
from lightrag import LightRAG
from lightrag.kg.shared_storage import initialize_pipeline_status
import os

async def load_existing():
    # Check for existing instance
    lightrag_dir = "./existing_lightrag_storage"
    if os.path.exists(lightrag_dir) and os.listdir(lightrag_dir):
        print("✅ Found existing LightRAG instance")
    
    # Load existing LightRAG
    lightrag_instance = LightRAG(
        working_dir=lightrag_dir,
        llm_model_func=...,  # Your LLM function
        embedding_func=...,  # Your embedding function
    )
    await lightrag_instance.initialize_storages()
    await initialize_pipeline_status()
    
    # Initialize RAGAnything with existing instance
    rag = RAGAnything(
        lightrag=lightrag_instance,  # Pass existing instance
        vision_model_func=...,       # Add vision support
    )
    
    # Query existing knowledge base
    result = await rag.aquery(
        "What data exists in this knowledge base?",
        mode="hybrid"
    )
    print(f"Answer: {result}")
    
    # Add new multimodal document
    await rag.process_document_complete(
        file_path="new_document.pdf",
        output_dir="./output"
    )

asyncio.run(load_existing())
```

### 5.5 Scenario 5: Use Local Ollama Models (No API Key)

```bash
# 1. Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 2. Pull models
ollama pull qwen2.5:latest        # LLM model
ollama pull bge-m3:latest         # Embedding model
ollama pull llava:latest          # Vision model (optional)

# 3. Start Ollama service (default port 11434)
ollama serve
```

```python
import asyncio
from raganything import RAGAnything, RAGAnythingConfig
from lightrag.llm.ollama import ollama_model_complete, ollama_embed
from lightrag.utils import EmbeddingFunc

async def main():
    config = RAGAnythingConfig(
        working_dir="./rag_storage",
        parser="mineru",
        enable_image_processing=True,
        enable_table_processing=True,
    )
    
    # Use Ollama
    def llm_func(prompt, system_prompt=None, history_messages=[], **kwargs):
        return ollama_model_complete(
            prompt=prompt,
            model="qwen2.5:latest",
            host="http://localhost:11434",
            system_prompt=system_prompt,
            history_messages=history_messages,
            **kwargs
        )
    
    embedding_func = EmbeddingFunc(
        embedding_dim=1024, max_token_size=8192,
        func=lambda texts: ollama_embed(
            texts,
            embed_model="bge-m3:latest",
            host="http://localhost:11434"
        ),
    )
    
    rag = RAGAnything(
        config=config,
        llm_model_func=llm_func,
        embedding_func=embedding_func,
    )
    
    # Process document
    await rag.process_document_complete(
        file_path="document.pdf",
        output_dir="./output"
    )
    
    # Query
    result = await rag.aquery("What is the main content?", mode="hybrid")
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 6. HPC Cluster Deployment (SLURM)

### 6.1 Architecture Overview

In HPC cluster environments, RAG-Anything uses this architecture:

```
Login Node
    ├── Submit SLURM jobs
    ├── Configure environment variables
    └── Monitor job status

GPU Node - Run Ollama Service
    ├── Start Ollama service (ollama_gpu_job.sh)
    ├── Publish service endpoint info
    └── Keep service running long-term

Compute Node - Run RAG Workloads
    ├── Read Ollama endpoint
    ├── Execute document ingest/query (rag_worker_job.sh)
    └── Use shared storage
```

### 6.2 Environment Setup

#### Step 1: Configure Login Node Environment

```bash
# On login node, activate environment
cd /ShareS/UserHome/user007/software/RAG-Anything
source scripts/login_env.sh

# Output example:
# [INFO] RAG-Anything login environment configured.
# [INFO] Shared root: /ShareS/UserHome/user007/rag-data
# [INFO] Runtime state: /ShareS/UserHome/user007/rag-data/runtime
# [INFO] Logs: /ShareS/UserHome/user007/software/RAG-Anything/logs/slurm
```

This script sets:
- `RAG_SHARED_ROOT`: Shared data directory
- `RAG_RUNTIME_STATE`: Runtime state files (Ollama endpoint info)
- `LOG_ROOT`: Log directory
- `OLLAMA_*`: Ollama configuration
- `RERANKER_*`: Reranker model configuration

#### Step 2: Prepare Required Files and Models

```bash
# Ensure shared directories exist
mkdir -p ${RAG_SHARED_ROOT}
mkdir -p ${RAG_RUNTIME_STATE}
mkdir -p ${LOG_ROOT}

# Download Reranker model (if needed)
# This model will be shared by GPU and compute nodes
mkdir -p ${HOME}/.huggingface/models
# Download bge-v2-gemma or other reranker models to this directory

# Check Ollama setup script
ls -l ${HOME}/setup/ollama.sh
```

### 6.3 Start Ollama GPU Service

#### Method 1: Use Default Configuration

```bash
# Submit GPU job (using script defaults)
sbatch scripts/slurm/ollama_gpu_job.sh

# Check job status
squeue -u $USER

# View logs
tail -f logs/slurm/ollama-<JOB_ID>.out
```

#### Method 2: Custom Resource Configuration

```bash
# Use different partition and GPU count
sbatch --partition=A100 --gres=gpu:2 scripts/slurm/ollama_gpu_job.sh

# Custom runtime
sbatch --time=48:00:00 scripts/slurm/ollama_gpu_job.sh
```

#### Method 3: Override Environment Variables

```bash
# Custom Ollama configuration
export OLLAMA_PORT=12345
export OLLAMA_CACHE=${HOME}/custom_ollama_cache
sbatch scripts/slurm/ollama_gpu_job.sh
```

#### Verify Ollama Service

```bash
# Wait for service to start (usually 30-60 seconds)
sleep 60

# Check service endpoint file
cat ${RAG_RUNTIME_STATE}/ollama_service.json

# Output example:
# {
#   "host": "gpu-node-01",
#   "port": 11434,
#   "job_id": "123456",
#   "cache": "/home/user007/.ollama/models",
#   "updated_at": "2025-01-15T10:30:00Z"
# }

# Test connection (from login node)
curl http://gpu-node-01:11434/api/tags
```

### 6.4 Run RAG Workloads

#### Scenario 1: Document Ingestion

```bash
# Set input file
export RAG_INPUT_FILE=/ShareS/UserHome/user007/data/paper.pdf
export RAG_WORKER_MODE=ingest

# Submit job (using default command)
sbatch scripts/slurm/rag_worker_job.sh

# Or specify Ollama host (if not auto-discovered)
export OLLAMA_HOST=http://gpu-node-01:11434
sbatch scripts/slurm/rag_worker_job.sh
```

#### Scenario 2: Custom Command

```bash
# Run custom Python script
sbatch scripts/slurm/rag_worker_job.sh -- \
  uv run python scripts/cluster_rag_worker.py \
  --mode ingest \
  --input-file /path/to/document.pdf \
  --working-dir ${RAG_SHARED_ROOT}/workspace \
  --parser mineru \
  --llm-model qwen2.5:latest \
  --embed-model bge-m3:latest \
  --embed-dim 1024
```

#### Scenario 3: Query Knowledge Base

```bash
# Submit query job
sbatch scripts/slurm/rag_worker_job.sh -- \
  uv run python scripts/cluster_rag_worker.py \
  --mode query \
  --query "What are the main findings?" \
  --working-dir ${RAG_SHARED_ROOT}/workspace \
  --query-mode hybrid
```

### 6.5 Monitoring and Debugging

#### View Logs

```bash
# Real-time Ollama logs
tail -f logs/slurm/ollama-<JOB_ID>.out
tail -f logs/slurm/ollama-serve.log

# Real-time RAG worker logs
tail -f logs/slurm/rag-worker-<JOB_ID>.out

# List all logs
ls -lht logs/slurm/
```

#### Common Troubleshooting

**Issue 1: RAG worker can't find Ollama service**

```bash
# Check service file exists
ls -l ${RAG_RUNTIME_STATE}/ollama_service.json

# Manually set OLLAMA_HOST
export OLLAMA_HOST=http://gpu-node-01:11434
```

**Issue 2: GPU node can't start Ollama**

```bash
# Check Ollama installation
which ollama
ollama --version

# Check GPU availability
nvidia-smi

# Check environment script
cat ${HOME}/setup/ollama.sh
```

**Issue 3: Compute nodes have no network access**

```bash
# Ensure tiktoken cache is pre-downloaded
export TIKTOKEN_CACHE_DIR=${HOME}/.cache/tiktoken
ls -l ${TIKTOKEN_CACHE_DIR}

# Pre-download models to shared storage
# Run on login node with network:
ollama pull qwen2.5:latest
ollama pull bge-m3:latest
```

### 6.6 Cluster Configuration Reference

#### `scripts/login_env.sh` - Key Environment Variables

```bash
# Shared storage
RAG_SHARED_ROOT=/ShareS/UserHome/user007/rag-data
RAG_RUNTIME_STATE=${RAG_SHARED_ROOT}/runtime

# Ollama configuration
OLLAMA_PORT=11434
OLLAMA_GENERATE_MODEL=qwen3:235b
OLLAMA_EMBED_MODEL=qwen3-embedding:8b
OLLAMA_EMBED_DIM=8192
OLLAMA_TIMEOUT_SECONDS=300

# Reranker configuration
RERANKER_MODEL_PATH=${HOME}/.huggingface/models/bge-v2-gemma
RERANKER_USE_FP16=1

# Cache directories
HF_HOME=${HOME}/.huggingface
TIKTOKEN_CACHE_DIR=${HOME}/.cache/tiktoken
```

#### Custom Configuration Example

```bash
# Override defaults before job submission
export OLLAMA_GENERATE_MODEL=llama3:70b
export OLLAMA_EMBED_MODEL=nomic-embed-text:latest
export OLLAMA_EMBED_DIM=768
export OLLAMA_TIMEOUT_SECONDS=600

# Submit job
sbatch scripts/slurm/rag_worker_job.sh
```

### 6.7 Best Practices

1. **Use Shared Storage**: Ensure all nodes access the same `RAG_SHARED_ROOT`
2. **Pre-download Models**: Download all models to shared cache on login node
3. **Monitor Resources**: Use `squeue`, `sacct` to monitor job status
4. **Log Management**: Regularly clean up `logs/slurm/` directory
5. **Long-running Service**: Set long time limits for Ollama GPU jobs (24-48 hours)
6. **Error Handling**: Scripts include health checks and auto-cleanup logic

---

## 7. Configuration Guide

### 7.1 Parser Configuration

#### MinerU Configuration

```python
# Basic parsing
await rag.process_document_complete(
    file_path="document.pdf",
    parser="mineru",
    parse_method="auto",  # auto/ocr/txt
)

# Advanced configuration
await rag.process_document_complete(
    file_path="document.pdf",
    parser="mineru",
    parse_method="auto",
    
    # MinerU-specific parameters
    lang="en",              # OCR language: ch/en/ja
    device="cuda:0",        # Inference device: cpu/cuda/npu/mps
    start_page=0,           # Start page (PDF)
    end_page=10,            # End page
    formula=True,           # Enable formula parsing
    table=True,             # Enable table parsing
    backend="pipeline",     # Backend: pipeline/vlm-*
    source="huggingface",   # Model source
)
```

#### Docling Configuration

```python
await rag.process_document_complete(
    file_path="document.docx",
    parser="docling",
    parse_method="auto",
)
```

### 7.2 Processor Configuration

```python
config = RAGAnythingConfig(
    working_dir="./rag_storage",
    parser="mineru",
    parse_method="auto",
    
    # Multimodal processing toggles
    enable_image_processing=True,
    enable_table_processing=True,
    enable_equation_processing=True,
)
```

### 7.3 Query Modes

```python
# Four query modes
result = await rag.aquery("question", mode="naive")    # Simple vector search
result = await rag.aquery("question", mode="local")    # Local graph traversal
result = await rag.aquery("question", mode="global")   # Global graph analysis
result = await rag.aquery("question", mode="hybrid")   # Hybrid (recommended)
```

### 7.4 Environment Variables Configuration

Complete `.env` file example:

```bash
# ===== Basic Configuration =====
# LLM Configuration
LLM_BINDING=openai
LLM_MODEL=gpt-4o-mini
LLM_BINDING_HOST=https://api.openai.com/v1
LLM_BINDING_API_KEY=your_api_key

# Embedding Model
EMBEDDING_BINDING=openai
EMBEDDING_MODEL=text-embedding-3-large
EMBEDDING_DIM=3072
EMBEDDING_BINDING_API_KEY=your_api_key

# ===== RAGAnything Configuration =====
# Parser
PARSER=mineru
PARSE_METHOD=auto
OUTPUT_DIR=./output

# Multimodal Processing
ENABLE_IMAGE_PROCESSING=true
ENABLE_TABLE_PROCESSING=true
ENABLE_EQUATION_PROCESSING=true

# Batch Processing
MAX_CONCURRENT_FILES=2
RECURSIVE_FOLDER_PROCESSING=true

# ===== Advanced Configuration =====
# Retrieval Parameters
TOP_K=60
COSINE_THRESHOLD=0.2
MAX_TOKEN_TEXT_CHUNK=4000

# Entity and Relation
SUMMARY_LANGUAGE=English
CHUNK_SIZE=1200
CHUNK_OVERLAP_SIZE=100

# LLM Cache
ENABLE_LLM_CACHE=true
MAX_ASYNC=4
MAX_TOKENS=32768
TEMPERATURE=0

# ===== Cluster Configuration (Optional) =====
# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_GENERATE_MODEL=qwen2.5:latest
OLLAMA_EMBED_MODEL=bge-m3:latest
OLLAMA_EMBED_DIM=1024

# Shared Storage
RAG_SHARED_ROOT=/path/to/shared/storage
RERANKER_MODEL_PATH=/path/to/reranker/model
```

---

## 8. FAQ

### 8.1 Installation Issues

**Q: MinerU installation failed?**

```bash
# Check Python version
python --version  # Need 3.10+

# Clear cache and reinstall
pip cache purge
pip install --no-cache-dir 'raganything[all]'

# If network timeout
pip install --default-timeout=100 raganything
```

**Q: LibreOffice not detected?**

```bash
# Check installation
which libreoffice
libreoffice --version

# Test Office document parsing
python examples/office_document_test.py --check-libreoffice --file dummy
```

**Q: GPU issues?**

```bash
# Check CUDA
nvidia-smi
nvcc --version

# MinerU GPU acceleration
await rag.process_document_complete(
    file_path="doc.pdf",
    device="cuda:0",  # Specify GPU
    backend="pipeline"
)
```

### 8.2 Usage Issues

**Q: How to handle large files?**

```python
# Method 1: Process by pages
await rag.process_document_complete(
    file_path="large.pdf",
    start_page=0,
    end_page=50  # Process first 50 pages
)

# Method 2: Increase timeout
import os
os.environ['TIMEOUT'] = '600'  # 10 minutes

# Method 3: Adjust chunk size
config = RAGAnythingConfig(
    chunk_size=800,  # Smaller chunks
    chunk_overlap=50
)
```

**Q: How to improve query speed?**

```python
# 1. Use local embedding model
EMBEDDING_BINDING=ollama
EMBEDDING_MODEL=bge-m3:latest

# 2. Adjust retrieval parameters
os.environ['TOP_K'] = '30'  # Fewer results
os.environ['MAX_ASYNC'] = '8'  # More concurrency

# 3. Enable caching
ENABLE_LLM_CACHE=true
```

**Q: How to handle specific language documents?**

```python
# OCR language setting
await rag.process_document_complete(
    file_path="chinese_doc.pdf",
    lang="ch",  # Chinese
    parse_method="ocr"
)

# Entity extraction language
os.environ['SUMMARY_LANGUAGE'] = 'Chinese'
```

### 8.3 Error Handling

**Error 1: `ModuleNotFoundError: No module named 'raganything'`**

```bash
# Confirm installation
pip list | grep raganything

# Reinstall
pip install --upgrade raganything
```

**Error 2: `FileNotFoundError: No such file or directory: 'mineru'`**

```bash
# Check MinerU
which mineru
mineru --version

# Reinstall
pip install --force-reinstall 'mineru[core]'
```

**Error 3: `RuntimeError: CUDA out of memory`**

```python
# Use CPU
await rag.process_document_complete(
    file_path="doc.pdf",
    device="cpu"
)

# Or reduce batch size
os.environ['EMBEDDING_BATCH_NUM'] = '16'
```

---

## 9. Advanced Usage

### 9.1 Custom Modal Processors

```python
from raganything.modalprocessors import GenericModalProcessor

class CustomVideoProcessor(GenericModalProcessor):
    """Custom video processor"""
    
    async def process_multimodal_content(
        self, 
        modal_content, 
        content_type, 
        file_path, 
        entity_name
    ):
        # Extract key frames
        frames = self.extract_key_frames(modal_content['video_path'])
        
        # Analyze frames with VLM
        descriptions = []
        for frame in frames:
            desc = await self.modal_caption_func(
                prompt="Describe this frame",
                image_data=frame
            )
            descriptions.append(desc)
        
        # Merge descriptions
        enhanced_description = "\n".join(descriptions)
        
        # Create entity
        entity_info = self.create_custom_entity(
            enhanced_description, 
            entity_name
        )
        
        return await self._create_entity_and_chunk(
            enhanced_description, 
            entity_info, 
            file_path
        )

# Use custom processor
video_processor = CustomVideoProcessor(
    lightrag=rag.lightrag,
    modal_caption_func=vision_model_func
)

# Process video content
await video_processor.process_multimodal_content(
    modal_content={"video_path": "video.mp4"},
    content_type="video",
    file_path="presentation.pptx",
    entity_name="Demo Video"
)
```

### 9.2 Context-Aware Processing

```python
# Enable context extraction
os.environ['CONTEXT_WINDOW'] = '2'  # 2 elements before/after
os.environ['CONTEXT_MODE'] = 'page'  # or 'element'
os.environ['INCLUDE_HEADERS'] = 'true'
os.environ['INCLUDE_CAPTIONS'] = 'true'

# Process document (auto context extraction)
await rag.process_document_complete(
    file_path="document.pdf",
    output_dir="./output"
)
```

See: [context_aware_processing.md](context_aware_processing.md)

### 9.3 Batch Processing Optimization

```python
# Parallel processing
os.environ['MAX_CONCURRENT_FILES'] = '4'
os.environ['MAX_PARALLEL_INSERT'] = '2'

await rag.process_folder_complete(
    folder_path="./documents",
    output_dir="./output",
    max_workers=4
)
```

See: [batch_processing.md](batch_processing.md)

### 9.4 Enhanced Markdown Output

```python
# Enable enhanced output
await rag.process_document_complete(
    file_path="document.pdf",
    output_dir="./output",
    enhanced_markdown=True  # Generate enhanced Markdown
)
```

See: [enhanced_markdown.md](enhanced_markdown.md)

### 9.5 Database Backend Selection

```bash
# PostgreSQL + pgvector (Recommended)
LIGHTRAG_KV_STORAGE=PGKVStorage
LIGHTRAG_VECTOR_STORAGE=PGVectorStorage
LIGHTRAG_GRAPH_STORAGE=Neo4JStorage
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# Neo4j Graph Database
NEO4J_URI=neo4j+s://xxx.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password

# Milvus Vector Database
MILVUS_URI=http://localhost:19530
MILVUS_DB_NAME=lightrag
```

---

## 10. Summary & Next Steps

### 10.1 Learning Path

```
Day 1: Basic Setup
├── Install RAG-Anything
├── Configure API keys or Ollama
└── Run first example

Day 2: Core Concepts
├── Document parsing flow
├── Multimodal processors
└── Query mode comparison

Day 3: Practical Scenarios
├── Process your own documents
├── Try different query methods
└── Adjust configuration

Day 4: Advanced Features
├── Batch document processing
├── Custom processors
└── Workflow integration

Day 5: Production Deployment (Optional)
├── HPC cluster deployment
├── Database backend configuration
└── Performance optimization
```

### 10.2 Quick Command Reference

```bash
# Installation
pip install 'raganything[all]'

# Run example
python examples/raganything_example.py document.pdf --api-key YOUR_KEY

# Check installation
python -c "from raganything import RAGAnything; print('✅ OK')"

# Test MinerU
mineru --version

# Test LibreOffice
libreoffice --version

# HPC: Start Ollama
source scripts/login_env.sh
sbatch scripts/slurm/ollama_gpu_job.sh

# HPC: Submit RAG job
export RAG_INPUT_FILE=/path/to/doc.pdf
sbatch scripts/slurm/rag_worker_job.sh
```

### 10.3 Resources

- **Main Docs**: [README.md](../README.md)
- **Examples**: `examples/` directory
- **Configuration**: `env.example`
- **GitHub Issues**: [Report Issues](https://github.com/HKUDS/RAG-Anything/issues)
- **Paper**: [LightRAG arXiv](https://arxiv.org/abs/2410.05779)

### 10.4 Community Support

- **Discord**: [Join Community](https://discord.gg/yF2MmDJyGJ)
- **GitHub Discussions**: [Discussions](https://github.com/HKUDS/RAG-Anything/discussions)

---

## Appendix: Glossary

| Term | Description |
|------|-------------|
| RAG | Retrieval-Augmented Generation - AI technique combining retrieval and generation |
| Multimodal | Processing text, images, tables, and other diverse data types |
| Knowledge Graph | Structured network of entities and relationships |
| Embedding | Vector representation of text |
| LLM | Large Language Model (e.g., GPT, Qwen) |
| VLM | Vision Language Model - LLM with image processing capability |
| Document Parsing | Extract structured content from PDF and other formats |
| OCR | Optical Character Recognition |
| Vector Database | Database for storing and retrieving vector embeddings |
| Hybrid Retrieval | Combine vector search and graph traversal |

---

## Conclusion

This guide covers everything from getting started with RAG-Anything to advanced deployment scenarios. Whether you're a researcher, developer, or data scientist, you can choose the approach that fits your needs.

**Key Takeaways:**

1. ✅ **Simple Start**: PyPI install + OpenAI API
2. ✅ **Local Deployment**: Ollama + Free models
3. ✅ **Production Grade**: HPC cluster + SLURM
4. ✅ **Flexible Extension**: Custom processors + Multiple backends

Start your RAG-Anything journey today! 🚀

---

<div align="center">

**[⭐ Star the Project](https://github.com/HKUDS/RAG-Anything)** | 
**[🐛 Report Issues](https://github.com/HKUDS/RAG-Anything/issues)** | 
**[💬 Discussions](https://github.com/HKUDS/RAG-Anything/discussions)**

</div>

