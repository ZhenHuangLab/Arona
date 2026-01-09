#!/usr/bin/env python3
"""
Local Embedding Service Performance Benchmark Script

Comprehensive performance testing for LocalEmbeddingProvider including:
- Throughput testing (texts/sec)
- Latency testing (p50/p95/p99 percentiles)
- GPU memory monitoring
- End-to-end RAG query testing

Usage:
    # Run all tests
    python scripts/benchmark_local_embedding.py --mode all
    
    # Run specific test
    python scripts/benchmark_local_embedding.py --mode throughput
    python scripts/benchmark_local_embedding.py --mode latency
    python scripts/benchmark_local_embedding.py --mode memory
    python scripts/benchmark_local_embedding.py --mode e2e
    
    # Custom configuration
    python scripts/benchmark_local_embedding.py --device cuda:0 --batch-size 64
"""

import asyncio
import argparse
import time
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
import numpy as np

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def print_header(title: str):
    """Print formatted header."""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")


def print_section(title: str):
    """Print formatted section."""
    print(f"\n{'─'*80}")
    print(f"  {title}")
    print(f"{'─'*80}")


class GPUMemoryMonitor:
    """GPU memory monitoring utility (device-normalized)."""

    def __init__(self, device: str | int = "cuda:0"):
        """Initialize memory monitor and normalize device to an index."""
        import torch
        self.torch = torch
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA not available")

        # Normalize to device index for torch.cuda.* calls
        if isinstance(device, int):
            self.device_index = device
        else:
            # Accept formats like "cuda", "cuda:0", or torch.device
            try:
                dev = torch.device(device)
                self.device_index = dev.index if dev.index is not None else 0
            except Exception:
                self.device_index = 0

    def get_memory_usage(self) -> float:
        """Get current GPU memory usage in GB."""
        return self.torch.cuda.memory_allocated(self.device_index) / 1024**3

    def get_peak_memory(self) -> float:
        """Get peak GPU memory usage in GB."""
        return self.torch.cuda.max_memory_allocated(self.device_index) / 1024**3

    def reset_peak_memory(self):
        """Reset peak memory statistics."""
        self.torch.cuda.reset_peak_memory_stats(self.device_index)

    def get_memory_summary(self) -> Dict[str, float]:
        """Get comprehensive memory summary."""
        return {
            "allocated_gb": self.get_memory_usage(),
            "peak_gb": self.get_peak_memory(),
            "reserved_gb": self.torch.cuda.memory_reserved(self.device_index) / 1024**3,
        }


class ThroughputBenchmark:
    """Throughput benchmark for embedding service."""

    def __init__(self, provider):
        """Initialize throughput benchmark."""
        self.provider = provider

    async def run(
        self,
        batch_sizes: List[int] = [100, 500, 1000],
        text_length: str = "medium"
    ) -> Dict[str, Any]:
        """
        Run throughput benchmark with concurrent requests.

        Tests the BatchProcessor's ability to handle concurrent requests
        by sending multiple small requests simultaneously, which better
        reflects real-world usage patterns.

        Args:
            batch_sizes: List of total texts to test (sent as concurrent requests)
            text_length: Text length ("short", "medium", "long")

        Returns:
            Benchmark results
        """
        print_section("Throughput Benchmark")

        # Generate test texts
        test_texts = self._generate_test_texts(text_length)

        results = {}

        for total_texts in batch_sizes:
            print(f"\nTesting {total_texts} texts (concurrent requests)")

            # Warmup
            _ = await self.provider.embed([test_texts[0]])

            # Prepare concurrent requests (each request has 1-5 texts)
            # This simulates realistic concurrent usage
            requests = []
            texts_per_request = 3  # Average texts per request
            num_requests = total_texts // texts_per_request

            for i in range(num_requests):
                # Vary request size slightly for realism
                request_size = min(texts_per_request + (i % 3), total_texts - i * texts_per_request)
                if request_size <= 0:
                    break
                request_texts = [test_texts[j % len(test_texts)] for j in range(request_size)]
                requests.append(request_texts)

            # Benchmark concurrent requests
            start_time = time.perf_counter()

            # Send all requests concurrently
            tasks = [self.provider.embed(req) for req in requests]
            embeddings_list = await asyncio.gather(*tasks)

            end_time = time.perf_counter()

            # Calculate metrics
            total_processed = sum(len(emb) for emb in embeddings_list)
            elapsed = end_time - start_time
            throughput = total_processed / elapsed

            results[total_texts] = {
                "elapsed_s": elapsed,
                "throughput_texts_per_sec": throughput,
                "num_requests": len(requests),
                "total_texts": total_processed,
            }

            print(f"  Requests: {len(requests)}")
            print(f"  Total texts: {total_processed}")
            print(f"  Elapsed: {elapsed:.3f}s")
            print(f"  Throughput: {throughput:.1f} texts/sec")

            # Check if meets target
            if throughput >= 100:
                print(f"  ✓ Meets target (>= 100 texts/sec)")
            else:
                print(f"  ✗ Below target (>= 100 texts/sec)")

        return results
    
    def _generate_test_texts(self, length: str = "medium") -> List[str]:
        """Generate test texts of different lengths."""
        if length == "short":
            return [
                "This is a short test sentence for embedding.",
                "Another short example text.",
                "Quick brown fox jumps over the lazy dog.",
            ]
        elif length == "long":
            return [
                " ".join(["This is a longer test sentence with more tokens."] * 20),
                " ".join(["Another example of a long text for testing."] * 20),
                " ".join(["Performance testing requires realistic data."] * 20),
            ]
        else:  # medium
            return [
                "This is a medium-length test sentence for embedding performance testing. "
                "It contains enough tokens to be realistic but not too long to slow down tests.",
                "Another medium-length example text that simulates typical document chunks. "
                "This helps us measure realistic performance under normal workload conditions.",
                "Performance benchmarking requires representative test data that matches "
                "the expected input distribution in production environments.",
            ]


