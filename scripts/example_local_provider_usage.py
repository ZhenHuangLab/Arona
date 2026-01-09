#!/usr/bin/env python3
"""
Example usage of LocalEmbeddingProvider and LocalRerankerProvider.

This script demonstrates how to configure and use the local GPU providers
for embedding and reranking tasks.
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir.parent))

from backend.config import ModelConfig, ProviderType, ModelType, RerankerConfig
from backend.services.model_factory import ModelFactory


async def example_embedding():
    """Example: Using LocalEmbeddingProvider."""
    print("\n=== Example: Local Embedding ===\n")
    
    # Create embedding config
    embedding_config = ModelConfig(
        provider=ProviderType.LOCAL_GPU,
        model_name="Qwen/Qwen3-Embedding-4B",
        model_type=ModelType.EMBEDDING,
        embedding_dim=2560,
        extra_params={
            "device": "cuda:0",
            "dtype": "float16",
            "attn_implementation": "sdpa",
        }
    )
    
    # Create provider via factory
    provider = ModelFactory.create_embedding_provider(embedding_config)
    
    # Generate embeddings
    texts = [
        "What is the capital of France?",
        "Paris is the capital of France.",
        "The Eiffel Tower is in Paris.",
    ]
    
    embeddings = await provider.embed(texts)
    
    print(f"Generated embeddings for {len(texts)} texts")
    print(f"Embedding shape: {embeddings.shape}")
    print(f"Embedding dimension: {provider.embedding_dim}")
    
    # Calculate similarity between first and second text
    import numpy as np
    similarity = np.dot(embeddings[0], embeddings[1]) / (
        np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1])
    )
    print(f"Similarity between text 0 and 1: {similarity:.4f}")


async def example_reranking():
    """Example: Using LocalRerankerProvider."""
    print("\n=== Example: Local Reranking ===\n")
    
    # Create reranker config
    reranker_config = RerankerConfig(
        enabled=True,
        provider="local_gpu",
        model_name="Qwen/Qwen3-Reranker-4B",
        device="cuda:1",
        dtype="float16",
        attn_implementation="sdpa",
    )
    
    # Create reranker via factory
    rerank_func = ModelFactory.create_reranker(reranker_config)
    
    # Rerank documents
    query = "What is the capital of France?"
    documents = [
        "The Eiffel Tower is a famous landmark.",
        "Paris is the capital of France.",
        "France is a country in Europe.",
        "The weather is nice today.",
    ]
    
    results = await rerank_func(query, documents)
    
    print(f"Reranked {len(documents)} documents")
    print("\nResults (sorted by relevance):")
    
    # Sort by relevance score
    sorted_results = sorted(
        enumerate(results),
        key=lambda x: x[1]["relevance_score"],
        reverse=True
    )
    
    for rank, (idx, result) in enumerate(sorted_results, 1):
        score = result["relevance_score"]
        doc = documents[idx]
        print(f"{rank}. [Score: {score:6.2f}] {doc}")


async def example_embedding_func():
    """Example: Using embedding function for RAGAnything."""
    print("\n=== Example: Embedding Function for RAGAnything ===\n")
    
    # Create embedding config
    embedding_config = ModelConfig(
        provider=ProviderType.LOCAL_GPU,
        model_name="Qwen/Qwen3-Embedding-4B",
        model_type=ModelType.EMBEDDING,
        embedding_dim=2560,
        extra_params={
            "device": "cuda:0",
            "dtype": "float16",
            "attn_implementation": "sdpa",
            "max_token_size": 8192,
        }
    )
    
    # Create RAGAnything-compatible embedding function
    embedding_func = ModelFactory.create_embedding_func(embedding_config)
    
    print(f"Embedding function created")
    print(f"Embedding dimension: {embedding_func.embedding_dim}")
    print(f"Max token size: {embedding_func.max_token_size}")
    
    # Use the function
    texts = ["Test text for embedding"]
    embeddings = await embedding_func.func(texts)
    
    print(f"Generated embeddings: {embeddings.shape}")


async def main():
    """Run all examples."""
    print("=" * 60)
    print("  Local GPU Provider Usage Examples")
    print("=" * 60)
    
    try:
        await example_embedding()
        await example_reranking()
        await example_embedding_func()
        
        print("\n" + "=" * 60)
        print("  All examples completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
