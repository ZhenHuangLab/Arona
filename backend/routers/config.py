"""
Configuration management endpoints.
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Request, HTTPException, status
from dotenv import load_dotenv

from backend.config import BackendConfig
from backend.services.rag_service import RAGService
from backend.services.background_indexer import BackgroundIndexer
from backend.services.model_factory import ModelFactory
from backend.utils.env_file import choose_env_file, update_env_file
from backend.utils.torch_runtime import ensure_torch_cuda_libs
from backend.models.config import (
    ConfigReloadRequest,
    ConfigReloadResponse,
    CurrentConfigResponse,
    IndexingConfigResponse,
    IndexingConfigUpdate,
    ModelsUpdateRequest,
    ModelsUpdateResponse,
)


router = APIRouter()
logger = logging.getLogger(__name__)


async def _stop_background_indexer(state) -> None:
    task = getattr(state, "background_indexer_task", None)
    if task is None:
        state.background_indexer = None
        state.background_indexer_task = None
        return

    task.cancel()
    try:
        await asyncio.wait_for(task, timeout=5.0)
    except asyncio.TimeoutError:
        logger.warning("Background indexer did not stop within timeout")
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"Error stopping background indexer: {e}", exc_info=True)
    finally:
        state.background_indexer = None
        state.background_indexer_task = None


async def _apply_config(
    request: Request,
    new_config: BackendConfig,
    *,
    prebuilt: Optional[dict[str, object]] = None,
) -> list[str]:
    """Apply a new BackendConfig to the running app (best-effort hot reload).

    This function prefers *in-place* updates of the existing RAGService to avoid
    unnecessarily reloading heavyweight models (e.g., local GPU embedding).

    `prebuilt` can provide already-constructed providers/functions from the caller
    (typically for validation + apply without double-loading).
    """
    state = request.app.state

    old_config = getattr(state, "config", None)
    old_rag_service: Optional[RAGService] = getattr(state, "rag_service", None)
    if old_config is None and old_rag_service is not None:
        old_config = getattr(old_rag_service, "config", None)

    # Stop background indexer first to avoid it using an old rag_service during reload.
    await _stop_background_indexer(state)

    ensure_torch_cuda_libs(new_config)

    reloaded_components: list[str] = ["config"]
    llm_changed = False
    embedding_changed = False
    reranker_changed = False
    vision_changed = False
    multimodal_embedding_changed = False

    if old_config is not None:
        try:
            llm_changed = old_config.llm != new_config.llm
            embedding_changed = old_config.embedding != new_config.embedding
            reranker_changed = getattr(old_config, "reranker", None) != getattr(new_config, "reranker", None)
            vision_changed = getattr(old_config, "vision", None) != getattr(new_config, "vision", None)
            multimodal_embedding_changed = getattr(old_config, "multimodal_embedding", None) != getattr(new_config, "multimodal_embedding", None)
        except Exception:
            # Keep minimal list if dataclass comparison fails.
            pass

    if llm_changed:
        reloaded_components.append("llm")
    if embedding_changed:
        reloaded_components.append("embedding")
    if reranker_changed:
        reloaded_components.append("reranker")
    if vision_changed:
        reloaded_components.append("vision")
    if multimodal_embedding_changed:
        reloaded_components.append("multimodal_embedding")

    if old_rag_service is None:
        # No existing service; fall back to full initialization.
        state.config = new_config
        state.rag_service = RAGService(new_config)
    else:
        # Best-effort: wait for in-flight ops to finish before swapping providers.
        try:
            await old_rag_service.wait_for_idle(timeout=5.0)
        except Exception:
            pass

        # Update the existing service in-place to avoid reloading unchanged models.
        old_rag_service.config = new_config

        old_embedding_provider = None
        old_multimodal_embedding_provider = None
        old_reranker_provider = None

        if embedding_changed:
            old_embedding_provider = getattr(old_rag_service, "embedding_provider", None)
            new_embedding_provider = None
            if prebuilt is not None:
                new_embedding_provider = prebuilt.get("embedding_provider")  # type: ignore[assignment]
            if new_embedding_provider is None:
                new_embedding_provider = ModelFactory.create_embedding_provider(new_config.embedding)
            old_rag_service.embedding_provider = new_embedding_provider  # type: ignore[assignment]
            old_rag_service.embedding_func = ModelFactory.create_embedding_func_from_provider(new_embedding_provider)  # type: ignore[arg-type]

        if multimodal_embedding_changed:
            old_multimodal_embedding_provider = getattr(old_rag_service, "multimodal_embedding_provider", None)
            if getattr(new_config, "multimodal_embedding", None):
                new_mm_provider = None
                if prebuilt is not None:
                    new_mm_provider = prebuilt.get("multimodal_embedding_provider")  # type: ignore[assignment]
                if new_mm_provider is None:
                    new_mm_provider = ModelFactory.create_embedding_provider(new_config.multimodal_embedding)  # type: ignore[arg-type]
                old_rag_service.multimodal_embedding_provider = new_mm_provider  # type: ignore[assignment]
            else:
                old_rag_service.multimodal_embedding_provider = None

        if llm_changed:
            new_llm_func = None
            if prebuilt is not None:
                new_llm_func = prebuilt.get("llm_func")  # type: ignore[assignment]
            if new_llm_func is None:
                new_llm_func = ModelFactory.create_llm_func(new_config.llm)
            old_rag_service.llm_func = new_llm_func  # type: ignore[assignment]

        if vision_changed:
            new_vision_func = None
            if getattr(new_config, "vision", None):
                if prebuilt is not None:
                    new_vision_func = prebuilt.get("vision_func")  # type: ignore[assignment]
                if new_vision_func is None:
                    new_vision_func = ModelFactory.create_vision_func(new_config.vision)  # type: ignore[arg-type]
            old_rag_service.vision_func = new_vision_func  # type: ignore[assignment]

        if reranker_changed:
            old_reranker_provider = getattr(old_rag_service, "reranker_provider", None)
            if getattr(new_config, "reranker", None):
                new_reranker_func = None
                if prebuilt is not None:
                    new_reranker_func = prebuilt.get("reranker_func")  # type: ignore[assignment]
                if new_reranker_func is None:
                    new_reranker_func = ModelFactory.create_reranker(new_config.reranker)  # type: ignore[arg-type]
                old_rag_service.reranker_func = new_reranker_func  # type: ignore[assignment]
                old_rag_service.reranker_provider = getattr(new_reranker_func, "_provider", None)  # type: ignore[assignment]
            else:
                old_rag_service.reranker_func = None
                old_rag_service.reranker_provider = None

        # Decide whether we need to rebuild the cached RAGAnything instance.
        rag_settings_changed = False
        if old_config is not None:
            try:
                rag_settings_changed = any(
                    getattr(old_config, key, None) != getattr(new_config, key, None)
                    for key in (
                        "working_dir",
                        "parser",
                        "enable_image_processing",
                        "enable_table_processing",
                        "enable_equation_processing",
                        "mineru_device",
                        "mineru_vram",
                    )
                )
            except Exception:
                rag_settings_changed = True

        if llm_changed or embedding_changed or reranker_changed or vision_changed or multimodal_embedding_changed or rag_settings_changed:
            old_rag_service._rag_instance = None

        state.config = new_config
        state.rag_service = old_rag_service

    # Restart background indexer if enabled
    if getattr(new_config, "auto_indexing_enabled", False):
        index_status_service = getattr(state, "index_status_service", None)
        if index_status_service is not None:
            indexer = BackgroundIndexer(new_config, state.rag_service, index_status_service)
            state.background_indexer = indexer
            state.background_indexer_task = asyncio.create_task(indexer.run_periodic_scan())
        else:
            logger.warning("index_status_service not found; background indexer will not be restarted")
            state.background_indexer = None
            state.background_indexer_task = None
    else:
        state.background_indexer = None
        state.background_indexer_task = None

    # Best-effort shutdown of replaced heavy providers (avoid shutting down the whole service).
    if old_rag_service is not None:
        try:
            if embedding_changed and old_embedding_provider is not None and hasattr(old_embedding_provider, "shutdown"):
                await old_embedding_provider.shutdown()
            if multimodal_embedding_changed and old_multimodal_embedding_provider is not None and hasattr(old_multimodal_embedding_provider, "shutdown"):
                await old_multimodal_embedding_provider.shutdown()
            if reranker_changed and old_reranker_provider is not None and hasattr(old_reranker_provider, "shutdown"):
                await old_reranker_provider.shutdown()
        except Exception as e:
            logger.warning("Provider shutdown during hot-reload failed: %s", e, exc_info=True)

    return reloaded_components


@router.post("/reload", response_model=ConfigReloadResponse)
async def reload_configuration(
    request: Request,
    req: Optional[ConfigReloadRequest] = None
):
    """
    Hot-reload configuration files without restarting the server.
    
    This reloads configuration files and (by default) applies changes immediately
    by rebuilding BackendConfig and reinitializing model providers.
    """
    try:
        reloaded_files = []
        errors = {}
        
        # Determine which files to reload
        config_files = req.config_files if req and req.config_files else None
        
        # Project root
        project_root = Path(__file__).parent.parent.parent

        if not config_files:
            env_file_loaded = getattr(request.app.state, "env_file_loaded", None)
            if env_file_loaded:
                env_path = Path(env_file_loaded)
                try:
                    rel = env_path.relative_to(project_root)
                    config_files = [rel.as_posix()]
                except Exception:
                    config_files = [env_path.name]
            else:
                # Prefer unified .env and fall back to legacy .env.backend
                for candidate in (".env", ".env.backend"):
                    if (project_root / candidate).exists():
                        config_files = [candidate]
                        break
                if not config_files:
                    config_files = [".env"]
        
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

        applied = False
        if req is None or req.apply:
            lock = getattr(request.app.state, "config_reload_lock", None)
            if lock is None:
                request.app.state.config_reload_lock = asyncio.Lock()
                lock = request.app.state.config_reload_lock

            async with lock:
                try:
                    new_config = BackendConfig.from_env()
                    await _apply_config(request, new_config)
                    # Track the latest env file used for reload (best-effort).
                    try:
                        if reloaded_files:
                            maybe_env = project_root / reloaded_files[0]
                            request.app.state.env_file_loaded = str(maybe_env)
                    except Exception:
                        pass
                    applied = True
                except Exception as e:
                    errors["apply"] = str(e)
                    status_str = "failed" if not reloaded_files else "partial"
                    message = (
                        "Configuration files reloaded but applying changes failed: "
                        + str(e)
                    )

        return ConfigReloadResponse(
            status=status_str,
            reloaded_files=reloaded_files,
            errors=errors,
            message=message + (" (applied)" if applied else ""),
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
        env_file_loaded = getattr(state, "env_file_loaded", None)
        env_file_display = env_file_loaded
        project_root = getattr(state, "project_root", None)
        if env_file_loaded and project_root:
            try:
                env_file_display = str(Path(env_file_loaded).resolve().relative_to(Path(project_root).resolve()))
            except Exception:
                env_file_display = env_file_loaded

        response = CurrentConfigResponse(
            backend={
                "host": config.host,
                "port": config.port,
                "cors_origins": config.cors_origins,
                "env_file_loaded": env_file_display,
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
                    "device": config.embedding.extra_params.get("device"),
                    "dtype": config.embedding.extra_params.get("dtype"),
                    "attn_implementation": config.embedding.extra_params.get("attn_implementation"),
                    "max_length": config.embedding.extra_params.get("max_length"),
                    "default_instruction": config.embedding.extra_params.get("default_instruction"),
                    "normalize": config.embedding.extra_params.get("normalize"),
                    "allow_image_urls": config.embedding.extra_params.get("allow_image_urls"),
                    "min_image_tokens": config.embedding.extra_params.get("min_image_tokens"),
                    "max_image_tokens": config.embedding.extra_params.get("max_image_tokens"),
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

        # Add multimodal embedding model if configured
        if getattr(config, "multimodal_embedding", None):
            response.models["multimodal_embedding"] = {
                "provider": config.multimodal_embedding.provider.value,
                "model_name": config.multimodal_embedding.model_name,
                "base_url": config.multimodal_embedding.base_url,
                "embedding_dim": config.multimodal_embedding.embedding_dim,
                "device": config.multimodal_embedding.extra_params.get("device"),
            }
        
        # Add reranker if configured
        if config.reranker and config.reranker.enabled:
            response.models["reranker"] = {
                "enabled": True,
                "provider": config.reranker.provider,
                "model_name": config.reranker.model_name if hasattr(config.reranker, 'model_name') else None,
                "model_path": config.reranker.model_path,
                "device": config.reranker.device,
                "dtype": config.reranker.dtype,
                "attn_implementation": config.reranker.attn_implementation,
                "batch_size": config.reranker.batch_size,
                "max_length": config.reranker.max_length,
                "min_image_tokens": getattr(config.reranker, "min_image_tokens", None),
                "max_image_tokens": getattr(config.reranker, "max_image_tokens", None),
                "allow_image_urls": getattr(config.reranker, "allow_image_urls", None),
                "base_url": getattr(config.reranker, "base_url", None),
            }
        
        return response
    
    except Exception as e:
        logger.error(f"Failed to get current config: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get current config: {str(e)}"
        )


@router.get("/indexing", response_model=IndexingConfigResponse)
async def get_indexing_config(request: Request):
    """
    Get current indexing configuration.

    Returns the current background indexing settings including:
    - auto_indexing_enabled: Whether background indexing is active
    - indexing_scan_interval: Seconds between scans for new files
    - indexing_max_files_per_batch: Max files processed per iteration
    """
    try:
        config = request.app.state.config

        return IndexingConfigResponse(
            auto_indexing_enabled=config.auto_indexing_enabled,
            indexing_scan_interval=config.indexing_scan_interval,
            indexing_max_files_per_batch=config.indexing_max_files_per_batch,
        )

    except Exception as e:
        logger.error(f"Failed to get indexing config: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get indexing config: {str(e)}"
        )


@router.put("/indexing", response_model=IndexingConfigResponse)
async def update_indexing_config(
    request: Request,
    update: IndexingConfigUpdate
):
    """
    Update indexing configuration at runtime.

    Supports partial updates - only specified fields will be changed.
    Changes take effect immediately for the background indexer.

    Note: Changes are runtime-only and will be lost on server restart.
    To persist changes, update environment variables or configuration files.
    """
    try:
        config = request.app.state.config

        # Apply partial updates
        # Reason: Only update fields that are explicitly provided (not None)
        if update.auto_indexing_enabled is not None:
            config.auto_indexing_enabled = update.auto_indexing_enabled
            logger.info(f"Updated auto_indexing_enabled to {update.auto_indexing_enabled}")

        if update.indexing_scan_interval is not None:
            config.indexing_scan_interval = update.indexing_scan_interval
            logger.info(f"Updated indexing_scan_interval to {update.indexing_scan_interval}")

        if update.indexing_max_files_per_batch is not None:
            config.indexing_max_files_per_batch = update.indexing_max_files_per_batch
            logger.info(f"Updated indexing_max_files_per_batch to {update.indexing_max_files_per_batch}")

        # Return updated configuration
        return IndexingConfigResponse(
            auto_indexing_enabled=config.auto_indexing_enabled,
            indexing_scan_interval=config.indexing_scan_interval,
            indexing_max_files_per_batch=config.indexing_max_files_per_batch,
        )

    except Exception as e:
        logger.error(f"Failed to update indexing config: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update indexing config: {str(e)}"
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


@router.put("/models", response_model=ModelsUpdateResponse)
async def update_models_config(request: Request, update: ModelsUpdateRequest):
    """Persist model settings into an env file and optionally apply them immediately."""
    project_root = Path(__file__).parent.parent.parent
    env_path = choose_env_file(project_root)

    if update.target_env_file:
        candidate = (project_root / update.target_env_file).resolve()
        root_resolved = project_root.resolve()
        if root_resolved not in candidate.parents and candidate != root_resolved:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="target_env_file must be within the project directory",
            )
        env_path = candidate

    env_updates: dict[str, str] = {}

    def _set(key: str, value) -> None:
        if value is None:
            return
        if isinstance(value, bool):
            env_updates[key] = "true" if value else "false"
        else:
            env_updates[key] = str(value)

    def _apply_model(prefix: str, model):
        if model is None:
            return
        _set(f"{prefix}_PROVIDER", model.provider)
        _set(f"{prefix}_MODEL_NAME", model.model_name)
        _set(f"{prefix}_API_KEY", model.api_key)
        _set(f"{prefix}_BASE_URL", model.base_url)
        _set(f"{prefix}_TEMPERATURE", model.temperature)
        _set(f"{prefix}_MAX_TOKENS", model.max_tokens)
        _set(f"{prefix}_EMBEDDING_DIM", model.embedding_dim)
        _set(f"{prefix}_DEVICE", model.device)
        _set(f"{prefix}_DTYPE", model.dtype)
        _set(f"{prefix}_ATTN_IMPLEMENTATION", model.attn_implementation)
        _set(f"{prefix}_MAX_LENGTH", model.max_length)
        _set(f"{prefix}_DEFAULT_INSTRUCTION", model.default_instruction)
        _set(f"{prefix}_NORMALIZE", model.normalize)
        _set(f"{prefix}_ALLOW_IMAGE_URLS", model.allow_image_urls)
        _set(f"{prefix}_MIN_IMAGE_TOKENS", model.min_image_tokens)
        _set(f"{prefix}_MAX_IMAGE_TOKENS", model.max_image_tokens)

    _apply_model("LLM", update.llm)
    _apply_model("EMBEDDING", update.embedding)
    _apply_model("VISION", update.vision)
    _apply_model("MULTIMODAL_EMBEDDING", update.multimodal_embedding)

    if update.multimodal_embedding is not None and any(
        v is not None for v in update.multimodal_embedding.model_dump().values()
    ):
        _set("MULTIMODAL_EMBEDDING_ENABLED", True)

    if update.reranker is not None:
        _set("RERANKER_ENABLED", update.reranker.enabled)
        _set("RERANKER_PROVIDER", update.reranker.provider)
        _set("RERANKER_MODEL_NAME", update.reranker.model_name)
        _set("RERANKER_MODEL_PATH", update.reranker.model_path)
        _set("RERANKER_DEVICE", update.reranker.device)
        _set("RERANKER_DTYPE", update.reranker.dtype)
        _set("RERANKER_ATTN_IMPLEMENTATION", update.reranker.attn_implementation)
        _set("RERANKER_BATCH_SIZE", update.reranker.batch_size)
        _set("RERANKER_MAX_LENGTH", update.reranker.max_length)
        _set("RERANKER_INSTRUCTION", update.reranker.instruction)
        _set("RERANKER_SYSTEM_PROMPT", update.reranker.system_prompt)
        _set("RERANKER_API_KEY", update.reranker.api_key)
        _set("RERANKER_BASE_URL", update.reranker.base_url)
        _set("RERANKER_MIN_IMAGE_TOKENS", update.reranker.min_image_tokens)
        _set("RERANKER_MAX_IMAGE_TOKENS", update.reranker.max_image_tokens)
        _set("RERANKER_ALLOW_IMAGE_URLS", update.reranker.allow_image_urls)

    if not env_updates:
        return ModelsUpdateResponse(
            status="noop",
            message="No changes provided",
            applied=False,
            env_file=str(env_path.relative_to(project_root)) if env_path.is_relative_to(project_root) else str(env_path),
        )

    lock = getattr(request.app.state, "config_reload_lock", None)
    if lock is None:
        request.app.state.config_reload_lock = asyncio.Lock()
        lock = request.app.state.config_reload_lock

    async with lock:
        # Validate & build the new config/providers before persisting to disk.
        old_env = {k: os.environ.get(k) for k in env_updates.keys()}
        current_config = getattr(request.app.state, "config", None)
        current_rag_service: Optional[RAGService] = getattr(request.app.state, "rag_service", None)
        if current_config is None and current_rag_service is not None:
            current_config = getattr(current_rag_service, "config", None)

        prebuilt: dict[str, object] = {}

        async def _shutdown_prebuilt() -> None:
            """Best-effort cleanup for prebuilt heavy providers when not applying."""
            try:
                embed_provider = prebuilt.get("embedding_provider")
                if embed_provider is not None and hasattr(embed_provider, "shutdown"):
                    await embed_provider.shutdown()  # type: ignore[misc]
            except Exception:
                pass
            try:
                mm_provider = prebuilt.get("multimodal_embedding_provider")
                if mm_provider is not None and hasattr(mm_provider, "shutdown"):
                    await mm_provider.shutdown()  # type: ignore[misc]
            except Exception:
                pass
            try:
                reranker_func = prebuilt.get("reranker_func")
                reranker_provider = getattr(reranker_func, "_provider", None) if reranker_func is not None else None
                if reranker_provider is not None and hasattr(reranker_provider, "shutdown"):
                    await reranker_provider.shutdown()  # type: ignore[misc]
            except Exception:
                pass

        try:
            for k, v in env_updates.items():
                os.environ[k] = v

            new_config = BackendConfig.from_env()

            llm_changed = True
            embedding_changed = True
            reranker_changed = True
            vision_changed = True
            multimodal_embedding_changed = True
            if current_config is not None:
                try:
                    llm_changed = current_config.llm != new_config.llm
                    embedding_changed = current_config.embedding != new_config.embedding
                    reranker_changed = getattr(current_config, "reranker", None) != getattr(new_config, "reranker", None)
                    vision_changed = getattr(current_config, "vision", None) != getattr(new_config, "vision", None)
                    multimodal_embedding_changed = getattr(current_config, "multimodal_embedding", None) != getattr(new_config, "multimodal_embedding", None)
                except Exception:
                    # If comparisons fail, treat as changed so we validate/apply conservatively.
                    pass

            if not any([llm_changed, embedding_changed, reranker_changed, vision_changed, multimodal_embedding_changed]):
                # No effective model changes; avoid rewriting env / reloading services.
                for k, old_v in old_env.items():
                    if old_v is None:
                        os.environ.pop(k, None)
                    else:
                        os.environ[k] = old_v
                return ModelsUpdateResponse(
                    status="noop",
                    message="No effective changes (requested settings match current configuration)",
                    applied=False,
                    env_file=str(env_path.relative_to(project_root)) if env_path.is_relative_to(project_root) else str(env_path),
                    reloaded_components=[],
                )

            ensure_torch_cuda_libs(new_config)

            # Build only the providers/functions that actually changed.
            if llm_changed:
                prebuilt["llm_func"] = ModelFactory.create_llm_func(new_config.llm)
            if embedding_changed:
                prebuilt["embedding_provider"] = ModelFactory.create_embedding_provider(new_config.embedding)
            if multimodal_embedding_changed and getattr(new_config, "multimodal_embedding", None):
                prebuilt["multimodal_embedding_provider"] = ModelFactory.create_embedding_provider(new_config.multimodal_embedding)  # type: ignore[arg-type]
            if vision_changed and getattr(new_config, "vision", None):
                prebuilt["vision_func"] = ModelFactory.create_vision_func(new_config.vision)  # type: ignore[arg-type]
            if reranker_changed and getattr(new_config, "reranker", None):
                prebuilt["reranker_func"] = ModelFactory.create_reranker(new_config.reranker)  # type: ignore[arg-type]
        except Exception as e:
            # Restore env on failure
            for k, old_v in old_env.items():
                if old_v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = old_v
            try:
                await _shutdown_prebuilt()
            except Exception:
                pass
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid configuration: {e}",
            ) from e

        # Persist and apply
        try:
            update_env_file(env_path, env_updates)
        except Exception as e:
            # Avoid leaking GPU memory if we built a provider but cannot persist.
            try:
                await _shutdown_prebuilt()
            except Exception:
                pass
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to persist env file: {e}",
            ) from e

        # Ensure os.environ matches persisted file (handles quoting/escaping)
        load_dotenv(dotenv_path=env_path, override=True)

        reloaded_components: list[str] = []
        applied = False
        if update.apply:
            try:
                reloaded_components = await _apply_config(request, new_config, prebuilt=prebuilt)
                applied = True
                try:
                    request.app.state.env_file_loaded = str(env_path)
                except Exception:
                    pass
            except Exception as e:
                try:
                    await _shutdown_prebuilt()
                except Exception:
                    pass
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to apply configuration: {e}",
                ) from e
        else:
            # Not applying runtime changes; release any prebuilt heavy providers.
            try:
                await _shutdown_prebuilt()
            except Exception:
                pass

        rel_env = None
        try:
            rel_env = str(env_path.relative_to(project_root))
        except Exception:
            rel_env = str(env_path)

        return ModelsUpdateResponse(
            status="success",
            message="Model configuration updated successfully",
            applied=applied,
            env_file=rel_env,
            reloaded_components=reloaded_components,
        )
