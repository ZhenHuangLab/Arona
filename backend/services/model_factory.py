"""
Model provider factory.

Creates appropriate provider instances based on configuration.
Converts providers to RAGAnything-compatible function signatures.
"""

from __future__ import annotations

import logging
from typing import Callable, Optional, List, Dict, Any

from lightrag.utils import EmbeddingFunc

from backend.config import ModelConfig, ProviderType, ModelType, RerankerConfig
from backend.providers.base import (
    BaseLLMProvider,
    BaseVisionProvider,
    BaseEmbeddingProvider,
    BaseRerankerProvider,
)

logger = logging.getLogger(__name__)


class ModelFactory:
    """Factory for creating model providers."""
    
    @staticmethod
    def create_llm_provider(config: ModelConfig) -> BaseLLMProvider:
        """
        Create LLM provider from configuration.
        
        Args:
            config: Model configuration
            
        Returns:
            LLM provider instance
        """
        if config.model_type != ModelType.LLM:
            raise ValueError(f"Expected LLM model type, got {config.model_type}")
        
        if config.provider in [ProviderType.OPENAI, ProviderType.AZURE, ProviderType.CUSTOM, ProviderType.LOCAL]:
            from backend.providers.openai import OpenAILLMProvider
            return OpenAILLMProvider(config)
        elif config.provider == ProviderType.ANTHROPIC:
            # TODO: Implement Anthropic provider
            raise NotImplementedError("Anthropic provider not yet implemented")
        else:
            raise ValueError(f"Unsupported provider: {config.provider}")
    
    @staticmethod
    def create_vision_provider(config: ModelConfig) -> BaseVisionProvider:
        """
        Create vision provider from configuration.
        
        Args:
            config: Model configuration
            
        Returns:
            Vision provider instance
        """
        if config.model_type != ModelType.VISION:
            raise ValueError(f"Expected VISION model type, got {config.model_type}")
        
        if config.provider in [ProviderType.OPENAI, ProviderType.AZURE, ProviderType.CUSTOM, ProviderType.LOCAL]:
            from backend.providers.openai import OpenAIVisionProvider
            return OpenAIVisionProvider(config)
        elif config.provider == ProviderType.ANTHROPIC:
            # TODO: Implement Anthropic vision provider
            raise NotImplementedError("Anthropic vision provider not yet implemented")
        else:
            raise ValueError(f"Unsupported provider: {config.provider}")
    
    @staticmethod
    def create_embedding_provider(config: ModelConfig) -> BaseEmbeddingProvider:
        """
        Create embedding provider from configuration.

        Args:
            config: Model configuration

        Returns:
            Embedding provider instance
        """
        if config.model_type != ModelType.EMBEDDING:
            raise ValueError(f"Expected EMBEDDING model type, got {config.model_type}")

        device = config.extra_params.get("device")
        is_cuda_device = isinstance(device, str) and device.startswith("cuda")

        # Local GPU embedding is explicitly enabled via provider=local_gpu.
        # Backward-compat: provider=local + cuda device + no base_url also means local GPU.
        is_local_gpu = (
            config.provider == ProviderType.LOCAL_GPU
            or (config.provider == ProviderType.LOCAL and config.base_url is None and is_cuda_device)
        )
        if config.provider == ProviderType.LOCAL and config.base_url is None and is_cuda_device:
            logger.warning(
                "Embedding provider configured as provider=local with cuda device but no base_url; "
                "treating as local GPU provider for backward compatibility. "
                "Prefer EMBEDDING_PROVIDER=local_gpu for explicit configuration."
            )

        if is_local_gpu:
            model_name_lower = config.model_name.lower()

            # Qwen3-VL embedding models (multimodal-capable; currently used in text-only path)
            if "qwen3-vl-embedding" in model_name_lower:
                from backend.providers.qwen3_vl import Qwen3VLEmbeddingProvider

                return Qwen3VLEmbeddingProvider(config)

            # Multimodal embedding models (GME-Qwen2-VL family)
            is_multimodal = "gme" in model_name_lower or "qwen2-vl" in model_name_lower
            if is_multimodal:
                try:
                    from backend.providers.local_embedding import MultimodalEmbeddingProvider
                except ImportError as e:
                    raise ImportError(
                        "Failed to import local GPU multimodal embedding provider. "
                        "This usually means your PyTorch/CUDA runtime is not correctly installed. "
                        "If you don't need local GPU embedding, configure an API-based provider "
                        "(e.g. EMBEDDING_PROVIDER=openai/custom) instead. "
                        "Original error: "
                        + str(e)
                    ) from e

                return MultimodalEmbeddingProvider(config)

            try:
                from backend.providers.local_embedding import LocalEmbeddingProvider
            except ImportError as e:
                raise ImportError(
                    "Failed to import local GPU embedding provider. "
                    "This usually means your PyTorch/CUDA runtime is not correctly installed. "
                    "If you don't need local GPU embedding, configure an API-based provider "
                    "(e.g. EMBEDDING_PROVIDER=openai/custom) instead. "
                    "Original error: "
                    + str(e)
                ) from e

            return LocalEmbeddingProvider(config)

        # Check if this is a Jina model (by model name or base URL)
        is_jina = (
            "jina" in config.model_name.lower() or
            (config.base_url and "jina.ai" in config.base_url.lower())
        )

        if is_jina:
            from backend.providers.jina import JinaEmbeddingProvider
            return JinaEmbeddingProvider(config)
        elif config.provider in [ProviderType.OPENAI, ProviderType.AZURE, ProviderType.CUSTOM, ProviderType.LOCAL]:
            from backend.providers.openai import OpenAIEmbeddingProvider
            return OpenAIEmbeddingProvider(config)
        else:
            raise ValueError(f"Unsupported provider: {config.provider}")
    
    @staticmethod
    def create_reranker_provider(config: RerankerConfig) -> Optional[BaseRerankerProvider]:
        """Create a BaseRerankerProvider from configuration."""
        if not config or not config.enabled:
            return None

        if config.provider in {"local", "local_gpu"}:
            # Check if this is a local GPU provider (by device parameter)
            is_local_gpu = config.device and config.device.startswith("cuda")

            if is_local_gpu:
                if not config.model_name:
                    raise ValueError("Local GPU reranker requires model_name")

                from backend.config import ModelConfig, ModelType

                extra_params: Dict[str, Any] = {
                    "device": config.device,
                    "dtype": config.dtype,
                    "attn_implementation": config.attn_implementation,
                    "batch_size": config.batch_size,
                    "max_length": config.max_length,
                    "min_image_tokens": config.min_image_tokens,
                    "max_image_tokens": config.max_image_tokens,
                    "allow_image_urls": config.allow_image_urls,
                }
                if config.model_path:
                    extra_params["model_path"] = config.model_path
                if config.instruction:
                    extra_params["instruction"] = config.instruction
                if config.system_prompt:
                    extra_params["system_prompt"] = config.system_prompt

                model_config = ModelConfig(
                    provider=ProviderType.LOCAL,
                    model_name=config.model_name,
                    model_type=ModelType.RERANKER,
                    extra_params=extra_params,
                )

                model_name_lower = config.model_name.lower()
                if "qwen3-vl-reranker" in model_name_lower:
                    from backend.providers.qwen3_vl import Qwen3VLRerankerProvider

                    return Qwen3VLRerankerProvider(model_config)

                try:
                    from backend.providers.local_embedding import LocalRerankerProvider
                except ImportError as e:
                    raise ImportError(
                        "Failed to import local GPU reranker provider. "
                        "This usually means your PyTorch/CUDA runtime is not correctly installed. "
                        "If you don't need local GPU reranking, set RERANKER_PROVIDER=api or disable reranking. "
                        "Original error: "
                        + str(e)
                    ) from e

                return LocalRerankerProvider(model_config)

            # CPU reranker (FlagEmbedding)
            if not config.model_path:
                raise ValueError("Local reranker requires model_path")

            from raganything.rerankers.flagembedding import FlagEmbeddingReranker
            from backend.providers.reranker_wrappers import FlagEmbeddingRerankerProvider

            reranker = FlagEmbeddingReranker(
                model_path=config.model_path,
                use_fp16=config.dtype == "float16",
                batch_size=config.batch_size,
            )
            return FlagEmbeddingRerankerProvider(reranker)

        if config.provider == "api":
            if not config.model_name:
                raise ValueError("API reranker requires model_name")
            if not config.api_key:
                raise ValueError("API reranker requires api_key")

            from raganything.rerankers.api_reranker import APIReranker
            from backend.providers.reranker_wrappers import APIRerankerProvider

            provider = ModelFactory._detect_reranker_provider(config)
            reranker = APIReranker(
                provider=provider,
                model_name=config.model_name,
                api_key=config.api_key,
                base_url=config.base_url,
                batch_size=config.batch_size,
            )
            return APIRerankerProvider(reranker)

        raise ValueError(f"Unknown reranker provider: {config.provider}")

    @staticmethod
    def create_reranker(config: RerankerConfig) -> Optional[Callable]:
        """
        Create a RAGAnything-compatible reranker function from configuration.

        Note: This returns the LightRAG/RAGAnything contract (list of dicts with scores),
        not raw float scores.
        """
        provider = ModelFactory.create_reranker_provider(config)
        if provider is None:
            return None

        async def rerank_func(query: str, documents: List[str], **kwargs) -> List[Dict[str, float]]:
            scores = await provider.rerank(query, documents, **kwargs)
            return [{"index": i, "relevance_score": float(s), "score": float(s)} for i, s in enumerate(scores)]

        # Keep a reference for lifecycle management (optional; used by RAGService).
        setattr(rerank_func, "_provider", provider)
        return rerank_func
    
    @staticmethod
    def create_llm_func(config: ModelConfig) -> Callable:
        """
        Create RAGAnything-compatible LLM function.
        
        Args:
            config: Model configuration
            
        Returns:
            Async function compatible with RAGAnything's llm_model_func signature
        """
        provider = ModelFactory.create_llm_provider(config)
        
        async def llm_func(
            prompt: str,
            system_prompt: Optional[str] = None,
            history_messages: Optional[List[Dict[str, str]]] = None,
            **kwargs
        ) -> str:
            """RAGAnything-compatible LLM function."""
            return await provider.complete(
                prompt=prompt,
                system_prompt=system_prompt,
                history_messages=history_messages,
                **kwargs
            )
        
        return llm_func
    
    @staticmethod
    def create_vision_func(config: ModelConfig) -> Callable:
        """
        Create RAGAnything-compatible vision function.
        
        Args:
            config: Model configuration
            
        Returns:
            Async function compatible with RAGAnything's vision_model_func signature
        """
        provider = ModelFactory.create_vision_provider(config)
        
        async def vision_func(
            prompt: str,
            images: Optional[List[str]] = None,
            system_prompt: Optional[str] = None,
            image_data: Optional[str] = None,
            messages: Optional[List[Dict[str, Any]]] = None,
            **kwargs
        ) -> str:
            """RAGAnything-compatible vision function.
            Accepts either:
            - images: list of base64 strings,
            - image_data: single base64 string (backward-compat),
            - messages: full Chat Completions messages (may include image_url parts),
            - or text-only prompt (falls back to chat completion with vision model).
            """
            # Handle backward-compat single image
            if image_data and not images:
                images = [image_data]

            # If full messages are provided, prefer sending them directly
            if messages is not None:
                try:
                    complete_with_messages = getattr(provider, "complete_with_messages", None)
                    if callable(complete_with_messages):
                        return await complete_with_messages(messages=messages, **kwargs)
                except Exception:
                    # Fall through to generic OpenAI-compatible call below
                    pass

                # Generic OpenAI-compatible path using LightRAG helper
                from lightrag.llm.openai import openai_complete_if_cache

                return await openai_complete_if_cache(
                    model=provider.model_name,
                    prompt="",  # messages used instead
                    system_prompt=None,
                    history_messages=[],
                    messages=messages,
                    api_key=provider.api_key,
                    base_url=provider.base_url,
                    **kwargs,
                )

            # Text-only fallback (no images, no messages)
            if not images:
                from lightrag.llm.openai import openai_complete_if_cache

                return await openai_complete_if_cache(
                    model=provider.model_name,
                    prompt=prompt,
                    system_prompt=system_prompt,
                    history_messages=[],
                    api_key=provider.api_key,
                    base_url=provider.base_url,
                    **kwargs,
                )

            # Normal vision call with images
            return await provider.complete_with_images(
                prompt=prompt,
                images=images,
                system_prompt=system_prompt,
                **kwargs,
            )

        return vision_func
    
    @staticmethod
    def create_embedding_func(config: ModelConfig) -> EmbeddingFunc:
        """
        Create RAGAnything-compatible embedding function.

        Args:
            config: Model configuration

        Returns:
            EmbeddingFunc instance compatible with RAGAnything
        """
        provider = ModelFactory.create_embedding_provider(config)

        async def embed_func(texts: List[str], **kwargs) -> Any:
            """RAGAnything-compatible embedding function.

            Note: LightRAG may pass scheduling kwargs like ``_priority``.
            Providers are expected to ignore unknown kwargs.
            """
            return await provider.embed(texts, **kwargs)

        return EmbeddingFunc(
            embedding_dim=provider.embedding_dim,
            max_token_size=config.extra_params.get("max_token_size", 8192),
            func=embed_func,
        )

    @staticmethod
    def create_embedding_func_from_provider(provider: BaseEmbeddingProvider) -> EmbeddingFunc:
        """
        Create RAGAnything-compatible embedding function from an existing provider.

        This is useful when you need to keep a reference to the provider
        for lifecycle management (e.g., shutdown).

        Args:
            provider: Embedding provider instance

        Returns:
            EmbeddingFunc instance compatible with RAGAnything
        """
        async def embed_func(texts: List[str], **kwargs) -> Any:
            """RAGAnything-compatible embedding function.

            Note: LightRAG may pass scheduling kwargs like ``_priority``.
            Providers are expected to ignore unknown kwargs.
            """
            return await provider.embed(texts, **kwargs)

        max_token_size = 8192
        provider_config = getattr(provider, "config", None)
        if provider_config is not None and hasattr(provider_config, "extra_params"):
            max_token_size = provider_config.extra_params.get("max_token_size", max_token_size)

        return EmbeddingFunc(
            embedding_dim=provider.embedding_dim,
            max_token_size=max_token_size,
            func=embed_func,
        )

    @staticmethod
    def _detect_reranker_provider(config: RerankerConfig) -> str:
        """
        Detect reranker provider from configuration.

        Args:
            config: Reranker configuration

        Returns:
            Provider name (jina, cohere, voyage, openai)
        """
        # Check base_url for known providers
        if config.base_url:
            base_url_lower = config.base_url.lower()
            if "jina" in base_url_lower:
                return "jina"
            elif "cohere" in base_url_lower:
                return "cohere"
            elif "voyage" in base_url_lower:
                return "voyage"
            elif "openai" in base_url_lower:
                return "openai"

        # Check model_name for known providers
        if config.model_name:
            model_lower = config.model_name.lower()
            if "jina" in model_lower:
                return "jina"
            elif "cohere" in model_lower or "rerank" in model_lower:
                return "cohere"
            elif "voyage" in model_lower:
                return "voyage"

        # Default to OpenAI-compatible format
        return "openai"
