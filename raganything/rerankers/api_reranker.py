"""API-based reranker adapter for RAGAnything.

Supports multiple reranker API providers:
- Jina AI Reranker API
- Cohere Rerank API
- Voyage AI Rerank API
- Generic OpenAI-compatible reranker APIs
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Sequence

import httpx

from .flagembedding import RerankerError

logger = logging.getLogger(__name__)


@dataclass
class APIReranker:
    """API-based reranker with support for multiple providers."""

    provider: str  # "jina", "cohere", "voyage", "openai"
    model_name: str
    api_key: str
    base_url: str | None = None
    batch_size: int = 16
    timeout: float = 30.0
    max_retries: int = 3
    
    _client: httpx.AsyncClient | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        """Validate configuration and set defaults."""
        if self.batch_size <= 0:
            raise ValueError("batch_size must be positive for APIReranker")
        
        # Set default base URLs for known providers
        if not self.base_url:
            if self.provider == "jina":
                self.base_url = "https://api.jina.ai/v1/rerank"
            elif self.provider == "cohere":
                self.base_url = "https://api.cohere.ai/v1/rerank"
            elif self.provider == "voyage":
                self.base_url = "https://api.voyageai.com/v1/rerank"
            elif self.provider == "openai":
                self.base_url = "https://api.openai.com/v1/rerank"
            else:
                raise ValueError(
                    f"Unknown provider '{self.provider}'. "
                    "Please specify base_url for custom providers."
                )
        
        logger.info(
            f"Initialized APIReranker: provider={self.provider}, "
            f"model={self.model_name}, base_url={self.base_url}"
        )

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            )
        return self._client

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def score_async(self, query: str, documents: Sequence[str]) -> List[float]:
        """
        Asynchronously score documents for a single query.
        
        Args:
            query: Search query
            documents: List of document texts to rerank
            
        Returns:
            List of relevance scores (same length as documents)
        """
        if not documents:
            return []

        # Process in batches if needed
        all_scores: List[float] = []
        
        for i in range(0, len(documents), self.batch_size):
            batch = documents[i : i + self.batch_size]
            batch_scores = await self._score_batch(query, batch)
            all_scores.extend(batch_scores)
        
        return all_scores

    async def _score_batch(self, query: str, documents: Sequence[str]) -> List[float]:
        """Score a single batch of documents."""
        client = await self._get_client()
        
        # Prepare request based on provider
        request_data = self._prepare_request(query, documents)
        headers = self._prepare_headers()
        
        # Retry logic
        last_error = None
        for attempt in range(self.max_retries):
            try:
                response = await client.post(
                    self.base_url,  # type: ignore[arg-type]
                    json=request_data,
                    headers=headers,
                )
                response.raise_for_status()
                
                # Parse response based on provider
                scores = self._parse_response(response.json(), len(documents))
                return scores
                
            except httpx.HTTPStatusError as exc:
                last_error = exc
                logger.warning(
                    f"Reranker API request failed (attempt {attempt + 1}/{self.max_retries}): "
                    f"HTTP {exc.response.status_code} - {exc.response.text}"
                )
                
                # Don't retry on client errors (4xx)
                if 400 <= exc.response.status_code < 500:
                    raise RerankerError(
                        f"Reranker API client error: {exc.response.status_code} - {exc.response.text}"
                    ) from exc
                
                # Exponential backoff for server errors
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    
            except Exception as exc:
                last_error = exc
                logger.warning(
                    f"Reranker API request failed (attempt {attempt + 1}/{self.max_retries}): {exc}"
                )
                
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
        
        # All retries failed
        raise RerankerError(
            f"Reranker API request failed after {self.max_retries} attempts: {last_error}"
        ) from last_error

    def _prepare_headers(self) -> Dict[str, str]:
        """Prepare HTTP headers based on provider."""
        headers = {"Content-Type": "application/json"}
        
        if self.provider == "jina":
            headers["Authorization"] = f"Bearer {self.api_key}"
        elif self.provider == "cohere":
            headers["Authorization"] = f"Bearer {self.api_key}"
        elif self.provider == "voyage":
            headers["Authorization"] = f"Bearer {self.api_key}"
        elif self.provider == "openai":
            headers["Authorization"] = f"Bearer {self.api_key}"
        else:
            # Generic: assume Bearer token
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        return headers

    def _prepare_request(self, query: str, documents: Sequence[str]) -> Dict[str, Any]:
        """Prepare request payload based on provider."""
        if self.provider == "jina":
            # Jina API format
            return {
                "model": self.model_name,
                "query": query,
                "documents": list(documents),
                "top_n": len(documents),  # Return all documents with scores
            }
        
        elif self.provider == "cohere":
            # Cohere API format
            return {
                "model": self.model_name,
                "query": query,
                "documents": list(documents),
                "top_n": len(documents),
                "return_documents": False,  # We only need scores
            }
        
        elif self.provider == "voyage":
            # Voyage AI API format
            return {
                "model": self.model_name,
                "query": query,
                "documents": list(documents),
                "top_k": len(documents),
            }
        
        elif self.provider == "openai":
            # OpenAI-compatible format (hypothetical)
            return {
                "model": self.model_name,
                "query": query,
                "documents": list(documents),
            }
        
        else:
            # Generic format (similar to OpenAI)
            return {
                "model": self.model_name,
                "query": query,
                "documents": list(documents),
            }

    def _parse_response(self, response_data: Dict[str, Any], expected_count: int) -> List[float]:
        """Parse API response and extract scores."""
        try:
            if self.provider == "jina":
                # Jina returns: {"results": [{"index": 0, "relevance_score": 0.95}, ...]}
                results = response_data.get("results", [])
                # Sort by index to maintain order
                results_sorted = sorted(results, key=lambda x: x.get("index", 0))
                scores = [float(r.get("relevance_score", 0.0)) for r in results_sorted]
                
            elif self.provider == "cohere":
                # Cohere returns: {"results": [{"index": 0, "relevance_score": 0.95}, ...]}
                results = response_data.get("results", [])
                results_sorted = sorted(results, key=lambda x: x.get("index", 0))
                scores = [float(r.get("relevance_score", 0.0)) for r in results_sorted]
                
            elif self.provider == "voyage":
                # Voyage returns: {"data": [{"index": 0, "relevance_score": 0.95}, ...]}
                data = response_data.get("data", [])
                data_sorted = sorted(data, key=lambda x: x.get("index", 0))
                scores = [float(d.get("relevance_score", 0.0)) for d in data_sorted]
                
            elif self.provider == "openai":
                # OpenAI-compatible format
                results = response_data.get("results", [])
                results_sorted = sorted(results, key=lambda x: x.get("index", 0))
                scores = [float(r.get("score", 0.0)) for r in results_sorted]
                
            else:
                # Generic: try to find scores in common formats
                if "results" in response_data:
                    results = response_data["results"]
                    results_sorted = sorted(results, key=lambda x: x.get("index", 0))
                    scores = [
                        float(r.get("relevance_score") or r.get("score", 0.0))
                        for r in results_sorted
                    ]
                elif "data" in response_data:
                    data = response_data["data"]
                    data_sorted = sorted(data, key=lambda x: x.get("index", 0))
                    scores = [
                        float(d.get("relevance_score") or d.get("score", 0.0))
                        for d in data_sorted
                    ]
                else:
                    raise ValueError(f"Unknown response format: {response_data.keys()}")
            
            # Validate score count
            if len(scores) != expected_count:
                logger.warning(
                    f"Expected {expected_count} scores but got {len(scores)}. "
                    f"Padding with zeros."
                )
                # Pad with zeros if needed
                while len(scores) < expected_count:
                    scores.append(0.0)
                # Truncate if too many
                scores = scores[:expected_count]
            
            return scores
            
        except Exception as exc:
            raise RerankerError(
                f"Failed to parse reranker response: {exc}. Response: {response_data}"
            ) from exc

    def __del__(self) -> None:
        """Cleanup on deletion."""
        if self._client is not None:
            # Schedule cleanup in event loop if available
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.close())
            except RuntimeError:
                # No event loop, can't cleanup
                pass

