from __future__ import annotations

import importlib.util
import logging
import os
from pathlib import Path

from backend.config import BackendConfig, ProviderType

logger = logging.getLogger(__name__)


def torch_lib_dir() -> Path | None:
    """
    Best-effort discovery of the installed torch package's `lib/` directory.

    This avoids importing torch (which may fail if CUDA libraries are misconfigured).
    """
    try:
        spec = importlib.util.find_spec("torch")
    except Exception:
        return None

    if spec is None or not spec.submodule_search_locations:
        return None

    torch_pkg_dir = Path(next(iter(spec.submodule_search_locations)))
    lib_dir = torch_pkg_dir / "lib"
    if not lib_dir.is_dir():
        return None
    return lib_dir


def prepend_to_ld_library_path(dir_path: Path) -> None:
    """
    Prepend a directory to LD_LIBRARY_PATH (deduplicated).

    Note: this affects dynamic library resolution for future dlopen() calls in this
    process (e.g. importing `torch` later). It does not change already-loaded libs.
    """
    lib_dir = str(dir_path)
    current = os.environ.get("LD_LIBRARY_PATH", "")
    parts = [p for p in current.split(os.pathsep) if p]
    if parts and parts[0] == lib_dir:
        return
    parts = [p for p in parts if p != lib_dir]
    os.environ["LD_LIBRARY_PATH"] = os.pathsep.join([lib_dir, *parts]) if parts else lib_dir


def needs_local_gpu_torch(config: BackendConfig) -> bool:
    """Return True if configuration selects any local GPU provider that imports torch."""

    def _is_local_gpu_model(model) -> bool:
        device = getattr(model, "extra_params", {}).get("device")
        is_cuda_device = isinstance(device, str) and device.startswith("cuda")
        return bool(
            model.provider == ProviderType.LOCAL_GPU
            or (model.provider == ProviderType.LOCAL and model.base_url is None and is_cuda_device)
        )

    if _is_local_gpu_model(config.embedding):
        return True

    if getattr(config, "multimodal_embedding", None) and _is_local_gpu_model(config.multimodal_embedding):
        return True

    reranker = config.reranker
    if reranker and reranker.enabled:
        is_cuda_device = isinstance(reranker.device, str) and reranker.device.startswith("cuda")
        if reranker.provider in {"local", "local_gpu"} and is_cuda_device:
            return True

    return False


def ensure_torch_cuda_libs(config: BackendConfig) -> None:
    """
    Ensure torch's bundled CUDA libs take precedence when local GPU providers are enabled.

    This is a best-effort mitigation for systems where an old CUDA toolkit path earlier in
    LD_LIBRARY_PATH causes torch CUDA imports to fail.
    """
    if not needs_local_gpu_torch(config):
        return

    lib_dir = torch_lib_dir()
    if lib_dir is not None:
        prepend_to_ld_library_path(lib_dir)
        logger.info("Prepended torch CUDA libs to LD_LIBRARY_PATH: %s", lib_dir)
    else:
        logger.warning(
            "Local GPU provider is configured but torch `lib/` directory was not found; "
            "torch import may fail if CUDA runtime libraries are misconfigured."
        )

