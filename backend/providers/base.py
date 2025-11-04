"""
Abstract base classes for model providers.

Defines the interface that all model providers must implement.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, AsyncIterator


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        history_messages: Optional[List[Dict[str, str]]] = None,
        **kwargs
    ) -> str:
        """
        Generate text completion.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            history_messages: Optional conversation history
            **kwargs: Provider-specific parameters
            
        Returns:
            Generated text response
        """
        pass
    
    @abstractmethod
    async def complete_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        history_messages: Optional[List[Dict[str, str]]] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Generate streaming text completion.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            history_messages: Optional conversation history
            **kwargs: Provider-specific parameters
            
        Yields:
            Text chunks as they are generated
        """
        pass


class BaseVisionProvider(ABC):
    """Abstract base class for vision-language model providers."""
    
    @abstractmethod
    async def complete_with_images(
        self,
        prompt: str,
        images: List[str],  # Base64 encoded images
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Generate text completion with image inputs.
        
        Args:
            prompt: User prompt
            images: List of base64-encoded images
            system_prompt: Optional system prompt
            **kwargs: Provider-specific parameters
            
        Returns:
            Generated text response
        """
        pass


class BaseEmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""
    
    @abstractmethod
    async def embed(
        self,
        texts: List[str],
        **kwargs
    ) -> List[List[float]]:
        """
        Generate embeddings for input texts.
        
        Args:
            texts: List of texts to embed
            **kwargs: Provider-specific parameters
            
        Returns:
            List of embedding vectors
        """
        pass
    
    @property
    @abstractmethod
    def embedding_dim(self) -> int:
        """Return the dimensionality of embeddings."""
        pass


class BaseRerankerProvider(ABC):
    """Abstract base class for reranking providers."""
    
    @abstractmethod
    async def rerank(
        self,
        query: str,
        documents: List[str],
        **kwargs
    ) -> List[float]:
        """
        Rerank documents for a query.
        
        Args:
            query: Search query
            documents: List of document texts to rerank
            **kwargs: Provider-specific parameters
            
        Returns:
            List of relevance scores (same length as documents)
        """
        pass

