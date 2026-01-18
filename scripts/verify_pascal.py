#!/usr/bin/env python3
"""
Pascal Architecture Compatibility Verification Script

Verifies that the system meets the requirements for running local embedding
models on NVIDIA Pascal architecture (GTX 1080 Ti) GPUs.

Checks:
1. GPU architecture is Pascal (Compute Capability 6.1)
2. FP16 computation works correctly
3. SDPA (Scaled Dot Product Attention) is available
4. BF16 is not supported (expected for Pascal)
5. Memory allocation and deallocation work properly

Exit codes:
0 - All checks passed
1 - Critical failure (GPU not available, wrong architecture, etc.)
2 - Warning (some features unavailable but system usable)
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def print_header(title: str):
    """Print a section header."""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print("=" * 70)


def check_pytorch_cuda():
    """Check if PyTorch with CUDA is available."""
    print_header("PyTorch and CUDA Check")

    try:
        import torch

        print(f"✓ PyTorch version: {torch.__version__}")
        print(f"✓ CUDA version: {torch.version.cuda}")

        if not torch.cuda.is_available():
            print("✗ CUDA is not available")
            return False

        print("✓ CUDA is available")
        print(f"✓ GPU count: {torch.cuda.device_count()}")

        return True

    except ImportError:
        print("✗ PyTorch is not installed")
        print("\nInstallation instructions:")
        print(
            "  pip install torch==2.3.1 torchvision==0.18.1 triton==2.3.1 --index-url https://download.pytorch.org/whl/cu118"
        )
        return False


def check_gpu_architecture():
    """Check GPU architecture and compute capability."""
    print_header("GPU Architecture Check")

    import torch

    if torch.cuda.device_count() == 0:
        print("✗ No CUDA GPUs detected")
        return False

    all_pascal = True
    for i in range(torch.cuda.device_count()):
        name = torch.cuda.get_device_name(i)
        capability = torch.cuda.get_device_capability(i)
        memory_gb = torch.cuda.get_device_properties(i).total_memory / (1024**3)

        print(f"\nGPU {i}:")
        print(f"  Name: {name}")
        print(f"  Compute Capability: {capability[0]}.{capability[1]}")
        print(f"  Total Memory: {memory_gb:.2f} GB")

        # Check if Pascal (6.x)
        if capability[0] == 6:
            print("  ✓ Pascal architecture detected")
        else:
            print(
                f"  ⚠ Not Pascal architecture (expected 6.x, got {capability[0]}.{capability[1]})"
            )
            all_pascal = False

    return all_pascal


def check_fp16_support():
    """Check FP16 computation support."""
    print_header("FP16 Support Check")

    import torch

    try:
        device = torch.device("cuda:0")

        # Create FP16 tensors
        a = torch.randn(1000, 1000, dtype=torch.float16, device=device)
        b = torch.randn(1000, 1000, dtype=torch.float16, device=device)

        # Perform FP16 matrix multiplication
        c = torch.matmul(a, b)

        print("✓ FP16 matrix multiplication successful")
        print(f"  Result shape: {c.shape}")
        print(f"  Result dtype: {c.dtype}")

        # Check for NaN or Inf
        if torch.isnan(c).any() or torch.isinf(c).any():
            print("✗ FP16 computation produced NaN or Inf values")
            return False

        print("✓ FP16 computation produces valid results")

        # Note about Pascal FP16 performance
        print("\nNote: Pascal architecture (GTX 1080 Ti) does not have Tensor Cores.")
        print("      FP16 performance is similar to FP32, but saves memory.")

        return True

    except Exception as e:
        print(f"✗ FP16 computation failed: {e}")
        return False


def check_sdpa_support():
    """Check Scaled Dot Product Attention (SDPA) support."""
    print_header("SDPA (Scaled Dot Product Attention) Check")

    import torch
    import torch.nn.functional as F

    # Check if SDPA function exists
    if not hasattr(F, "scaled_dot_product_attention"):
        print("✗ torch.nn.functional.scaled_dot_product_attention not found")
        print("  This function was added in PyTorch 2.0+")
        return False

    print("✓ torch.nn.functional.scaled_dot_product_attention is available")

    try:
        device = torch.device("cuda:0")

        # Create sample tensors for SDPA
        batch_size, num_heads, seq_len, head_dim = 2, 8, 128, 64

        query = torch.randn(
            batch_size, num_heads, seq_len, head_dim, dtype=torch.float16, device=device
        )
        key = torch.randn(
            batch_size, num_heads, seq_len, head_dim, dtype=torch.float16, device=device
        )
        value = torch.randn(
            batch_size, num_heads, seq_len, head_dim, dtype=torch.float16, device=device
        )

        # Run SDPA
        output = F.scaled_dot_product_attention(query, key, value)

        print("✓ SDPA computation successful")
        print(f"  Input shape: {query.shape}")
        print(f"  Output shape: {output.shape}")

        # Check for NaN or Inf
        if torch.isnan(output).any() or torch.isinf(output).any():
            print("✗ SDPA produced NaN or Inf values")
            return False

        print("✓ SDPA produces valid results")

        print("\nNote: Pascal does not support Flash Attention 2.")
        print("      Using 'sdpa' or 'eager' attention implementation is recommended.")

        return True

    except Exception as e:
        print(f"✗ SDPA computation failed: {e}")
        return False


def check_bf16_support():
    """Check BF16 support (should NOT be supported on Pascal)."""
    print_header("BF16 Support Check (Expected: NOT supported)")

    import torch

    try:
        device = torch.device("cuda:0")

        # Try to create BF16 tensor
        a = torch.randn(100, 100, dtype=torch.bfloat16, device=device)
        b = torch.randn(100, 100, dtype=torch.bfloat16, device=device)
        torch.matmul(a, b)

        print("⚠ BF16 computation succeeded (unexpected for Pascal)")
        print("  Pascal architecture typically does not support BF16 efficiently")
        print("  Performance may be poor. Use FP16 instead.")

        return True  # Not a failure, just unexpected

    except Exception as e:
        print("✓ BF16 is not supported (expected for Pascal)")
        print(f"  Error: {e}")
        return True  # This is expected


def check_memory_allocation():
    """Check GPU memory allocation and deallocation."""
    print_header("GPU Memory Allocation Check")

    import torch

    try:
        device = torch.device("cuda:0")

        # Get initial memory stats
        torch.cuda.reset_peak_memory_stats(device)
        initial_allocated = torch.cuda.memory_allocated(device) / (1024**3)

        print(f"Initial allocated memory: {initial_allocated:.2f} GB")

        # Allocate a large tensor (4GB)
        size = 1024 * 1024 * 1024  # 1B float32 elements = 4GB
        tensor = torch.randn(size, dtype=torch.float32, device=device)

        allocated = torch.cuda.memory_allocated(device) / (1024**3)
        print(f"After allocation: {allocated:.2f} GB")

        # Free the tensor
        del tensor
        torch.cuda.empty_cache()

        final_allocated = torch.cuda.memory_allocated(device) / (1024**3)
        print(f"After deallocation: {final_allocated:.2f} GB")

        print("✓ Memory allocation and deallocation successful")

        return True

    except Exception as e:
        print(f"✗ Memory allocation failed: {e}")
        return False


def main():
    """Run all verification checks."""
    print("\n" + "=" * 70)
    print("  Pascal Architecture Compatibility Verification")
    print("  Target: NVIDIA GTX 1080 Ti (Compute Capability 6.1)")
    print("=" * 70)

    checks = [
        ("PyTorch and CUDA", check_pytorch_cuda),
        ("GPU Architecture", check_gpu_architecture),
        ("FP16 Support", check_fp16_support),
        ("SDPA Support", check_sdpa_support),
        ("BF16 Support", check_bf16_support),
        ("Memory Allocation", check_memory_allocation),
    ]

    results = {}
    for name, check_func in checks:
        try:
            results[name] = check_func()
        except Exception as e:
            print(f"\n✗ Unexpected error in {name}: {e}")
            results[name] = False

    # Print summary
    print_header("Verification Summary")

    all_passed = True
    critical_failed = False

    for name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status:10} {name}")

        if not passed:
            all_passed = False
            # Critical checks
            if name in ["PyTorch and CUDA", "GPU Architecture", "FP16 Support"]:
                critical_failed = True

    print("\n" + "=" * 70)

    if critical_failed:
        print("✗ CRITICAL FAILURE: System does not meet minimum requirements")
        print("\nRecommendations:")
        print("  1. Ensure NVIDIA drivers are installed (nvidia-smi)")
        print("  2. Install PyTorch with CUDA 11.8 support")
        print("  3. Verify GPU is GTX 1080 Ti or similar Pascal architecture")
        return 1
    elif not all_passed:
        print("⚠ WARNING: Some checks failed, but system is usable")
        print("\nRecommendations:")
        print("  1. Use FP16 instead of BF16 for Pascal architecture")
        print("  2. Use 'sdpa' or 'eager' attention implementation")
        print("  3. Avoid Flash Attention 2 (not supported on Pascal)")
        return 2
    else:
        print("✓ ALL CHECKS PASSED")
        print("\nYour system is ready for local embedding deployment!")
        print("\nNext steps:")
        print("  1. Download models: python scripts/download_local_models.py")
        print("  2. Configure .env.backend with EMBEDDING_PROVIDER=local_gpu")
        print("  3. Start backend: bash scripts/start_backend.sh")
        return 0


if __name__ == "__main__":
    sys.exit(main())
