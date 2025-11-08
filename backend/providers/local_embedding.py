"""
Local GPU embedding and reranking provider implementation.

Supports local deployment of Qwen3-Embedding-4B and Qwen3-Reranker-4B models
on NVIDIA GPUs with FP16 precision and Pascal architecture compatibility.
"""

from __future__ import annotations

import asyncio
import logging
from typing import List, Optional
import numpy as np
import torch
from sentence_transformers import SentenceTransformer
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from backend.providers.base import BaseEmbeddingProvider, BaseRerankerProvider
from backend.config import ModelConfig

logger = logging.getLogger(__name__)


class LocalEmbeddingProvider(BaseEmbeddingProvider):
    """Local GPU embedding provider using sentence-transformers."""
    
    def __init__(self, config: ModelConfig):
        """
        Initialize local embedding provider.
        
        Args:
            config: Model configuration with device, dtype, and model_name
        
        Raises:
            ValueError: If required configuration is missing
            RuntimeError: If model loading fails
        """
        self.config = config
        self.model_name = config.model_name
        self._embedding_dim = config.embedding_dim
        
        if not self._embedding_dim:
            raise ValueError("Embedding dimension must be specified in config")
        
        # Get device from extra_params or default to cuda:0
        self.device = config.extra_params.get("device", "cuda:0")
        dtype_str = config.extra_params.get("dtype", "float16")
        attn_impl = config.extra_params.get("attn_implementation", "sdpa")
        
        # Convert dtype string to torch dtype
        self.dtype = torch.float16 if dtype_str == "float16" else torch.float32
        
        logger.info(
            f"Loading local embedding model: {self.model_name} "
            f"(device={self.device}, dtype={dtype_str}, attn={attn_impl})"
        )
        
        try:
            # Load model with sentence-transformers
            # Note: sentence-transformers handles model_kwargs internally
            model_kwargs = {
                "torch_dtype": self.dtype,
                "attn_implementation": attn_impl,
                "trust_remote_code": True,
            }
            
            # Get model path from config or use model_name for HF download
            model_path = config.extra_params.get("model_path", self.model_name)
            
            self.model = SentenceTransformer(
                model_path,
                device=self.device,
                model_kwargs=model_kwargs,
            )
            
            # Verify model dtype
            if hasattr(self.model, '_first_module'):
                actual_dtype = next(self.model._first_module().parameters()).dtype
                if actual_dtype != self.dtype:
                    logger.warning(
                        f"Model dtype mismatch: expected {self.dtype}, got {actual_dtype}"
                    )
            
            # Warmup inference to allocate GPU memory
            logger.info("Performing warmup inference...")
            _ = self.model.encode(
                ["warmup text"],
                convert_to_tensor=True,
                show_progress_bar=False,
            )
            
            # Log memory usage
            if torch.cuda.is_available():
                allocated = torch.cuda.memory_allocated(self.device) / 1024**3
                logger.info(f"GPU memory allocated: {allocated:.2f} GB")
            
            logger.info(f"Local embedding model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load local embedding model: {e}")
            raise RuntimeError(f"Failed to load local embedding model: {e}") from e
    
    async def embed(
        self,
        texts: List[str],
        **kwargs
    ) -> np.ndarray:
        """
        Generate embeddings for input texts.
        
        Args:
            texts: List of texts to embed
            **kwargs: Additional parameters (ignored for now)
            
        Returns:
            numpy array of embeddings with shape (len(texts), embedding_dim)
        
        Raises:
            RuntimeError: If embedding generation fails
        """
        if not texts:
            return np.array([])
        
        try:
            # Run inference in thread pool to avoid blocking event loop
            loop = asyncio.get_event_loop()
            embeddings = await loop.run_in_executor(
                None,
                self._encode_sync,
                texts,
            )
            
            return embeddings
            
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            raise RuntimeError(f"Embedding generation failed: {e}") from e
    
    def _encode_sync(self, texts: List[str]) -> np.ndarray:
        """
        Synchronous encoding method for thread pool execution.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            numpy array of embeddings
        """
        with torch.no_grad():
            # Encode texts to tensor
            embeddings_tensor = self.model.encode(
                texts,
                convert_to_tensor=True,
                show_progress_bar=False,
                batch_size=32,  # Default batch size, can be made configurable
            )
            
            # Convert to numpy
            embeddings_np = embeddings_tensor.cpu().numpy()
            
            return embeddings_np.astype(np.float32)
    
    @property
    def embedding_dim(self) -> int:
        """Return the dimensionality of embeddings."""
        return self._embedding_dim


