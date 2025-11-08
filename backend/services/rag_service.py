"""
RAG Service - High-level wrapper around RAGAnything.

Manages RAGAnything instances and provides simplified API for backend.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

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

        # Create embedding provider (save reference for shutdown)
        self.embedding_provider = ModelFactory.create_embedding_provider(config.embedding)

        # Create model functions from config
        self.llm_func = ModelFactory.create_llm_func(config.llm)
        self.embedding_func = ModelFactory.create_embedding_func_from_provider(self.embedding_provider)

        # Optional vision function
        self.vision_func = None
        if config.vision:
            self.vision_func = ModelFactory.create_vision_func(config.vision)

        # Optional reranker
        self.reranker_func = None
        if config.reranker:
            self.reranker_func = ModelFactory.create_reranker(config.reranker)

        logger.info("RAG service initialized with configuration:")
        logger.info(f"  LLM: {config.llm.provider}/{config.llm.model_name}")
        logger.info(f"  Embedding: {config.embedding.provider}/{config.embedding.model_name}")
        if config.vision:
            logger.info(f"  Vision: {config.vision.provider}/{config.vision.model_name}")
        if config.reranker and config.reranker.enabled:
            logger.info(f"  Reranker: {config.reranker.provider}")
    
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
    
    async def process_document(
        self,
        file_path: str | Path,
        output_dir: Optional[str | Path] = None,
        parse_method: str = "auto",
        **kwargs
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
        rag = await self.get_rag_instance()
        
        if output_dir is None:
            output_dir = Path(self.config.working_dir) / "parsed_output"
        
        logger.info(f"Processing document: {file_path}")
        
        try:
            await rag.process_document_complete(
                file_path=str(file_path),
                output_dir=str(output_dir),
                parse_method=parse_method,
                **kwargs
            )
            
            logger.info(f"Document processed successfully: {file_path}")
            
            return {
                "status": "success",
                "file_path": str(file_path),
                "output_dir": str(output_dir),
            }
        except Exception as e:
            logger.error(f"Failed to process document {file_path}: {e}", exc_info=True)
            return {
                "status": "error",
                "file_path": str(file_path),
                "error": str(e),
            }
    
    async def query(
        self,
        query: str,
        mode: str = "hybrid",
        **kwargs
    ) -> str:
        """
        Execute a RAG query.
        
        Args:
            query: User query text
            mode: Query mode ("naive", "local", "global", "hybrid")
            **kwargs: Additional query parameters
            
        Returns:
            Query response text
        """
        rag = await self.get_rag_instance()
        
        logger.info(f"Executing query: {query[:100]}... (mode={mode})")
        
        try:
            result = await rag.aquery(query, mode=mode, **kwargs)
            logger.info("Query executed successfully")
            return result
        except Exception as e:
            logger.error(f"Query failed: {e}", exc_info=True)
            raise
    
    async def query_with_multimodal(
        self,
        query: str,
        multimodal_content: Optional[List[Dict[str, Any]]] = None,
        mode: str = "hybrid",
        **kwargs
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
        rag = await self.get_rag_instance()
        
        logger.info(f"Executing multimodal query: {query[:100]}... (mode={mode})")
        
        try:
            result = await rag.aquery_with_multimodal(
                query=query,
                multimodal_content=multimodal_content,
                mode=mode,
                **kwargs
            )
            logger.info("Multimodal query executed successfully")
            return result
        except Exception as e:
            logger.error(f"Multimodal query failed: {e}", exc_info=True)
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
                    "dimension": self.config.embedding.embedding_dim,
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

        return status

    async def shutdown(self) -> None:
        """
        Gracefully shutdown the RAG service.

        Stops all background tasks and releases resources.
        """
        logger.info("Shutting down RAG service...")

        # Shutdown embedding provider if it has a shutdown method
        if hasattr(self.embedding_provider, 'shutdown'):
            await self.embedding_provider.shutdown()

        logger.info("RAG service shutdown complete")

