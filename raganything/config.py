"""Configuration classes for RAGAnything.

Contains configuration dataclasses with environment variable support.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List
import warnings

from lightrag.utils import get_env_value


def _get_ollama_base_url() -> str:
    """Return the Ollama base URL using layered environment fallbacks."""

    # Prefer explicit base URL, then legacy host, finally the local default.
    base_url = get_env_value("OLLAMA_BASE_URL", "", str)
    if not base_url:
        base_url = get_env_value("OLLAMA_HOST", "", str)
    if not base_url:
        return "http://127.0.0.1:11434"
    return base_url


@dataclass
class RAGAnythingConfig:
    """Configuration class for RAGAnything with environment variable support"""

    # Directory Configuration
    # ---
    working_dir: str = field(default=get_env_value("WORKING_DIR", "./rag_storage", str))
    """Directory where RAG storage and cache files are stored."""

    # Parser Configuration
    # ---
    parse_method: str = field(default=get_env_value("PARSE_METHOD", "auto", str))
    """Default parsing method for document parsing: 'auto', 'ocr', or 'txt'."""

    parser_output_dir: str = field(default=get_env_value("OUTPUT_DIR", "./output", str))
    """Default output directory for parsed content."""

    parser: str = field(default=get_env_value("PARSER", "mineru", str))
    """Parser selection: 'mineru' or 'docling'."""

    display_content_stats: bool = field(
        default=get_env_value("DISPLAY_CONTENT_STATS", True, bool)
    )
    """Whether to display content statistics during parsing."""

    # Multimodal Processing Configuration
    # ---
    enable_image_processing: bool = field(
        default=get_env_value("ENABLE_IMAGE_PROCESSING", True, bool)
    )
    """Enable image content processing."""

    enable_table_processing: bool = field(
        default=get_env_value("ENABLE_TABLE_PROCESSING", True, bool)
    )
    """Enable table content processing."""

    enable_equation_processing: bool = field(
        default=get_env_value("ENABLE_EQUATION_PROCESSING", True, bool)
    )
    """Enable equation content processing."""

    # MinerU Configuration
    # ---
    mineru_device: str | None = field(
        default=(get_env_value("MINERU_DEVICE", "", str) or None)
    )
    """Device for MinerU model inference (e.g., 'cpu', 'cuda', 'cuda:1')."""

    mineru_vram: int | None = field(default=(get_env_value("MINERU_VRAM", 0, int) or None))
    """Upper limit of GPU memory (MiB) for a single MinerU process (pipeline backend)."""

    # Batch Processing Configuration
    # ---
    max_concurrent_files: int = field(
        default=get_env_value("MAX_CONCURRENT_FILES", 1, int)
    )
    """Maximum number of files to process concurrently."""

    supported_file_extensions: List[str] = field(
        default_factory=lambda: get_env_value(
            "SUPPORTED_FILE_EXTENSIONS",
            ".pdf,.jpg,.jpeg,.png,.bmp,.tiff,.tif,.gif,.webp,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.txt,.md",
            str,
        ).split(",")
    )
    """List of supported file extensions for batch processing."""

    recursive_folder_processing: bool = field(
        default=get_env_value("RECURSIVE_FOLDER_PROCESSING", True, bool)
    )
    """Whether to recursively process subfolders in batch mode."""

    # Context Extraction Configuration
    # ---
    context_window: int = field(default=get_env_value("CONTEXT_WINDOW", 1, int))
    """Number of pages/chunks to include before and after current item for context."""

    context_mode: str = field(default=get_env_value("CONTEXT_MODE", "page", str))
    """Context extraction mode: 'page' for page-based, 'chunk' for chunk-based."""

    max_context_tokens: int = field(
        default=get_env_value("MAX_CONTEXT_TOKENS", 2000, int)
    )
    """Maximum number of tokens in extracted context."""

    include_headers: bool = field(default=get_env_value("INCLUDE_HEADERS", True, bool))
    """Whether to include document headers and titles in context."""

    include_captions: bool = field(
        default=get_env_value("INCLUDE_CAPTIONS", True, bool)
    )
    """Whether to include image/table captions in context."""

    context_filter_content_types: List[str] = field(
        default_factory=lambda: get_env_value(
            "CONTEXT_FILTER_CONTENT_TYPES", "text", str
        ).split(",")
    )
    """Content types to include in context extraction (e.g., 'text', 'image', 'table')."""

    content_format: str = field(default=get_env_value("CONTENT_FORMAT", "minerU", str))
    """Default content format for context extraction when processing documents."""

    # Ollama Integration
    # ---
    ollama_base_url: str = field(default_factory=_get_ollama_base_url)
    """Base URL where the Ollama service listens (e.g., ``http://gpu01:11434``)."""

    ollama_llm_model: str = field(
        default=get_env_value(
            "OLLAMA_LLM_MODEL",
            get_env_value("OLLAMA_GENERATE_MODEL", "qwen3:235b", str),
            str,
        )
    )
    """Model tag used for text generation via Ollama."""

    ollama_embed_model: str = field(
        default=get_env_value(
            "OLLAMA_EMBED_MODEL",
            get_env_value("OLLAMA_EMBEDDING_MODEL", "qwen3-embedding:8b", str),
            str,
        )
    )
    """Model tag used for embedding generation via Ollama."""

    ollama_embedding_dim: int = field(
        default=get_env_value("OLLAMA_EMBED_DIM", 8192, int)
    )
    """Expected embedding vector dimension for the Ollama embedding model."""

    ollama_request_timeout: float = field(
        default=get_env_value("OLLAMA_TIMEOUT_SECONDS", 300, float)
    )
    """Request timeout (seconds) for Ollama HTTP calls."""

    ollama_max_retries: int = field(
        default=get_env_value("OLLAMA_MAX_RETRIES", 2, int)
    )
    """Number of retry attempts for transient Ollama failures."""

    ollama_retry_backoff: float = field(
        default=get_env_value("OLLAMA_RETRY_BACKOFF", 0.5, float)
    )
    """Base backoff seconds between Ollama retry attempts."""

    # Reranker Configuration
    # ---
    enable_rerank: bool = field(
        default=get_env_value("ENABLE_RERANK", True, bool)
    )
    """Toggle the FlagEmbedding reranker stage for retrieval results."""

    reranker_model_path: str = field(
        default=get_env_value("RERANKER_MODEL_PATH", "", str)
    )
    """Filesystem path to the FlagEmbedding reranker weights cache."""

    reranker_use_fp16: bool = field(
        default=get_env_value("RERANKER_USE_FP16", False, bool)
    )
    """Whether to request fp16 weights from FlagEmbedding (requires GPU support)."""

    reranker_batch_size: int = field(
        default=get_env_value("RERANKER_BATCH_SIZE", 16, int)
    )
    """Maximum number of documents to score per rerank batch."""

    def __post_init__(self):
        """Post-initialization setup for backward compatibility"""
        # Support legacy environment variable names for backward compatibility
        legacy_parse_method = get_env_value("MINERU_PARSE_METHOD", None, str)
        if legacy_parse_method and not get_env_value("PARSE_METHOD", None, str):
            self.parse_method = legacy_parse_method
            warnings.warn(
                "MINERU_PARSE_METHOD is deprecated. Use PARSE_METHOD instead.",
                DeprecationWarning,
                stacklevel=2,
            )

        # Normalize Ollama URL for downstream HTTP clients.
        base_url = (self.ollama_base_url or "").strip()
        if base_url:
            if not base_url.startswith(("http://", "https://")):
                # Reason: LightRAG passes the URL across nodes; enforce explicit scheme.
                base_url = f"http://{base_url}"
            self.ollama_base_url = base_url.rstrip("/")

        if self.ollama_embedding_dim <= 0:
            warnings.warn(
                "OLLAMA_EMBED_DIM must be positive; falling back to 8192.",
                RuntimeWarning,
                stacklevel=2,
            )
            self.ollama_embedding_dim = 8192

        if self.ollama_max_retries < 0:
            warnings.warn(
                "OLLAMA_MAX_RETRIES cannot be negative; clamping to zero.",
                RuntimeWarning,
                stacklevel=2,
            )
            self.ollama_max_retries = 0

        if self.mineru_vram is not None and self.mineru_vram <= 0:
            # Treat zero/negative as "unset"
            self.mineru_vram = None

        # Note: Reranker validation is now handled by backend/model_factory.py
        # The backend passes rerank_model_func directly to RAGAnything, so we don't
        # need to validate RERANKER_MODEL_PATH here. This allows both local and API
        # rerankers to work correctly.
        #
        # Legacy behavior (for direct RAGAnything usage without backend):
        # Only disable reranking if using local reranker without model path
        if self.enable_rerank and not self.reranker_model_path:
            # Check if we're being used directly (not through backend)
            # If RERANKER_PROVIDER is set to 'api', don't warn
            reranker_provider = get_env_value("RERANKER_PROVIDER", "", str)
            if reranker_provider != "api":
                # Reason: FlagEmbedding cannot load without a cached model location.
                warnings.warn(
                    "ENABLE_RERANK is true but RERANKER_MODEL_PATH is empty; disabling reranker stage. "
                    "Set RERANKER_PROVIDER=api if using API-based reranker.",
                    RuntimeWarning,
                    stacklevel=2,
                )
                self.enable_rerank = False

    @property
    def mineru_parse_method(self) -> str:
        """
        Backward compatibility property for old code.

        .. deprecated::
           Use `parse_method` instead. This property will be removed in a future version.
        """
        warnings.warn(
            "mineru_parse_method is deprecated. Use parse_method instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.parse_method

    @mineru_parse_method.setter
    def mineru_parse_method(self, value: str):
        """Setter for backward compatibility"""
        warnings.warn(
            "mineru_parse_method is deprecated. Use parse_method instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.parse_method = value
