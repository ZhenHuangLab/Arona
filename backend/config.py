"""
Unified Model Provider Configuration for RAG-Anything Backend

Supports multiple LLM/embedding providers via base_url + api_key pattern.
Eliminates Ollama-specific coupling while maintaining backward compatibility.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any

import yaml


class ProviderType(str, Enum):
    """Supported model provider types."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE = "azure"
    CUSTOM = "custom"  # Any OpenAI-compatible API
    LOCAL = "local"    # Local models (Ollama, LM Studio, etc.)
    LOCAL_GPU = "local_gpu"  # Local GPU inference (in-process HF/ST models)


class ModelType(str, Enum):
    """Model capability types."""
    LLM = "llm"              # Text generation
    VISION = "vision"        # Vision-language model
    EMBEDDING = "embedding"  # Text embeddings
    RERANKER = "reranker"    # Document reranking


@dataclass
class ModelConfig:
    """Configuration for a single model."""
    
    provider: ProviderType
    model_name: str
    model_type: ModelType
    
    # API configuration
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    
    # Model-specific parameters
    embedding_dim: Optional[int] = None  # For embedding models
    max_tokens: Optional[int] = None
    temperature: float = 0.7
    
    # Additional provider-specific settings
    extra_params: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate configuration."""
        # LOCAL_GPU only makes sense for in-process models.
        if self.provider == ProviderType.LOCAL_GPU and self.model_type != ModelType.EMBEDDING:
            raise ValueError("LOCAL_GPU provider is only supported for embedding models")

        # API-based providers require api_key
        if self.provider in [ProviderType.OPENAI, ProviderType.ANTHROPIC, ProviderType.AZURE]:
            if not self.api_key:
                raise ValueError(f"{self.provider} provider requires api_key")

        # Embedding models require dimension (but not rerankers)
        if self.model_type == ModelType.EMBEDDING:
            # Local GPU providers may omit embedding_dim (it can be determined from the model).
            device = self.extra_params.get("device")
            is_cuda_device = isinstance(device, str) and device.startswith("cuda")
            is_local_gpu = (
                self.provider == ProviderType.LOCAL_GPU
                or (self.provider == ProviderType.LOCAL and self.base_url is None and is_cuda_device)
            )
            if not is_local_gpu and not self.embedding_dim:
                raise ValueError("Embedding models require embedding_dim parameter")
    
    @classmethod
    def from_env(cls, prefix: str, model_type: ModelType) -> ModelConfig:
        """
        Create ModelConfig from environment variables.

        Example:
            LLM_PROVIDER=openai
            LLM_MODEL_NAME=gpt-4o-mini
            LLM_API_KEY=sk-...
            LLM_BASE_URL=https://api.openai.com/v1

            # For local GPU providers:
            EMBEDDING_PROVIDER=local_gpu
            EMBEDDING_MODEL_NAME=Qwen/Qwen3-Embedding-4B
            EMBEDDING_EMBEDDING_DIM=2560
            EMBEDDING_DEVICE=cuda:0
            EMBEDDING_DTYPE=float16
            EMBEDDING_ATTN_IMPLEMENTATION=sdpa
        """
        provider = os.getenv(f"{prefix}_PROVIDER", "openai")
        model_name = os.getenv(f"{prefix}_MODEL_NAME")
        api_key = os.getenv(f"{prefix}_API_KEY")
        base_url = os.getenv(f"{prefix}_BASE_URL")

        if model_name is not None:
            model_name = model_name.strip()
        if api_key == "":
            api_key = None
        if base_url == "":
            base_url = None

        if not model_name:
            raise ValueError(f"Missing required env var: {prefix}_MODEL_NAME")

        # Read optional parameters before creating the object
        embedding_dim = None
        if model_type == ModelType.EMBEDDING:
            dim = os.getenv(f"{prefix}_EMBEDDING_DIM")
            if dim:
                embedding_dim = int(dim)

        temperature = None
        temp = os.getenv(f"{prefix}_TEMPERATURE")
        if temp:
            temperature = float(temp)

        max_tokens = None
        max_tok = os.getenv(f"{prefix}_MAX_TOKENS")
        if max_tok:
            max_tokens = int(max_tok)

        # Read extra_params for local GPU providers
        extra_params = {}

        # Device configuration (for local GPU providers)
        device = os.getenv(f"{prefix}_DEVICE")
        if device:
            extra_params["device"] = device

        # Model path (for local models)
        model_path = os.getenv(f"{prefix}_MODEL_PATH")
        if model_path:
            extra_params["model_path"] = model_path

        # Data type (for local GPU providers)
        dtype = os.getenv(f"{prefix}_DTYPE")
        if dtype:
            extra_params["dtype"] = dtype

        # Attention implementation (for local GPU providers)
        attn_impl = os.getenv(f"{prefix}_ATTN_IMPLEMENTATION")
        if attn_impl:
            extra_params["attn_implementation"] = attn_impl

        # Batch processing parameters (for local GPU providers)
        # Token budget
        max_batch_tokens = os.getenv(f"{prefix}_MAX_BATCH_TOKENS")
        if max_batch_tokens:
            extra_params["max_batch_tokens"] = int(max_batch_tokens)

        # Dynamic batch size by number of requests
        max_batch_size = os.getenv(f"{prefix}_MAX_BATCH_SIZE")
        if max_batch_size:
            extra_params["max_batch_size"] = int(max_batch_size)

        # Batch collection wait time (preferred)
        max_wait_time = os.getenv(f"{prefix}_MAX_WAIT_TIME")
        if max_wait_time:
            extra_params["max_wait_time"] = float(max_wait_time)

        # Backward-compat alias: MAX_QUEUE_TIME → max_wait_time (only if not set above)
        max_queue_time = os.getenv(f"{prefix}_MAX_QUEUE_TIME")
        if max_queue_time and "max_wait_time" not in extra_params:
            extra_params["max_wait_time"] = float(max_queue_time)

        # Internal encode() batch size for sentence-transformers
        encode_batch_size = os.getenv(f"{prefix}_ENCODE_BATCH_SIZE")
        if encode_batch_size:
            extra_params["encode_batch_size"] = int(encode_batch_size)

        # Multimodal embedding parameters (used by MultimodalEmbeddingProvider)
        min_image_tokens = os.getenv(f"{prefix}_MIN_IMAGE_TOKENS")
        if min_image_tokens:
            extra_params["min_image_tokens"] = int(min_image_tokens)

        max_image_tokens = os.getenv(f"{prefix}_MAX_IMAGE_TOKENS")
        if max_image_tokens:
            extra_params["max_image_tokens"] = int(max_image_tokens)

        max_length = os.getenv(f"{prefix}_MAX_LENGTH")
        if max_length:
            extra_params["max_length"] = int(max_length)

        default_instruction = os.getenv(f"{prefix}_DEFAULT_INSTRUCTION")
        if default_instruction:
            extra_params["default_instruction"] = default_instruction

        normalize = os.getenv(f"{prefix}_NORMALIZE")
        if normalize:
            extra_params["normalize"] = normalize.lower() == "true"

        allow_image_urls = os.getenv(f"{prefix}_ALLOW_IMAGE_URLS")
        if allow_image_urls:
            extra_params["allow_image_urls"] = allow_image_urls.lower() == "true"

        max_image_bytes = os.getenv(f"{prefix}_MAX_IMAGE_BYTES")
        if max_image_bytes:
            extra_params["max_image_bytes"] = int(max_image_bytes)

        config = cls(
            provider=ProviderType(provider),
            model_name=model_name,
            model_type=model_type,
            api_key=api_key,
            base_url=base_url,
            embedding_dim=embedding_dim,
            temperature=temperature,
            max_tokens=max_tokens,
            extra_params=extra_params,
        )

        return config


@dataclass
class RerankerConfig:
    """Configuration for reranking models."""

    enabled: bool = True
    provider: str = "local"  # "local" or "api"

    # For local GPU reranker
    model_name: Optional[str] = None
    model_path: Optional[str] = None
    device: Optional[str] = None
    dtype: str = "float16"
    attn_implementation: str = "sdpa"
    batch_size: int = 16
    max_length: int = 8192
    min_image_tokens: int = 4
    max_image_tokens: int = 1280
    allow_image_urls: bool = False
    instruction: Optional[str] = None
    system_prompt: Optional[str] = None

    # For API-based reranker (future)
    api_key: Optional[str] = None
    base_url: Optional[str] = None

    @classmethod
    def from_env(cls) -> RerankerConfig:
        """Create RerankerConfig from environment variables."""
        enabled = os.getenv("RERANKER_ENABLED", "false").lower() == "true"
        provider = os.getenv("RERANKER_PROVIDER", "local")
        # Backward/forward compat: treat local_gpu as local (device decides CPU/GPU).
        if provider == "local_gpu":
            provider = "local"

        config = cls(
            enabled=enabled,
            provider=provider,
        )

        if provider == "local":
            config.model_name = os.getenv("RERANKER_MODEL_NAME") or None
            config.model_path = os.getenv("RERANKER_MODEL_PATH") or None
            config.device = os.getenv("RERANKER_DEVICE") or None

            config.instruction = os.getenv("RERANKER_INSTRUCTION") or None
            config.system_prompt = os.getenv("RERANKER_SYSTEM_PROMPT") or None

            min_image_tokens = os.getenv("RERANKER_MIN_IMAGE_TOKENS")
            if min_image_tokens:
                config.min_image_tokens = int(min_image_tokens)

            max_image_tokens = os.getenv("RERANKER_MAX_IMAGE_TOKENS")
            if max_image_tokens:
                config.max_image_tokens = int(max_image_tokens)

            allow_image_urls = os.getenv("RERANKER_ALLOW_IMAGE_URLS")
            if allow_image_urls:
                config.allow_image_urls = allow_image_urls.lower() == "true"

            dtype = os.getenv("RERANKER_DTYPE")
            if dtype:
                config.dtype = dtype

            attn_impl = os.getenv("RERANKER_ATTN_IMPLEMENTATION")
            if attn_impl:
                config.attn_implementation = attn_impl

            batch_size = os.getenv("RERANKER_BATCH_SIZE")
            if batch_size:
                config.batch_size = int(batch_size)

            max_length = os.getenv("RERANKER_MAX_LENGTH")
            if max_length:
                config.max_length = int(max_length)
        else:
            config.api_key = os.getenv("RERANKER_API_KEY") or None
            config.base_url = os.getenv("RERANKER_BASE_URL") or None
            config.model_name = os.getenv("RERANKER_MODEL_NAME") or None

        return config


@dataclass
class BackendConfig:
    """Complete backend configuration."""
    
    # Model configurations
    llm: ModelConfig
    embedding: ModelConfig
    vision: Optional[ModelConfig] = None
    reranker: Optional[RerankerConfig] = None
    multimodal_embedding: Optional[ModelConfig] = None
    
    # Storage configuration (will be converted to absolute paths in from_env)
    working_dir: str = "./rag_storage"
    upload_dir: str = "./uploads"
    
    # RAGAnything configuration
    parser: str = "mineru"  # or "docling"
    enable_parser_fallback: bool = True  # Fallback to alternative parser on failure
    fallback_parser: str = "docling"  # Parser to use when primary fails
    enable_image_processing: bool = True
    enable_table_processing: bool = True
    enable_equation_processing: bool = True
    mineru_device: Optional[str] = None  # Device for MinerU (cpu, cuda, cuda:0)
    mineru_vram: Optional[int] = None  # VRAM limit (MiB) for MinerU pipeline backend

    # Background indexing configuration
    auto_indexing_enabled: bool = True
    indexing_scan_interval: int = 60  # seconds between scans
    indexing_max_files_per_batch: int = 5  # max files to process per iteration

    # API server configuration
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: list[str] = field(default_factory=lambda: ["*"])
    
    @classmethod
    def from_env(cls) -> BackendConfig:
        """Create BackendConfig from environment variables."""
        
        # Load model configurations
        llm = ModelConfig.from_env("LLM", ModelType.LLM)
        embedding = ModelConfig.from_env("EMBEDDING", ModelType.EMBEDDING)
        
        # Optional vision model
        vision = None
        if os.getenv("VISION_MODEL_NAME"):
            vision = ModelConfig.from_env("VISION", ModelType.VISION)
        
        # Optional reranker
        reranker = None
        if os.getenv("RERANKER_ENABLED", "false").lower() == "true":
            reranker = RerankerConfig.from_env()

        # Optional multimodal embedding model (separate from text embedding)
        multimodal_embedding = None
        if os.getenv("MULTIMODAL_EMBEDDING_ENABLED", "false").lower() == "true":
            multimodal_embedding = ModelConfig.from_env(
                "MULTIMODAL_EMBEDDING", ModelType.EMBEDDING
            )
        
        # Storage paths - convert to absolute paths
        working_dir = os.path.abspath(os.getenv("WORKING_DIR", "./rag_storage"))
        upload_dir = os.path.abspath(os.getenv("UPLOAD_DIR", "./uploads"))
        
        # RAGAnything settings
        parser = os.getenv("PARSER", "mineru")
        enable_image = os.getenv("ENABLE_IMAGE_PROCESSING", "true").lower() == "true"
        enable_table = os.getenv("ENABLE_TABLE_PROCESSING", "true").lower() == "true"
        enable_equation = os.getenv("ENABLE_EQUATION_PROCESSING", "true").lower() == "true"
        mineru_device = os.getenv("MINERU_DEVICE")  # None means auto-detect
        mineru_vram_raw = os.getenv("MINERU_VRAM")
        mineru_vram: Optional[int] = None
        if mineru_vram_raw:
            try:
                mineru_vram = int(mineru_vram_raw)
            except ValueError:
                raise ValueError("MINERU_VRAM must be an integer (MiB)") from None

        # Background indexing settings
        auto_indexing_enabled = os.getenv("AUTO_INDEXING_ENABLED", "true").lower() == "true"
        indexing_scan_interval = int(os.getenv("INDEXING_SCAN_INTERVAL", "60"))
        indexing_max_files_per_batch = int(os.getenv("INDEXING_MAX_FILES_PER_BATCH", "5"))

        # API server settings
        host = os.getenv("API_HOST", "0.0.0.0")
        port = int(os.getenv("API_PORT", "8000"))
        cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")
        
        return cls(
            llm=llm,
            embedding=embedding,
            vision=vision,
            reranker=reranker,
            multimodal_embedding=multimodal_embedding,
            working_dir=working_dir,
            upload_dir=upload_dir,
            parser=parser,
            enable_image_processing=enable_image,
            enable_table_processing=enable_table,
            enable_equation_processing=enable_equation,
            mineru_device=mineru_device,
            mineru_vram=mineru_vram,
            auto_indexing_enabled=auto_indexing_enabled,
            indexing_scan_interval=indexing_scan_interval,
            indexing_max_files_per_batch=indexing_max_files_per_batch,
            host=host,
            port=port,
            cors_origins=cors_origins,
        )
    
    @classmethod
    def from_yaml(cls, config_path: str | Path) -> BackendConfig:
        """Load configuration from YAML file."""
        with open(config_path) as f:
            data = yaml.safe_load(f)
        
        # Parse model configs
        llm_data = data["models"]["llm"]
        llm = ModelConfig(
            provider=ProviderType(llm_data["provider"]),
            model_name=llm_data["model_name"],
            model_type=ModelType.LLM,
            api_key=llm_data.get("api_key"),
            base_url=llm_data.get("base_url"),
            temperature=llm_data.get("temperature", 0.7),
            max_tokens=llm_data.get("max_tokens"),
        )
        
        embed_data = data["models"]["embedding"]
        embedding = ModelConfig(
            provider=ProviderType(embed_data["provider"]),
            model_name=embed_data["model_name"],
            model_type=ModelType.EMBEDDING,
            api_key=embed_data.get("api_key"),
            base_url=embed_data.get("base_url"),
            embedding_dim=embed_data["embedding_dim"],
        )
        
        # Optional vision
        vision = None
        if "vision" in data["models"]:
            vision_data = data["models"]["vision"]
            vision = ModelConfig(
                provider=ProviderType(vision_data["provider"]),
                model_name=vision_data["model_name"],
                model_type=ModelType.VISION,
                api_key=vision_data.get("api_key"),
                base_url=vision_data.get("base_url"),
            )
        
        # Optional reranker
        reranker = None
        if "reranker" in data and data["reranker"].get("enabled"):
            reranker_data = data["reranker"]
            use_fp16 = bool(reranker_data.get("use_fp16", False))
            dtype = reranker_data.get("dtype") or ("float16" if use_fp16 else "float32")
            reranker = RerankerConfig(
                enabled=True,
                provider=reranker_data.get("provider", "local"),
                model_name=reranker_data.get("model_name"),
                model_path=reranker_data.get("model_path"),
                device=reranker_data.get("device"),
                dtype=dtype,
                attn_implementation=reranker_data.get("attn_implementation", "sdpa"),
                batch_size=int(reranker_data.get("batch_size", 16)),
                max_length=int(reranker_data.get("max_length", 8192)),
                min_image_tokens=int(reranker_data.get("min_image_tokens", 4)),
                max_image_tokens=int(reranker_data.get("max_image_tokens", 1280)),
                allow_image_urls=bool(reranker_data.get("allow_image_urls", False)),
                instruction=reranker_data.get("instruction"),
                system_prompt=reranker_data.get("system_prompt"),
                api_key=reranker_data.get("api_key"),
                base_url=reranker_data.get("base_url"),
            )
        
        return cls(
            llm=llm,
            embedding=embedding,
            vision=vision,
            reranker=reranker,
            working_dir=os.path.abspath(data.get("working_dir", "./rag_storage")),
            upload_dir=os.path.abspath(data.get("upload_dir", "./uploads")),
            parser=data.get("parser", "mineru"),
            enable_image_processing=data.get("enable_image_processing", True),
            enable_table_processing=data.get("enable_table_processing", True),
            enable_equation_processing=data.get("enable_equation_processing", True),
            mineru_device=data.get("mineru_device"),
            mineru_vram=data.get("mineru_vram"),
        )
