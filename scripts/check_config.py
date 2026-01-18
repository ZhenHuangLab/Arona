#!/usr/bin/env python3
"""
Configuration Validation Script

Checks backend configuration and environment variables.
"""

import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load environment from .env (preferred) or .env.backend (legacy)
from dotenv import load_dotenv

env_file = None
for env_name in (".env", ".env.backend"):
    candidate = PROJECT_ROOT / env_name
    if candidate.exists():
        env_file = candidate
        break

if env_file is not None:
    load_dotenv(dotenv_path=env_file, override=False)
    print(f"✓ Loaded environment from {env_file}\n")
else:
    print("⚠ Warning: No .env or .env.backend found; using current environment\n")

from backend.config import BackendConfig


def print_section(title: str):
    """Print a section header."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print("=" * 60)


def check_config():
    """Validate and display backend configuration."""

    try:
        config = BackendConfig.from_env()
    except Exception as e:
        print(f"❌ Error loading configuration: {e}")
        return False

    # LLM Configuration
    print_section("LLM Configuration")
    print(f"Provider:    {config.llm.provider.value}")
    print(f"Model:       {config.llm.model_name}")
    print(f"Base URL:    {config.llm.base_url or 'Default'}")
    print(f"API Key:     {'Set' if config.llm.api_key else 'Not set'}")
    print(f"Temperature: {config.llm.temperature}")
    print(f"Max Tokens:  {config.llm.max_tokens or 'Default'}")

    # Embedding Configuration
    print_section("Embedding Configuration")
    print(f"Provider:    {config.embedding.provider.value}")
    print(f"Model:       {config.embedding.model_name}")
    print(f"Base URL:    {config.embedding.base_url or 'Default'}")
    print(f"API Key:     {'Set' if config.embedding.api_key else 'Not set'}")
    print(f"Dimension:   {config.embedding.embedding_dim}")

    # Vision Configuration
    print_section("Vision Configuration")
    if config.vision:
        print(f"Provider:    {config.vision.provider.value}")
        print(f"Model:       {config.vision.model_name}")
        print(f"Base URL:    {config.vision.base_url or 'Default'}")
        print(f"API Key:     {'Set' if config.vision.api_key else 'Not set'}")
    else:
        print("Not configured (optional)")

    # Reranker Configuration
    print_section("Reranker Configuration")
    if config.reranker and config.reranker.enabled:
        print("Enabled:     Yes")
        print(f"Provider:    {config.reranker.provider}")

        if config.reranker.provider == "api":
            print(f"Model:       {config.reranker.model_name or 'Not set'}")
            print(f"Base URL:    {config.reranker.base_url or 'Auto-detected'}")
            print(f"API Key:     {'Set' if config.reranker.api_key else 'Not set'}")
            print(f"Batch Size:  {config.reranker.batch_size}")
        else:
            # local CPU or local GPU (device=cuda:*)
            print(f"Model:       {config.reranker.model_name or 'Not set'}")
            print(f"Model Path:  {config.reranker.model_path or 'Not set'}")
            print(f"Device:      {config.reranker.device or 'cpu'}")
            print(f"DType:       {config.reranker.dtype}")
            print(f"Batch Size:  {config.reranker.batch_size}")
            print(f"Max Length:  {config.reranker.max_length}")
    else:
        print("Disabled")

    # Storage Configuration
    print_section("Storage Configuration")
    print(f"Working Dir: {config.working_dir}")
    print(f"Upload Dir:  {config.upload_dir}")

    working_path = Path(config.working_dir)
    upload_path = Path(config.upload_dir)

    if working_path.exists():
        print("  ✓ Working directory exists")
    else:
        print("  ⚠ Working directory will be created on startup")

    if upload_path.exists():
        print("  ✓ Upload directory exists")
    else:
        print("  ⚠ Upload directory will be created on startup")

    # RAGAnything Configuration
    print_section("RAGAnything Configuration")
    print(f"Parser:              {config.parser}")
    print(f"Image Processing:    {config.enable_image_processing}")
    print(f"Table Processing:    {config.enable_table_processing}")
    print(f"Equation Processing: {config.enable_equation_processing}")

    # API Server Configuration
    print_section("API Server Configuration")
    print(f"Host:         {config.host}")
    print(f"Port:         {config.port}")
    print(f"CORS Origins: {', '.join(config.cors_origins)}")

    # HuggingFace Environment
    print_section("HuggingFace Environment")
    hf_home = os.getenv("HF_HOME")
    hf_hub_cache = os.getenv("HF_HUB_CACHE")
    hf_endpoint = os.getenv("HF_ENDPOINT")
    mineru_source = os.getenv("MINERU_MODEL_SOURCE")

    print(f"HF_HOME:             {hf_home or 'Not set (will use default)'}")
    print(f"HF_HUB_CACHE:        {hf_hub_cache or 'Not set (will use default)'}")
    print(f"HF_ENDPOINT:         {hf_endpoint or 'Not set (will use default)'}")
    print(f"MINERU_MODEL_SOURCE: {mineru_source or 'Not set (will use default)'}")

    if hf_home:
        hf_home_path = Path(hf_home)
        if hf_home_path.exists():
            print("  ✓ HF_HOME directory exists")
        else:
            print(f"  ⚠ HF_HOME directory does not exist: {hf_home}")

    # Validation Summary
    print_section("Validation Summary")

    issues = []
    warnings = []

    # Check required fields
    if not config.llm.model_name:
        issues.append("LLM model name not set")

    if not config.embedding.model_name:
        issues.append("Embedding model name not set")

    # Embedding dim is required for API-based embedding. Local GPU providers may omit it.
    is_local_gpu_embedding = config.embedding.provider.value in ["local_gpu"] or (
        config.embedding.provider.value == "local"
        and config.embedding.base_url is None
        and str(config.embedding.extra_params.get("device", "")).startswith("cuda")
    )
    if not is_local_gpu_embedding and not config.embedding.embedding_dim:
        issues.append("Embedding dimension not set")

    # Check API keys for API providers
    if config.llm.provider.value in ["openai", "azure", "anthropic"]:
        if not config.llm.api_key:
            warnings.append(f"LLM API key not set for {config.llm.provider.value}")

    if config.embedding.provider.value in ["openai", "azure"]:
        if not config.embedding.api_key:
            warnings.append(
                f"Embedding API key not set for {config.embedding.provider.value}"
            )

    if config.reranker and config.reranker.enabled:
        if config.reranker.provider == "api":
            if not config.reranker.api_key:
                warnings.append("Reranker API key not set")
            if not config.reranker.model_name:
                issues.append("Reranker model name not set")
        else:
            is_local_gpu_reranker = bool(
                config.reranker.device and config.reranker.device.startswith("cuda")
            )
            if is_local_gpu_reranker:
                if not config.reranker.model_name:
                    issues.append("Local GPU reranker model name not set")
            else:
                if not config.reranker.model_path:
                    issues.append("Local reranker model path not set")

    # Check parser
    if config.parser not in ["mineru", "docling"]:
        issues.append(f"Invalid parser: {config.parser}")

    # Print results
    if issues:
        print("\n❌ Critical Issues:")
        for issue in issues:
            print(f"  - {issue}")

    if warnings:
        print("\n⚠ Warnings:")
        for warning in warnings:
            print(f"  - {warning}")

    if not issues and not warnings:
        print("\n✓ Configuration is valid!")
        return True
    elif not issues:
        print("\n⚠ Configuration has warnings but should work")
        return True
    else:
        print("\n❌ Configuration has critical issues")
        return False


def main():
    """Main entry point."""
    print("RAG-Anything Configuration Checker")
    print("=" * 60)

    success = check_config()

    print("\n" + "=" * 60)
    if success:
        print("✓ Configuration check completed successfully")
        sys.exit(0)
    else:
        print("❌ Configuration check failed")
        print("\nPlease fix the issues above and try again.")
        print("See docs/TROUBLESHOOTING.md for help.")
        sys.exit(1)


if __name__ == "__main__":
    main()
