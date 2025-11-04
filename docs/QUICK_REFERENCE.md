# RAG-Anything Quick Reference Card

> **Print-friendly cheat sheet for common tasks**

## 🚀 Installation

```bash
# Basic
pip install raganything

# Full (recommended)
pip install 'raganything[all]'

# From source
git clone https://github.com/HKUDS/RAG-Anything.git
cd RAG-Anything
uv sync --all-extras
```

## ⚙️ Setup

### OpenAI API
```bash
export OPENAI_API_KEY=your_key
export OPENAI_BASE_URL=https://api.openai.com/v1  # optional
```

### Local Ollama
```bash
# Install and start
curl -fsSL https://ollama.com/install.sh | sh
ollama serve

# Pull models
ollama pull qwen2.5:latest
ollama pull bge-m3:latest
ollama pull llava:latest  # for vision
```

## 📄 Basic Usage

### Process Single Document
```python
import asyncio
from raganything import RAGAnything, RAGAnythingConfig

config = RAGAnythingConfig(
    working_dir="./rag_storage",
    parser="mineru",  # or "docling"
    enable_image_processing=True,
    enable_table_processing=True,
)

rag = RAGAnything(
    config=config,
    llm_model_func=your_llm_func,
    embedding_func=your_embed_func,
)

await rag.process_document_complete(
    file_path="document.pdf",
    output_dir="./output"
)
```

### Query
```python
# Text query
result = await rag.aquery("Your question?", mode="hybrid")

# VLM enhanced (auto image analysis)
result = await rag.aquery("What do the charts show?", mode="hybrid")

# Multimodal with specific content
result = await rag.aquery_with_multimodal(
    "Explain this formula",
    multimodal_content=[{
        "type": "equation",
        "latex": "E=mc^2",
        "equation_caption": "Energy equation"
    }],
    mode="hybrid"
)
```

## 🗂️ Batch Processing

```python
await rag.process_folder_complete(
    folder_path="./documents",
    output_dir="./output",
    file_extensions=[".pdf", ".docx", ".pptx"],
    recursive=True,
    max_workers=4
)
```

## 🖥️ HPC Cluster (SLURM)

### Setup
```bash
cd /path/to/RAG-Anything
source scripts/login_env.sh
```

### Start Ollama Service
```bash
# Default
sbatch scripts/slurm/ollama_gpu_job.sh

# Custom resources
sbatch --partition=A100 --gres=gpu:2 --time=48:00:00 \
  scripts/slurm/ollama_gpu_job.sh

# Check status
squeue -u $USER
cat ${RAG_RUNTIME_STATE}/ollama_service.json
```

### Run RAG Worker
```bash
# Ingest document
export RAG_INPUT_FILE=/path/to/document.pdf
sbatch scripts/slurm/rag_worker_job.sh

# Custom command
sbatch scripts/slurm/rag_worker_job.sh -- \
  uv run python scripts/cluster_rag_worker.py \
  --mode ingest \
  --input-file /path/to/doc.pdf \
  --parser mineru

# Query
sbatch scripts/slurm/rag_worker_job.sh -- \
  uv run python scripts/cluster_rag_worker.py \
  --mode query \
  --query "What is this about?"
```

## 🔧 Configuration (.env)

### Essential
```bash
# LLM
LLM_BINDING=openai
LLM_MODEL=gpt-4o-mini
LLM_BINDING_API_KEY=your_key

# Embedding
EMBEDDING_BINDING=openai
EMBEDDING_MODEL=text-embedding-3-large
EMBEDDING_DIM=3072

# Parser
PARSER=mineru
PARSE_METHOD=auto
```

### Performance
```bash
# Cache
ENABLE_LLM_CACHE=true

# Concurrency
MAX_ASYNC=4
MAX_PARALLEL_INSERT=2

# Retrieval
TOP_K=60
CHUNK_SIZE=1200
```

### Cluster
```bash
# Ollama
OLLAMA_BASE_URL=http://gpu-node:11434
OLLAMA_GENERATE_MODEL=qwen2.5:latest
OLLAMA_EMBED_MODEL=bge-m3:latest
OLLAMA_EMBED_DIM=1024

# Storage
RAG_SHARED_ROOT=/shared/storage
RERANKER_MODEL_PATH=/path/to/reranker
```

