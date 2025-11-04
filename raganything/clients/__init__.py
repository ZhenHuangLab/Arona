"""Client adapters for external services used by RAGAnything."""

from .ollama import OllamaClient, OllamaClientError

__all__ = ["OllamaClient", "OllamaClientError"]
