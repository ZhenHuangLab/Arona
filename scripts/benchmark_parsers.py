#!/usr/bin/env python3
"""
Parser Performance Benchmark Script
Compares MinerU (CPU/GPU, different backends) vs Docling
"""

import sys
import time
import argparse
from pathlib import Path
from typing import Dict, Any, List
import json


def print_header(title: str):
    """Print formatted header"""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")


def benchmark_parser(
    parser_name: str, file_path: str, output_dir: str, **kwargs
) -> Dict[str, Any]:
    """
    Benchmark a parser configuration

    Returns:
        Dict with timing and result information
    """
    from raganything.parser import MineruParser, DoclingParser

    print(f"\n{'─'*80}")
    print(f"Testing: {parser_name}")
    print(f"{'─'*80}")

    # Print configuration
    print("Configuration:")
    for key, value in kwargs.items():
        print(f"  {key}: {value}")

    # Select parser
    if "docling" in parser_name.lower():
        parser = DoclingParser()
    else:
        parser = MineruParser()

    # Prepare output directory
    test_output_dir = Path(output_dir) / parser_name.replace(" ", "_").replace("/", "_")
    test_output_dir.mkdir(parents=True, exist_ok=True)

    # Run benchmark
    start_time = time.time()
    success = False
    error_msg = None
    content_count = 0

    try:
        content_list = parser.parse_pdf(
            pdf_path=file_path, output_dir=str(test_output_dir), **kwargs
        )
        end_time = time.time()
        success = True
        content_count = len(content_list)

    except Exception as e:
        end_time = time.time()
        error_msg = str(e)
        print(f"\n❌ Error: {error_msg}")

    elapsed_time = end_time - start_time

    # Print results
    if success:
        print("\n✅ Success")
        print(f"   Time: {elapsed_time:.2f}s")
        print(f"   Content blocks: {content_count}")
    else:
        print("\n❌ Failed")
        print(f"   Time: {elapsed_time:.2f}s")

    return {
        "parser": parser_name,
        "success": success,
        "time": elapsed_time,
        "content_count": content_count,
        "error": error_msg,
        "config": kwargs,
    }


def run_benchmarks(file_path: str, output_dir: str) -> List[Dict[str, Any]]:
    """Run all benchmark configurations"""

    results = []

    # Check if GPU is available
    try:
        import torch

        has_gpu = torch.cuda.is_available()
        if has_gpu:
            gpu_name = torch.cuda.get_device_name(0)
            print(f"\n🎮 GPU detected: {gpu_name}")
        else:
            print("\n💻 No GPU detected, will test CPU only")
    except ImportError:
        has_gpu = False
        print("\n💻 PyTorch not available, will test CPU only")

    # Test configurations
    configs = [
        {
            "name": "MinerU Pipeline CPU",
            "backend": "pipeline",
            "device": "cpu",
            "method": "auto",
        },
    ]

    if has_gpu:
        configs.extend(
            [
                {
                    "name": "MinerU Pipeline GPU",
                    "backend": "pipeline",
                    "device": "cuda:0",
                    "method": "auto",
                },
                {
                    "name": "MinerU VLM-Transformers GPU",
                    "backend": "vlm-transformers",
                    "device": "cuda:0",
                    "method": "auto",
                },
            ]
        )

    # Add Docling
    configs.append({"name": "Docling", "method": "auto"})

    # Run benchmarks
    print_header("Running Benchmarks")

    for config in configs:
        name = config.pop("name")
        result = benchmark_parser(
            parser_name=name, file_path=file_path, output_dir=output_dir, **config
        )
        results.append(result)

        # Small delay between tests
        time.sleep(2)

    return results


def print_summary(results: List[Dict[str, Any]]):
    """Print benchmark summary"""

    print_header("Benchmark Summary")

    # Sort by time (successful ones first)
    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]

    successful.sort(key=lambda x: x["time"])

    if successful:
        print("Successful Tests (sorted by speed):\n")
        print(f"{'Rank':<6} {'Parser':<30} {'Time':<12} {'Blocks':<10} {'Speed':<15}")
        print("─" * 80)

        fastest_time = successful[0]["time"]

        for i, result in enumerate(successful, 1):
            speedup = fastest_time / result["time"]
            speedup_str = f"{speedup:.2f}x" if i > 1 else "baseline"

            print(
                f"{i:<6} {result['parser']:<30} {result['time']:>8.2f}s   "
                f"{result['content_count']:>6}     {speedup_str:<15}"
            )

    if failed:
        print("\n\nFailed Tests:\n")
        for result in failed:
            print(f"❌ {result['parser']}")
            print(f"   Error: {result['error'][:100]}...")

    # Recommendations
    print("\n\nRecommendations:\n")

    if successful:
        best = successful[0]
        print(f"✅ Fastest configuration: {best['parser']}")
        print(f"   Time: {best['time']:.2f}s")
        print(f"   Content blocks: {best['content_count']}")

        # Check if GPU helped
        gpu_results = [r for r in successful if "GPU" in r["parser"]]
        cpu_results = [r for r in successful if "CPU" in r["parser"]]

        if gpu_results and cpu_results:
            gpu_time = min(r["time"] for r in gpu_results)
            cpu_time = min(r["time"] for r in cpu_results)
            speedup = cpu_time / gpu_time

            print(f"\n   GPU Speedup: {speedup:.2f}x faster than CPU")

            if speedup < 1.5:
                print("   ⚠️  GPU speedup is minimal (<1.5x)")
                print("      This may indicate:")
                print("      - GPU architecture limitations (Pascal vs Volta)")
                print("      - Small document size (GPU overhead dominates)")
                print("      - CPU-bound operations in the pipeline")
    else:
        print("❌ All tests failed. Please check:")
        print("   1. MinerU/Docling installation")
        print("   2. Model files availability")
        print("   3. CUDA/GPU configuration")


def save_results(results: List[Dict[str, Any]], output_file: str):
    """Save results to JSON file"""
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n📊 Results saved to: {output_path}")


def main():
    """Main benchmark function"""
    parser = argparse.ArgumentParser(description="Benchmark MinerU and Docling parsers")
    parser.add_argument("file", help="PDF file to test")
    parser.add_argument(
        "--output-dir",
        "-o",
        default="./benchmark_output",
        help="Output directory for parsed results",
    )
    parser.add_argument(
        "--results-file",
        "-r",
        default="./benchmark_results.json",
        help="JSON file to save benchmark results",
    )

    args = parser.parse_args()

    # Check file exists
    if not Path(args.file).exists():
        print(f"❌ Error: File not found: {args.file}")
        sys.exit(1)

    print("\n" + "=" * 80)
    print("  Parser Performance Benchmark")
    print("=" * 80)
    print(f"\nTest file: {args.file}")
    print(f"Output directory: {args.output_dir}")

    # Run benchmarks
    results = run_benchmarks(args.file, args.output_dir)

    # Print summary
    print_summary(results)

    # Save results
    save_results(results, args.results_file)

    print("\n" + "=" * 80)
    print("  Benchmark Complete")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
