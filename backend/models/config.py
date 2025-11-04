"""
Configuration management models.
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class ConfigReloadRequest(BaseModel):
    """Request to reload configuration."""
    config_files: Optional[list[str]] = Field(
        None,
        description="Specific config files to reload. If None, reload all."
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
    reloaded_files: list[str] = Field(default_factory=list, description="Files that were reloaded")
    errors: Dict[str, str] = Field(default_factory=dict, description="Errors encountered")
    message: str = Field(..., description="Human-readable message")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "reloaded_files": [".env.backend"],
                "errors": {},
                "message": "Configuration reloaded successfully"
            }
        }


class CurrentConfigResponse(BaseModel):
    """Current configuration response."""
    backend: Dict[str, Any] = Field(default_factory=dict, description="Backend configuration")
    models: Dict[str, Any] = Field(default_factory=dict, description="Model configurations")
    storage: Dict[str, Any] = Field(default_factory=dict, description="Storage configuration")
    processing: Dict[str, Any] = Field(default_factory=dict, description="Processing configuration")

    class Config:
        json_schema_extra = {
            "example": {
                "backend": {
                    "host": "0.0.0.0",
                    "port": 8000,
                    "cors_origins": ["*"]
                },
                "models": {
                    "llm": {
                        "provider": "openai",
                        "model_name": "gpt-4o-mini"
                    }
                },
                "storage": {
                    "working_dir": "./rag_storage",
                    "upload_dir": "./uploads"
                },
                "processing": {
                    "parser": "mineru",
                    "enable_image_processing": True
                }
            }
        }


class IndexingConfigResponse(BaseModel):
    """Response model for indexing configuration."""
    auto_indexing_enabled: bool = Field(
        ...,
        description="Whether automatic background indexing is enabled"
    )
    indexing_scan_interval: int = Field(
        ...,
        ge=1,
        description="Seconds between background scans for new files"
    )
    indexing_max_files_per_batch: int = Field(
        ...,
        ge=1,
        description="Maximum number of files to process per iteration"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "auto_indexing_enabled": True,
                "indexing_scan_interval": 60,
                "indexing_max_files_per_batch": 5
            }
        }


class IndexingConfigUpdate(BaseModel):
    """Request model for updating indexing configuration (partial updates supported)."""
    auto_indexing_enabled: Optional[bool] = Field(
        None,
        description="Whether automatic background indexing is enabled"
    )
    indexing_scan_interval: Optional[int] = Field(
        None,
        ge=1,
        description="Seconds between background scans for new files"
    )
    indexing_max_files_per_batch: Optional[int] = Field(
        None,
        ge=1,
        description="Maximum number of files to process per iteration"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "indexing_scan_interval": 120,
                "indexing_max_files_per_batch": 10
            }
        }

