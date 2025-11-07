#!/usr/bin/env python3
"""
GPU Diagnostic Script for MinerU and Docling
Checks GPU availability, CUDA compatibility, and parser configurations
"""

import sys
import subprocess
from pathlib import Path


def print_section(title: str):
    """Print a formatted section header"""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def run_command(cmd: list, description: str) -> tuple[bool, str]:
    """Run a command and return success status and output"""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.returncode == 0, result.stdout + result.stderr
    except Exception as e:
        return False, str(e)


def check_nvidia_gpu():
    """Check NVIDIA GPU availability and details"""
    print_section("1. NVIDIA GPU Detection")
    
    # Check nvidia-smi
    success, output = run_command(["nvidia-smi"], "nvidia-smi")
    if success:
        print("✅ NVIDIA GPU detected")
        print("\nGPU Information:")
        print(output)
        
        # Extract GPU name and VRAM
        for line in output.split('\n'):
            if 'GeForce' in line or 'Tesla' in line or 'Quadro' in line or 'RTX' in line:
                print(f"   GPU Model: {line.strip()}")
    else:
        print("❌ NVIDIA GPU not detected or nvidia-smi not available")
        print(f"   Error: {output}")
        return False
    
    return True


def check_cuda():
    """Check CUDA installation and version"""
    print_section("2. CUDA Installation")
    
    # Check nvcc
    success, output = run_command(["nvcc", "--version"], "nvcc")
    if success:
        print("✅ CUDA Toolkit installed")
        for line in output.split('\n'):
            if 'release' in line.lower():
                print(f"   {line.strip()}")
    else:
        print("⚠️  CUDA Toolkit (nvcc) not found in PATH")
        print("   This is OK if you have CUDA runtime libraries")
    
    # Check PyTorch CUDA
    print("\nPyTorch CUDA Support:")
    try:
        import torch
        print(f"   PyTorch version: {torch.__version__}")
        print(f"   CUDA available: {torch.cuda.is_available()}")
        
        if torch.cuda.is_available():
            print(f"   CUDA version (PyTorch): {torch.version.cuda}")
            print(f"   Number of GPUs: {torch.cuda.device_count()}")
            
            for i in range(torch.cuda.device_count()):
                props = torch.cuda.get_device_properties(i)
                print(f"\n   GPU {i}: {props.name}")
                print(f"      Compute Capability: {props.major}.{props.minor}")
                print(f"      Total Memory: {props.total_memory / 1024**3:.2f} GB")
                
                # Check architecture
                cc = f"{props.major}.{props.minor}"
                arch_name = get_architecture_name(props.major, props.minor)
                print(f"      Architecture: {arch_name}")
                
                # Warn about Volta requirement
                if props.major < 7:
                    print(f"      ⚠️  WARNING: MinerU officially requires Volta (7.0+) or later")
                    print(f"         Your GPU has compute capability {cc} ({arch_name})")
                    print(f"         Some features may not work or may fall back to CPU")
                else:
                    print(f"      ✅ Meets MinerU's Volta (7.0+) requirement")
        else:
            print("   ❌ CUDA not available in PyTorch")
            
    except ImportError:
        print("   ❌ PyTorch not installed")
        return False
    
    return True


def get_architecture_name(major: int, minor: int) -> str:
    """Get NVIDIA architecture name from compute capability"""
    arch_map = {
        3: "Kepler",
        5: "Maxwell",
        6: "Pascal",
        7: "Volta/Turing",
        8: "Ampere",
        9: "Hopper/Ada Lovelace"
    }
    return arch_map.get(major, f"Unknown (CC {major}.{minor})")


def check_mineru_installation():
    """Check MinerU installation and configuration"""
    print_section("3. MinerU Installation")
    
    # Check mineru command
    success, output = run_command(["mineru", "--version"], "mineru")
    if success:
        print("✅ MinerU installed")
        print(f"   Version: {output.strip()}")
    else:
        print("❌ MinerU not installed or not in PATH")
        return False
    
    # Check mineru.json configuration
    config_path = Path("mineru.json")
    if config_path.exists():
        print(f"\n✅ Configuration file found: {config_path}")
        
        import json
        try:
            with open(config_path) as f:
                config = json.load(f)
            
            # Check models directory
            if "models-dir" in config:
                print("\n   Models Directory:")
                for backend, path in config["models-dir"].items():
                    exists = Path(path).exists()
                    status = "✅" if exists else "❌"
                    print(f"      {status} {backend}: {path}")
            
            # Check LLM-aided config
            if "llm-aided-config" in config:
                print("\n   LLM-Aided Configuration:")
                llm_config = config["llm-aided-config"]
                if "title_aided" in llm_config:
                    enabled = llm_config["title_aided"].get("enable", False)
                    status = "Enabled" if enabled else "Disabled"
                    print(f"      Title-Aided: {status}")
                    
        except Exception as e:
            print(f"   ⚠️  Error reading config: {e}")
    else:
        print(f"\n⚠️  Configuration file not found: {config_path}")
    
    return True