## 🎯 Query Modes

| Mode | Best For |
|------|----------|
| `naive` | Simple vector search |
| `local` | Local context, specific topics |
| `global` | Overview, summary questions |
| `hybrid` | **Recommended for most cases** |

## 🔍 Common Commands

### Verification
```bash
# Check installation
python -c "from raganything import RAGAnything; print('✅')"

# Check MinerU
mineru --version

# Check LibreOffice
libreoffice --version

# Test Ollama
curl http://localhost:11434/api/tags
```

### Examples
```bash
# Basic example
python examples/raganything_example.py doc.pdf --api-key KEY

# Batch processing
python examples/batch_processing_example.py

# Office test (no API key needed)
python examples/office_document_test.py --file doc.docx

# Check LibreOffice
python examples/office_document_test.py --check-libreoffice --file dummy
```

### Logs
```bash
# HPC logs
tail -f logs/slurm/ollama-<JOB_ID>.out
tail -f logs/slurm/rag-worker-<JOB_ID>.out
ls -lht logs/slurm/
```

## 🐛 Troubleshooting

### Installation Issues
```bash
# Clear cache
pip cache purge
pip install --no-cache-dir 'raganything[all]'

# Force reinstall
pip install --force-reinstall raganything
```

### MinerU Issues
```bash
# Reinstall
pip install --force-reinstall 'mineru[core]'

# Use CPU if GPU fails
await rag.process_document_complete(file_path="doc.pdf", device="cpu")
```

### Memory Issues
```bash
# Reduce batch size
export EMBEDDING_BATCH_NUM=16

# Process by pages
await rag.process_document_complete(
    file_path="large.pdf",
    start_page=0,
    end_page=50
)
```

### Ollama Connection
```bash
# Check service
curl http://localhost:11434/api/tags

# Manual host
export OLLAMA_HOST=http://gpu-node:11434
```

## 📚 Advanced Features

### Custom Processor
```python
from raganything.modalprocessors import GenericModalProcessor

class CustomProcessor(GenericModalProcessor):
    async def process_multimodal_content(self, modal_content, 
                                        content_type, file_path, entity_name):
        # Your logic here
        pass
```

### Context Extraction
```bash
export CONTEXT_WINDOW=2
export CONTEXT_MODE=page
export INCLUDE_HEADERS=true
```

### Direct Content Insertion
```python
content_list = [
    {"type": "text", "text": "...", "page_idx": 0},
    {"type": "image", "img_path": "/abs/path/img.jpg", 
     "image_caption": ["..."], "page_idx": 1},
    {"type": "table", "table_body": "...", 
     "table_caption": ["..."], "page_idx": 2},
]

await rag.insert_content_list(
    content_list=content_list,
    file_path="document.pdf"
)
```

### Load Existing LightRAG
```python
from lightrag import LightRAG

lightrag = LightRAG(working_dir="./existing")
await lightrag.initialize_storages()

rag = RAGAnything(
    lightrag=lightrag,  # Reuse existing
    vision_model_func=...
)
```

## 🔗 Quick Links

- **Full Guides**: `docs/QUICKSTART_GUIDE_zh.md` / `docs/QUICKSTART_GUIDE_en.md`
- **Tutorials Index**: `docs/TUTORIALS.md`
- **Examples**: `examples/` directory
- **GitHub**: https://github.com/HKUDS/RAG-Anything
- **Issues**: https://github.com/HKUDS/RAG-Anything/issues
- **Discord**: https://discord.gg/yF2MmDJyGJ

## 📝 Quick Notes

- **Parsers**: MinerU (powerful OCR) vs Docling (better for Office)
- **Parse Methods**: `auto` (smart), `ocr` (force OCR), `txt` (text only)
- **Default Port**: Ollama uses `11434`
- **Cache**: Models auto-download to `~/.cache/` on first use
- **GPU**: Set `device="cuda:0"` for GPU acceleration
- **Language**: Set `lang="ch"` for Chinese OCR, `lang="en"` for English

---

<div align="center">

**RAG-Anything v2025** | [⭐ Star](https://github.com/HKUDS/RAG-Anything) | [📖 Docs](https://github.com/HKUDS/RAG-Anything)

</div>

