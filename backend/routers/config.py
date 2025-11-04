"""
Configuration management endpoints.
"""

import logging
import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Request, HTTPException, status
from dotenv import load_dotenv

from backend.models.config import (
    ConfigReloadRequest,
    ConfigReloadResponse,
    CurrentConfigResponse
)


router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/reload", response_model=ConfigReloadResponse)
async def reload_configuration(
    request: Request,
    req: Optional[ConfigReloadRequest] = None
):
    """
    Hot-reload configuration files without restarting the server.
    
    WARNING: This reloads environment variables but does NOT reinitialize
    the RAG service or model providers. For full configuration changes,
    a server restart is recommended.
    """
    try:
        reloaded_files = []
        errors = {}
        
        # Determine which files to reload
        config_files = req.config_files if req and req.config_files else [".env.backend"]
        
        # Project root
        project_root = Path(__file__).parent.parent.parent
        
        for config_file in config_files:
            config_path = project_root / config_file
            
            if not config_path.exists():
                errors[config_file] = f"File not found: {config_path}"
                logger.warning(f"Config file not found: {config_path}")
                continue
            
            try:
                # Reload environment file
                if config_file.endswith(".env") or ".env." in config_file:
                    load_dotenv(dotenv_path=config_path, override=True)
                    reloaded_files.append(config_file)
                    logger.info(f"Reloaded environment file: {config_file}")
                
                # For YAML files, we would need to reload the config object
                # This is more complex and requires reinitializing services
                elif config_file.endswith(".yaml") or config_file.endswith(".yml"):
                    errors[config_file] = "YAML reload requires server restart"
                    logger.warning(f"YAML reload not supported for hot-reload: {config_file}")
                
                else:
                    errors[config_file] = "Unsupported file type"
            
            except Exception as e:
                errors[config_file] = str(e)
                logger.error(f"Error reloading {config_file}: {e}", exc_info=True)
        
        # Determine status
        if errors and not reloaded_files:
            status_str = "failed"
            message = "Failed to reload any configuration files"
        elif errors:
            status_str = "partial"
            message = f"Reloaded {len(reloaded_files)} file(s) with {len(errors)} error(s)"
        else:
            status_str = "success"
            message = f"Successfully reloaded {len(reloaded_files)} configuration file(s)"
        
        logger.info(f"Configuration reload: {status_str} - {message}")
        
        return ConfigReloadResponse(
            status=status_str,
            reloaded_files=reloaded_files,
            errors=errors,
            message=message
        )
    
    except Exception as e:
        logger.error(f"Configuration reload failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Configuration reload failed: {str(e)}"
        )


@router.get("/current", response_model=CurrentConfigResponse)
async def get_current_config(request: Request):
    """
    Get current configuration settings.
    
    Returns the current active configuration from the backend.
    """
    state = request.app.state
    
    try:
        config = state.config
        
        # Build response
        response = CurrentConfigResponse(
            backend={
                "host": config.host,
                "port": config.port,
                "cors_origins": config.cors_origins,
            },
            models={
                "llm": {
                    "provider": config.llm.provider.value,
                    "model_name": config.llm.model_name,
                    "base_url": config.llm.base_url,
                    "temperature": config.llm.temperature,
                    "max_tokens": config.llm.max_tokens,
                },
                "embedding": {
                    "provider": config.embedding.provider.value,
                    "model_name": config.embedding.model_name,
                    "base_url": config.embedding.base_url,
                    "embedding_dim": config.embedding.embedding_dim,
                },
            },
            storage={
                "working_dir": config.working_dir,
                "upload_dir": config.upload_dir,
            },
            processing={
                "parser": config.parser,
                "enable_image_processing": config.enable_image_processing,
                "enable_table_processing": config.enable_table_processing,
                "enable_equation_processing": config.enable_equation_processing,
            }
        )
        
        # Add vision model if configured
        if config.vision:
            response.models["vision"] = {
                "provider": config.vision.provider.value,
                "model_name": config.vision.model_name,
                "base_url": config.vision.base_url,
            }
        
        # Add reranker if configured
        if config.reranker and config.reranker.enabled:
            response.models["reranker"] = {
                "enabled": True,
                "provider": config.reranker.provider,
                "model_name": config.reranker.model_name if hasattr(config.reranker, 'model_name') else None,
                "model_path": config.reranker.model_path,
            }
        
        return response
    
    except Exception as e:
        logger.error(f"Failed to get current config: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get current config: {str(e)}"
        )


@router.get("/files")
async def list_config_files():
    """
    List available configuration files.
    
    Returns a list of configuration files that can be reloaded.
    """
    try:
        project_root = Path(__file__).parent.parent.parent
        
        config_files = []
        
        # Check for .env files
        for env_file in [".env.backend", ".env", "env.example"]:
            env_path = project_root / env_file
            if env_path.exists():
                config_files.append({
                    "path": env_file,
                    "type": "env",
                    "exists": True,
                    "size": env_path.stat().st_size
                })
        
        # Check for YAML config files
        configs_dir = project_root / "configs"
        if configs_dir.exists():
            for yaml_file in configs_dir.glob("*.yaml"):
                if not yaml_file.name.endswith(".example"):
                    config_files.append({
                        "path": f"configs/{yaml_file.name}",
                        "type": "yaml",
                        "exists": True,
                        "size": yaml_file.stat().st_size
                    })
        
        return {
            "config_files": config_files,
            "total": len(config_files)
        }
    
    except Exception as e:
        logger.error(f"Failed to list config files: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list config files: {str(e)}"
        )