def check_docling_installation():
    """Check Docling installation"""
    print_section("4. Docling Installation")
    
    # Check docling command
    success, output = run_command(["docling", "--version"], "docling")
    if success:
        print("✅ Docling installed")
        print(f"   Version: {output.strip()}")
    else:
        print("❌ Docling not installed or not in PATH")
        return False
    
    # Check Docling GPU support
    try:
        from docling.backend.docling_parse_backend import DoclingParseDocumentBackend
        print("\n✅ Docling Python package available")
        print("   Note: Docling supports GPU acceleration via PyTorch")
    except ImportError:
        print("\n⚠️  Docling Python package not found")
    
    return True


def test_mineru_gpu():
    """Test MinerU with GPU"""
    print_section("5. MinerU GPU Test")
    
    print("Testing MinerU with different backends...")
    print("(This requires a test PDF file)")
    
    # Check for test file
    test_files = [
        "test.pdf",
        "examples/test.pdf",
        "uploads/test.pdf"
    ]
    
    test_file = None
    for f in test_files:
        if Path(f).exists():
            test_file = f
            break
    
    if not test_file:
        print("\n⚠️  No test PDF file found")
        print("   Create a test.pdf in the current directory to run GPU tests")
        return
    
    print(f"\n✅ Using test file: {test_file}")
    
    # Test pipeline backend
    print("\n   Testing backend='pipeline' with device='cuda:0'...")
    cmd = [
        "mineru",
        "-p", test_file,
        "-o", "/tmp/mineru_gpu_test",
        "-b", "pipeline",
        "-d", "cuda:0"
    ]
    
    success, output = run_command(cmd, "MinerU pipeline test")
    if success:
        print("   ✅ Pipeline backend test successful")
    else:
        print("   ❌ Pipeline backend test failed")
        if "cuda" in output.lower() or "gpu" in output.lower():
            print("   GPU-related error detected:")
            for line in output.split('\n'):
                if 'cuda' in line.lower() or 'gpu' in line.lower() or 'error' in line.lower():
                    print(f"      {line.strip()}")


def print_recommendations():
    """Print recommendations based on findings"""
    print_section("6. Recommendations")
    
    try:
        import torch
        if torch.cuda.is_available():
            props = torch.cuda.get_device_properties(0)
            cc_major = props.major
            
            if cc_major < 7:
                print("⚠️  Your GPU has compute capability < 7.0 (pre-Volta)")
                print("\nRecommendations:")
                print("   1. MinerU may work but some features might be slower or unavailable")
                print("   2. Try backend='pipeline' with device='cuda:0' first")
                print("   3. If you encounter errors, use device='cpu' as fallback")
                print("   4. Consider upgrading to Ampere (RTX 30xx) or newer for best performance")
                print("\nTo test GPU acceleration:")
                print("   python -m raganything.parser test.pdf --backend pipeline --device cuda:0")
            else:
                print("✅ Your GPU meets MinerU's requirements")
                print("\nRecommendations:")
                print("   1. Use backend='pipeline' with device='cuda:0' for best performance")
                print("   2. Try backend='vlm-transformers' for vision-language model features")
                print("\nTo test GPU acceleration:")
                print("   python -m raganything.parser test.pdf --backend pipeline --device cuda:0")
        else:
            print("❌ CUDA not available")
            print("\nRecommendations:")
            print("   1. Use device='cpu' for MinerU")
            print("   2. Check CUDA installation and PyTorch CUDA support")
            
    except ImportError:
        print("❌ PyTorch not installed")
        print("\nRecommendations:")
        print("   1. Install PyTorch with CUDA support")
        print("   2. Visit: https://pytorch.org/get-started/locally/")


def main():
    """Main diagnostic function"""
    print("\n" + "="*70)
    print("  MinerU & Docling GPU Diagnostic Tool")
    print("="*70)
    
    # Run all checks
    gpu_ok = check_nvidia_gpu()
    cuda_ok = check_cuda()
    mineru_ok = check_mineru_installation()
    docling_ok = check_docling_installation()
    
    if gpu_ok and cuda_ok and mineru_ok:
        test_mineru_gpu()
    
    print_recommendations()
    
    print("\n" + "="*70)
    print("  Diagnostic Complete")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()

