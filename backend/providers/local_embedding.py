"""
Local GPU embedding and reranking provider implementation.

Supports local deployment of Qwen3-Embedding-4B and Qwen3-Reranker-4B models
on NVIDIA GPUs with FP16 precision and Pascal architecture compatibility.

Also supports multimodal embedding with GME-Qwen2-VL-2B for text+image joint encoding.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import List, Optional, Union, Any, Dict
import numpy as np
import torch
from PIL import Image
from sentence_transformers import SentenceTransformer
from transformers import AutoModelForCausalLM, AutoTokenizer, AutoModel, AutoProcessor

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
        encode_batch_size: int = 128,
    ):
        """
        Initialize batch processor.

        Args:
            model: SentenceTransformer model for encoding
            max_batch_size: Maximum number of requests per batch (default: 32)
            max_wait_time: Maximum wait time in seconds (default: 0.1 = 100ms)
            device: Device for inference (e.g., "cuda:0")
            encode_batch_size: Batch size for sentence-transformers encode() (default: 128)
        """
        self.model = model
        self.max_batch_size = max_batch_size
        self.max_wait_time = max_wait_time
        self.device = device
        self.max_batch_tokens = max_batch_tokens
        self.encode_batch_size = encode_batch_size

        # Request queue (unbounded to avoid blocking)
        self.queue: asyncio.Queue[Optional[BatchRequest]] = asyncio.Queue()

        # Background processing task
        self._processor_task: Optional[asyncio.Task] = None
        self._shutdown = False
        # Deferred requests that exceeded token budget; served before queue
        self._deferred: List[BatchRequest] = []

        logger.info(
            (
                f"BatchProcessor initialized: max_batch_size={max_batch_size}, "
                f"max_wait_time={max_wait_time}s, device={device}, "
                f"max_batch_tokens={max_batch_tokens}, encode_batch_size={encode_batch_size}"
            )
        )

    def start(self) -> None:
        """Start the background processing task."""
        if self._processor_task is None:
            self._processor_task = asyncio.create_task(self._process_loop())
            logger.info("BatchProcessor background task started")

    async def shutdown(self, timeout: Optional[float] = 5.0) -> None:
        """
        Gracefully shutdown the batch processor.

        Stops accepting new requests and drains any pending requests already in the queue.

        Notes:
        - This method tries to let the background loop exit cleanly. If it does not exit
          within ``timeout`` seconds (default: 5s), the loop is cancelled and all pending
          requests are failed with an exception.
        """
        logger.info("BatchProcessor shutting down...")
        self._shutdown = True

        if self._processor_task:
            # Wake any pending queue.get() call.
            await self.queue.put(None)
            try:
                if timeout is None:
                    await self._processor_task
                else:
                    await asyncio.wait_for(self._processor_task, timeout=timeout)
            except asyncio.TimeoutError:
                logger.warning("BatchProcessor shutdown timed out; cancelling background task")
                self._processor_task.cancel()
                try:
                    await self._processor_task
                except asyncio.CancelledError:
                    pass
            except asyncio.CancelledError:
                pass
            finally:
                self._processor_task = None

        # Fail any remaining queued/deferred requests.
        self._fail_pending(RuntimeError("BatchProcessor shut down"))

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

        if self._shutdown:
            raise RuntimeError("BatchProcessor is shut down")

        # Ensure background task is running (defensive)
        if self._processor_task is None:
            self.start()

        # Create a future for this request
        loop = asyncio.get_running_loop()
        future: asyncio.Future = loop.create_future()

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

        while True:
            try:
                # Collect a batch of requests
                batch = await self._collect_batch()

                if not batch:
                    # If we're shutting down and there's nothing left to do, exit cleanly.
                    if self._shutdown and not self._deferred and self.queue.empty():
                        break
                    continue

                # Process the batch
                await self._process_batch(batch)

            except asyncio.CancelledError:
                # Cancellation is used as a last resort during shutdown timeout.
                break

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

        # If shutting down and nothing pending, return immediately (do not block).
        if self._shutdown and not self._deferred and self.queue.empty():
            return []

        # Determine first request: prefer deferred list
        if self._deferred:
            first_request = self._deferred.pop(0)
        else:
            # Wait for the first request (blocking)
            first_request = await self.queue.get()

            # Sentinel used to unblock shutdown.
            if first_request is None:
                return []

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
                if request is None:
                    break
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
                    if request is None:
                        break
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

    def _fail_pending(self, exc: Exception) -> None:
        """Fail any queued/deferred requests with the provided exception."""
        # Fail deferred requests
        while self._deferred:
            request = self._deferred.pop(0)
            if not request.future.done():
                request.future.set_exception(exc)

        # Drain the queue without blocking
        while True:
            try:
                request = self.queue.get_nowait()
            except asyncio.QueueEmpty:
                break
            if request is None:
                continue
            if not request.future.done():
                request.future.set_exception(exc)

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
                batch_size=self.encode_batch_size,  # Use configurable batch size
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

            # Determine embedding dimension from model if not provided.
            model_dim = None
            if hasattr(self.model, "get_sentence_embedding_dimension"):
                try:
                    model_dim = int(self.model.get_sentence_embedding_dimension())
                except Exception:
                    model_dim = None

            if self._embedding_dim is None:
                if model_dim is None:
                    raise ValueError(
                        "Embedding dimension not provided and could not be determined from model"
                    )
                self._embedding_dim = model_dim
                logger.info(f"Detected embedding dimension from model: {self._embedding_dim}")
            elif model_dim is not None and self._embedding_dim != model_dim:
                raise ValueError(
                    f"Configured embedding_dim ({self._embedding_dim}) does not match model dimension ({model_dim})"
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
            encode_batch_size = config.extra_params.get("encode_batch_size", 128)

            self.batch_processor = BatchProcessor(
                model=self.model,
                max_batch_size=max_batch_size,
                max_wait_time=max_wait_time,
                device=self.device,
                max_batch_tokens=config.extra_params.get("max_batch_tokens"),
                encode_batch_size=encode_batch_size,
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
        self.batch_size = int(config.extra_params.get("batch_size", 16))
        self.max_length = int(config.extra_params.get("max_length", 8192))
        dtype_str = config.extra_params.get("dtype", "float16")
        attn_impl = config.extra_params.get("attn_implementation", "sdpa")

        if self.batch_size <= 0:
            raise ValueError(f"Invalid reranker batch_size: {self.batch_size}")
        if self.max_length <= 0:
            raise ValueError(f"Invalid reranker max_length: {self.max_length}")

        # Instruction-aware reranking (Qwen3 embedding/reranker series).
        # See the official model card for the yes/no scoring template.
        self.default_instruction = config.extra_params.get(
            "instruction",
            "Given a web search query, retrieve relevant passages that answer the query",
        )

        # System prompt used by the official template; can be overridden if needed.
        self.system_prompt = config.extra_params.get(
            "system_prompt",
            (
                "Judge whether the Document meets the requirements based on the Query and the Instruct provided. "
                "Note that the answer can only be \"yes\" or \"no\"."
            ),
        )

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

            # Qwen3-Reranker is a CausalLM model; reranking scores are derived from
            # the next-token probabilities of "yes" vs "no" given a prompt.
            self.model = AutoModelForCausalLM.from_pretrained(
                model_path,
                torch_dtype=self.dtype,
                attn_implementation=attn_impl,
                trust_remote_code=True,
            )

            # Set pad_token_id in model config (critical for padded batches).
            if self.model.config.pad_token_id is None:
                self.model.config.pad_token_id = self.tokenizer.pad_token_id

            # Precompute token IDs for yes/no scoring. We expect both to be single tokens.
            self._token_yes_id = self._require_single_token_id("yes")
            self._token_no_id = self._require_single_token_id("no")

            # Precompute prompt prefix/suffix token IDs.
            prefix = (
                f"<|im_start|>system\n{self.system_prompt}<|im_end|>\n"
                "<|im_start|>user\n"
            )
            suffix = (
                "<|im_end|>\n"
                "<|im_start|>assistant\n"
                "<think>\n\n</think>\n\n"
            )
            self._prefix_token_ids = self.tokenizer.encode(prefix, add_special_tokens=False)
            self._suffix_token_ids = self.tokenizer.encode(suffix, add_special_tokens=False)

            if len(self._prefix_token_ids) + len(self._suffix_token_ids) >= self.max_length:
                raise ValueError(
                    "Reranker prompt template is too long for max_length="
                    f"{self.max_length} (prefix={len(self._prefix_token_ids)}, suffix={len(self._suffix_token_ids)})"
                )

            # Move model to device
            self.model = self.model.to(self.device)
            self.model.eval()

            # Verify model dtype
            actual_dtype = next(self.model.parameters()).dtype
            if actual_dtype != self.dtype:
                logger.warning(
                    f"Model dtype mismatch: expected {self.dtype}, got {actual_dtype}"
                )

            # Warmup inference (use a small batch to allocate kernels and caches).
            logger.info("Performing warmup inference...")
            with torch.no_grad():
                dummy_pairs = [
                    self._format_pair(
                        instruction=self.default_instruction,
                        query="warmup query",
                        document="warmup document",
                    )
                ]
                dummy_inputs = self._build_model_inputs(dummy_pairs)
                _ = self.model(**dummy_inputs)

            # Log memory usage
            if torch.cuda.is_available():
                allocated = torch.cuda.memory_allocated(self.device) / 1024**3
                logger.info(f"GPU memory allocated: {allocated:.2f} GB")

            logger.info(f"Local reranker model loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load local reranker model: {e}")
            raise RuntimeError(f"Failed to load local reranker model: {e}") from e

    def _require_single_token_id(self, token: str) -> int:
        """
        Resolve a token like "yes"/"no" to a single vocabulary ID.

        Qwen3-Reranker scoring relies on the next-token distribution over these IDs.
        """
        ids = self.tokenizer(token, add_special_tokens=False).input_ids
        if len(ids) != 1:
            raise ValueError(
                f'Expected "{token}" to be a single token, got token ids: {ids}'
            )
        return int(ids[0])

    @staticmethod
    def _format_pair(instruction: str, query: str, document: str) -> str:
        """
        Format a single reranker pair according to the Qwen3 reranker model card.

        NOTE: This is instruction-aware. For retrieval tasks, the default
        instruction is usually sufficient, but callers can override it via kwargs.
        """
        return (
            f"<Instruct>: {instruction}\n"
            f"<Query>: {query}\n"
            f"<Document>: {document}"
        )

    def _build_model_inputs(self, pairs: List[str]) -> Dict[str, torch.Tensor]:
        """
        Tokenize and pad reranker pairs using the official prefix/suffix template.

        Returns a dict suitable for ``AutoModelForCausalLM`` forward pass.
        """
        max_pair_len = self.max_length - len(self._prefix_token_ids) - len(self._suffix_token_ids)
        if max_pair_len <= 0:
            raise ValueError(
                "Invalid max_length for reranker batching: "
                f"max_length={self.max_length}, template_tokens={len(self._prefix_token_ids) + len(self._suffix_token_ids)}"
            )

        # Step 1: tokenize pair contents without padding; we pad after adding prefix/suffix.
        enc = self.tokenizer(
            pairs,
            padding=False,
            truncation="longest_first",
            return_attention_mask=False,
            max_length=max_pair_len,
            add_special_tokens=False,
        )

        input_ids = enc.get("input_ids")
        if not isinstance(input_ids, list):
            raise RuntimeError("Tokenizer returned unexpected input_ids type")

        # Step 2: add prefix/suffix tokens around each example.
        enc["input_ids"] = [
            self._prefix_token_ids + ids + self._suffix_token_ids for ids in input_ids
        ]

        # Step 3: pad to max_length and build attention_mask.
        batch = self.tokenizer.pad(
            enc,
            padding=True,
            return_tensors="pt",
        )

        # Move tensors to device
        return {k: v.to(self.device) for k, v in batch.items() if isinstance(v, torch.Tensor)}
    
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
            instruction = kwargs.get("instruction", self.default_instruction)

            # Run inference in thread pool to avoid blocking event loop
            loop = asyncio.get_event_loop()
            scores = await loop.run_in_executor(
                None,
                self._rerank_sync,
                query,
                documents,
                instruction,
            )

            return scores

        except Exception as e:
            logger.error(f"Reranking failed: {e}")
            raise RuntimeError(f"Reranking failed: {e}") from e

    def _rerank_sync(self, query: str, documents: List[str], instruction: str) -> List[float]:
        """
        Synchronous reranking method for thread pool execution.

        Args:
            query: Search query
            documents: List of document texts

        Returns:
            List of relevance scores in [0, 1] (probability of "yes")
        """
        with torch.no_grad():
            scores: List[float] = []
            for start in range(0, len(documents), self.batch_size):
                batch_docs = documents[start : start + self.batch_size]

                # Build instruction-aware pairs
                batch_pairs = [
                    self._format_pair(instruction=instruction, query=query, document=doc)
                    for doc in batch_docs
                ]

                inputs = self._build_model_inputs(batch_pairs)
                outputs = self.model(**inputs)

                # Next-token distribution at the last position
                next_logits = outputs.logits[:, -1, :]

                # Convert to P(yes) vs P(no)
                yes_logits = next_logits[:, self._token_yes_id]
                no_logits = next_logits[:, self._token_no_id]
                binary_logits = torch.stack([no_logits, yes_logits], dim=1).float()
                probs_yes = torch.softmax(binary_logits, dim=1)[:, 1]

                scores.extend(probs_yes.detach().cpu().tolist())

            return scores


class MultimodalEmbeddingProvider(BaseEmbeddingProvider):
    """
    Multimodal embedding provider using GME-Qwen2-VL-2B.

    Supports:
    - Pure text embedding
    - Pure image embedding
    - Text + image joint embedding

    The model is loaded to a specific GPU device with FP16 precision.
    """

    def __init__(self, config: ModelConfig):
        """
        Initialize multimodal embedding provider.

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

        # Get device from extra_params or default to cuda:2
        self.device = config.extra_params.get("device", "cuda:2")
        dtype_str = config.extra_params.get("dtype", "float16")
        attn_impl = config.extra_params.get("attn_implementation", "sdpa")

        # Convert dtype string to torch dtype
        self.dtype = torch.float16 if dtype_str == "float16" else torch.float32

        # Multimodal-specific parameters
        self.min_image_tokens = config.extra_params.get("min_image_tokens", 256)
        self.max_image_tokens = config.extra_params.get("max_image_tokens", 1280)
        self.max_length = config.extra_params.get("max_length", 1800)
        self.default_instruction = config.extra_params.get(
            "default_instruction",
            "You are a helpful assistant."
        )
        self.normalize = config.extra_params.get("normalize", True)
        self.allow_image_urls = config.extra_params.get("allow_image_urls", False)
        self.max_image_bytes = config.extra_params.get("max_image_bytes", 10 * 1024 * 1024)

        logger.info(
            f"Loading multimodal embedding model: {self.model_name} "
            f"(device={self.device}, dtype={dtype_str}, attn={attn_impl})"
        )

        try:
            # Get model path from config or use model_name for HF download
            model_path = config.extra_params.get("model_path", self.model_name)

            # Load the vision-language model
            # GME-Qwen2-VL uses custom model architecture, so we use AutoModel with trust_remote_code
            model_kwargs = {
                "torch_dtype": self.dtype,
                "attn_implementation": attn_impl,
                "trust_remote_code": True,
            }

            self.model = AutoModel.from_pretrained(
                model_path,
                **model_kwargs
            )
            self.model.eval()
            self.model.to(self.device)

            # Load processor with image token constraints
            min_pixels = self.min_image_tokens * 28 * 28
            max_pixels = self.max_image_tokens * 28 * 28

            self.processor = AutoProcessor.from_pretrained(
                model_path,
                min_pixels=min_pixels,
                max_pixels=max_pixels,
                trust_remote_code=True,
            )
            self.processor.tokenizer.padding_side = 'right'

            # Warmup inference to allocate GPU memory
            logger.info("Performing warmup inference...")
            with torch.no_grad():
                warmup_inputs = self._prepare_inputs(
                    texts=["warmup text"],
                    images=None,
                    instruction=self.default_instruction
                )
                _ = self._forward(**warmup_inputs)

            # Log memory usage
            if torch.cuda.is_available():
                allocated = torch.cuda.memory_allocated(self.device) / 1024**3
                logger.info(f"GPU memory allocated: {allocated:.2f} GB")

            logger.info(f"Multimodal embedding model loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load multimodal embedding model: {e}")
            raise RuntimeError(f"Failed to load multimodal embedding model: {e}") from e

    def _prepare_inputs(
        self,
        texts: List[str],
        images: Optional[List[Union[str, Image.Image]]],
        instruction: Optional[str] = None
    ) -> Dict[str, torch.Tensor]:
        """
        Prepare inputs for the multimodal model.

        Args:
            texts: List of text strings
            images: Optional list of images (PIL Image or path/URL)
            instruction: Optional instruction prompt

        Returns:
            Dictionary of model inputs (input_ids, attention_mask, pixel_values, etc.)
        """
        if instruction is None:
            instruction = self.default_instruction

        # Build input messages
        all_messages = []
        all_images = []

        for i, text in enumerate(texts):
            input_str = ''

            # Add image token if image is provided
            if images is not None and i < len(images):
                input_str += '<|vision_start|><|image_pad|><|vision_end|>'
                img = self._load_image(images[i])
                all_images.append(img)

            # Add text
            if text:
                input_str += text

            # Format as chat message
            message = (
                f'<|im_start|>system\n{instruction}<|im_end|>\n'
                f'<|im_start|>user\n{input_str}<|im_end|>\n'
                f'<|im_start|>assistant\n<|endoftext|>'
            )
            all_messages.append(message)

        # Process inputs
        inputs = self.processor(
            text=all_messages,
            images=all_images if all_images else None,
            padding="longest",
            truncation=True,
            max_length=self.max_length,
            return_tensors='pt'
        )

        # Move to device
        inputs = {k: v.to(self.device) if isinstance(v, torch.Tensor) else v
                  for k, v in inputs.items()}

        return inputs

    def _load_image(self, image: Union[str, Image.Image]) -> Image.Image:
        """
        Load image from various sources.

        Args:
            image: PIL Image, file path, or URL

        Returns:
            PIL Image in RGB mode
        """
        if isinstance(image, Image.Image):
            return image.convert("RGB")

        # Import here to avoid dependency if not using images
        import base64
        from io import BytesIO
        import requests

        if isinstance(image, str):
            if image.startswith("http://") or image.startswith("https://"):
                if not self.allow_image_urls:
                    raise ValueError(
                        "Loading images from URLs is disabled. "
                        "Set *_ALLOW_IMAGE_URLS=true (e.g., MULTIMODAL_EMBEDDING_ALLOW_IMAGE_URLS=true) to enable."
                    )
                # URL
                response = requests.get(image, stream=True, timeout=10.0)
                response.raise_for_status()

                content_length = response.headers.get("Content-Length")
                if content_length is not None:
                    try:
                        if int(content_length) > self.max_image_bytes:
                            raise ValueError(
                                f"Image too large ({content_length} bytes) > max_image_bytes ({self.max_image_bytes})"
                            )
                    except ValueError:
                        # If Content-Length is invalid, ignore and enforce via streaming limit.
                        pass

                buf = BytesIO()
                downloaded = 0
                for chunk in response.iter_content(chunk_size=8192):
                    if not chunk:
                        continue
                    downloaded += len(chunk)
                    if downloaded > self.max_image_bytes:
                        raise ValueError(
                            f"Image download exceeded max_image_bytes ({self.max_image_bytes})"
                        )
                    buf.write(chunk)
                buf.seek(0)
                img = Image.open(buf)
            elif image.startswith("file://"):
                # File URL
                img = Image.open(image[7:])
            elif image.startswith("data:image"):
                # Base64 data URL
                if "base64," in image:
                    _, base64_data = image.split("base64,", 1)
                    data = base64.b64decode(base64_data)
                    img = Image.open(BytesIO(data))
                else:
                    raise ValueError(f"Invalid data URL format: {image}")
            else:
                # Local file path
                img = Image.open(image)

            return img.convert("RGB")

        raise ValueError(f"Unsupported image type: {type(image)}")

    def _forward(
        self,
        input_ids: Optional[torch.LongTensor] = None,
        attention_mask: Optional[torch.Tensor] = None,
        position_ids: Optional[torch.LongTensor] = None,
        inputs_embeds: Optional[torch.FloatTensor] = None,
        pixel_values: Optional[torch.Tensor] = None,
        image_grid_thw: Optional[torch.LongTensor] = None,
        **kwargs
    ) -> torch.Tensor:
        """
        Forward pass through the model to generate embeddings.

        Args:
            input_ids: Token IDs
            attention_mask: Attention mask
            position_ids: Position IDs
            inputs_embeds: Pre-computed input embeddings
            pixel_values: Image pixel values
            image_grid_thw: Image grid dimensions

        Returns:
            Normalized embeddings tensor
        """
        # Prepare input embeddings with image tokens
        if inputs_embeds is None:
            inputs_embeds = self.model.model.embed_tokens(input_ids)

            if pixel_values is not None:
                # Encode images
                pixel_values = pixel_values.type(self.model.visual.get_dtype())
                image_embeds = self.model.visual(
                    pixel_values,
                    grid_thw=image_grid_thw
                ).to(inputs_embeds.device)

                # Replace image tokens with image embeddings
                image_mask = input_ids == self.model.config.image_token_id
                inputs_embeds[image_mask] = image_embeds

        # Forward through model
        outputs = self.model.model(
            input_ids=None,
            position_ids=position_ids,
            attention_mask=attention_mask.to(inputs_embeds.device) if attention_mask is not None else None,
            inputs_embeds=inputs_embeds,
            return_dict=True,
            output_hidden_states=True,
        )

        # Pool embeddings (use last token for right-padded sequences)
        # Check if left-padded (all sequences end with valid tokens)
        left_padding = (attention_mask[:, -1].sum() == attention_mask.shape[0])

        if left_padding:
            # Left-padded: take last hidden state
            embeddings = outputs.last_hidden_state[:, -1]
        else:
            # Right-padded: take last valid token for each sequence
            sequence_lengths = attention_mask.sum(dim=1) - 1
            batch_size = outputs.last_hidden_state.shape[0]
            embeddings = outputs.last_hidden_state[
                torch.arange(batch_size, device=outputs.last_hidden_state.device),
                sequence_lengths
            ]

        # Normalize embeddings
        if self.normalize:
            embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)

        return embeddings.contiguous()

    async def embed(
        self,
        texts: List[str],
        **kwargs
    ) -> np.ndarray:
        """
        Generate embeddings for pure text inputs.

        Args:
            texts: List of texts to embed
            **kwargs: Additional parameters (e.g., instruction)

        Returns:
            numpy array of embeddings with shape (len(texts), embedding_dim)

        Raises:
            RuntimeError: If embedding generation fails
        """
        if not texts:
            return np.array([])

        try:
            instruction = kwargs.get("instruction", self.default_instruction)

            # Prepare inputs (no images)
            inputs = self._prepare_inputs(
                texts=texts,
                images=None,
                instruction=instruction
            )

            # Generate embeddings
            loop = asyncio.get_event_loop()
            embeddings = await loop.run_in_executor(
                None,
                self._encode_sync,
                inputs
            )

            return embeddings

        except Exception as e:
            logger.error(f"Text embedding generation failed: {e}")
            raise RuntimeError(f"Text embedding generation failed: {e}") from e

    async def embed_multimodal(
        self,
        texts: List[str],
        images: List[Union[str, Image.Image]],
        **kwargs
    ) -> np.ndarray:
        """
        Generate embeddings for text + image inputs.

        Args:
            texts: List of texts to embed
            images: List of images (PIL Image, file path, or URL)
            **kwargs: Additional parameters (e.g., instruction)

        Returns:
            numpy array of embeddings with shape (len(texts), embedding_dim)

        Raises:
            RuntimeError: If embedding generation fails
            ValueError: If texts and images have different lengths
        """
        if not texts:
            return np.array([])

        if len(texts) != len(images):
            raise ValueError(
                f"texts and images must have the same length, "
                f"got {len(texts)} texts and {len(images)} images"
            )

        try:
            instruction = kwargs.get("instruction", self.default_instruction)

            # Prepare inputs (with images)
            inputs = self._prepare_inputs(
                texts=texts,
                images=images,
                instruction=instruction
            )

            # Generate embeddings
            loop = asyncio.get_event_loop()
            embeddings = await loop.run_in_executor(
                None,
                self._encode_sync,
                inputs
            )

            return embeddings

        except Exception as e:
            logger.error(f"Multimodal embedding generation failed: {e}")
            raise RuntimeError(f"Multimodal embedding generation failed: {e}") from e

    def _encode_sync(self, inputs: Dict[str, torch.Tensor]) -> np.ndarray:
        """
        Synchronous encoding method for thread pool execution.

        Args:
            inputs: Preprocessed model inputs

        Returns:
            numpy array of embeddings
        """
        with torch.no_grad():
            embeddings_tensor = self._forward(**inputs)
            embeddings_np = embeddings_tensor.cpu().numpy()
            return embeddings_np.astype(np.float32)

    @property
    def embedding_dim(self) -> int:
        """Return the dimensionality of embeddings."""
        return self._embedding_dim

    async def shutdown(self) -> None:
        """
        Gracefully shutdown the multimodal embedding provider.

        This provider does not maintain background tasks today, but we expose a
        shutdown hook for symmetry with LocalEmbeddingProvider and to make
        application shutdown logic consistent.
        """
        logger.info("Shutting down MultimodalEmbeddingProvider...")
        logger.info("MultimodalEmbeddingProvider shutdown complete")