class LocalRerankerProvider(BaseRerankerProvider):
    """Local GPU reranker provider using Qwen3-Reranker-4B."""
    
    def __init__(self, config: ModelConfig):
        """
        Initialize local reranker provider.
        
        Args:
            config: Model configuration with device, dtype, and model_name
        
        Raises:
            ValueError: If required configuration is missing
            RuntimeError: If model loading fails
        """
        self.config = config
        self.model_name = config.model_name
        
        # Get device from extra_params or default to cuda:1
        self.device = config.extra_params.get("device", "cuda:1")
        dtype_str = config.extra_params.get("dtype", "float16")
        attn_impl = config.extra_params.get("attn_implementation", "sdpa")
        
        # Convert dtype string to torch dtype
        self.dtype = torch.float16 if dtype_str == "float16" else torch.float32
        
        logger.info(
            f"Loading local reranker model: {self.model_name} "
            f"(device={self.device}, dtype={dtype_str}, attn={attn_impl})"
        )
        
        try:
            # Get model path from config or use model_name for HF download
            model_path = config.extra_params.get("model_path", self.model_name)
            
            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(
                model_path,
                trust_remote_code=True,
            )

            # Set padding side to left (Qwen3-Reranker requirement)
            self.tokenizer.padding_side = "left"

            # Set pad_token if not set (MUST be done before any tokenization)
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token

            # Also set pad_token_id to ensure consistency
            if self.tokenizer.pad_token_id is None:
                self.tokenizer.pad_token_id = self.tokenizer.eos_token_id

            # Load model
            self.model = AutoModelForSequenceClassification.from_pretrained(
                model_path,
                torch_dtype=self.dtype,
                attn_implementation=attn_impl,
                trust_remote_code=True,
            )

            # Set pad_token_id in model config (critical for batch processing)
            if self.model.config.pad_token_id is None:
                self.model.config.pad_token_id = self.tokenizer.pad_token_id

            # Move model to device
            self.model = self.model.to(self.device)
            self.model.eval()

            # Verify model dtype
            actual_dtype = next(self.model.parameters()).dtype
            if actual_dtype != self.dtype:
                logger.warning(
                    f"Model dtype mismatch: expected {self.dtype}, got {actual_dtype}"
                )

            # Warmup inference (now safe to use batch size > 1)
            logger.info("Performing warmup inference...")
            with torch.no_grad():
                dummy_inputs = self.tokenizer(
                    [["warmup query", "warmup document"]],
                    padding=True,
                    truncation=True,
                    return_tensors="pt",
                    max_length=512,
                ).to(self.device)
                _ = self.model(**dummy_inputs)
            
            # Log memory usage
            if torch.cuda.is_available():
                allocated = torch.cuda.memory_allocated(self.device) / 1024**3
                logger.info(f"GPU memory allocated: {allocated:.2f} GB")
            
            logger.info(f"Local reranker model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load local reranker model: {e}")
            raise RuntimeError(f"Failed to load local reranker model: {e}") from e
    
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
            **kwargs: Additional parameters (ignored for now)
            
        Returns:
            List of relevance scores (same length as documents)
        
        Raises:
            RuntimeError: If reranking fails
        """
        if not documents:
            return []
        
        try:
            # Run inference in thread pool to avoid blocking event loop
            loop = asyncio.get_event_loop()
            scores = await loop.run_in_executor(
                None,
                self._rerank_sync,
                query,
                documents,
            )
            
            return scores
            
        except Exception as e:
            logger.error(f"Reranking failed: {e}")
            raise RuntimeError(f"Reranking failed: {e}") from e
    
    def _rerank_sync(self, query: str, documents: List[str]) -> List[float]:
        """
        Synchronous reranking method for thread pool execution.
        
        Args:
            query: Search query
            documents: List of document texts
            
        Returns:
            List of relevance scores
        """
        with torch.no_grad():
            # Prepare input pairs (query, document)
            pairs = [[query, doc] for doc in documents]
            
            # Tokenize
            inputs = self.tokenizer(
                pairs,
                padding=True,
                truncation=True,
                return_tensors="pt",
                max_length=8192,  # Qwen3-Reranker supports 8k context
            ).to(self.device)
            
            # Forward pass
            outputs = self.model(**inputs)

            # Extract scores from logits
            # Qwen3-Reranker outputs logits of shape (batch_size, 2) for binary classification
            # We take the score for the positive class (index 1)
            logits = outputs.logits

            # Handle different logits shapes
            if logits.dim() == 2 and logits.shape[1] == 2:
                # Binary classification: (batch_size, 2) -> take positive class score
                scores = logits[:, 1].cpu().tolist()
            elif logits.dim() == 2 and logits.shape[1] == 1:
                # Single score per sample: (batch_size, 1) -> squeeze
                scores = logits.squeeze(-1).cpu().tolist()
            elif logits.dim() == 1:
                # Already 1D: (batch_size,)
                scores = logits.cpu().tolist()
            else:
                # Fallback: squeeze and convert
                scores = logits.squeeze().cpu().tolist()

            # Ensure scores is a list
            if not isinstance(scores, list):
                scores = [scores]

            return scores

