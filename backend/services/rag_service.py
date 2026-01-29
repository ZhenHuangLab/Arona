"""
RAG Service - High-level wrapper around RAGAnything.

Manages RAGAnything instances and provides simplified API for backend.
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional, Dict, Any, List, AsyncIterator

from raganything import RAGAnything, RAGAnythingConfig

from backend.config import BackendConfig
from backend.services.model_factory import ModelFactory


logger = logging.getLogger(__name__)


class RAGService:
    """
    Service layer for RAG operations.

    Manages RAGAnything instances and provides high-level API.
    """

    def __init__(self, config: BackendConfig):
        """
        Initialize RAG service.

        Args:
            config: Backend configuration
        """
        self.config = config
        self._rag_instance: Optional[RAGAnything] = None
        self._lock = asyncio.Lock()
        self._llm_cache_lock = asyncio.Lock()
        self._active_ops_lock = asyncio.Lock()
        self._idle_event = asyncio.Event()
        self._idle_event.set()
        self._active_ops = 0

        # Create embedding provider (save reference for shutdown)
        self.embedding_provider = ModelFactory.create_embedding_provider(
            config.embedding
        )

        # Optional multimodal embedding provider (separate from text embedding)
        self.multimodal_embedding_provider = None
        if getattr(config, "multimodal_embedding", None):
            self.multimodal_embedding_provider = ModelFactory.create_embedding_provider(
                config.multimodal_embedding
            )

        # Create model functions from config
        self.llm_func = ModelFactory.create_llm_func(config.llm)
        self.embedding_func = ModelFactory.create_embedding_func_from_provider(
            self.embedding_provider
        )

        # Optional vision function
        self.vision_func = None
        if config.vision:
            self.vision_func = ModelFactory.create_vision_func(config.vision)

        # Optional reranker
        self.reranker_func = None
        self.reranker_provider = None
        if config.reranker:
            self.reranker_func = ModelFactory.create_reranker(config.reranker)
            if self.reranker_func is not None:
                self.reranker_provider = getattr(self.reranker_func, "_provider", None)

        logger.info("RAG service initialized with configuration:")
        logger.info(f"  LLM: {config.llm.provider}/{config.llm.model_name}")
        logger.info(
            f"  Embedding: {config.embedding.provider}/{config.embedding.model_name}"
        )
        if config.vision:
            logger.info(
                f"  Vision: {config.vision.provider}/{config.vision.model_name}"
            )
        if config.reranker and config.reranker.enabled:
            logger.info(f"  Reranker: {config.reranker.provider}")
        if self.multimodal_embedding_provider is not None:
            logger.info(
                "  Multimodal Embedding: "
                f"{config.multimodal_embedding.provider}/{config.multimodal_embedding.model_name}"
            )

    @asynccontextmanager
    async def _operation(self):
        """Track in-flight operations to support safe hot-reload/shutdown."""
        async with self._active_ops_lock:
            self._active_ops += 1
            self._idle_event.clear()
        try:
            yield
        finally:
            async with self._active_ops_lock:
                self._active_ops -= 1
                if self._active_ops <= 0:
                    self._active_ops = 0
                    self._idle_event.set()

    async def wait_for_idle(self, timeout: Optional[float] = 10.0) -> bool:
        """Wait until there are no in-flight operations."""
        try:
            if timeout is None:
                await self._idle_event.wait()
            else:
                await asyncio.wait_for(self._idle_event.wait(), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            return False

    async def get_rag_instance(self) -> RAGAnything:
        """
        Get or create RAGAnything instance.

        Returns:
            Initialized RAGAnything instance
        """
        if self._rag_instance is not None:
            return self._rag_instance

        async with self._lock:
            # Double-check after acquiring lock
            if self._rag_instance is not None:
                return self._rag_instance

            logger.info("Creating new RAGAnything instance...")

            # Create RAGAnything configuration
            rag_config = RAGAnythingConfig(
                working_dir=self.config.working_dir,
                parser=self.config.parser,
                enable_image_processing=self.config.enable_image_processing,
                enable_table_processing=self.config.enable_table_processing,
                enable_equation_processing=self.config.enable_equation_processing,
                mineru_device=self.config.mineru_device,
                mineru_vram=self.config.mineru_vram,
            )

            # Create RAGAnything instance
            self._rag_instance = RAGAnything(
                config=rag_config,
                llm_model_func=self.llm_func,
                vision_model_func=self.vision_func,
                embedding_func=self.embedding_func,
                rerank_model_func=self.reranker_func,
            )

            # Initialize (this sets up LightRAG and storage)
            await self._rag_instance._ensure_lightrag_initialized()

            logger.info("RAGAnything instance created and initialized")

            return self._rag_instance

    @asynccontextmanager
    async def _llm_cache_disabled(self, rag: RAGAnything):
        """
        Temporarily disable LightRAG LLM response cache for a single operation.

        This avoids stale/deterministic results (e.g. retry/regenerate should not
        return a cached response).
        """
        lightrag = getattr(rag, "lightrag", None)
        llm_cache = getattr(lightrag, "llm_response_cache", None)
        global_config = getattr(llm_cache, "global_config", None)

        if not isinstance(global_config, dict):
            yield
            return

        async with self._llm_cache_lock:
            prev_enable_llm_cache = global_config.get("enable_llm_cache", True)
            prev_enable_extract_cache = global_config.get(
                "enable_llm_cache_for_entity_extract", True
            )
            global_config["enable_llm_cache"] = False
            global_config["enable_llm_cache_for_entity_extract"] = False
            try:
                yield
            finally:
                global_config["enable_llm_cache"] = prev_enable_llm_cache
                global_config["enable_llm_cache_for_entity_extract"] = (
                    prev_enable_extract_cache
                )

    async def process_document(
        self,
        file_path: str | Path,
        output_dir: Optional[str | Path] = None,
        parse_method: str = "auto",
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Process a document and add it to the knowledge base.

        Args:
            file_path: Path to document file
            output_dir: Optional output directory for parsed content
            parse_method: Parsing method ("auto", "ocr", "txt")
            **kwargs: Additional processing parameters

        Returns:
            Processing result metadata
        """
        async with self._operation():
            rag = await self.get_rag_instance()

            if output_dir is None:
                output_dir = Path(self.config.working_dir) / "parsed_output"

            logger.info(f"Processing document: {file_path}")

            try:
                await rag.process_document_complete(
                    file_path=str(file_path),
                    output_dir=str(output_dir),
                    parse_method=parse_method,
                    **kwargs,
                )

                logger.info(f"Document processed successfully: {file_path}")

                return {
                    "status": "success",
                    "file_path": str(file_path),
                    "output_dir": str(output_dir),
                }
            except Exception as e:
                logger.error(
                    f"Failed to process document {file_path}: {e}", exc_info=True
                )
                return {
                    "status": "error",
                    "file_path": str(file_path),
                    "error": str(e),
                }

    async def query(self, query: str, mode: str = "hybrid", **kwargs) -> str:
        """
        Execute a RAG query.

        Args:
            query: User query text
            mode: Query mode ("naive", "local", "global", "hybrid")
            **kwargs: Additional query parameters

        Returns:
            Query response text
        """
        async with self._operation():
            rag = await self.get_rag_instance()
            bypass_cache = bool(kwargs.pop("bypass_cache", False))

            logger.info(f"Executing query: {query[:100]}... (mode={mode})")

            try:
                if bypass_cache:
                    async with self._llm_cache_disabled(rag):
                        result = await rag.aquery(query, mode=mode, **kwargs)
                else:
                    result = await rag.aquery(query, mode=mode, **kwargs)
                logger.info("Query executed successfully")
                return result
            except Exception as e:
                logger.error(f"Query failed: {e}", exc_info=True)
                raise

    async def query_stream(
        self,
        query: str,
        mode: str = "hybrid",
        **kwargs,
    ) -> AsyncIterator[str]:
        """
        Execute a RAG query with streaming output (best-effort).

        Depending on the configured provider + LightRAG integration, this may
        yield incremental chunks or a single full response.
        """
        async with self._operation():
            rag = await self.get_rag_instance()
            bypass_cache = bool(kwargs.pop("bypass_cache", False))

            logger.info(f"Executing streaming query: {query[:100]}... (mode={mode})")

            # RAGAnything wraps LightRAG. LightRAG supports stream=True by returning
            # an AsyncIterator[str]. Some providers may only yield once.
            if bypass_cache:
                async with self._llm_cache_disabled(rag):
                    result = await rag.aquery(query, mode=mode, stream=True, **kwargs)
            else:
                result = await rag.aquery(query, mode=mode, stream=True, **kwargs)

            if isinstance(result, str):
                yield result
                return

            async for chunk in result:
                yield str(chunk)

    async def query_with_multimodal(
        self,
        query: str,
        multimodal_content: Optional[List[Dict[str, Any]]] = None,
        mode: str = "hybrid",
        **kwargs,
    ) -> str:
        """
        Execute a multimodal RAG query.

        Args:
            query: User query text
            multimodal_content: Optional multimodal content (images, tables, equations)
            mode: Query mode ("naive", "local", "global", "hybrid")
            **kwargs: Additional query parameters

        Returns:
            Query response text
        """
        async with self._operation():
            rag = await self.get_rag_instance()
            bypass_cache = bool(kwargs.pop("bypass_cache", False))

            logger.info(f"Executing multimodal query: {query[:100]}... (mode={mode})")

            try:
                if bypass_cache:
                    async with self._llm_cache_disabled(rag):
                        result = await rag.aquery_with_multimodal(
                            query=query,
                            multimodal_content=multimodal_content,
                            mode=mode,
                            **kwargs,
                        )
                else:
                    result = await rag.aquery_with_multimodal(
                        query=query,
                        multimodal_content=multimodal_content,
                        mode=mode,
                        **kwargs,
                    )
                logger.info("Multimodal query executed successfully")
                return result
            except Exception as e:
                logger.error(f"Multimodal query failed: {e}", exc_info=True)
                raise

    async def get_retrieval_prompt(
        self,
        query: str,
        mode: str = "hybrid",
        conversation_history: list[dict] | None = None,
        **kwargs,
    ) -> str:
        """
        Get the RAG retrieval prompt/context without running the LLM.

        Uses LightRAG's `only_need_prompt=True` to retrieve context only.
        Forces vlm_enhanced=False to avoid image processing overhead.

        Args:
            query: User query text
            mode: Query mode ("naive", "local", "global", "hybrid")
            conversation_history: Optional conversation history
            **kwargs: Additional query parameters

        Returns:
            Raw retrieval prompt containing context and image paths
        """
        async with self._operation():
            rag = await self.get_rag_instance()

            logger.info(f"Getting retrieval prompt: {query[:100]}... (mode={mode})")

            try:
                prompt_kwargs = dict(kwargs)
                # Force vlm_enhanced=False to get raw prompt with image paths
                prompt_kwargs["vlm_enhanced"] = False
                prompt_kwargs["only_need_prompt"] = True
                # Disable streaming for prompt retrieval
                prompt_kwargs.pop("stream", None)

                # Keep retrieval aligned with the main query call: pass conversation_history through
                # instead of rewriting the query string.
                if conversation_history:
                    prompt_kwargs["conversation_history"] = conversation_history

                result = await rag.aquery(query, mode=mode, **prompt_kwargs)
                logger.info("Retrieval prompt fetched successfully")
                return result
            except Exception as e:
                logger.error(f"Failed to get retrieval prompt: {e}", exc_info=True)
                raise

    async def get_retrieval_data(
        self,
        query: str,
        mode: str = "hybrid",
        conversation_history: list[dict] | None = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Get structured retrieval results (entities/relationships/chunks) without running the LLM.

        This uses LightRAG's `aquery_data` so callers can reliably associate retrieved
        chunks with their metadata (e.g., multimodal chunks that contain `Image Path:`).

        Args:
            query: User query text
            mode: Query mode ("naive", "local", "global", "hybrid", "mix", "bypass")
            conversation_history: Optional conversation history (passed through for consistency)
            **kwargs: Additional query parameters (top_k, chunk_top_k, enable_rerank, etc.)

        Returns:
            Structured LightRAG data dict (see LightRAG aquery_data docs).
        """
        async with self._operation():
            rag = await self.get_rag_instance()

            logger.info(f"Getting retrieval data: {query[:100]}... (mode={mode})")

            try:
                # Import lazily to keep module import side-effects minimal.
                from lightrag import QueryParam  # type: ignore

                data_kwargs = dict(kwargs)
                # Data retrieval doesn't need streaming.
                data_kwargs.pop("stream", None)
                # Ensure callers can't accidentally request prompt/context-only via kwargs.
                data_kwargs.pop("only_need_prompt", None)
                data_kwargs.pop("only_need_context", None)

                # Keep retrieval aligned with the main query call: pass conversation_history through
                # (LightRAG uses it for LLM context, not retrieval).
                if conversation_history:
                    data_kwargs["conversation_history"] = conversation_history

                # Match the same rerank defaults used by RAGAnything.query to avoid noisy warnings.
                if hasattr(rag, "_apply_query_defaults"):
                    data_kwargs = rag._apply_query_defaults(data_kwargs)  # type: ignore[attr-defined]

                query_param = QueryParam(mode=mode, stream=False, **data_kwargs)
                return await rag.lightrag.aquery_data(query, query_param)
            except Exception as e:
                logger.error(f"Failed to get retrieval data: {e}", exc_info=True)
                raise

    async def get_status(self) -> Dict[str, Any]:
        """
        Get RAG service status.

        Returns:
            Status information
        """
        status = {
            "initialized": self._rag_instance is not None,
            "working_dir": self.config.working_dir,
            "models": {
                "llm": {
                    "provider": self.config.llm.provider.value,
                    "model": self.config.llm.model_name,
                },
                "embedding": {
                    "provider": self.config.embedding.provider.value,
                    "model": self.config.embedding.model_name,
                    "dimension": getattr(
                        self.embedding_provider,
                        "embedding_dim",
                        self.config.embedding.embedding_dim,
                    ),
                },
            },
        }

        if self.config.vision:
            status["models"]["vision"] = {
                "provider": self.config.vision.provider.value,
                "model": self.config.vision.model_name,
            }

        if self.config.reranker and self.config.reranker.enabled:
            status["reranker"] = {
                "enabled": True,
                "provider": self.config.reranker.provider,
            }

        if self.multimodal_embedding_provider is not None:
            status["models"]["multimodal_embedding"] = {
                "provider": self.config.multimodal_embedding.provider.value,
                "model": self.config.multimodal_embedding.model_name,
                "dimension": self.multimodal_embedding_provider.embedding_dim,
            }

        return status

    async def shutdown(self) -> None:
        """
        Gracefully shutdown the RAG service.

        Stops all background tasks and releases resources.
        """
        logger.info("Shutting down RAG service...")

        # Wait briefly for in-flight operations to finish (best-effort).
        await self.wait_for_idle(timeout=5.0)

        # Shutdown embedding provider if it has a shutdown method
        if hasattr(self.embedding_provider, "shutdown"):
            await self.embedding_provider.shutdown()

        # Shutdown multimodal embedding provider if present
        if self.multimodal_embedding_provider and hasattr(
            self.multimodal_embedding_provider, "shutdown"
        ):
            await self.multimodal_embedding_provider.shutdown()

        # Shutdown reranker provider if present
        if self.reranker_provider is not None and hasattr(
            self.reranker_provider, "shutdown"
        ):
            await self.reranker_provider.shutdown()

        self._rag_instance = None

        logger.info("RAG service shutdown complete")
