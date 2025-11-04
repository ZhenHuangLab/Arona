"""
Model provider factory.

Creates appropriate provider instances based on configuration.
Converts providers to RAGAnything-compatible function signatures.
"""

from __future__ import annotations

from typing import Callable, Optional, List, Dict, Any

from lightrag.utils import EmbeddingFunc

from backend.config import ModelConfig, ProviderType, ModelType, RerankerConfig
from backend.providers.base import BaseLLMProvider, BaseVisionProvider, BaseEmbeddingProvider


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
    def create_reranker(config: RerankerConfig) -> Optional[Callable]:
        """
        Create reranker from configuration.
        
        Args:
            config: Reranker configuration
            
        Returns:
            Reranker function or None if disabled
        """
        if not config or not config.enabled:
            return None
        
        if config.provider == "local":
            # Use FlagEmbedding reranker
            if not config.model_path:
                raise ValueError("Local reranker requires model_path")

            from raganything.rerankers.flagembedding import FlagEmbeddingReranker

            reranker = FlagEmbeddingReranker(
                model_path=config.model_path,
                use_fp16=config.use_fp16,
                batch_size=config.batch_size,
            )

            # Return async wrapper
            # Accept **_kwargs to stay compatible with LightRAG, which may pass extra
            # parameters such as top_n when calling the reranker. We ignore them
            # here because our contract is to return one score per input document.
            async def rerank_func(query: str, documents: List[str], **_kwargs) -> List[Dict[str, float]]:
                # Return new-format results to avoid LightRAG's legacy adaptation path.
                # Reason: Some LightRAG versions mishandle legacy float lists during rerank merge.
                scores = await reranker.score_async(query, documents)
                return [{"index": i, "relevance_score": float(s), "score": float(s)} for i, s in enumerate(scores)]

            return rerank_func

        elif config.provider == "api":
            # Use API-based reranker (Jina, Cohere, Voyage, etc.)
            if not config.model_name:
                raise ValueError("API reranker requires model_name")
            if not config.api_key:
                raise ValueError("API reranker requires api_key")

            from raganything.rerankers.api_reranker import APIReranker

            # Determine provider from base_url or model_name
            provider = ModelFactory._detect_reranker_provider(config)

            reranker = APIReranker(
                provider=provider,
                model_name=config.model_name,
                api_key=config.api_key,
                base_url=config.base_url,
                batch_size=config.batch_size,
            )

            # Return async wrapper
            # Accept **_kwargs to stay compatible with LightRAG, which may pass extra
            # parameters such as top_n when calling the reranker. We ignore them
            # here because our contract is to return one score per input document.
            async def rerank_func(query: str, documents: List[str], **_kwargs) -> List[Dict[str, float]]:
                # Return new-format results to avoid LightRAG's legacy adaptation path.
                scores = await reranker.score_async(query, documents)
                return [{"index": i, "relevance_score": float(s), "score": float(s)} for i, s in enumerate(scores)]

            return rerank_func

        else:
            raise ValueError(f"Unknown reranker provider: {config.provider}")
    
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
        
        async def embed_func(texts: List[str]) -> Any:
            """RAGAnything-compatible embedding function."""
            return await provider.embed(texts)
        
        return EmbeddingFunc(
            embedding_dim=provider.embedding_dim,
            max_token_size=config.extra_params.get("max_token_size", 8192),
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

