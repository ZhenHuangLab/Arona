"""FlagEmbedding reranker adapter for RAGAnything."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Iterable, List, Sequence


class RerankerError(RuntimeError):
    """Raised when the FlagEmbedding reranker cannot be constructed or executed."""


@dataclass
class FlagEmbeddingReranker:
    """Lazy loader around ``FlagLLMReranker`` with simple batching support."""

    model_path: str
    use_fp16: bool = True
    batch_size: int = 16
    _model: object | None = field(default=None, init=False, repr=False)
    _lock: Lock = field(default_factory=Lock, init=False, repr=False)

    def __post_init__(self) -> None:
        resolved = Path(self.model_path).expanduser()
        if not resolved.exists():
            raise RerankerError(
                f"FlagEmbedding model path '{resolved}' does not exist; pre-download the weights."
            )
        self.model_path = str(resolved)
        if self.batch_size <= 0:
            raise ValueError("batch_size must be positive for FlagEmbeddingReranker")

    def score(self, query: str, documents: Sequence[str]) -> List[float]:
        """Synchronously score documents for a single query."""

        if not documents:
            return []

        reranker = self._ensure_model()
        scores: List[float] = []
        for batch in _chunk_sequence(documents, self.batch_size):
            batch_scores = [
                _to_float(reranker.compute_score([query, doc]))  # type: ignore[attr-defined]
                for doc in batch
            ]
            scores.extend(batch_scores)
        return scores

    async def score_async(self, query: str, documents: Sequence[str]) -> List[float]:
        """Asynchronously score documents by offloading to a worker thread."""

        return await asyncio.to_thread(self.score, query, list(documents))

    def _ensure_model(self) -> object:
        if self._model is not None:
            return self._model
        with self._lock:
            if self._model is None:
                try:
                    # Lazily import FlagEmbedding to avoid startup cost when rerank is disabled.
                    from FlagEmbedding import FlagLLMReranker

                    self._model = FlagLLMReranker(
                        self.model_path,
                        use_fp16=self.use_fp16,
                    )
                except Exception as exc:  # pylint: disable=broad-except
                    raise RerankerError(
                        f"Failed to initialize FlagEmbedding reranker: {exc}"
                    ) from exc
        return self._model


def _chunk_sequence(items: Sequence[str], size: int) -> Iterable[Sequence[str]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


def _to_float(value: object) -> float:
    if isinstance(value, (float, int)):
        return float(value)
    # Reason: FlagEmbedding may return torch.Tensor/np.ndarray objects; convert safely.
    if hasattr(value, "item"):
        return float(value.item())  # type: ignore[call-arg]
    if hasattr(value, "tolist"):
        arr = value.tolist()  # type: ignore[call-arg]
        if isinstance(arr, (list, tuple)) and arr:
            return float(arr[0])
    raise RerankerError(f"Unsupported reranker score type: {type(value)!r}")
