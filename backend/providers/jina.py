"""
Jina AI provider implementation.

Provides custom implementation for Jina AI embeddings and reranking APIs.
"""

from __future__ import annotations

from typing import List, Optional
import numpy as np
import httpx

from backend.providers.base import BaseEmbeddingProvider
from backend.config import ModelConfig


class JinaEmbeddingProvider(BaseEmbeddingProvider):
    """Jina AI embedding provider with custom API implementation."""
    
    def __init__(self, config: ModelConfig):
        """
        Initialize Jina embedding provider.
        
        Args:
            config: Model configuration
        """
        self.config = config
        self.model_name = config.model_name
        self.api_key = config.api_key
        self.base_url = config.base_url or "https://api.jina.ai/v1/embeddings"
        self._embedding_dim = config.embedding_dim
        
        if not self._embedding_dim:
            raise ValueError("Embedding dimension must be specified in config")
        
        if not self.api_key:
            raise ValueError("Jina API key is required")
    
    async def embed(
        self,
        texts: List[str],
        **kwargs
    ) -> np.ndarray:
        """
        Generate embeddings using Jina AI API.
        
        Note: Jina AI doesn't support encoding_format parameter,
        so we use a custom implementation instead of lightrag's openai_embed.
        
        Args:
            texts: List of texts to embed
            **kwargs: Additional parameters
            
        Returns:
            numpy array of embeddings
        """
        if not texts:
            return np.array([])
        
        # Prepare request
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": self.model_name,
            "input": texts,
            # Note: Do NOT include encoding_format - Jina doesn't support it
        }
        
        # Add any extra parameters from kwargs
        # Filter out parameters that Jina doesn't support
        supported_params = {"task", "dimensions", "late_chunking", "embedding_type"}
        for key, value in kwargs.items():
            if key in supported_params:
                payload[key] = value
        
        # Make API request
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    self.base_url,
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                
                result = response.json()
                
                # Extract embeddings from response
                # Jina API returns: {"data": [{"embedding": [...], "index": 0}, ...]}
                embeddings = [item["embedding"] for item in result["data"]]
                
                return np.array(embeddings, dtype=np.float32)
                
            except httpx.HTTPStatusError as e:
                error_detail = e.response.text
                raise RuntimeError(
                    f"Jina API request failed with status {e.response.status_code}: {error_detail}"
                ) from e
            except Exception as e:
                raise RuntimeError(f"Jina embedding request failed: {e}") from e
    
    @property
    def embedding_dim(self) -> int:
        """Return the dimensionality of embeddings."""
        return self._embedding_dim

