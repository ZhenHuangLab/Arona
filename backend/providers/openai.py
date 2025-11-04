"""
OpenAI-compatible provider implementation.

Supports OpenAI, Azure OpenAI, and any OpenAI-compatible API (LM Studio, vLLM, etc.)
"""

from __future__ import annotations

import asyncio
from typing import List, Optional, Dict, Any, AsyncIterator

import numpy as np

from backend.providers.base import BaseLLMProvider, BaseVisionProvider, BaseEmbeddingProvider
from backend.config import ModelConfig


class OpenAILLMProvider(BaseLLMProvider):
    """OpenAI-compatible LLM provider."""
    
    def __init__(self, config: ModelConfig):
        """
        Initialize OpenAI LLM provider.
        
        Args:
            config: Model configuration
        """
        self.config = config
        self.model_name = config.model_name
        self.api_key = config.api_key
        self.base_url = config.base_url
        self.temperature = config.temperature
        self.max_tokens = config.max_tokens
    
    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        history_messages: Optional[List[Dict[str, str]]] = None,
        **kwargs
    ) -> str:
        """Generate text completion using OpenAI API."""
        # Import here to avoid dependency if not using OpenAI
        from lightrag.llm.openai import openai_complete_if_cache
        
        response = await openai_complete_if_cache(
            model=self.model_name,
            prompt=prompt,
            system_prompt=system_prompt,
            history_messages=history_messages or [],
            api_key=self.api_key,
            base_url=self.base_url,
            temperature=kwargs.get("temperature", self.temperature),
            max_tokens=kwargs.get("max_tokens", self.max_tokens),
            **kwargs
        )
        
        return response
    
    async def complete_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        history_messages: Optional[List[Dict[str, str]]] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Generate streaming text completion."""
        # For now, yield the complete response
        # TODO: Implement true streaming with OpenAI streaming API
        response = await self.complete(prompt, system_prompt, history_messages, **kwargs)
        yield response


class OpenAIVisionProvider(BaseVisionProvider):
    """OpenAI-compatible vision-language model provider."""
    
    def __init__(self, config: ModelConfig):
        """
        Initialize OpenAI vision provider.
        
        Args:
            config: Model configuration
        """
        self.config = config
        self.model_name = config.model_name
        self.api_key = config.api_key
        self.base_url = config.base_url
    
    async def complete_with_images(
        self,
        prompt: str,
        images: List[str],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """Generate text completion with image inputs."""
        from lightrag.llm.openai import openai_complete_if_cache
        
        # Build messages with images
        content = [{"type": "text", "text": prompt}]
        
        for img_base64 in images:
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{img_base64}"}
            })
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": content})
        
        response = await openai_complete_if_cache(
            model=self.model_name,
            prompt="",  # Empty prompt when using messages
            system_prompt=None,
            history_messages=[],
            messages=messages,
            api_key=self.api_key,
            base_url=self.base_url,
            **kwargs
        )
        
        return response


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    """OpenAI-compatible embedding provider."""
    
    def __init__(self, config: ModelConfig):
        """
        Initialize OpenAI embedding provider.
        
        Args:
            config: Model configuration
        """
        self.config = config
        self.model_name = config.model_name
        self.api_key = config.api_key
        self.base_url = config.base_url
        self._embedding_dim = config.embedding_dim
        
        if not self._embedding_dim:
            raise ValueError("Embedding dimension must be specified in config")
    
    async def embed(
        self,
        texts: List[str],
        **kwargs
    ) -> np.ndarray:
        """Generate embeddings using OpenAI API."""
        from lightrag.llm.openai import openai_embed
        
        embeddings = await openai_embed(
            texts=texts,
            model=self.model_name,
            api_key=self.api_key,
            base_url=self.base_url,
            **kwargs
        )
        
        return embeddings
    
    @property
    def embedding_dim(self) -> int:
        """Return the dimensionality of embeddings."""
        return self._embedding_dim

