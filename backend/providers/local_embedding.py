"""
Local GPU embedding and reranking provider implementation.

Supports local deployment of Qwen3-Embedding-4B and Qwen3-Reranker-4B models
on NVIDIA GPUs with FP16 precision and Pascal architecture compatibility.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import List, Optional
import numpy as np
import torch
from sentence_transformers import SentenceTransformer
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from backend.providers.base import BaseEmbeddingProvider, BaseRerankerProvider
from backend.config import ModelConfig

logger = logging.getLogger(__name__)


@dataclass
class BatchRequest:
    """
    Represents a single batch processing request.

    Attributes:
        texts: List of texts to embed
        future: asyncio.Future to return the result
        timestamp: Request arrival time (for timeout calculation)
    """
    texts: List[str]
    future: asyncio.Future
    timestamp: float


class BatchProcessor:
    """
    Dynamic batch processor for embedding requests.

    Collects incoming requests in a queue and processes them in batches
    to maximize GPU utilization and throughput. Batches are triggered when:
    - Number of requests reaches max_batch_size, OR
    - Wait time exceeds max_wait_time

    This design is inspired by Ray Serve's dynamic batching and TEI's
    token-based batching approach.
    """

    def __init__(
        self,
        model: SentenceTransformer,
        max_batch_size: int = 32,
        max_wait_time: float = 0.1,
        device: str = "cuda:0",
        max_batch_tokens: Optional[int] = None,
    ):
        """
        Initialize batch processor.

        Args:
            model: SentenceTransformer model for encoding
            max_batch_size: Maximum number of requests per batch (default: 32)
            max_wait_time: Maximum wait time in seconds (default: 0.1 = 100ms)
            device: Device for inference (e.g., "cuda:0")
        """
        self.model = model
        self.max_batch_size = max_batch_size
        self.max_wait_time = max_wait_time
        self.device = device
        self.max_batch_tokens = max_batch_tokens

        # Request queue (unbounded to avoid blocking)
        self.queue: asyncio.Queue[BatchRequest] = asyncio.Queue()

        # Background processing task
        self._processor_task: Optional[asyncio.Task] = None
        self._shutdown = False
        # Deferred requests that exceeded token budget; served before queue
        self._deferred: List[BatchRequest] = []

        logger.info(
            (
                f"BatchProcessor initialized: max_batch_size={max_batch_size}, "
                f"max_wait_time={max_wait_time}s, device={device}, "
                f"max_batch_tokens={max_batch_tokens}"
            )
        )

    def start(self) -> None:
        """Start the background processing task."""
        if self._processor_task is None:
            self._processor_task = asyncio.create_task(self._process_loop())
            logger.info("BatchProcessor background task started")

    async def shutdown(self) -> None:
        """
        Gracefully shutdown the batch processor.

        Stops accepting new requests and waits for current batch to complete.
        """
        logger.info("BatchProcessor shutting down...")
        self._shutdown = True

        if self._processor_task:
            # Cancel the background task to unblock any pending queue.get()
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass
            finally:
                self._processor_task = None

        logger.info("BatchProcessor shutdown complete")

    async def embed(self, texts: List[str]) -> np.ndarray:
        """
        Submit an embedding request and wait for the result.

        Args:
            texts: List of texts to embed

        Returns:
            numpy array of embeddings with shape (len(texts), embedding_dim)

        Raises:
            RuntimeError: If embedding generation fails
        """
        if not texts:
            return np.array([])

        # Create a future for this request
        future: asyncio.Future = asyncio.Future()

        # Create batch request
        request = BatchRequest(
            texts=texts,
            future=future,
            timestamp=time.time()
        )

        # Add to queue
        await self.queue.put(request)

        # Wait for result
        return await future

    async def _process_loop(self) -> None:
        """
        Background task that continuously processes batches.

        Runs until shutdown is requested. Catches and logs exceptions
        to prevent the task from crashing.
        """
        logger.info("BatchProcessor processing loop started")

        while not self._shutdown:
            try:
                # Collect a batch of requests
                batch = await self._collect_batch()

                if batch:
                    # Process the batch
                    await self._process_batch(batch)

            except Exception as e:
                # Log error but continue running (Fail-Fast for individual requests,
                # but keep the background task alive)
                logger.error(f"Error in batch processing loop: {e}", exc_info=True)

        logger.info("BatchProcessor processing loop stopped")

    async def _collect_batch(self) -> List[BatchRequest]:
        """
        Collect a batch of requests from the queue.

        Batching is triggered when:
        1. Number of requests reaches max_batch_size, OR
        2. Wait time exceeds max_wait_time (from first request arrival)

        Returns:
            List of BatchRequest objects
        """
        batch: List[BatchRequest] = []

        # Determine first request: prefer deferred list
        if self._deferred:
            first_request = self._deferred.pop(0)
        else:
            # Wait for the first request (blocking)
            first_request = await self.queue.get()

        batch.append(first_request)
        first_request_time = first_request.timestamp

        # Track token budget if enabled
        total_tokens = self._count_request_tokens(first_request) if self.max_batch_tokens else 0

        # First, try to drain additional deferred requests into this batch
        while self._deferred and len(batch) < self.max_batch_size:
            candidate = self._deferred[0]
            if self.max_batch_tokens:
                cand_tokens = self._count_request_tokens(candidate)
                if total_tokens + cand_tokens > self.max_batch_tokens:
                    # Can't fit the next deferred request; keep it for later
                    break
                total_tokens += cand_tokens
            batch.append(candidate)
            self._deferred.pop(0)

        # Then quickly collect any requests already in the queue (non-blocking)
        while len(batch) < self.max_batch_size:
            try:
                request = self.queue.get_nowait()
                if self.max_batch_tokens:
                    req_tokens = self._count_request_tokens(request)
                    # If adding this request would exceed token budget, stash it for next round
                    if total_tokens + req_tokens > self.max_batch_tokens:
                        self._deferred.append(request)
                        break
                    total_tokens += req_tokens
                batch.append(request)
            except asyncio.QueueEmpty:
                break

        # If we haven't reached max_batch_size, wait for more requests
        # up to max_wait_time
        if len(batch) < self.max_batch_size:
            elapsed = time.time() - first_request_time
            remaining_time = self.max_wait_time - elapsed

            while len(batch) < self.max_batch_size and remaining_time > 0:
                try:
                    request = await asyncio.wait_for(
                        self.queue.get(),
                        timeout=remaining_time
                    )
                    if self.max_batch_tokens:
                        req_tokens = self._count_request_tokens(request)
                        if total_tokens + req_tokens > self.max_batch_tokens:
                            # Defer to next batch and stop collecting
                            self._deferred.append(request)
                            break
                        total_tokens += req_tokens
                    batch.append(request)

                    # Update remaining time
                    elapsed = time.time() - first_request_time
                    remaining_time = self.max_wait_time - elapsed

                except asyncio.TimeoutError:
                    # Timeout reached, stop collecting
                    break

        logger.debug(
            (
                f"Collected batch of {len(batch)} requests "
                f"(waited {time.time() - first_request_time:.3f}s) "
                + (
                    f"token_budget={total_tokens}/{self.max_batch_tokens}"
                    if self.max_batch_tokens
                    else ""
                )
            )
        )

        return batch

    async def _process_batch(self, batch: List[BatchRequest]) -> None:
        """
        Process a batch of requests and distribute results.

        Merges all texts from the batch, performs batch inference,
        and distributes results back to individual futures.

        Args:
            batch: List of BatchRequest objects to process
        """
        try:
            # Merge all texts and track indices for each request
            all_texts: List[str] = []
            request_indices: List[tuple[int, int]] = []

            for request in batch:
                start_idx = len(all_texts)
                all_texts.extend(request.texts)
                end_idx = len(all_texts)
                request_indices.append((start_idx, end_idx))

            logger.debug(
                f"Processing batch: {len(batch)} requests, {len(all_texts)} texts total"
            )

            # Perform batch inference in thread pool to avoid blocking event loop
            loop = asyncio.get_event_loop()
            all_embeddings = await loop.run_in_executor(
                None,
                self._encode_sync,
                all_texts
            )

            # Distribute results to individual futures
            for request, (start, end) in zip(batch, request_indices):
                try:
                    # Extract embeddings for this request
                    result = all_embeddings[start:end]

                    # Set result on the future
                    request.future.set_result(result)

                except Exception as e:
                    # Set exception on the future (Fail-Fast)
                    logger.error(f"Error distributing result: {e}", exc_info=True)
                    request.future.set_exception(
                        RuntimeError(f"Failed to distribute embedding result: {e}")
                    )

            logger.debug(f"Batch processing complete: {len(batch)} requests")

        except Exception as e:
            # If batch processing fails, propagate error to all requests
            logger.error(f"Batch processing failed: {e}", exc_info=True)

            for request in batch:
                if not request.future.done():
                    request.future.set_exception(
                        RuntimeError(f"Batch embedding generation failed: {e}")
                    )

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
                batch_size=32,  # Internal batch size for sentence-transformers
            )

            # Convert to numpy
            embeddings_np = embeddings_tensor.cpu().numpy()

            return embeddings_np.astype(np.float32)

    # -------------------------
    # Token counting utilities
    # -------------------------
    def _count_request_tokens(self, request: BatchRequest) -> int:
        """
        Estimate token count for all texts in a request using the model tokenizer.

        Falls back to character count if tokenizer is not available.
        """
        return self._count_texts_tokens(request.texts)

    def _count_texts_tokens(self, texts: List[str]) -> int:
        try:
            # sentence-transformers exposes .tokenize which returns dict-like with input_ids
            tokenized = self.model.tokenize(texts)  # type: ignore[attr-defined]
            input_ids = tokenized.get("input_ids") if isinstance(tokenized, dict) else getattr(tokenized, "input_ids", None)
            if input_ids is None:
                raise AttributeError("tokenize() returned no input_ids")
            return sum(len(ids) for ids in input_ids)
        except Exception:
            # Fallback heuristic: characters as tokens
            return sum(len(t) for t in texts)


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

            # Initialize batch processor
            max_batch_size = config.extra_params.get("max_batch_size", 32)
            max_wait_time = config.extra_params.get("max_wait_time", 0.1)

            self.batch_processor = BatchProcessor(
                model=self.model,
                max_batch_size=max_batch_size,
                max_wait_time=max_wait_time,
                device=self.device,
                max_batch_tokens=config.extra_params.get("max_batch_tokens"),
            )

            # Start background processing task
            self.batch_processor.start()

            logger.info(
                f"BatchProcessor initialized and started: "
                f"max_batch_size={max_batch_size}, max_wait_time={max_wait_time}s"
            )

        except Exception as e:
            logger.error(f"Failed to load local embedding model: {e}")
            raise RuntimeError(f"Failed to load local embedding model: {e}") from e
    
    async def embed(
        self,
        texts: List[str],
        **kwargs
    ) -> np.ndarray:
        """
        Generate embeddings for input texts using dynamic batching.

        Requests are automatically batched by the BatchProcessor to maximize
        GPU utilization and throughput.

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
            # Submit request to batch processor
            embeddings = await self.batch_processor.embed(texts)
            return embeddings

        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            raise RuntimeError(f"Embedding generation failed: {e}") from e

    async def shutdown(self) -> None:
        """
        Gracefully shutdown the embedding provider.

        Stops the batch processor and waits for pending requests to complete.
        Should be called before application shutdown.
        """
        logger.info("Shutting down LocalEmbeddingProvider...")
        await self.batch_processor.shutdown()
        logger.info("LocalEmbeddingProvider shutdown complete")
    
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