class LatencyBenchmark:
    """Latency benchmark for embedding service."""
    
    def __init__(self, provider):
        """Initialize latency benchmark."""
        self.provider = provider
    
    async def run(
        self,
        num_requests: int = 100,
        text_length: str = "medium"
    ) -> Dict[str, Any]:
        """
        Run latency benchmark.
        
        Args:
            num_requests: Number of requests to test
            text_length: Text length ("short", "medium", "long")
        
        Returns:
            Benchmark results with percentiles
        """
        print_section("Latency Benchmark")
        
        # Generate test texts
        test_texts = self._generate_test_texts(text_length)
        
        print(f"Testing {num_requests} requests...")
        
        # Warmup
        _ = await self.provider.embed([test_texts[0]])
        
        # Collect latencies
        latencies = []
        
        for i in range(num_requests):
            text = test_texts[i % len(test_texts)]
            
            start_time = time.perf_counter()
            _ = await self.provider.embed([text])
            end_time = time.perf_counter()
            
            latency_ms = (end_time - start_time) * 1000
            latencies.append(latency_ms)
            
            if (i + 1) % 20 == 0:
                print(f"  Progress: {i + 1}/{num_requests}")
        
        # Calculate percentiles
        latencies_array = np.array(latencies)
        p50 = np.percentile(latencies_array, 50)
        p95 = np.percentile(latencies_array, 95)
        p99 = np.percentile(latencies_array, 99)
        mean = np.mean(latencies_array)
        
        results = {
            "num_requests": num_requests,
            "mean_ms": mean,
            "p50_ms": p50,
            "p95_ms": p95,
            "p99_ms": p99,
            "min_ms": np.min(latencies_array),
            "max_ms": np.max(latencies_array),
        }
        
        print(f"\nLatency Statistics:")
        print(f"  Mean:   {mean:.2f} ms")
        print(f"  p50:    {p50:.2f} ms")
        print(f"  p95:    {p95:.2f} ms")
        print(f"  p99:    {p99:.2f} ms")
        print(f"  Min:    {results['min_ms']:.2f} ms")
        print(f"  Max:    {results['max_ms']:.2f} ms")
        
        # Check if meets target
        if p95 < 200:
            print(f"\n  ✓ Meets target (p95 < 200ms)")
        else:
            print(f"\n  ✗ Above target (p95 < 200ms)")
        
        return results
    
    def _generate_test_texts(self, length: str = "medium") -> List[str]:
        """Generate test texts (same as ThroughputBenchmark)."""
        if length == "short":
            return [
                "This is a short test sentence for embedding.",
                "Another short example text.",
                "Quick brown fox jumps over the lazy dog.",
            ]
        elif length == "long":
            return [
                " ".join(["This is a longer test sentence with more tokens."] * 20),
                " ".join(["Another example of a long text for testing."] * 20),
                " ".join(["Performance testing requires realistic data."] * 20),
            ]
        else:  # medium
            return [
                "This is a medium-length test sentence for embedding performance testing. "
                "It contains enough tokens to be realistic but not too long to slow down tests.",
                "Another medium-length example text that simulates typical document chunks. "
                "This helps us measure realistic performance under normal workload conditions.",
                "Performance benchmarking requires representative test data that matches "
                "the expected input distribution in production environments.",
            ]


