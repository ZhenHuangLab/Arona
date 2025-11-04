#!/usr/bin/env python3
"""
Cluster RAG Worker - CLI wrapper for RAGAnything on HPC clusters

This script provides a command-line interface to RAGAnything functionality,
designed for use with SLURM job schedulers and Ollama-backed LLM services.

Usage:
    # Ingest documents
    python scripts/cluster_rag_worker.py --mode ingest \
        --input-file /path/to/document.pdf \
        --working-dir /shared/rag-data/workspace

    # Query the knowledge base
    python scripts/cluster_rag_worker.py --mode query \
        --query "What is the main topic?" \
        --working-dir /shared/rag-data/workspace

Environment Variables (see env.example for full list):
    OLLAMA_HOST: Ollama service URL (required)
    OLLAMA_GENERATE_MODEL: Model for text generation (default: qwen2.5:latest)
    OLLAMA_EMBED_MODEL: Model for embeddings (default: bge-m3:latest)
    OLLAMA_EMBED_DIM: Embedding dimension (default: 1024)
    PARSER: Parser to use (mineru or docling, default: mineru)
    WORKING_DIR: Default working directory for RAG storage
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Optional, TYPE_CHECKING

PROJECT_ROOT = Path(__file__).parent.parent


def ensure_project_root_on_path() -> None:
    """Ensure the repository root is available for runtime imports."""
    # Reason: HPC jobs may start in arbitrary working directories; explicitly seed sys.path.
    project_root_str = str(PROJECT_ROOT)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)


if TYPE_CHECKING:  # pragma: no cover - typing aid only
    from lightrag.utils import EmbeddingFunc
    from raganything.clients.ollama import OllamaClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def get_env(key: str, default: Optional[str] = None, required: bool = False) -> str:
    """Get environment variable with validation."""
    value = os.getenv(key, default)
    if required and not value:
        raise ValueError(f"Required environment variable {key} is not set")
    return value or ""


def create_ollama_llm_func(client: OllamaClient, model: str):
    """
    Create LLM function wrapper for Ollama.

    Returns a function compatible with RAGAnything's llm_model_func signature.
    """
    async def llm_func(prompt: str, system_prompt: Optional[str] = None,
                       history_messages: Optional[list] = None, **kwargs) -> str:
        """Wrapper function for Ollama chat completion."""
        try:
            # Reason: LightRAG awaits LLM func; wrap sync client.chat in asyncio.to_thread
            response = await asyncio.to_thread(
                client.chat,
                prompt=prompt,
                model=model,
                system_prompt=system_prompt,
                history_messages=history_messages or [],
                stream=False,
                options=kwargs.get("options"),
            )
            return response
        except Exception as e:
            logger.error(f"Ollama LLM call failed: {e}")
            raise

    return llm_func


def create_ollama_embed_func(
    client: OllamaClient,
    model: str,
    dim: int,
) -> EmbeddingFunc:
    """
    Create embedding function wrapper for Ollama.

    Returns an EmbeddingFunc instance compatible with RAGAnything.
    """
    ensure_project_root_on_path()
    from lightrag.utils import EmbeddingFunc

    async def embed_func(texts: list[str]) -> np.ndarray:
        """Wrapper function for Ollama embeddings."""
        import numpy as np

        payload = list(texts)
        if not payload:
            # Reason: LightRAG can call into embedding with an empty batch; return shape-consistent zeros.
            return np.zeros((0, dim), dtype=float)

        try:
            # Reason: LightRAG awaits embedding call; delegate sync Ollama client to a thread.
            vectors = await asyncio.to_thread(
                client.embed,
                payload,
                model=model,
            )
        except Exception as e:  # pylint: disable=broad-except
            logger.error(f"Ollama embedding call failed: {e}")
            raise

        if len(vectors) != len(payload):
            raise ValueError(
                "Ollama returned {returned} embeddings for {expected} inputs".format(
                    returned=len(vectors),
                    expected=len(payload),
                )
            )

        sanitized_vectors: list[np.ndarray] = []
        for index, vector in enumerate(vectors):
            length = len(vector)
            if length == 0:
                logger.warning(
                    "Ollama returned empty embedding for chunk %s; substituting zeros",
                    index,
                )
                # Reason: Prevent nano_vectordb from crashing on zero-width vectors by zero-filling.
                sanitized_vectors.append(np.zeros(dim, dtype=float))
                continue
            if length != dim:
                raise ValueError(
                    "Ollama embedding length {actual} != configured embed_dim {expected} (chunk {index})".format(
                        actual=length,
                        expected=dim,
                        index=index,
                    )
                )
            sanitized_vectors.append(np.asarray(vector, dtype=float))

        # Reason: Guarantee LightRAG receives consistent embedding widths, avoiding numpy.vstack failures.
        return np.asarray(sanitized_vectors, dtype=float)

    return EmbeddingFunc(
        embedding_dim=dim,
        max_token_size=8192,  # Standard for most embedding models
        func=embed_func,
    )


async def run_ingest(
    input_file: str,
    working_dir: str,
    ollama_host: str,
    llm_model: str,
    embed_model: str,
    embed_dim: int,
    parser: str,
) -> None:
    """
    Run document ingestion workflow.

    Args:
        input_file: Path to document to process
        working_dir: Working directory for RAG storage
        ollama_host: Ollama service URL
        llm_model: Model name for text generation
        embed_model: Model name for embeddings
        embed_dim: Embedding dimension
        parser: Parser to use (mineru or docling)
    """
    ensure_project_root_on_path()
    from raganything import RAGAnything, RAGAnythingConfig
    from raganything.clients.ollama import OllamaClient

    logger.info(f"Starting ingestion: {input_file}")
    logger.info(f"  Working dir: {working_dir}")
    logger.info(f"  Ollama host: {ollama_host}")
    logger.info(f"  LLM model: {llm_model}")
    logger.info(f"  Embed model: {embed_model} (dim={embed_dim})")
    logger.info(f"  Parser: {parser}")

    # Validate input file
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"Input file not found: {input_file}")

    # Create Ollama client
    ollama_client = OllamaClient(
        base_url=ollama_host,
        timeout=float(get_env("OLLAMA_TIMEOUT_SECONDS", "300")),
        max_retries=int(get_env("OLLAMA_MAX_RETRIES", "2")),
        backoff_factor=float(get_env("OLLAMA_RETRY_BACKOFF", "0.5")),
    )

    # Create RAGAnything configuration
    config = RAGAnythingConfig(
        working_dir=working_dir,
        parser=parser,
        parse_method="auto",
        enable_image_processing=True,
        enable_table_processing=True,
        enable_equation_processing=True,
    )

    # Create function wrappers
    llm_func = create_ollama_llm_func(ollama_client, llm_model)
    embed_func = create_ollama_embed_func(ollama_client, embed_model, embed_dim)

    # Initialize RAGAnything
    rag = RAGAnything(
        config=config,
        llm_model_func=llm_func,
        embedding_func=embed_func,
    )

    # Process document
    output_dir = os.path.join(working_dir, "parsed_output")
    os.makedirs(output_dir, exist_ok=True)

    await rag.process_document_complete(
        file_path=input_file,
        output_dir=output_dir,
        parse_method="auto",
    )

    logger.info(f"✓ Ingestion completed successfully for: {input_file}")


async def run_query(
    query: str,
    working_dir: str,
    ollama_host: str,
    llm_model: str,
    embed_model: str,
    embed_dim: int,
    mode: str = "hybrid",
) -> None:
    """
    Run query workflow.

    Args:
        query: Query string
        working_dir: Working directory for RAG storage
        ollama_host: Ollama service URL
        llm_model: Model name for text generation
        embed_model: Model name for embeddings
        embed_dim: Embedding dimension
        mode: Query mode (naive, local, global, or hybrid)
    """
    ensure_project_root_on_path()
    from raganything import RAGAnything, RAGAnythingConfig
    from raganything.clients.ollama import OllamaClient

    logger.info(f"Starting query: {query}")
    logger.info(f"  Working dir: {working_dir}")
    logger.info(f"  Ollama host: {ollama_host}")
    logger.info(f"  Query mode: {mode}")

    # Create Ollama client
    ollama_client = OllamaClient(
        base_url=ollama_host,
        timeout=float(get_env("OLLAMA_TIMEOUT_SECONDS", "300")),
        max_retries=int(get_env("OLLAMA_MAX_RETRIES", "2")),
        backoff_factor=float(get_env("OLLAMA_RETRY_BACKOFF", "0.5")),
    )

    # Create RAGAnything configuration
    config = RAGAnythingConfig(
        working_dir=working_dir,
        parser="mineru",  # Parser doesn't matter for queries
        parse_method="auto",
    )

    # Create function wrappers
    llm_func = create_ollama_llm_func(ollama_client, llm_model)
    embed_func = create_ollama_embed_func(ollama_client, embed_model, embed_dim)

    # Initialize RAGAnything
    rag = RAGAnything(
        config=config,
        llm_model_func=llm_func,
        embedding_func=embed_func,
    )

    # Execute query
    result = await rag.aquery(query, mode=mode)

    logger.info(f"\n{'='*80}\nQuery: {query}\n{'='*80}")
    logger.info(f"Answer:\n{result}")
    logger.info(f"{'='*80}\n")


def main() -> int:
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(
        description="Cluster RAG Worker - CLI wrapper for RAGAnything",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--mode",
        choices=["ingest", "query"],
        required=True,
        help="Operation mode: ingest documents or query knowledge base",
    )

    parser.add_argument(
        "--input-file",
        help="Path to document file (required for ingest mode)",
    )

    parser.add_argument(
        "--query",
        help="Query string (required for query mode)",
    )

    parser.add_argument(
        "--working-dir",
        default=get_env("WORKING_DIR", "./rag_storage"),
        help="Working directory for RAG storage (default: ./rag_storage or $WORKING_DIR)",
    )

    parser.add_argument(
        "--ollama-host",
        default=get_env("OLLAMA_HOST"),
        help="Ollama service URL (default: $OLLAMA_HOST, required)",
    )

    parser.add_argument(
        "--llm-model",
        default=get_env("OLLAMA_GENERATE_MODEL", "qwen2.5:latest"),
        help="LLM model name (default: qwen2.5:latest or $OLLAMA_GENERATE_MODEL)",
    )

    parser.add_argument(
        "--embed-model",
        default=get_env("OLLAMA_EMBED_MODEL", "bge-m3:latest"),
        help="Embedding model name (default: bge-m3:latest or $OLLAMA_EMBED_MODEL)",
    )

    parser.add_argument(
        "--embed-dim",
        type=int,
        default=int(get_env("OLLAMA_EMBED_DIM", "1024")),
        help="Embedding dimension (default: 1024 or $OLLAMA_EMBED_DIM)",
    )

    parser.add_argument(
        "--parser",
        default=get_env("PARSER", "mineru"),
        choices=["mineru", "docling"],
        help="Document parser to use (default: mineru or $PARSER)",
    )

    parser.add_argument(
        "--query-mode",
        default="hybrid",
        choices=["naive", "local", "global", "hybrid"],
        help="Query mode (default: hybrid)",
    )

    args = parser.parse_args()

    # Validate required arguments
    if not args.ollama_host:
        parser.error("--ollama-host is required (or set $OLLAMA_HOST)")

    if args.mode == "ingest" and not args.input_file:
        parser.error("--input-file is required for ingest mode")

    if args.mode == "query" and not args.query:
        parser.error("--query is required for query mode")

    try:
        if args.mode == "ingest":
            asyncio.run(run_ingest(
                input_file=args.input_file,
                working_dir=args.working_dir,
                ollama_host=args.ollama_host,
                llm_model=args.llm_model,
                embed_model=args.embed_model,
                embed_dim=args.embed_dim,
                parser=args.parser,
            ))
        else:  # query mode
            asyncio.run(run_query(
                query=args.query,
                working_dir=args.working_dir,
                ollama_host=args.ollama_host,
                llm_model=args.llm_model,
                embed_model=args.embed_model,
                embed_dim=args.embed_dim,
                mode=args.query_mode,
            ))

        return 0

    except Exception as e:
        logger.error(f"Operation failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())
