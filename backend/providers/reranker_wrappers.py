from __future__ import annotations

from typing import Any, List

from backend.providers.base import BaseRerankerProvider


class FlagEmbeddingRerankerProvider(BaseRerankerProvider):
    """Adapter for raganything FlagEmbeddingReranker to BaseRerankerProvider."""

    def __init__(self, reranker: Any):
        self._reranker = reranker

    async def rerank(self, query: str, documents: List[str], **kwargs) -> List[float]:
        _ = kwargs
        scores = await self._reranker.score_async(query, documents)
        return [float(s) for s in scores]


class APIRerankerProvider(BaseRerankerProvider):
    """Adapter for raganything APIReranker to BaseRerankerProvider."""

    def __init__(self, reranker: Any):
        self._reranker = reranker

    async def rerank(self, query: str, documents: List[str], **kwargs) -> List[float]:
        _ = kwargs
        scores = await self._reranker.score_async(query, documents)
        return [float(s) for s in scores]
