# RAG-Anything 新手快速入门指南

> **翻译说明**: 这是为中文用户准备的快速入门指南。The user requested this in Chinese: "How should I use this RAG-Anything project? Can you summarize the current situation and create a tutorial for newcomers?"

## 📖 目录

1. [RAG-Anything 是什么？](#1-rag-anything-是什么)
2. [核心功能](#2-核心功能)
3. [系统架构](#3-系统架构)
4. [快速开始](#4-快速开始)
5. [使用场景和示例](#5-使用场景和示例)
6. [HPC 集群部署](#6-hpc-集群部署slurm)
7. [配置详解](#7-配置详解)
8. [常见问题](#8-常见问题)
9. [进阶使用](#9-进阶使用)

---

## 1. RAG-Anything 是什么？

**RAG-Anything** 是一个**全能多模态文档处理 RAG（检索增强生成）系统**，建立在 [LightRAG](https://github.com/HKUDS/LightRAG) 之上。

### 为什么需要 RAG-Anything？

传统的 RAG 系统只能处理纯文本，但现代文档往往包含：
- 📊 **表格数据**
- 🖼️ **图片、图表**  
- 📐 **数学公式**
- 📄 **混合排版的 PDF、Office 文档**

RAG-Anything 解决了这个痛点，**一站式处理所有类型的文档内容**。

### 核心优势

| 特性 | 说明 |
|-----|------|
| 🔄 端到端多模态流程 | 从文档解析到智能问答一条龙 |
| 📄 通用文档支持 | PDF、Word、PPT、Excel、图片、Markdown 等 |
| 🧠 专业内容分析 | 针对图片、表格、公式的专门处理器 |
| 🔗 多模态知识图谱 | 自动提取实体和跨模态关系 |
| ⚡ 灵活的处理模式 | 支持 MinerU、Docling 等多种解析器 |
| 🎯 混合智能检索 | 文本+多模态内容的上下文感知搜索 |

---

## 2. 核心功能

### 2.1 文档解析阶段

**支持的解析器：**
- **MinerU**: 强大的 OCR 和表格提取，支持 GPU 加速
- **Docling**: 针对 Office 文档优化，更好的结构保留

**支持的文档格式：**
```
PDF、DOC/DOCX、PPT/PPTX、XLS/XLSX
JPG/PNG/BMP/TIFF/GIF/WebP
TXT、Markdown
```

### 2.2 多模态内容理解

系统会自动识别并处理：
- 🔍 **图片**: 使用视觉模型生成描述
- 📊 **表格**: 结构化数据解释和统计分析
- 📐 **公式**: LaTeX 格式支持，概念映射
- 🔧 **自定义内容**: 可扩展的处理框架

### 2.3 知识图谱索引

- 提取多模态实体
- 建立跨模态关系
- 保留文档层次结构
- 加权关系评分

### 2.4 智能检索

提供三种查询方式：
1. **纯文本查询**: 直接搜索知识库
2. **VLM 增强查询**: 自动分析检索到的图片
3. **多模态查询**: 结合特定多模态内容进行分析

---

## 3. 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                      RAG-Anything 系统架构                        │
└─────────────────────────────────────────────────────────────────┘

    文档输入 (PDF/Office/Images)
         ↓
    ┌────────────┐
    │  解析层    │  MinerU / Docling
    └────────────┘
         ↓
    ┌────────────┐
    │  内容分类  │  自动路由到不同处理器
    └────────────┘
         ↓
    ┌─────────────────────────────────────┐
    │    多模态处理器 (并行处理)         │
    │  • ImageModalProcessor             │
    │  • TableModalProcessor             │
    │  • EquationModalProcessor          │
    │  • GenericModalProcessor           │
    └─────────────────────────────────────┘
         ↓
    ┌────────────┐
    │ LightRAG   │  知识图谱构建
    │ 知识图谱   │  • 实体提取
    └────────────┘  • 关系建立
         ↓
    ┌────────────┐
    │  智能检索  │  • 向量相似度
    │            │  • 图遍历
    └────────────┘  • 上下文感知
         ↓
    查询结果输出
```

---

## 4. 快速开始

### 4.1 环境要求

- **Python**: 3.10+
- **操作系统**: Linux/macOS/Windows
- **可选**: LibreOffice (处理 Office 文档)

### 4.2 安装

#### 方式 1: 从 PyPI 安装（推荐）

```bash
# 基础安装
pip install raganything

# 完整安装（包含所有可选依赖）
pip install 'raganything[all]'

# 按需安装
pip install 'raganything[image]'        # 图片格式支持
pip install 'raganything[text]'         # 文本文件支持
pip install 'raganything[image,text]'   # 多个功能
```

#### 方式 2: 从源码安装

```bash
# 安装 uv 包管理器
curl -LsSf https://astral.sh/uv/install.sh | sh

# 克隆项目
git clone https://github.com/HKUDS/RAG-Anything.git
cd RAG-Anything

# 安装依赖
uv sync

# 如果网络超时（特别是 opencv）：
UV_HTTP_TIMEOUT=120 uv sync

# 使用 uv 运行示例
uv run python examples/raganything_example.py --help

# 安装所有可选依赖
uv sync --all-extras
```

### 4.3 安装可选依赖

#### LibreOffice (Office 文档支持)

```bash
# macOS
brew install --cask libreoffice

# Ubuntu/Debian
sudo apt-get install libreoffice

# CentOS/RHEL
sudo yum install libreoffice

# Windows
# 从官网下载: https://www.libreoffice.org/download/download/
```

#### 验证 MinerU 安装

```bash
# 检查版本
mineru --version

# 检查配置
python -c "from raganything import RAGAnything; rag = RAGAnything(); print('✅ MinerU 安装正常' if rag.check_parser_installation() else '❌ MinerU 安装有问题')"
```

### 4.4 配置 API 密钥

创建 `.env` 文件（参考 `env.example`）：

```bash
# OpenAI 配置
LLM_BINDING=openai
LLM_MODEL=gpt-4o-mini
LLM_BINDING_HOST=https://api.openai.com/v1
LLM_BINDING_API_KEY=your_api_key_here

# 嵌入模型配置
EMBEDDING_BINDING=openai
EMBEDDING_MODEL=text-embedding-3-large
EMBEDDING_DIM=3072
EMBEDDING_BINDING_API_KEY=your_api_key_here

# 或使用本地 Ollama
# EMBEDDING_BINDING=ollama
# EMBEDDING_MODEL=bge-m3:latest
# EMBEDDING_DIM=1024
# EMBEDDING_BINDING_HOST=http://localhost:11434

# 文档处理配置
PARSER=mineru                    # 或 docling
PARSE_METHOD=auto                # auto/ocr/txt
ENABLE_IMAGE_PROCESSING=true
ENABLE_TABLE_PROCESSING=true
ENABLE_EQUATION_PROCESSING=true
```

---

## 5. 使用场景和示例

### 5.1 场景一：处理学术论文（端到端）

**用例**: 分析一篇包含大量图表和公式的 PDF 论文

```python
import asyncio
from raganything import RAGAnything, RAGAnythingConfig
from lightrag.llm.openai import openai_complete_if_cache, openai_embed
from lightrag.utils import EmbeddingFunc

async def main():
    # 配置
    api_key = "your-api-key"
    base_url = "https://api.openai.com/v1"  # 可选
    
    # 创建配置
    config = RAGAnythingConfig(
        working_dir="./rag_storage",
        parser="mineru",
        parse_method="auto",
        enable_image_processing=True,
        enable_table_processing=True,
        enable_equation_processing=True,
    )
    
    # LLM 函数
    def llm_model_func(prompt, system_prompt=None, history_messages=[], **kwargs):
        return openai_complete_if_cache(
            "gpt-4o-mini",
            prompt,
            system_prompt=system_prompt,
            history_messages=history_messages,
            api_key=api_key,
            base_url=base_url,
            **kwargs,
        )
    
    # 视觉模型函数（用于图片分析）
    def vision_model_func(prompt, system_prompt=None, history_messages=[], 
                         image_data=None, messages=None, **kwargs):
        if messages:  # VLM 增强查询模式
            return openai_complete_if_cache(
                "gpt-4o", "", system_prompt=None, history_messages=[],
                messages=messages, api_key=api_key, base_url=base_url, **kwargs
            )
        elif image_data:  # 单图片模式
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
        else:  # 纯文本
            return llm_model_func(prompt, system_prompt, history_messages, **kwargs)
    
    # 嵌入函数
    embedding_func = EmbeddingFunc(
        embedding_dim=3072,
        max_token_size=8192,
        func=lambda texts: openai_embed(
            texts, model="text-embedding-3-large",
            api_key=api_key, base_url=base_url
        ),
    )
    
    # 初始化 RAGAnything
    rag = RAGAnything(
        config=config,
        llm_model_func=llm_model_func,
        vision_model_func=vision_model_func,
        embedding_func=embedding_func,
    )
    
    # 处理文档
    print("📄 正在处理论文...")
    await rag.process_document_complete(
        file_path="path/to/research_paper.pdf",
        output_dir="./output",
        parse_method="auto"
    )
    print("✅ 文档处理完成！")
    
    # 查询 1: 纯文本查询
    print("\n🔍 执行文本查询...")
    result = await rag.aquery(
        "论文的主要研究发现是什么？",
        mode="hybrid"
    )
    print(f"回答: {result}\n")
    
    # 查询 2: VLM 增强查询（自动分析图片）
    print("🔍 执行 VLM 增强查询...")
    result = await rag.aquery(
        "图表中展示了什么数据趋势？",
        mode="hybrid"
        # vlm_enhanced=True 当提供 vision_model_func 时自动启用
    )
    print(f"回答: {result}\n")
    
    # 查询 3: 带特定公式的多模态查询
    print("🔍 执行多模态查询...")
    result = await rag.aquery_with_multimodal(
        "解释这个公式并说明它与论文的关联",
        multimodal_content=[{
            "type": "equation",
            "latex": r"E = mc^2",
            "equation_caption": "质能方程"
        }],
        mode="hybrid"
    )
    print(f"回答: {result}")

if __name__ == "__main__":
    asyncio.run(main())
```

### 5.2 场景二：批量处理多个文档

```python
import asyncio
from raganything import RAGAnything

async def batch_process():
    # ... 初始化代码同上 ...
    
    # 批量处理整个文件夹
    await rag.process_folder_complete(
        folder_path="./documents",
        output_dir="./output",
        file_extensions=[".pdf", ".docx", ".pptx"],
        recursive=True,          # 递归处理子文件夹
        max_workers=4            # 并行处理数量
    )
    
    print("✅ 所有文档处理完成！")

asyncio.run(batch_process())
```

### 5.3 场景三：直接插入预解析内容

**用例**: 已有解析好的内容列表，无需重新解析

```python
import asyncio
from raganything import RAGAnything

async def insert_parsed_content():
    # ... 初始化 RAGAnything ...
    
    # 预解析的内容列表
    content_list = [
        {
            "type": "text",
            "text": "这是研究论文的引言部分。",
            "page_idx": 0
        },
        {
            "type": "image",
            "img_path": "/absolute/path/to/figure1.jpg",  # 必须是绝对路径
            "image_caption": ["图1：系统架构"],
            "image_footnote": ["来源：作者设计"],
            "page_idx": 1
        },
        {
            "type": "table",
            "table_body": "| 方法 | 准确率 | F1分数 |\n|-----|-------|-------|\n| 我们的 | 95.2% | 0.94 |\n| 基线 | 87.3% | 0.85 |",
            "table_caption": ["表1：性能对比"],
            "table_footnote": ["测试集结果"],
            "page_idx": 2
        },
        {
            "type": "equation",
            "latex": r"P(d|q) = \frac{P(q|d) \cdot P(d)}{P(q)}",
            "text": "文档相关性概率公式",
            "page_idx": 3
        }
    ]
    
    # 直接插入内容列表
    await rag.insert_content_list(
        content_list=content_list,
        file_path="research_paper.pdf",
        display_stats=True
    )
    
    # 查询
    result = await rag.aquery(
        "研究的主要性能指标是什么？",
        mode="hybrid"
    )
    print(f"回答: {result}")

asyncio.run(insert_parsed_content())
```

### 5.4 场景四：加载已有的 LightRAG 实例

**用例**: 已有一个 LightRAG 知识库，想添加多模态处理能力

```python
import asyncio
from raganything import RAGAnything
from lightrag import LightRAG
from lightrag.kg.shared_storage import initialize_pipeline_status
import os

async def load_existing():
    # 检查是否存在已有实例
    lightrag_dir = "./existing_lightrag_storage"
    if os.path.exists(lightrag_dir) and os.listdir(lightrag_dir):
        print("✅ 找到已有的 LightRAG 实例")
    
    # 加载已有的 LightRAG 实例
    lightrag_instance = LightRAG(
        working_dir=lightrag_dir,
        llm_model_func=...,  # 你的 LLM 函数
        embedding_func=...,  # 你的嵌入函数
    )
    await lightrag_instance.initialize_storages()
    await initialize_pipeline_status()
    
    # 用已有实例初始化 RAGAnything
    rag = RAGAnything(
        lightrag=lightrag_instance,  # 传入已有实例
        vision_model_func=...,       # 添加视觉模型支持
    )
    
    # 查询已有知识库
    result = await rag.aquery(
        "这个知识库中有什么数据？",
        mode="hybrid"
    )
    print(f"回答: {result}")
    
    # 向已有知识库添加新的多模态文档
    await rag.process_document_complete(
        file_path="new_document.pdf",
        output_dir="./output"
    )

asyncio.run(load_existing())
```

### 5.5 场景五：使用本地 Ollama 模型（无需 API 密钥）

```bash
# 1. 安装 Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 2. 拉取模型
ollama pull qwen2.5:latest        # LLM 模型
ollama pull bge-m3:latest         # 嵌入模型
ollama pull llava:latest          # 视觉模型（可选）

# 3. 启动 Ollama 服务（默认端口 11434）
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
    
    # 使用 Ollama
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
        embedding_dim=1024,
        max_token_size=8192,
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
    
    # 处理文档
    await rag.process_document_complete(
        file_path="document.pdf",
        output_dir="./output"
    )
    
    # 查询
    result = await rag.aquery("文档的主要内容是什么？", mode="hybrid")
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 6. HPC 集群部署（SLURM）

### 6.1 架构概览

在 HPC 集群环境中，RAG-Anything 使用以下架构：

```
登录节点 (Login Node)
    ├── 提交 SLURM 作业
    ├── 配置环境变量
    └── 监控作业状态

GPU 节点 (GPU Node) - 运行 Ollama 服务
    ├── 启动 Ollama 服务 (ollama_gpu_job.sh)
    ├── 发布服务端点信息
    └── 保持服务长期运行

计算节点 (Compute Node) - 运行 RAG 工作负载
    ├── 读取 Ollama 端点
    ├── 执行文档摄取/查询 (rag_worker_job.sh)
    └── 使用共享存储
```

### 6.2 环境准备

#### 步骤 1: 配置登录节点环境

```bash
# 在登录节点上，激活环境
cd /ShareS/UserHome/user007/software/RAG-Anything
source scripts/login_env.sh

# 输出示例：
# [INFO] RAG-Anything login environment configured.
# [INFO] Shared root: /ShareS/UserHome/user007/rag-data
# [INFO] Runtime state: /ShareS/UserHome/user007/rag-data/runtime
# [INFO] Logs: /ShareS/UserHome/user007/software/RAG-Anything/logs/slurm
```

这个脚本会设置：
- `RAG_SHARED_ROOT`: 共享数据目录
- `RAG_RUNTIME_STATE`: 运行时状态文件（Ollama 端点信息）
- `LOG_ROOT`: 日志目录
- `OLLAMA_*`: Ollama 配置
- `RERANKER_*`: 重排序模型配置

#### 步骤 2: 准备必需的文件和模型

```bash
# 确保共享目录存在
mkdir -p ${RAG_SHARED_ROOT}
mkdir -p ${RAG_RUNTIME_STATE}
mkdir -p ${LOG_ROOT}

# 下载 Reranker 模型（如果需要）
# 这个模型会被 GPU 节点和计算节点共享
mkdir -p ${HOME}/.huggingface/models
# 下载 bge-v2-gemma 或其他重排序模型到此目录

# 检查 Ollama 安装脚本
ls -l ${HOME}/setup/ollama.sh
```

### 6.3 启动 Ollama GPU 服务

#### 方法 1: 使用默认配置

```bash
# 提交 GPU 作业（使用脚本中的默认配置）
sbatch scripts/slurm/ollama_gpu_job.sh

# 检查作业状态
squeue -u $USER

# 查看日志
tail -f logs/slurm/ollama-<JOB_ID>.out
```

#### 方法 2: 自定义资源配置

```bash
# 使用不同的分区和 GPU 数量
sbatch --partition=A100 --gres=gpu:2 scripts/slurm/ollama_gpu_job.sh

# 自定义运行时间
sbatch --time=48:00:00 scripts/slurm/ollama_gpu_job.sh
```

#### 方法 3: 覆盖环境变量

```bash
# 自定义 Ollama 配置
export OLLAMA_PORT=12345
export OLLAMA_CACHE=${HOME}/custom_ollama_cache
sbatch scripts/slurm/ollama_gpu_job.sh
```

#### 验证 Ollama 服务

```bash
# 等待服务启动（通常 30-60 秒）
sleep 60

# 检查服务端点文件
cat ${RAG_RUNTIME_STATE}/ollama_service.json

# 输出示例：
# {
#   "host": "gpu-node-01",
#   "port": 11434,
#   "job_id": "123456",
#   "cache": "/home/user007/.ollama/models",
#   "updated_at": "2025-01-15T10:30:00Z"
# }

# 测试连接（从登录节点）
curl http://gpu-node-01:11434/api/tags
```

### 6.4 运行 RAG 工作负载

#### 场景 1: 文档摄取（Ingest）

```bash
# 设置输入文件
export RAG_INPUT_FILE=/ShareS/UserHome/user007/data/paper.pdf
export RAG_WORKER_MODE=ingest

# 提交作业（使用默认命令）
sbatch scripts/slurm/rag_worker_job.sh

# 或指定 Ollama 主机（如果未自动发现）
export OLLAMA_HOST=http://gpu-node-01:11434
sbatch scripts/slurm/rag_worker_job.sh
```

#### 场景 2: 自定义命令

```bash
# 运行自定义 Python 脚本
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

#### 场景 3: 查询知识库

```bash
# 提交查询作业
sbatch scripts/slurm/rag_worker_job.sh -- \
  uv run python scripts/cluster_rag_worker.py \
  --mode query \
  --query "论文的主要发现是什么？" \
  --working-dir ${RAG_SHARED_ROOT}/workspace \
  --query-mode hybrid
```

### 6.5 监控和调试

#### 查看日志

```bash
# 实时查看 Ollama 日志
tail -f logs/slurm/ollama-<JOB_ID>.out
tail -f logs/slurm/ollama-serve.log

# 实时查看 RAG worker 日志
tail -f logs/slurm/rag-worker-<JOB_ID>.out

# 查看所有日志
ls -lht logs/slurm/
```

#### 常见问题排查

**问题 1: RAG worker 找不到 Ollama 服务**

```bash
# 检查服务文件是否存在
ls -l ${RAG_RUNTIME_STATE}/ollama_service.json

# 手动设置 OLLAMA_HOST
export OLLAMA_HOST=http://gpu-node-01:11434
```

**问题 2: GPU 节点无法启动 Ollama**

```bash
# 检查 Ollama 安装
which ollama
ollama --version

# 检查 GPU 可用性
nvidia-smi

# 检查环境脚本
cat ${HOME}/setup/ollama.sh
```

**问题 3: 计算节点没有网络访问**

```bash
# 确保 tiktoken 缓存已预下载
export TIKTOKEN_CACHE_DIR=${HOME}/.cache/tiktoken
ls -l ${TIKTOKEN_CACHE_DIR}

# 预下载模型文件到共享存储
# 在有网络的登录节点执行：
ollama pull qwen2.5:latest
ollama pull bge-m3:latest
```

### 6.6 集群配置文件参考

#### `scripts/login_env.sh` - 关键环境变量

```bash
# 共享存储
RAG_SHARED_ROOT=/ShareS/UserHome/user007/rag-data
RAG_RUNTIME_STATE=${RAG_SHARED_ROOT}/runtime

# Ollama 配置
OLLAMA_PORT=11434
OLLAMA_GENERATE_MODEL=qwen3:235b
OLLAMA_EMBED_MODEL=qwen3-embedding:8b
OLLAMA_EMBED_DIM=8192
OLLAMA_TIMEOUT_SECONDS=300

# Reranker 配置
RERANKER_MODEL_PATH=${HOME}/.huggingface/models/bge-v2-gemma
RERANKER_USE_FP16=1

# 缓存目录
HF_HOME=${HOME}/.huggingface
TIKTOKEN_CACHE_DIR=${HOME}/.cache/tiktoken
```

#### 自定义配置示例

```bash
# 在提交作业前覆盖默认值
export OLLAMA_GENERATE_MODEL=llama3:70b
export OLLAMA_EMBED_MODEL=nomic-embed-text:latest
export OLLAMA_EMBED_DIM=768
export OLLAMA_TIMEOUT_SECONDS=600

# 提交作业
sbatch scripts/slurm/rag_worker_job.sh
```

### 6.7 最佳实践

1. **使用共享存储**: 确保所有节点访问相同的 `RAG_SHARED_ROOT`
2. **预下载模型**: 在登录节点预先下载所有模型到共享缓存
3. **监控资源**: 使用 `squeue`, `sacct` 监控作业状态
4. **日志管理**: 定期清理 `logs/slurm/` 目录
5. **长期服务**: Ollama GPU 作业设置较长的时间限制（24-48小时）
6. **错误处理**: 脚本包含健康检查和自动清理逻辑

---

## 7. 配置详解

### 7.1 解析器配置

#### MinerU 配置

```python
# 基础解析
await rag.process_document_complete(
    file_path="document.pdf",
    parser="mineru",
    parse_method="auto",  # auto/ocr/txt
)

# 高级配置
await rag.process_document_complete(
    file_path="document.pdf",
    parser="mineru",
    parse_method="auto",
    
    # MinerU 特定参数
    lang="ch",              # OCR 语言: ch/en/ja
    device="cuda:0",        # 推理设备: cpu/cuda/npu/mps
    start_page=0,           # 起始页码（PDF）
    end_page=10,            # 结束页码
    formula=True,           # 启用公式解析
    table=True,             # 启用表格解析
    backend="pipeline",     # 后端: pipeline/vlm-*
    source="huggingface",   # 模型来源
)
```

#### Docling 配置

```python
await rag.process_document_complete(
    file_path="document.docx",
    parser="docling",
    parse_method="auto",
)
```

### 7.2 处理器配置

```python
config = RAGAnythingConfig(
    working_dir="./rag_storage",
    parser="mineru",
    parse_method="auto",
    
    # 多模态处理开关
    enable_image_processing=True,
    enable_table_processing=True,
    enable_equation_processing=True,
)
```

### 7.3 查询模式

```python
# 四种查询模式
result = await rag.aquery("问题", mode="naive")    # 简单向量搜索
result = await rag.aquery("问题", mode="local")    # 局部图遍历
result = await rag.aquery("问题", mode="global")   # 全局图分析
result = await rag.aquery("问题", mode="hybrid")   # 混合模式（推荐）
```

### 7.4 环境变量配置

`.env` 文件完整示例：

```bash
# ===== 基础配置 =====
# LLM 配置
LLM_BINDING=openai
LLM_MODEL=gpt-4o-mini
LLM_BINDING_HOST=https://api.openai.com/v1
LLM_BINDING_API_KEY=your_api_key

# 嵌入模型配置
EMBEDDING_BINDING=openai
EMBEDDING_MODEL=text-embedding-3-large
EMBEDDING_DIM=3072
EMBEDDING_BINDING_API_KEY=your_api_key

# ===== RAGAnything 配置 =====
# 解析器
PARSER=mineru
PARSE_METHOD=auto
OUTPUT_DIR=./output

# 多模态处理
ENABLE_IMAGE_PROCESSING=true
ENABLE_TABLE_PROCESSING=true
ENABLE_EQUATION_PROCESSING=true

# 批量处理
MAX_CONCURRENT_FILES=2
RECURSIVE_FOLDER_PROCESSING=true

# ===== 高级配置 =====
# 检索参数
TOP_K=60
COSINE_THRESHOLD=0.2
MAX_TOKEN_TEXT_CHUNK=4000

# 实体和关系配置
SUMMARY_LANGUAGE=Chinese
CHUNK_SIZE=1200
CHUNK_OVERLAP_SIZE=100

# LLM 缓存
ENABLE_LLM_CACHE=true
MAX_ASYNC=4
MAX_TOKENS=32768
TEMPERATURE=0

# ===== 集群配置（可选）=====
# Ollama 配置
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_GENERATE_MODEL=qwen2.5:latest
OLLAMA_EMBED_MODEL=bge-m3:latest
OLLAMA_EMBED_DIM=1024

# 共享存储
RAG_SHARED_ROOT=/path/to/shared/storage
RERANKER_MODEL_PATH=/path/to/reranker/model
```

---

## 8. 常见问题

### 8.1 安装相关

**Q: MinerU 安装失败怎么办？**

```bash
# 检查 Python 版本
python --version  # 需要 3.10+

# 清理缓存重新安装
pip cache purge
pip install --no-cache-dir 'raganything[all]'

# 如果网络超时
pip install --default-timeout=100 raganything
```

**Q: LibreOffice 未检测到？**

```bash
# 检查安装
which libreoffice
libreoffice --version

# 测试 Office 文档解析
python examples/office_document_test.py --check-libreoffice --file dummy
```

**Q: GPU 相关问题？**

```bash
# 检查 CUDA
nvidia-smi
nvcc --version

# MinerU GPU 加速
await rag.process_document_complete(
    file_path="doc.pdf",
    device="cuda:0",  # 指定 GPU
    backend="pipeline"
)
```

### 8.2 使用相关

**Q: 如何处理大文件？**

```python
# 方法 1: 分页处理
await rag.process_document_complete(
    file_path="large.pdf",
    start_page=0,
    end_page=50  # 先处理前 50 页
)

# 方法 2: 增加超时
import os
os.environ['TIMEOUT'] = '600'  # 10 分钟

# 方法 3: 调整 chunk 大小
config = RAGAnythingConfig(
    chunk_size=800,  # 减小 chunk 大小
    chunk_overlap=50
)
```

**Q: 如何提高查询速度？**

```python
# 1. 使用本地嵌入模型
EMBEDDING_BINDING=ollama
EMBEDDING_MODEL=bge-m3:latest

# 2. 调整检索参数
os.environ['TOP_K'] = '30'  # 减少返回数量
os.environ['MAX_ASYNC'] = '8'  # 增加并发

# 3. 使用缓存
ENABLE_LLM_CACHE=true
```

**Q: 如何处理特定语言文档？**

```python
# OCR 语言设置
await rag.process_document_complete(
    file_path="chinese_doc.pdf",
    lang="ch",  # 中文
    parse_method="ocr"
)

# 实体提取语言
os.environ['SUMMARY_LANGUAGE'] = 'Chinese'
```

### 8.3 错误处理

**错误 1: `ModuleNotFoundError: No module named 'raganything'`**

```bash
# 确认安装
pip list | grep raganything

# 重新安装
pip install --upgrade raganything
```

**错误 2: `FileNotFoundError: [Errno 2] No such file or directory: 'mineru'`**

```bash
# 检查 MinerU
which mineru
mineru --version

# 重新安装
pip install --force-reinstall 'mineru[core]'
```

**错误 3: `RuntimeError: CUDA out of memory`**

```python
# 使用 CPU
await rag.process_document_complete(
    file_path="doc.pdf",
    device="cpu"
)

# 或减小批处理大小
os.environ['EMBEDDING_BATCH_NUM'] = '16'
```

---

## 9. 进阶使用

### 9.1 自定义模态处理器

```python
from raganything.modalprocessors import GenericModalProcessor

class CustomVideoProcessor(GenericModalProcessor):
    """自定义视频处理器"""
    
    async def process_multimodal_content(
        self, 
        modal_content, 
        content_type, 
        file_path, 
        entity_name
    ):
        # 提取视频关键帧
        frames = self.extract_key_frames(modal_content['video_path'])
        
        # 使用 VLM 分析帧
        descriptions = []
        for frame in frames:
            desc = await self.modal_caption_func(
                prompt="描述这一帧的内容",
                image_data=frame
            )
            descriptions.append(desc)
        
        # 合并描述
        enhanced_description = "\n".join(descriptions)
        
        # 创建实体
        entity_info = self.create_custom_entity(
            enhanced_description, 
            entity_name
        )
        
        return await self._create_entity_and_chunk(
            enhanced_description, 
            entity_info, 
            file_path
        )

# 使用自定义处理器
video_processor = CustomVideoProcessor(
    lightrag=rag.lightrag,
    modal_caption_func=vision_model_func
)

# 处理视频内容
await video_processor.process_multimodal_content(
    modal_content={"video_path": "video.mp4"},
    content_type="video",
    file_path="presentation.pptx",
    entity_name="Demo Video"
)
```

### 9.2 上下文感知处理

```python
# 启用上下文提取
os.environ['CONTEXT_WINDOW'] = '2'  # 前后 2 个元素
os.environ['CONTEXT_MODE'] = 'page'  # 或 'element'
os.environ['INCLUDE_HEADERS'] = 'true'
os.environ['INCLUDE_CAPTIONS'] = 'true'

# 处理文档（自动提取上下文）
await rag.process_document_complete(
    file_path="document.pdf",
    output_dir="./output"
)
```

详细文档: [context_aware_processing.md](context_aware_processing.md)

### 9.3 批处理优化

```python
# 并行处理多个文件
os.environ['MAX_CONCURRENT_FILES'] = '4'
os.environ['MAX_PARALLEL_INSERT'] = '2'

await rag.process_folder_complete(
    folder_path="./documents",
    output_dir="./output",
    max_workers=4
)
```

详细文档: [batch_processing.md](batch_processing.md)

### 9.4 增强 Markdown 输出

```python
# 启用增强输出
await rag.process_document_complete(
    file_path="document.pdf",
    output_dir="./output",
    enhanced_markdown=True  # 生成增强的 Markdown
)
```

详细文档: [enhanced_markdown.md](enhanced_markdown.md)

### 9.5 数据库后端选择

```bash
# PostgreSQL + pgvector（推荐）
LIGHTRAG_KV_STORAGE=PGKVStorage
LIGHTRAG_VECTOR_STORAGE=PGVectorStorage
LIGHTRAG_GRAPH_STORAGE=Neo4JStorage
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# Neo4j 图数据库
NEO4J_URI=neo4j+s://xxx.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password

# Milvus 向量数据库
MILVUS_URI=http://localhost:19530
MILVUS_DB_NAME=lightrag
```

---

## 10. 总结和下一步

### 10.1 学习路径建议

```
第 1 天：基础设置
├── 安装 RAG-Anything
├── 配置 API 密钥或 Ollama
└── 运行第一个示例

第 2 天：理解核心概念
├── 文档解析流程
├── 多模态处理器
└── 查询模式对比

第 3 天：实践场景
├── 处理自己的文档
├── 尝试不同查询方式
└── 调整配置参数

第 4 天：进阶功能
├── 批处理文档
├── 自定义处理器
└── 集成到工作流

第 5 天：生产部署（可选）
├── HPC 集群部署
├── 数据库后端配置
└── 性能优化
```

### 10.2 常用命令速查

```bash
# 安装
pip install 'raganything[all]'

# 运行示例
python examples/raganything_example.py document.pdf --api-key YOUR_KEY

# 检查安装
python -c "from raganything import RAGAnything; print('✅ OK')"

# 测试 MinerU
mineru --version

# 测试 LibreOffice
libreoffice --version

# HPC: 启动 Ollama
source scripts/login_env.sh
sbatch scripts/slurm/ollama_gpu_job.sh

# HPC: 提交 RAG 作业
export RAG_INPUT_FILE=/path/to/doc.pdf
sbatch scripts/slurm/rag_worker_job.sh
```

### 10.3 参考资源

- **主文档**: [README.md](../README.md)
- **示例代码**: `examples/` 目录
- **配置参考**: `env.example`
- **GitHub Issues**: [报告问题](https://github.com/HKUDS/RAG-Anything/issues)
- **论文**: [LightRAG arXiv](https://arxiv.org/abs/2410.05779)

### 10.4 社区支持

- **Discord**: [加入社区](https://discord.gg/yF2MmDJyGJ)
- **微信群**: 见 [Issue #7](https://github.com/HKUDS/RAG-Anything/issues/7)
- **GitHub Discussions**: [讨论区](https://github.com/HKUDS/RAG-Anything/discussions)

---

## 附录: 术语表

| 术语 | 英文 | 说明 |
|-----|------|------|
| 检索增强生成 | RAG (Retrieval-Augmented Generation) | 结合检索和生成的 AI 技术 |
| 多模态 | Multimodal | 处理文本、图像、表格等多种类型的数据 |
| 知识图谱 | Knowledge Graph | 结构化的实体和关系网络 |
| 嵌入 | Embedding | 将文本转换为向量表示 |
| 大语言模型 | LLM (Large Language Model) | 如 GPT、Qwen 等 |
| 视觉语言模型 | VLM (Vision Language Model) | 可处理图像的 LLM |
| 文档解析 | Document Parsing | 从 PDF 等格式提取结构化内容 |
| OCR | Optical Character Recognition | 光学字符识别 |
| 向量数据库 | Vector Database | 存储和检索向量嵌入的数据库 |
| 混合检索 | Hybrid Retrieval | 结合向量搜索和图遍历 |

---

## 结语

这份指南涵盖了 RAG-Anything 从入门到进阶的各个方面。无论你是研究人员、开发者还是数据科学家，都可以根据自己的需求选择合适的使用方式。

**关键要点回顾：**

1. ✅ **简单开始**: PyPI 安装 + OpenAI API
2. ✅ **本地部署**: Ollama + 免费模型
3. ✅ **生产级**: HPC 集群 + SLURM
4. ✅ **灵活扩展**: 自定义处理器 + 多种后端

开始你的 RAG-Anything 之旅吧！ 🚀

---

<div align="center">

**[⭐ Star 项目](https://github.com/HKUDS/RAG-Anything)** | 
**[🐛 报告问题](https://github.com/HKUDS/RAG-Anything/issues)** | 
**[💬 讨论交流](https://github.com/HKUDS/RAG-Anything/discussions)**

</div>

