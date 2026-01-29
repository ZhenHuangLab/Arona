"""
Configuration management models.
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class ConfigReloadRequest(BaseModel):
    """Request to reload configuration."""

    config_files: Optional[list[str]] = Field(
        None, description="Specific config files to reload. If None, reload all."
    )
    apply: bool = Field(
        True,
        description="Whether to apply the reloaded configuration (rebuild BackendConfig + reinitialize services).",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "config_files": [".env.backend", "configs/model_providers.yaml"]
            }
        }


class ConfigReloadResponse(BaseModel):
    """Response from configuration reload."""

    status: str = Field(..., description="Reload status")
    reloaded_files: list[str] = Field(
        default_factory=list, description="Files that were reloaded"
    )
    errors: Dict[str, str] = Field(
        default_factory=dict, description="Errors encountered"
    )
    message: str = Field(..., description="Human-readable message")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "reloaded_files": [".env.backend"],
                "errors": {},
                "message": "Configuration reloaded successfully",
            }
        }


class ModelConfigUpdate(BaseModel):
    """Partial update for a ModelConfig-backed component (LLM/Embedding/Vision)."""

    provider: Optional[str] = None
    model_name: Optional[str] = None
    api_key: Optional[str] = Field(
        None,
        description="Optional API key. If omitted, keep existing value.",
    )
    base_url: Optional[str] = None

    # Common generation params
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None

    # Embedding params
    embedding_dim: Optional[int] = None

    # Local GPU params
    device: Optional[str] = None
    dtype: Optional[str] = None
    attn_implementation: Optional[str] = None
    max_length: Optional[int] = None
    default_instruction: Optional[str] = None
    normalize: Optional[bool] = None
    allow_image_urls: Optional[bool] = None
    min_image_tokens: Optional[int] = None
    max_image_tokens: Optional[int] = None


class RerankerConfigUpdate(BaseModel):
    """Partial update for reranker configuration."""

    enabled: Optional[bool] = None
    provider: Optional[str] = None  # local | local_gpu | api
    model_name: Optional[str] = None
    model_path: Optional[str] = None
    device: Optional[str] = None
    dtype: Optional[str] = None
    attn_implementation: Optional[str] = None
    batch_size: Optional[int] = None
    max_length: Optional[int] = None
    instruction: Optional[str] = None
    system_prompt: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    min_image_tokens: Optional[int] = None
    max_image_tokens: Optional[int] = None
    allow_image_urls: Optional[bool] = None


class ModelsUpdateRequest(BaseModel):
    """Update model-related configuration and optionally apply it immediately."""

    llm: Optional[ModelConfigUpdate] = None
    embedding: Optional[ModelConfigUpdate] = None
    vision: Optional[ModelConfigUpdate] = None
    multimodal_embedding: Optional[ModelConfigUpdate] = None
    reranker: Optional[RerankerConfigUpdate] = None

    apply: bool = Field(
        True,
        description="Whether to apply immediately (reinitialize services).",
    )
    target_env_file: Optional[str] = Field(
        None,
        description="Optional env file to persist into (relative to project root). Defaults to .env if present, else .env.backend.",
    )


class ModelsUpdateResponse(BaseModel):
    """Response for model configuration updates."""

    status: str
    message: str
    applied: bool = False
    env_file: Optional[str] = None
    reloaded_components: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class CurrentConfigResponse(BaseModel):
    """Current configuration response."""

    backend: Dict[str, Any] = Field(
        default_factory=dict, description="Backend configuration"
    )
    models: Dict[str, Any] = Field(
        default_factory=dict, description="Model configurations"
    )
    storage: Dict[str, Any] = Field(
        default_factory=dict, description="Storage configuration"
    )
    processing: Dict[str, Any] = Field(
        default_factory=dict, description="Processing configuration"
    )
    chat: Dict[str, Any] = Field(
        default_factory=dict, description="Chat configuration"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "backend": {"host": "0.0.0.0", "port": 8000, "cors_origins": ["*"]},
                "models": {"llm": {"provider": "openai", "model_name": "gpt-4o-mini"}},
                "storage": {"working_dir": "./rag_storage", "upload_dir": "./uploads"},
                "processing": {"parser": "mineru", "enable_image_processing": True},
                "chat": {"auto_attach_retrieved_images": True, "max_retrieved_images": 4},
            }
        }


class IndexingConfigResponse(BaseModel):
    """Response model for indexing configuration."""

    auto_indexing_enabled: bool = Field(
        ..., description="Whether automatic background indexing is enabled"
    )
    indexing_scan_interval: int = Field(
        ..., ge=1, description="Seconds between background scans for new files"
    )
    indexing_max_files_per_batch: int = Field(
        ..., ge=1, description="Maximum number of files to process per iteration"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "auto_indexing_enabled": True,
                "indexing_scan_interval": 60,
                "indexing_max_files_per_batch": 5,
            }
        }


class IndexingConfigUpdate(BaseModel):
    """Request model for updating indexing configuration (partial updates supported)."""

    auto_indexing_enabled: Optional[bool] = Field(
        None, description="Whether automatic background indexing is enabled"
    )
    indexing_scan_interval: Optional[int] = Field(
        None, ge=1, description="Seconds between background scans for new files"
    )
    indexing_max_files_per_batch: Optional[int] = Field(
        None, ge=1, description="Maximum number of files to process per iteration"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "indexing_scan_interval": 120,
                "indexing_max_files_per_batch": 10,
            }
        }


class ChatConfigResponse(BaseModel):
    """Response model for chat configuration."""

    auto_attach_retrieved_images: bool = Field(
        ..., description="Whether to auto-attach retrieved images to assistant responses"
    )
    max_retrieved_images: int = Field(
        ..., ge=0, description="Maximum number of retrieved images to attach"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "auto_attach_retrieved_images": True,
                "max_retrieved_images": 4,
            }
        }


class ChatConfigUpdate(BaseModel):
    """Request model for updating chat configuration (partial updates supported)."""

    auto_attach_retrieved_images: Optional[bool] = Field(
        None, description="Whether to auto-attach retrieved images to assistant responses"
    )
    max_retrieved_images: Optional[int] = Field(
        None, ge=0, description="Maximum number of retrieved images to attach"
    )
    apply: bool = Field(
        True, description="Whether to apply changes immediately to runtime config"
    )
    target_env_file: Optional[str] = Field(
        None, description="Optional env file to persist into"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "auto_attach_retrieved_images": True,
                "max_retrieved_images": 4,
            }
        }
