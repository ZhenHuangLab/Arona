"""
Model provider implementations.

Important:
This package intentionally avoids importing optional/heavy dependencies at import
time (for example `torch` for local GPU providers). Provider implementations are
imported lazily so that the backend can start in environments without CUDA/Torch
as long as GPU providers are not selected in configuration.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from backend.providers.base import (  # noqa: F401
        BaseEmbeddingProvider,
        BaseLLMProvider,
        BaseRerankerProvider,
        BaseVisionProvider,
    )
    from backend.providers.jina import JinaEmbeddingProvider  # noqa: F401
    from backend.providers.local_embedding import (  # noqa: F401
        LocalEmbeddingProvider,
        LocalRerankerProvider,
        MultimodalEmbeddingProvider,
    )
    from backend.providers.openai import (  # noqa: F401
        OpenAIEmbeddingProvider,
        OpenAILLMProvider,
        OpenAIVisionProvider,
    )


__all__ = [
    # Base classes
    "BaseLLMProvider",
    "BaseVisionProvider",
    "BaseEmbeddingProvider",
    "BaseRerankerProvider",
    # Providers
    "OpenAILLMProvider",
    "OpenAIVisionProvider",
    "OpenAIEmbeddingProvider",
    "JinaEmbeddingProvider",
    "LocalEmbeddingProvider",
    "LocalRerankerProvider",
    "MultimodalEmbeddingProvider",
]


_EXPORTS: dict[str, tuple[str, str]] = {
    # Base classes
    "BaseLLMProvider": ("backend.providers.base", "BaseLLMProvider"),
    "BaseVisionProvider": ("backend.providers.base", "BaseVisionProvider"),
    "BaseEmbeddingProvider": ("backend.providers.base", "BaseEmbeddingProvider"),
    "BaseRerankerProvider": ("backend.providers.base", "BaseRerankerProvider"),
    # Providers
    "OpenAILLMProvider": ("backend.providers.openai", "OpenAILLMProvider"),
    "OpenAIVisionProvider": ("backend.providers.openai", "OpenAIVisionProvider"),
    "OpenAIEmbeddingProvider": ("backend.providers.openai", "OpenAIEmbeddingProvider"),
    "JinaEmbeddingProvider": ("backend.providers.jina", "JinaEmbeddingProvider"),
    # Optional torch/transformers based providers
    "LocalEmbeddingProvider": (
        "backend.providers.local_embedding",
        "LocalEmbeddingProvider",
    ),
    "LocalRerankerProvider": (
        "backend.providers.local_embedding",
        "LocalRerankerProvider",
    ),
    "MultimodalEmbeddingProvider": (
        "backend.providers.local_embedding",
        "MultimodalEmbeddingProvider",
    ),
}


def __getattr__(name: str) -> Any:  # pragma: no cover
    """
    Lazy attribute loader for provider classes.

    This prevents import-time failures when optional dependencies (e.g. torch CUDA)
    are not available. Accessing a GPU provider will still raise, but with a more
    actionable message.
    """

    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module_name, attr_name = _EXPORTS[name]
    try:
        module = __import__(module_name, fromlist=[attr_name])
        return getattr(module, attr_name)
    except ImportError as e:
        if module_name.endswith(".local_embedding"):
            raise ImportError(
                "Failed to import local GPU providers (torch/CUDA dependency issue). "
                "If you don't need local GPU embedding/reranking, use an API-based provider "
                "(e.g. EMBEDDING_PROVIDER=openai) and avoid importing these classes. "
                "Original error: " + str(e)
            ) from e
        raise


def __dir__() -> list[str]:  # pragma: no cover
    return sorted(set(list(globals().keys()) + list(_EXPORTS.keys())))
