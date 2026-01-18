"""
Quick Start: Using API Reranker with RAG-Anything

This example shows how to use API-based rerankers (Jina, Cohere, Voyage)
with RAG-Anything for improved retrieval quality.
"""

import asyncio
import os
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from raganything import RAGAnything, RAGAnythingConfig
from raganything.rerankers.api_reranker import APIReranker


async def example_with_jina_reranker():
    """Example: Using Jina AI reranker with RAG-Anything."""

    print("\n" + "=" * 60)
    print("Example: RAG-Anything with Jina AI Reranker")
    print("=" * 60 + "\n")

    # Check API keys
    jina_api_key = os.getenv("JINA_API_KEY")
    openai_api_key = os.getenv("OPENAI_API_KEY")

    if not jina_api_key:
        print("❌ JINA_API_KEY not set. Please set it to run this example.")
        return

    if not openai_api_key:
        print("❌ OPENAI_API_KEY not set. Please set it to run this example.")
        return

    # 1. Create API reranker
    print("1. Creating Jina AI reranker...")
    reranker = APIReranker(
        provider="jina",
        model_name="jina-reranker-v2-base-multilingual",
        api_key=jina_api_key,
        batch_size=16,
    )

    # Create reranker function for RAGAnything
    async def rerank_func(query: str, documents: list[str]) -> list[float]:
        return await reranker.score_async(query, documents)

    print("✅ Reranker created\n")

    # 2. Create RAGAnything configuration
    print("2. Configuring RAG-Anything...")
    config = RAGAnythingConfig(
        working_dir="./rag_storage_api_reranker",
        parser="mineru",
        enable_image_processing=True,
        enable_table_processing=True,
        enable_equation_processing=True,
    )
    print("✅ Configuration ready\n")

    # 3. Define LLM and embedding functions
    print("3. Setting up LLM and embedding functions...")

    from lightrag.llm.openai import openai_complete_if_cache, openai_embed
    from lightrag.utils import EmbeddingFunc

    async def llm_model_func(prompt, system_prompt=None, history_messages=[], **kwargs):
        return await openai_complete_if_cache(
            "gpt-4o-mini",
            prompt,
            system_prompt=system_prompt,
            history_messages=history_messages,
            api_key=openai_api_key,
            **kwargs,
        )

    async def embed_func(texts: list[str]):
        return await openai_embed(
            texts,
            model="text-embedding-3-small",
            api_key=openai_api_key,
        )

    embedding_func = EmbeddingFunc(
        embedding_dim=1536,
        max_token_size=8192,
        func=embed_func,
    )

    print("✅ Functions ready\n")

    # 4. Initialize RAGAnything with API reranker
    print("4. Initializing RAG-Anything with API reranker...")
    rag = RAGAnything(
        config=config,
        llm_model_func=llm_model_func,
        embedding_func=embedding_func,
        rerank_model_func=rerank_func,  # ← API reranker here!
    )
    print(f"✅ RAG-Anything initialized ({rag.__class__.__name__})\n")

    # 5. Process a document (optional - skip if you already have data)
    print("5. Processing document (optional)...")
    print("   Skipping document processing in this example.")
    print("   To process documents, use:")
    print("   await rag.process_document_complete('path/to/doc.pdf', './output')\n")

    # 6. Query with reranking
    print("6. Querying with API reranker...")
    print("   Note: This will use Jina AI to rerank retrieved documents")
    print("   for better relevance.\n")

    # Example query (will work if you have processed documents)
    # result = await rag.aquery(
    #     "What are the main findings?",
    #     mode="hybrid"
    # )
    # print(f"Result: {result}\n")

    print("✅ Example complete!\n")
    print("=" * 60)
    print("Summary:")
    print("  - Created Jina AI reranker")
    print("  - Configured RAG-Anything with API reranker")
    print("  - Ready to process documents and query with reranking")
    print("=" * 60 + "\n")

    # Cleanup
    await reranker.close()


async def example_standalone_reranker():
    """Example: Using API reranker standalone (without RAG-Anything)."""

    print("\n" + "=" * 60)
    print("Example: Standalone API Reranker Usage")
    print("=" * 60 + "\n")

    jina_api_key = os.getenv("JINA_API_KEY")
    if not jina_api_key:
        print("❌ JINA_API_KEY not set. Skipping this example.")
        return

    # Create reranker
    reranker = APIReranker(
        provider="jina",
        model_name="jina-reranker-v2-base-multilingual",
        api_key=jina_api_key,
    )

    # Sample query and documents
    query = "What is machine learning?"
    documents = [
        "Machine learning is a subset of artificial intelligence that focuses on data and algorithms.",
        "Python is a high-level programming language used for web development and data science.",
        "Deep learning is a type of machine learning based on artificial neural networks.",
        "The weather forecast predicts rain tomorrow afternoon.",
        "Supervised learning requires labeled training data to train models.",
    ]

    print(f"Query: {query}\n")
    print(f"Documents to rerank: {len(documents)}\n")

    # Rerank documents
    scores = await reranker.score_async(query, documents)

    # Sort by relevance
    ranked = sorted(zip(documents, scores), key=lambda x: x[1], reverse=True)

    print("Reranked Results (by relevance):\n")
    for i, (doc, score) in enumerate(ranked, 1):
        print(f"{i}. [Score: {score:.4f}]")
        print(f"   {doc}\n")

    print("=" * 60)
    print("✅ Standalone reranker example complete!")
    print("=" * 60 + "\n")

    # Cleanup
    await reranker.close()


async def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print(" API Reranker Quick Start Examples")
    print("=" * 70)

    print("\nThese examples demonstrate how to use API-based rerankers")
    print("with RAG-Anything for improved retrieval quality.\n")

    print("Required environment variables:")
    print("  - JINA_API_KEY: Your Jina AI API key")
    print("  - OPENAI_API_KEY: Your OpenAI API key (for LLM/embeddings)")
    print("\nGet your Jina API key at: https://jina.ai/")
    print("=" * 70 + "\n")

    # Run examples
    await example_standalone_reranker()
    await example_with_jina_reranker()

    print("\n" + "=" * 70)
    print("All examples completed!")
    print("=" * 70)
    print("\nNext steps:")
    print("  1. Set up your .env.backend with API reranker config")
    print("  2. Start the backend: python -m backend.main")
    print("  3. Process documents and query with improved reranking")
    print("\nFor more details, see:")
    print("  - examples/README_API_RERANKER.md")
    print("  - docs/API_RERANKER_IMPLEMENTATION.md")
    print("  - docs/QUICKSTART_NEW_ARCHITECTURE.md")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