class MemoryBenchmark:
    """GPU memory usage benchmark."""

    def __init__(self, provider, monitor: GPUMemoryMonitor):
        """Initialize memory benchmark."""
        self.provider = provider
        self.monitor = monitor

    async def run(
        self,
        batch_sizes: List[int] = [32, 64, 128],
        text_length: str = "medium"
    ) -> Dict[str, Any]:
        """
        Run memory benchmark.

        Args:
            batch_sizes: List of batch sizes to test
            text_length: Text length ("short", "medium", "long")

        Returns:
            Memory usage results
        """
        print_section("Memory Benchmark")

        # Generate test texts
        test_texts = self._generate_test_texts(text_length)

        results = {}

        for batch_size in batch_sizes:
            print(f"\nTesting batch size: {batch_size} texts")

            # Prepare batch
            texts = [test_texts[i % len(test_texts)] for i in range(batch_size)]

            # Reset peak memory
            self.monitor.reset_peak_memory()

            # Get baseline memory
            baseline_memory = self.monitor.get_memory_usage()

            # Run inference
            _ = await self.provider.embed(texts)

            # Get memory stats
            memory_summary = self.monitor.get_memory_summary()

            results[batch_size] = {
                "baseline_gb": baseline_memory,
                "allocated_gb": memory_summary["allocated_gb"],
                "peak_gb": memory_summary["peak_gb"],
                "reserved_gb": memory_summary["reserved_gb"],
                "delta_gb": memory_summary["peak_gb"] - baseline_memory,
            }

            print(f"  Baseline:  {baseline_memory:.2f} GB")
            print(f"  Allocated: {memory_summary['allocated_gb']:.2f} GB")
            print(f"  Peak:      {memory_summary['peak_gb']:.2f} GB")
            print(f"  Reserved:  {memory_summary['reserved_gb']:.2f} GB")
            print(f"  Delta:     {results[batch_size]['delta_gb']:.2f} GB")

            # Check if meets target
            if memory_summary["peak_gb"] < 11.0:
                print(f"  ✓ Meets target (< 11GB)")
            else:
                print(f"  ✗ Exceeds target (< 11GB)")

        return results

    def _generate_test_texts(self, length: str = "medium") -> List[str]:
        """Generate test texts."""
        if length == "short":
            return [
                "This is a short test sentence for embedding.",
                "Another short example text.",
                "Quick brown fox jumps over the lazy dog.",
            ]
        elif length == "long":
            return [
                " ".join(["This is a longer test sentence with more tokens."] * 20),
                " ".join(["Another example of a long text for testing."] * 20),
                " ".join(["Performance testing requires realistic data."] * 20),
            ]
        else:  # medium
            return [
                "This is a medium-length test sentence for embedding performance testing. "
                "It contains enough tokens to be realistic but not too long to slow down tests.",
                "Another medium-length example text that simulates typical document chunks. "
                "This helps us measure realistic performance under normal workload conditions.",
                "Performance benchmarking requires representative test data that matches "
                "the expected input distribution in production environments.",
            ]


class EndToEndTest:
    """End-to-end RAG query test."""

    async def run(self, device: str = "cuda:0") -> Dict[str, Any]:
        """
        Run end-to-end RAG query test.

        Args:
            device: GPU device to use

        Returns:
            Test results
        """
        print_section("End-to-End RAG Query Test")

        print("Initializing RAG service with local embedding provider...")

        try:
            # Import required modules
            from backend.config import ModelConfig, ModelType, ProviderType
            from backend.providers.local_embedding import LocalEmbeddingProvider

            # Create embedding config
            embedding_config = ModelConfig(
                provider=ProviderType.LOCAL_GPU,
                model_name="Qwen/Qwen3-Embedding-4B",
                model_type=ModelType.EMBEDDING,
                embedding_dim=2560,
                extra_params={
                    "device": device,
                    "dtype": "float16",
                    "attn_implementation": "sdpa",
                    "max_batch_size": 32,
                    "max_wait_time": 0.1,
                }
            )

            # Initialize provider
            print("Loading embedding model...")
            provider = LocalEmbeddingProvider(embedding_config)

            # Test embedding generation
            print("\nTesting embedding generation...")
            test_texts = [
                "What is the capital of France?",
                "Paris is the capital and most populous city of France.",
                "The Eiffel Tower is located in Paris.",
            ]

            start_time = time.perf_counter()
            embeddings = await provider.embed(test_texts)
            end_time = time.perf_counter()

            elapsed = end_time - start_time

            print(f"  Generated {len(test_texts)} embeddings")
            print(f"  Shape: {embeddings.shape}")
            print(f"  Time: {elapsed*1000:.2f} ms")
            print(f"  Dimension: {embeddings.shape[1]}")

            # Verify embedding properties
            assert embeddings.shape[0] == len(test_texts), "Wrong number of embeddings"
            assert embeddings.shape[1] == 2560, "Wrong embedding dimension"

            # Shutdown provider
            await provider.shutdown()

            print("\n  ✓ End-to-end test passed")

            return {
                "success": True,
                "num_texts": len(test_texts),
                "embedding_dim": embeddings.shape[1],
                "elapsed_ms": elapsed * 1000,
            }

        except Exception as e:
            print(f"\n  ✗ End-to-end test failed: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e),
            }


