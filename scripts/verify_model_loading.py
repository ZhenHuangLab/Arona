#!/usr/bin/env python3
"""
Verify local embedding/reranker model loading and performance for Task 7.

This script performs comprehensive testing of downloaded models:
- FP16 vs FP32 precision comparison
- eager vs sdpa attention implementation comparison
- Batch inference testing with various batch sizes
- GPU memory profiling
- Performance benchmarking

Usage:
    # Verify all models
    python scripts/verify_model_loading.py --all

    # Verify specific model
    python scripts/verify_model_loading.py --model Qwen/Qwen3-Embedding-4B

    # Compare FP16 vs FP32
    python scripts/verify_model_loading.py --model Qwen/Qwen3-Embedding-4B --compare-dtypes

    # Compare eager vs sdpa attention
    python scripts/verify_model_loading.py --model Qwen/Qwen3-Embedding-4B --compare-attn

    # Test batch inference
    python scripts/verify_model_loading.py --model Qwen/Qwen3-Embedding-4B --test-batch
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Dict, Any, List

import torch
import numpy as np

# Model configurations
MODEL_CONFIGS = {
    "Qwen/Qwen3-Embedding-4B": {
        "type": "embedding",
        "device": "cuda:0",
        "embedding_dim": 2560,
        "test_batch_sizes": [1, 8, 16, 32],
    },
    "Qwen/Qwen3-Reranker-4B": {
        "type": "reranker",
        "device": "cuda:1",
        "test_batch_sizes": [1, 4, 8, 16],
    },
    "Alibaba-NLP/gme-Qwen2-VL-2B-Instruct": {
        "type": "multimodal",
        "device": "cuda:2",
        "embedding_dim": 1536,
        "test_batch_sizes": [1, 4, 8, 16],
    },
}


def print_section(title: str) -> None:
    """Print a formatted section header."""
    print(f"\n{'=' * 80}")
    print(f"  {title}")
    print("=" * 80)


def measure_memory(device: str) -> float:
    """Measure current GPU memory usage in GB."""
    return torch.cuda.memory_allocated(device) / 1024**3


def _qwen3_reranker_format_pair(instruction: str, query: str, document: str) -> str:
    """Format a single pair for Qwen3-Reranker scoring."""
    return (
        f"<Instruct>: {instruction}\n" f"<Query>: {query}\n" f"<Document>: {document}"
    )


def _qwen3_reranker_build_inputs(
    tokenizer,
    pairs: List[str],
    device: str,
    max_length: int = 8192,
    system_prompt: str | None = None,
) -> Dict[str, torch.Tensor]:
    """
    Build padded model inputs for Qwen3-Reranker (CausalLM yes/no template).

    The model expects a system/user prompt wrapper; scoring is based on the
    next token distribution of "yes" vs "no".
    """
    if system_prompt is None:
        system_prompt = (
            "Judge whether the Document meets the requirements based on the Query and the Instruct provided. "
            'Note that the answer can only be "yes" or "no".'
        )

    prefix = f"<|im_start|>system\n{system_prompt}<|im_end|>\n<|im_start|>user\n"
    suffix = "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"

    prefix_tokens = tokenizer.encode(prefix, add_special_tokens=False)
    suffix_tokens = tokenizer.encode(suffix, add_special_tokens=False)
    max_pair_len = max_length - len(prefix_tokens) - len(suffix_tokens)
    if max_pair_len <= 0:
        raise RuntimeError("Reranker template too long for max_length")

    enc = tokenizer(
        pairs,
        padding=False,
        truncation="longest_first",
        return_attention_mask=False,
        max_length=max_pair_len,
        add_special_tokens=False,
    )
    enc["input_ids"] = [
        prefix_tokens + ids + suffix_tokens for ids in enc.get("input_ids", [])
    ]
    inputs = tokenizer.pad(enc, padding=True, return_tensors="pt")
    return {k: v.to(device) for k, v in inputs.items() if isinstance(v, torch.Tensor)}


def _qwen3_reranker_score_pairs(
    model,
    tokenizer,
    pairs: List[str],
    device: str,
    token_yes_id: int,
    token_no_id: int,
    max_length: int = 8192,
    system_prompt: str | None = None,
) -> List[float]:
    """Score pairs via P(yes) computed from the next-token distribution."""
    inputs = _qwen3_reranker_build_inputs(
        tokenizer=tokenizer,
        pairs=pairs,
        device=device,
        max_length=max_length,
        system_prompt=system_prompt,
    )
    with torch.no_grad():
        outputs = model(**inputs)
        next_logits = outputs.logits[:, -1, :]
        yes_logits = next_logits[:, token_yes_id]
        no_logits = next_logits[:, token_no_id]
        probs_yes = torch.softmax(
            torch.stack([no_logits, yes_logits], dim=1).float(), dim=1
        )[:, 1]
        return probs_yes.detach().cpu().tolist()


def test_embedding_model(
    model_id: str,
    device: str,
    dtype: torch.dtype = torch.float16,
    attn_implementation: str = "sdpa",
) -> Dict[str, Any]:
    """
    Test embedding model loading and inference.

    Args:
        model_id: HuggingFace model ID
        device: CUDA device
        dtype: Model dtype (float16 or float32)
        attn_implementation: Attention implementation (eager or sdpa)

    Returns:
        Test results dictionary
    """
    from sentence_transformers import SentenceTransformer

    results = {
        "model_id": model_id,
        "device": device,
        "dtype": str(dtype),
        "attn_implementation": attn_implementation,
        "success": False,
    }

    try:
        # Ensure device context is initialized and selected
        dev = torch.device(device)
        torch.cuda.set_device(dev)
        # Clear cache
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats(dev)
        initial_memory = measure_memory(dev)

        # Load model
        print(f"Loading {model_id} with dtype={dtype}, attn={attn_implementation}...")
        start_time = time.time()

        model = SentenceTransformer(
            model_id,
            device=device,
            model_kwargs={
                "torch_dtype": dtype,
                "attn_implementation": attn_implementation,
            },
        )

        load_time = time.time() - start_time
        loaded_memory = measure_memory(dev)
        reserved_loaded = torch.cuda.memory_reserved(device) / 1024**3
        reserved_initial = torch.cuda.memory_reserved(device) / 1024**3
        memory_used = loaded_memory - initial_memory
        reserved_used = reserved_loaded - reserved_initial

        print(f"  Load time: {load_time:.2f}s")
        print(f"  Memory used: {memory_used:.2f} GB (allocated)")
        print(f"  Memory reserved: {reserved_used:.2f} GB (delta)")

        # Warmup (no NumPy conversion to avoid NumPy 2.x issues)
        print("  Warming up...")
        _ = model.encode("warmup")
        warmup_memory = measure_memory(dev)

        # Verify attention backend if available
        try:
            attn_backend = None
            if hasattr(model[0], "auto_model") and hasattr(
                model[0].auto_model, "config"
            ):
                attn_backend = getattr(
                    model[0].auto_model.config, "attn_implementation", None
                )
            if attn_backend:
                print(f"  Detected attn backend: {attn_backend}")
                if attn_backend != attn_implementation:
                    print(
                        f"  ⚠ Attention backend mismatch (requested {attn_implementation}, got {attn_backend})"
                    )
            results["attn_backend_detected"] = attn_backend
        except Exception:
            results["attn_backend_detected"] = None

        # Test single inference
        print("  Testing single inference...")
        test_text = "This is a test sentence for embedding generation."

        start_time = time.time()
        embedding = model.encode(test_text)
        if hasattr(embedding, "cpu"):
            embedding = embedding.cpu().numpy()
        if not isinstance(embedding, np.ndarray):
            embedding = np.array(embedding)
        inference_time = time.time() - start_time

        print(f"  Inference time: {inference_time*1000:.2f}ms")
        print(f"  Embedding shape: {embedding.shape}")

        # Get peak memory
        peak_memory = torch.cuda.max_memory_allocated(dev) / 1024**3
        peak_reserved = torch.cuda.max_memory_reserved(dev) / 1024**3

        results.update(
            {
                "success": True,
                "load_time_s": load_time,
                "memory_used_gb": memory_used,
                "memory_reserved_used_gb": reserved_used,
                "warmup_memory_gb": warmup_memory,
                "peak_memory_gb": peak_memory,
                "peak_memory_reserved_gb": peak_reserved,
                "inference_time_ms": inference_time * 1000,
                "embedding_dim": embedding.shape[0],
            }
        )

        # Clean up and force GC
        import gc

        del model
        torch.cuda.empty_cache()
        gc.collect()

    except Exception as e:
        results["error"] = f"{type(e).__name__}: {e}"
        print(f"  ✗ Error: {results['error']}")

    return results


def test_reranker_model(
    model_id: str,
    device: str,
    dtype: torch.dtype = torch.float16,
    attn_implementation: str = "sdpa",
) -> Dict[str, Any]:
    """
    Test reranker model loading and inference.

    Args:
        model_id: HuggingFace model ID
        device: CUDA device
        dtype: Model dtype (float16 or float32)
        attn_implementation: Attention implementation (eager or sdpa)

    Returns:
        Test results dictionary
    """
    from transformers import AutoModelForCausalLM, AutoTokenizer

    results = {
        "model_id": model_id,
        "device": device,
        "dtype": str(dtype),
        "attn_implementation": attn_implementation,
        "success": False,
    }

    try:
        # Ensure device context is initialized and selected
        dev = torch.device(device)
        torch.cuda.set_device(dev)
        # Clear cache
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats(dev)
        initial_memory = measure_memory(dev)
        initial_reserved = torch.cuda.memory_reserved(dev) / 1024**3

        # Load model
        print(f"Loading {model_id} with dtype={dtype}, attn={attn_implementation}...")
        start_time = time.time()

        tokenizer = AutoTokenizer.from_pretrained(
            model_id,
            padding_side="left",
            trust_remote_code=True,
        )
        # Ensure pad token exists for batched padding
        if tokenizer.pad_token is None and tokenizer.eos_token is not None:
            tokenizer.pad_token = tokenizer.eos_token
        if (
            getattr(tokenizer, "pad_token_id", None) is None
            and tokenizer.eos_token_id is not None
        ):
            tokenizer.pad_token_id = tokenizer.eos_token_id

        yes_ids = tokenizer("yes", add_special_tokens=False).input_ids
        no_ids = tokenizer("no", add_special_tokens=False).input_ids
        if len(yes_ids) != 1 or len(no_ids) != 1:
            raise RuntimeError(
                f'Expected "yes"/"no" to be single tokens, got yes={yes_ids}, no={no_ids}'
            )
        token_yes_id = yes_ids[0]
        token_no_id = no_ids[0]

        model = AutoModelForCausalLM.from_pretrained(
            model_id,
            torch_dtype=dtype,
            attn_implementation=attn_implementation,
            trust_remote_code=True,
        ).to(device)
        model.eval()

        if (
            getattr(model.config, "pad_token_id", None) is None
            and getattr(tokenizer, "pad_token_id", None) is not None
        ):
            model.config.pad_token_id = tokenizer.pad_token_id

        # Verify attention backend if available
        attn_backend = getattr(
            getattr(model, "config", None), "attn_implementation", None
        )
        if attn_backend:
            print(f"  Detected attn backend: {attn_backend}")
            if attn_backend != attn_implementation:
                print(
                    f"  ⚠ Attention backend mismatch (requested {attn_implementation}, got {attn_backend})"
                )

        load_time = time.time() - start_time
        loaded_memory = measure_memory(dev)
        reserved_loaded = torch.cuda.memory_reserved(dev) / 1024**3
        memory_used = loaded_memory - initial_memory
        reserved_used = reserved_loaded - initial_reserved

        print(f"  Load time: {load_time:.2f}s")
        print(f"  Memory used: {memory_used:.2f} GB (allocated)")
        print(f"  Memory reserved: {reserved_used:.2f} GB (delta)")

        # Warmup
        print("  Warming up...")
        warmup_pairs = [
            _qwen3_reranker_format_pair(
                instruction="Given a web search query, retrieve relevant passages that answer the query",
                query="warmup",
                document="warmup document",
            )
        ]
        _ = _qwen3_reranker_score_pairs(
            model=model,
            tokenizer=tokenizer,
            pairs=warmup_pairs,
            device=device,
            token_yes_id=token_yes_id,
            token_no_id=token_no_id,
            max_length=8192,
        )
        warmup_memory = measure_memory(dev)

        # Test single inference
        print("  Testing single inference...")
        query = "What is the capital of France?"
        document = "Paris is the capital and largest city of France."

        instruction = (
            "Given a web search query, retrieve relevant passages that answer the query"
        )
        pairs = [_qwen3_reranker_format_pair(instruction, query, document)]

        start_time = time.time()
        scores = _qwen3_reranker_score_pairs(
            model=model,
            tokenizer=tokenizer,
            pairs=pairs,
            device=device,
            token_yes_id=token_yes_id,
            token_no_id=token_no_id,
            max_length=8192,
        )
        inference_time = time.time() - start_time
        score = float(scores[0])

        print(f"  Inference time: {inference_time*1000:.2f}ms")
        print(f"  Reranker score (P(yes)): {score:.4f}")

        # Get peak memory
        peak_memory = torch.cuda.max_memory_allocated(dev) / 1024**3
        peak_reserved = torch.cuda.max_memory_reserved(dev) / 1024**3

        results.update(
            {
                "success": True,
                "load_time_s": load_time,
                "memory_used_gb": memory_used,
                "warmup_memory_gb": warmup_memory,
                "peak_memory_gb": peak_memory,
                "memory_reserved_used_gb": reserved_used,
                "peak_memory_reserved_gb": peak_reserved,
                "inference_time_ms": inference_time * 1000,
                "test_score": score,
            }
        )

        # Clean up and force GC
        import gc

        del model, tokenizer
        torch.cuda.empty_cache()
        gc.collect()

    except Exception as e:
        results["error"] = f"{type(e).__name__}: {e}"
        print(f"  ✗ Error: {results['error']}")

    return results


def test_batch_inference(
    model_id: str,
    model_type: str,
    device: str,
    batch_sizes: List[int],
) -> Dict[str, Any]:
    """
    Test batch inference with various batch sizes.

    Args:
        model_id: HuggingFace model ID
        model_type: Model type (embedding or reranker)
        device: CUDA device
        batch_sizes: List of batch sizes to test

    Returns:
        Batch test results dictionary
    """
    print_section(f"Batch Inference Test: {model_id}")

    results = {
        "model_id": model_id,
        "model_type": model_type,
        "device": device,
        "batch_results": {},
    }

    try:
        if model_type == "embedding" or model_type == "multimodal":
            from sentence_transformers import SentenceTransformer

            model = SentenceTransformer(
                model_id,
                device=device,
                model_kwargs={
                    "torch_dtype": torch.float16,
                    "attn_implementation": "sdpa",
                },
            )

            for batch_size in batch_sizes:
                print(f"\nTesting batch_size={batch_size}...")

                # Generate test texts
                test_texts = [f"Test sentence number {i}" for i in range(batch_size)]

                # Clear cache and measure
                torch.cuda.empty_cache()
                torch.cuda.reset_peak_memory_stats(device)
                initial_memory = measure_memory(device)
                initial_reserved = torch.cuda.memory_reserved(device) / 1024**3

                # Inference
                start_time = time.time()
                embeddings = model.encode(test_texts, batch_size=batch_size)
                if hasattr(embeddings, "cpu"):
                    embeddings = embeddings.cpu().numpy()
                if not isinstance(embeddings, np.ndarray):
                    embeddings = np.array(embeddings)
                inference_time = time.time() - start_time

                peak_memory = torch.cuda.max_memory_allocated(device) / 1024**3
                peak_reserved = torch.cuda.max_memory_reserved(device) / 1024**3
                memory_used = peak_memory - initial_memory
                reserved_used = peak_reserved - initial_reserved

                throughput = batch_size / inference_time

                print(f"  Time: {inference_time:.3f}s")
                print(f"  Throughput: {throughput:.1f} texts/sec")
                print(f"  Memory used: {memory_used:.2f} GB (allocated)")
                print(f"  Memory reserved: {reserved_used:.2f} GB (delta)")
                print(f"  Output shape: {embeddings.shape}")

                results["batch_results"][batch_size] = {
                    "inference_time_s": inference_time,
                    "throughput_texts_per_sec": throughput,
                    "memory_used_gb": memory_used,
                    "memory_reserved_used_gb": reserved_used,
                    "output_shape": list(embeddings.shape),
                }

            del model

        elif model_type == "reranker":
            from transformers import AutoModelForCausalLM, AutoTokenizer

            tokenizer = AutoTokenizer.from_pretrained(
                model_id,
                padding_side="left",
                trust_remote_code=True,
            )
            if tokenizer.pad_token is None and tokenizer.eos_token is not None:
                tokenizer.pad_token = tokenizer.eos_token
            if (
                getattr(tokenizer, "pad_token_id", None) is None
                and tokenizer.eos_token_id is not None
            ):
                tokenizer.pad_token_id = tokenizer.eos_token_id

            yes_ids = tokenizer("yes", add_special_tokens=False).input_ids
            no_ids = tokenizer("no", add_special_tokens=False).input_ids
            if len(yes_ids) != 1 or len(no_ids) != 1:
                raise RuntimeError(
                    f'Expected "yes"/"no" to be single tokens, got yes={yes_ids}, no={no_ids}'
                )
            token_yes_id = yes_ids[0]
            token_no_id = no_ids[0]

            model = AutoModelForCausalLM.from_pretrained(
                model_id,
                torch_dtype=torch.float16,
                attn_implementation="sdpa",
                trust_remote_code=True,
            ).to(device)
            model.eval()
            if (
                getattr(model.config, "pad_token_id", None) is None
                and getattr(tokenizer, "pad_token_id", None) is not None
            ):
                model.config.pad_token_id = tokenizer.pad_token_id

            query = "What is machine learning?"
            instruction = "Given a web search query, retrieve relevant passages that answer the query"

            for batch_size in batch_sizes:
                print(f"\nTesting batch_size={batch_size}...")

                # Generate test documents
                documents = [
                    f"Document {i} about machine learning and AI."
                    for i in range(batch_size)
                ]

                # Clear cache and measure
                torch.cuda.empty_cache()
                torch.cuda.reset_peak_memory_stats(device)
                initial_memory = measure_memory(device)
                initial_reserved = torch.cuda.memory_reserved(device) / 1024**3

                # True batched inference
                start_time = time.time()
                pairs = [
                    _qwen3_reranker_format_pair(instruction, query, doc)
                    for doc in documents
                ]
                scores = _qwen3_reranker_score_pairs(
                    model=model,
                    tokenizer=tokenizer,
                    pairs=pairs,
                    device=device,
                    token_yes_id=token_yes_id,
                    token_no_id=token_no_id,
                    max_length=8192,
                )
                inference_time = time.time() - start_time

                peak_memory = torch.cuda.max_memory_allocated(device) / 1024**3
                peak_reserved = torch.cuda.max_memory_reserved(device) / 1024**3
                memory_used = peak_memory - initial_memory
                reserved_used = peak_reserved - initial_reserved

                throughput = batch_size / inference_time

                print(f"  Time: {inference_time:.3f}s")
                print(f"  Throughput: {throughput:.1f} docs/sec")
                print(f"  Memory used: {memory_used:.2f} GB (allocated)")
                print(f"  Memory reserved: {reserved_used:.2f} GB (delta)")
                print(f"  Scores sample: {scores[:3]}...")

                results["batch_results"][batch_size] = {
                    "inference_time_s": inference_time,
                    "throughput_docs_per_sec": throughput,
                    "memory_used_gb": memory_used,
                    "memory_reserved_used_gb": reserved_used,
                    "num_scores": len(scores),
                }

            del model, tokenizer

        torch.cuda.empty_cache()
        results["success"] = True

    except Exception as e:
        results["error"] = f"{type(e).__name__}: {e}"
        print(f"\n✗ Batch test failed: {results['error']}")

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Verify local embedding/reranker model loading and performance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--model",
        type=str,
        choices=list(MODEL_CONFIGS.keys()),
        help="Model to verify",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Verify all models",
    )
    parser.add_argument(
        "--compare-dtypes",
        action="store_true",
        help="Compare FP16 vs FP32 performance",
    )
    parser.add_argument(
        "--compare-attn",
        action="store_true",
        help="Compare eager vs sdpa attention",
    )
    parser.add_argument(
        "--test-batch",
        action="store_true",
        help="Test batch inference with various batch sizes",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="model_verification_report.json",
        help="Output JSON report file",
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.model and not args.all:
        parser.error("Either --model or --all must be specified")

    # Check CUDA
    if not torch.cuda.is_available():
        print("✗ CUDA not available")
        sys.exit(1)

    print(f"CUDA available: {torch.cuda.device_count()} GPU(s)")

    # Determine models to test
    if args.all:
        models_to_test = list(MODEL_CONFIGS.keys())
    else:
        models_to_test = [args.model]

    # Run tests
    report = {"models": {}}

    for model_id in models_to_test:
        config = MODEL_CONFIGS[model_id]
        model_type = config["type"]
        device = config["device"]

        print_section(f"Testing: {model_id}")

        model_report = {
            "model_id": model_id,
            "model_type": model_type,
            "device": device,
        }

        # Basic test with FP16 + sdpa (default)
        print("\n[Test 1] FP16 + sdpa (default configuration)")
        if model_type == "embedding" or model_type == "multimodal":
            test_func = test_embedding_model
        else:
            test_func = test_reranker_model

        basic_results = test_func(model_id, device, torch.float16, "sdpa")
        model_report["basic_test"] = basic_results

        # Compare dtypes if requested
        if args.compare_dtypes:
            print("\n[Test 2] FP32 comparison")
            fp32_results = test_func(model_id, device, torch.float32, "sdpa")
            model_report["fp32_test"] = fp32_results

        # Compare attention if requested
        if args.compare_attn:
            print("\n[Test 3] Eager attention comparison")
            eager_results = test_func(model_id, device, torch.float16, "eager")
            model_report["eager_test"] = eager_results

        # Batch inference test if requested
        if args.test_batch:
            # Extra cleanup between tests
            import gc as _gc

            torch.cuda.empty_cache()
            _gc.collect()
            batch_results = test_batch_inference(
                model_id,
                model_type,
                device,
                config["test_batch_sizes"],
            )
            model_report["batch_test"] = batch_results

        report["models"][model_id] = model_report

    # Save report
    output_path = Path(args.output)
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)

    print_section("Summary")
    print(f"Report saved to: {output_path}")

    # Print summary
    for model_id, model_report in report["models"].items():
        basic_success = model_report.get("basic_test", {}).get("success", False)
        status = "✓ PASS" if basic_success else "✗ FAIL"
        print(f"{status} {model_id}")


if __name__ == "__main__":
    main()
