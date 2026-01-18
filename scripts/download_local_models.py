#!/usr/bin/env python3
"""
Download and verify local embedding/reranker models for Task 7.

This script downloads Qwen3-Embedding-4B, Qwen3-Reranker-4B, and optionally
GME-Qwen2-VL-2B-Instruct models from HuggingFace, verifies FP16 loading,
tests simple inference, and measures GPU memory usage.

Usage:
    # Download a specific model
    python scripts/download_local_models.py --model Qwen/Qwen3-Embedding-4B --device cuda:0

    # Download all Plan B models
    python scripts/download_local_models.py --all

    # Download without verification (faster)
    python scripts/download_local_models.py --model Qwen/Qwen3-Embedding-4B --no-verify

Environment Variables:
    HF_HOME: HuggingFace cache directory (default: ~/.huggingface)
    HF_HUB_CACHE: HuggingFace Hub cache directory (default: $HF_HOME/hub)
    HF_ENDPOINT: HuggingFace mirror endpoint (e.g., https://hf-mirror.com)
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Supported models for Plan B
SUPPORTED_MODELS = {
    "Qwen/Qwen3-Embedding-4B": {
        "type": "embedding",
        "embedding_dim": 2560,
        "default_device": "cuda:0",
        "expected_vram_gb": 8.0,
    },
    "Qwen/Qwen3-Reranker-4B": {
        "type": "reranker",
        "default_device": "cuda:1",
        "expected_vram_gb": 8.0,
    },
    "Alibaba-NLP/gme-Qwen2-VL-2B-Instruct": {
        "type": "multimodal",
        "embedding_dim": 1536,
        "default_device": "cuda:2",
        "expected_vram_gb": 4.0,
    },
}


def print_section(title: str) -> None:
    """Print a formatted section header."""
    print(f"\n{'=' * 80}")
    print(f"  {title}")
    print("=" * 80)


def check_environment() -> Dict[str, str]:
    """Check and display HuggingFace environment configuration."""
    print_section("Environment Configuration")

    hf_home = os.environ.get("HF_HOME", os.path.expanduser("~/.huggingface"))
    hf_hub_cache = os.environ.get("HF_HUB_CACHE", os.path.join(hf_home, "hub"))
    hf_endpoint = os.environ.get("HF_ENDPOINT", "")

    print(f"HF_HOME: {hf_home}")
    print(f"HF_HUB_CACHE: {hf_hub_cache}")
    if hf_endpoint:
        print(f"HF_ENDPOINT: {hf_endpoint} (using mirror)")
    else:
        print("HF_ENDPOINT: (not set, using default HuggingFace)")

    # Ensure cache directories exist
    os.makedirs(hf_home, exist_ok=True)
    os.makedirs(hf_hub_cache, exist_ok=True)

    return {
        "hf_home": hf_home,
        "hf_hub_cache": hf_hub_cache,
        "hf_endpoint": hf_endpoint,
    }


def check_cuda_available() -> bool:
    """Check if CUDA is available."""
    try:
        import torch

        cuda_available = torch.cuda.is_available()
        if cuda_available:
            print(f"✓ CUDA available: {torch.cuda.device_count()} GPU(s)")
            for i in range(torch.cuda.device_count()):
                props = torch.cuda.get_device_properties(i)
                print(
                    f"  GPU {i}: {props.name} ({props.total_memory / 1024**3:.1f} GB)"
                )
        else:
            print("✗ CUDA not available")
        return cuda_available
    except ImportError:
        print("✗ PyTorch not installed")
        return False


def download_model(model_id: str, cache_dir: str) -> Optional[str]:
    """
    Download a model from HuggingFace using snapshot_download.

    Args:
        model_id: HuggingFace model ID (e.g., "Qwen/Qwen3-Embedding-4B")
        cache_dir: Cache directory for downloaded models

    Returns:
        Path to downloaded model directory, or None if failed
    """
    print_section(f"Downloading Model: {model_id}")

    try:
        from huggingface_hub import snapshot_download

        print(f"Downloading {model_id} to {cache_dir}...")
        print("This may take a while depending on your network speed...")

        model_path = snapshot_download(
            repo_id=model_id,
            repo_type="model",
            cache_dir=cache_dir,
            resume_download=True,
        )

        print(f"✓ Model downloaded successfully to: {model_path}")
        return model_path

    except ImportError:
        print("✗ huggingface_hub not installed. Please install it:")
        print("  pip install huggingface_hub")
        return None
    except Exception as e:
        print(f"✗ Download failed: {type(e).__name__}: {e}")
        print("\n[HELP] Troubleshooting:")
        print("  1. Check your internet connection")
        print(
            "  2. Try using a HuggingFace mirror: export HF_ENDPOINT=https://hf-mirror.com"
        )
        print(f"  3. Manually download from: https://huggingface.co/{model_id}")
        return None


def verify_model_loading(
    model_id: str,
    model_info: Dict[str, Any],
    device: str = "cuda:0",
) -> Dict[str, Any]:
    """
    Verify model can be loaded in FP16 and perform simple inference.

    Args:
        model_id: HuggingFace model ID
        model_info: Model metadata from SUPPORTED_MODELS
        device: CUDA device to use

    Returns:
        Verification results dictionary
    """
    print_section(f"Verifying Model: {model_id}")

    results = {
        "model_id": model_id,
        "device": device,
        "success": False,
        "error": None,
    }

    try:
        import torch

        if not torch.cuda.is_available():
            results["error"] = "CUDA not available"
            print(f"✗ {results['error']}")
            return results

        # Clear CUDA cache before loading
        torch.cuda.empty_cache()
        initial_memory = torch.cuda.memory_allocated(device) / 1024**3
        initial_reserved = torch.cuda.memory_reserved(device) / 1024**3

        model_type = model_info["type"]
        print(f"Model type: {model_type}")
        print(f"Loading to device: {device}")
        print(f"Initial GPU memory: {initial_memory:.2f} GB")

        if model_type == "embedding" or model_type == "multimodal":
            # Load with SentenceTransformer
            from sentence_transformers import SentenceTransformer

            print("Loading with SentenceTransformer...")
            model = SentenceTransformer(
                model_id,
                device=device,
                model_kwargs={
                    "torch_dtype": torch.float16,
                    "attn_implementation": "sdpa",  # Pascal-compatible
                },
            )

            # Verify dtype and attention backend if available
            if hasattr(model[0], "auto_model"):
                actual_dtype = model[0].auto_model.dtype
                print(f"Model dtype: {actual_dtype}")
                if actual_dtype != torch.float16:
                    print(f"⚠ Warning: Expected float16, got {actual_dtype}")
                attn_backend = getattr(
                    getattr(model[0].auto_model, "config", None),
                    "attn_implementation",
                    None,
                )
                if attn_backend:
                    print(f"Attention backend: {attn_backend}")

            # Test simple inference
            print("Testing inference...")
            test_text = "This is a test sentence for embedding."
            embedding = model.encode(test_text)
            if hasattr(embedding, "cpu"):
                embedding = embedding.cpu().numpy()
            import numpy as np

            if not isinstance(embedding, np.ndarray):
                embedding = np.array(embedding)

            expected_dim = model_info.get("embedding_dim")
            actual_dim = embedding.shape[0]
            print(f"Embedding dimension: {actual_dim}")

            if expected_dim and actual_dim != expected_dim:
                print(f"⚠ Warning: Expected {expected_dim}D, got {actual_dim}D")

            results["embedding_dim"] = actual_dim

        elif model_type == "reranker":
            # Qwen3-Reranker is a CausalLM model. Scores are derived from the
            # next-token probability of "yes" vs "no" given the official prompt.
            from transformers import AutoModelForCausalLM, AutoTokenizer

            print("Loading with AutoModelForCausalLM...")
            tokenizer = AutoTokenizer.from_pretrained(
                model_id,
                padding_side="left",
                trust_remote_code=True,
            )
            # Ensure pad token exists for batched padding
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token
            if tokenizer.pad_token_id is None:
                tokenizer.pad_token_id = tokenizer.eos_token_id

            # Resolve yes/no token IDs (must be single tokens)
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
                attn_implementation="sdpa",  # Pascal-compatible
                trust_remote_code=True,
            ).to(device)
            model.eval()

            # Align pad token id in model config if needed
            if getattr(model.config, "pad_token_id", None) is None:
                model.config.pad_token_id = tokenizer.pad_token_id

            print(f"Model dtype: {model.dtype}")
            attn_backend = getattr(
                getattr(model, "config", None), "attn_implementation", None
            )
            if attn_backend:
                print(f"Attention backend: {attn_backend}")

            # Test simple inference
            print("Testing inference...")
            query = "What is the capital of France?"
            document = "Paris is the capital and largest city of France."

            instruction = "Given a web search query, retrieve relevant passages that answer the query"
            pair = (
                f"<Instruct>: {instruction}\n"
                f"<Query>: {query}\n"
                f"<Document>: {document}"
            )

            prefix = (
                "<|im_start|>system\n"
                "Judge whether the Document meets the requirements based on the Query and the Instruct provided. "
                'Note that the answer can only be "yes" or "no".'
                "<|im_end|>\n<|im_start|>user\n"
            )
            suffix = "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"

            prefix_tokens = tokenizer.encode(prefix, add_special_tokens=False)
            suffix_tokens = tokenizer.encode(suffix, add_special_tokens=False)
            max_length = 8192
            max_pair_len = max_length - len(prefix_tokens) - len(suffix_tokens)
            if max_pair_len <= 0:
                raise RuntimeError("Reranker template too long for max_length=8192")

            enc = tokenizer(
                [pair],
                padding=False,
                truncation="longest_first",
                return_attention_mask=False,
                max_length=max_pair_len,
                add_special_tokens=False,
            )
            enc["input_ids"] = [prefix_tokens + enc["input_ids"][0] + suffix_tokens]
            inputs = tokenizer.pad(enc, padding=True, return_tensors="pt")
            inputs = {k: v.to(device) for k, v in inputs.items() if hasattr(v, "to")}

            with torch.no_grad():
                outputs = model(**inputs)
                next_logits = outputs.logits[:, -1, :]
                yes_logits = next_logits[:, token_yes_id]
                no_logits = next_logits[:, token_no_id]
                probs_yes = torch.softmax(
                    torch.stack([no_logits, yes_logits], dim=1).float(), dim=1
                )[:, 1]
                score = float(probs_yes[0].item())

            print(f"Reranker score (P(yes)): {score:.4f}")
            results["test_score"] = score

        else:
            results["error"] = f"Unknown model type: {model_type}"
            print(f"✗ {results['error']}")
            return results

        # Measure GPU memory after loading
        loaded_memory = torch.cuda.memory_allocated(device) / 1024**3
        reserved_loaded = torch.cuda.memory_reserved(device) / 1024**3
        memory_used = loaded_memory - initial_memory
        reserved_used = reserved_loaded - initial_reserved

        print(f"GPU memory after loading: {loaded_memory:.2f} GB (allocated)")
        print(f"Memory used by model: {memory_used:.2f} GB (allocated)")
        print(f"Memory reserved delta: {reserved_used:.2f} GB")

        expected_vram = model_info.get("expected_vram_gb", 0)
        if expected_vram > 0:
            if memory_used > expected_vram * 1.2:
                print(
                    f"⚠ Warning: Memory usage ({memory_used:.2f} GB) exceeds expected ({expected_vram:.2f} GB)"
                )
            elif memory_used < expected_vram * 0.8:
                print(
                    f"⚠ Warning: Memory usage ({memory_used:.2f} GB) is lower than expected ({expected_vram:.2f} GB)"
                )

        results["memory_used_gb"] = memory_used
        results["memory_reserved_used_gb"] = reserved_used
        results["success"] = True
        print("✓ Verification passed")

    except ImportError as e:
        results["error"] = f"Missing dependency: {e}"
        print(f"✗ {results['error']}")
        print("\n[HELP] Install required packages:")
        print("  pip install torch sentence-transformers transformers accelerate")
    except Exception as e:
        results["error"] = f"{type(e).__name__}: {e}"
        print(f"✗ Verification failed: {results['error']}")

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Download and verify local embedding/reranker models",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--model",
        type=str,
        choices=list(SUPPORTED_MODELS.keys()),
        help="Model to download (e.g., Qwen/Qwen3-Embedding-4B)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Download all Plan B models (Qwen3-Embedding-4B and Qwen3-Reranker-4B)",
    )
    parser.add_argument(
        "--device",
        type=str,
        help="CUDA device to use for verification (e.g., cuda:0). If not specified, uses model's default device.",
    )
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Skip model loading verification (faster, download only)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="model_download_report.json",
        help="Output JSON report file (default: model_download_report.json)",
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.model and not args.all:
        parser.error("Either --model or --all must be specified")

    # Check environment
    env_config = check_environment()

    # Check CUDA availability
    if not args.no_verify:
        if not check_cuda_available():
            print("\n✗ CUDA not available. Use --no-verify to skip verification.")
            sys.exit(1)

    # Determine models to download
    if args.all:
        models_to_download = [
            "Qwen/Qwen3-Embedding-4B",
            "Qwen/Qwen3-Reranker-4B",
        ]
    else:
        models_to_download = [args.model]

    # Download and verify models
    report = {
        "environment": env_config,
        "models": {},
    }

    for model_id in models_to_download:
        model_info = SUPPORTED_MODELS[model_id]
        device = args.device or model_info["default_device"]

        # Download model
        model_path = download_model(model_id, env_config["hf_hub_cache"])

        model_report = {
            "model_id": model_id,
            "model_path": model_path,
            "download_success": model_path is not None,
        }

        # Verify model if requested
        if not args.no_verify and model_path:
            verification_results = verify_model_loading(model_id, model_info, device)
            model_report["verification"] = verification_results

        report["models"][model_id] = model_report

    # Save report
    output_path = Path(args.output)
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)

    print_section("Summary")
    print(f"Report saved to: {output_path}")

    # Print summary
    success_count = sum(1 for m in report["models"].values() if m["download_success"])
    total_count = len(report["models"])
    print(f"Downloaded: {success_count}/{total_count} models")

    if not args.no_verify:
        verified_count = sum(
            1
            for m in report["models"].values()
            if m.get("verification", {}).get("success", False)
        )
        print(f"Verified: {verified_count}/{total_count} models")

    # Exit with error if any download failed
    if success_count < total_count:
        sys.exit(1)


if __name__ == "__main__":
    main()