async def run_benchmarks(args):
    """Run selected benchmarks."""
    print_header("Local Embedding Service Performance Benchmark")

    print(f"Configuration:")
    print(f"  Device: {args.device}")
    print(f"  Model: {args.model}")
    print(f"  Mode: {args.mode}")

    # Initialize provider for non-e2e tests
    provider = None
    monitor = None

    if args.mode != "e2e":
        print("\nInitializing embedding provider...")

        from backend.config import ModelConfig, ModelType, ProviderType
        from backend.providers.local_embedding import LocalEmbeddingProvider

        embedding_config = ModelConfig(
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
            }
        )

        provider = LocalEmbeddingProvider(embedding_config)
        monitor = GPUMemoryMonitor(args.device)

        print("  ✓ Provider initialized")

    # Run selected tests
    results = {}

    try:
        if args.mode in ["throughput", "all"]:
            benchmark = ThroughputBenchmark(provider)
            results["throughput"] = await benchmark.run(
                batch_sizes=[100, 500, 1000],
                text_length="medium"
            )

        if args.mode in ["latency", "all"]:
            benchmark = LatencyBenchmark(provider)
            results["latency"] = await benchmark.run(
                num_requests=100,
                text_length="medium"
            )

        if args.mode in ["memory", "all"]:
            benchmark = MemoryBenchmark(provider, monitor)
            results["memory"] = await benchmark.run(
                batch_sizes=[32, 64, 128],
                text_length="medium"
            )

        if args.mode in ["e2e", "all"]:
            test = EndToEndTest()
            results["e2e"] = await test.run(device=args.device)

    finally:
        # Cleanup
        if provider is not None:
            print("\nShutting down provider...")
            await provider.shutdown()
            print("  ✓ Provider shutdown complete")

    # Print summary
    print_summary(results, args.mode)

    return results


def print_summary(results: Dict[str, Any], mode: str):
    """Print benchmark summary."""
    print_header("Benchmark Summary")

    all_passed = True

    # Throughput summary
    if "throughput" in results:
        print("Throughput Test:")
        for batch_size, result in results["throughput"].items():
            throughput = result["throughput_texts_per_sec"]
            status = "✓" if throughput >= 100 else "✗"
            print(f"  {status} {batch_size} texts: {throughput:.1f} texts/sec")
            if throughput < 100:
                all_passed = False

    # Latency summary
    if "latency" in results:
        print("\nLatency Test:")
        p95 = results["latency"]["p95_ms"]
        status = "✓" if p95 < 200 else "✗"
        print(f"  {status} p95: {p95:.2f} ms (target: < 200ms)")
        if p95 >= 200:
            all_passed = False

    # Memory summary
    if "memory" in results:
        print("\nMemory Test:")
        for batch_size, result in results["memory"].items():
            peak_gb = result["peak_gb"]
            status = "✓" if peak_gb < 11.0 else "✗"
            print(f"  {status} {batch_size} texts: {peak_gb:.2f} GB (target: < 11GB)")
            if peak_gb >= 11.0:
                all_passed = False

    # E2E summary
    if "e2e" in results:
        print("\nEnd-to-End Test:")
        success = results["e2e"].get("success", False)
        status = "✓" if success else "✗"
        print(f"  {status} RAG query: {'Passed' if success else 'Failed'}")
        if not success:
            all_passed = False

    # Overall status
    print("\n" + "="*80)
    if all_passed:
        print("  ✓ ALL TESTS PASSED")
    else:
        print("  ✗ SOME TESTS FAILED")
    print("="*80)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Benchmark local embedding service performance"
    )
    parser.add_argument(
        "--mode",
        choices=["throughput", "latency", "memory", "e2e", "all"],
        default="all",
        help="Benchmark mode to run"
    )
    parser.add_argument(
        "--device",
        default="cuda:0",
        help="GPU device to use (default: cuda:0)"
    )
    parser.add_argument(
        "--model",
        default="Qwen/Qwen3-Embedding-4B",
        help="Model name (default: Qwen/Qwen3-Embedding-4B)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Batch size for provider (default: 32)"
    )
    parser.add_argument(
        "--encode-batch-size",
        type=int,
        default=128,
        help="Internal encode() batch size for sentence-transformers (default: 128)"
    )
    parser.add_argument(
        "--max-wait-time",
        type=float,
        default=0.1,
        help="Max wait time (seconds) for dynamic batching (default: 0.1)"
    )

    args = parser.parse_args()

    # Run benchmarks
    try:
        results = asyncio.run(run_benchmarks(args))
    except KeyboardInterrupt:
        print("\n\nBenchmark interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nBenchmark failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
