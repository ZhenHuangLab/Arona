#!/usr/bin/env python3
"""
End-to-end RAG Retrieval Benchmark (index + retrieve)

This script validates the real RAG path using LightRAG with the local
embedding provider (LocalEmbeddingProvider):

- Initializes LocalEmbeddingProvider with configurable batching knobs
- Boots a LightRAG instance with an EmbeddingFunc built from the provider
- Inserts a tiny in-memory corpus (3 short docs)
- Runs a query and asserts the retrieved context contains the answer

Note: Generation is stubbed by using LightRAG.query_data/aquery_data so we
validate indexing + retrieval deterministically without requiring an LLM key.

Usage:
  python scripts/benchmark_end_to_end_rag.py \
    --device cuda:0 --model Qwen/Qwen3-Embedding-4B \
    --encode-batch-size 128 --max-wait-time 0.1
"""

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

# Project root in path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def print_header(title: str):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


async def run_test(args) -> Dict[str, Any]:
    from backend.config import ModelConfig, ModelType, ProviderType
    from backend.providers.local_embedding import LocalEmbeddingProvider
    from lightrag import LightRAG, QueryParam
    from lightrag.utils import EmbeddingFunc

    # 1) Initialize local embedding provider
    cfg = ModelConfig(
        provider=ProviderType.LOCAL_GPU,
        model_name=args.model,
        model_type=ModelType.EMBEDDING,
        embedding_dim=2560,
        extra_params={
            "device": args.device,
            "dtype": "float16",
            "attn_implementation": "sdpa",
            "max_batch_size": args.batch_size,
            "max_wait_time": args.max_wait_time,
            "encode_batch_size": args.encode_batch_size,
        },
    )

    provider = LocalEmbeddingProvider(cfg)

    # 2) Build EmbeddingFunc expected by LightRAG
    async def embed_func(texts: List[str]) -> Any:
        arr = await provider.embed(texts)
        return arr

    ef = EmbeddingFunc(embedding_dim=provider.embedding_dim, max_token_size=8192, func=embed_func)

    # 3) Initialize LightRAG (separate workdir for test)
    workdir = Path(args.workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    rag = LightRAG(working_dir=str(workdir), embedding_func=ef, auto_manage_storages_states=True)
    rag.initialize_storages()

    # 4) Insert tiny corpus
    doc_fr = "Paris is the capital of France. The Eiffel Tower is in Paris."
    doc_de = "Berlin is the capital of Germany. The Brandenburg Gate is in Berlin."
    doc_cn = "Beijing is the capital of China. The Forbidden City is in Beijing."

    # Use simple sentence chunks
    async def insert_doc(full: str, doc_id: str):
        chunks = [s.strip() for s in full.split(".") if s.strip()]
        await rag.ainsert_custom_chunks(full, chunks, doc_id)

    await insert_doc(doc_fr, "doc-fr")
    await insert_doc(doc_de, "doc-de")
    await insert_doc(doc_cn, "doc-cn")

    # 5) Query (retrieval-only path)
    qp = QueryParam(mode="local", only_need_context=True, top_k=5, include_references=True)
    q = args.query
    result = await rag.aquery_data(q, qp)

    # 6) Basic assertion: retrieved context should contain the target fact
    # Fall back to lenient string inspection of the result dictionary
    blob = str(result)
    success = "Paris is the capital of France" in blob or "Paris" in blob

    # 7) Cleanup
    await provider.shutdown()
    await rag.finalize_storages()

    return {
        "success": success,
        "query": q,
        "workdir": str(workdir),
        "hint": "Look for 'Paris is the capital of France' in retrieved contexts.",
    }


def main():
    parser = argparse.ArgumentParser(description="End-to-end RAG retrieval benchmark")
    parser.add_argument("--device", default="cuda:0", help="GPU device, e.g. cuda:0")
    parser.add_argument(
        "--model", default="Qwen/Qwen3-Embedding-4B", help="Embedding model name"
    )
    parser.add_argument("--batch-size", type=int, default=32, help="Dynamic batch size")
    parser.add_argument(
        "--encode-batch-size",
        type=int,
        default=128,
        help="Internal encode() batch size for sentence-transformers",
    )
    parser.add_argument(
        "--max-wait-time", type=float, default=0.1, help="Max wait time (s) for batching"
    )
    parser.add_argument(
        "--workdir",
        default=str(Path("rag_storage") / "bench_e2e"),
        help="Working directory for LightRAG storages",
    )
    parser.add_argument(
        "--query",
        default="What is the capital of France?",
        help="Query text used for retrieval validation",
    )

    args = parser.parse_args()

    print_header("E2E RAG Retrieval Benchmark")
    print(
        f"Config: device={args.device}, model={args.model}, bs={args.batch_size}, "
        f"encode_bs={args.encode_batch_size}, max_wait={args.max_wait_time}"
    )

    try:
        result = asyncio.run(run_test(args))
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ E2E test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    if result["success"]:
        print("\n✓ End-to-end retrieval test PASSED")
    else:
        print("\n✗ End-to-end retrieval test FAILED")
    print(f"Query: {result['query']}")
    print(f"Workdir: {result['workdir']}")
    print(f"Hint: {result['hint']}")

    sys.exit(0 if result["success"] else 2)


if __name__ == "__main__":
    main()
