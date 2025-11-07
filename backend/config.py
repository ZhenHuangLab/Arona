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


class ModelType(str, Enum):
    """Model capability types."""
    LLM = "llm"              # Text generation
    VISION = "vision"        # Vision-language model
    EMBEDDING = "embedding"  # Text embeddings


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
        # API-based providers require api_key
        if self.provider in [ProviderType.OPENAI, ProviderType.ANTHROPIC, ProviderType.AZURE]:
            if not self.api_key:
                raise ValueError(f"{self.provider} provider requires api_key")
        
        # Embedding models require dimension
        if self.model_type == ModelType.EMBEDDING and not self.embedding_dim:
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
        """
        provider = os.getenv(f"{prefix}_PROVIDER", "openai")
        model_name = os.getenv(f"{prefix}_MODEL_NAME")
        api_key = os.getenv(f"{prefix}_API_KEY")
        base_url = os.getenv(f"{prefix}_BASE_URL")

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

        config = cls(
            provider=ProviderType(provider),
            model_name=model_name,
            model_type=model_type,
            api_key=api_key,
            base_url=base_url,
            embedding_dim=embedding_dim,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        return config


@dataclass
class RerankerConfig:
    """Configuration for reranking models."""
    
    enabled: bool = True
    provider: str = "local"  # "local" or "api"
    
    # For local FlagEmbedding reranker
    model_path: Optional[str] = None
    use_fp16: bool = False
    batch_size: int = 16
    
    # For API-based reranker (future)
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model_name: Optional[str] = None
    
    @classmethod
    def from_env(cls) -> RerankerConfig:
        """Create RerankerConfig from environment variables."""
        enabled = os.getenv("RERANKER_ENABLED", "true").lower() == "true"
        provider = os.getenv("RERANKER_PROVIDER", "local")
        
        config = cls(
            enabled=enabled,
            provider=provider,
        )
        
        if provider == "local":
            config.model_path = os.getenv("RERANKER_MODEL_PATH")
            config.use_fp16 = os.getenv("RERANKER_USE_FP16", "false").lower() == "true"
            batch_size = os.getenv("RERANKER_BATCH_SIZE")
            if batch_size:
                config.batch_size = int(batch_size)
        else:
            config.api_key = os.getenv("RERANKER_API_KEY")
            config.base_url = os.getenv("RERANKER_BASE_URL")
            config.model_name = os.getenv("RERANKER_MODEL_NAME")
        
        return config


@dataclass
class BackendConfig:
    """Complete backend configuration."""
    
    # Model configurations
    llm: ModelConfig
    embedding: ModelConfig
    vision: Optional[ModelConfig] = None
    reranker: Optional[RerankerConfig] = None
    
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
        if os.getenv("RERANKER_ENABLED", "true").lower() == "true":
            reranker = RerankerConfig.from_env()
        
        # Storage paths - convert to absolute paths
        working_dir = os.path.abspath(os.getenv("WORKING_DIR", "./rag_storage"))
        upload_dir = os.path.abspath(os.getenv("UPLOAD_DIR", "./uploads"))
        
        # RAGAnything settings
        parser = os.getenv("PARSER", "mineru")
        enable_image = os.getenv("ENABLE_IMAGE_PROCESSING", "true").lower() == "true"
        enable_table = os.getenv("ENABLE_TABLE_PROCESSING", "true").lower() == "true"
        enable_equation = os.getenv("ENABLE_EQUATION_PROCESSING", "true").lower() == "true"
        mineru_device = os.getenv("MINERU_DEVICE")  # None means auto-detect

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
            working_dir=working_dir,
            upload_dir=upload_dir,
            parser=parser,
            enable_image_processing=enable_image,
            enable_table_processing=enable_table,
            enable_equation_processing=enable_equation,
            mineru_device=mineru_device,
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
            reranker = RerankerConfig(
                enabled=True,
                provider=reranker_data.get("provider", "local"),
                model_path=reranker_data.get("model_path"),
                use_fp16=reranker_data.get("use_fp16", False),
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
        )

