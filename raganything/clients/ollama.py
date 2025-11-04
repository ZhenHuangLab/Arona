"""Minimal Ollama HTTP client used by RAGAnything."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import List, Optional, Sequence
from urllib import error, request
from urllib.parse import urljoin


class OllamaClientError(RuntimeError):
    """Raised when the Ollama service rejects or cannot handle a request."""


@dataclass
class OllamaClient:
    """Blocking HTTP client for the Ollama REST API with retry semantics."""

    base_url: str
    timeout: float = 120.0
    max_retries: int = 2
    backoff_factor: float = 0.5

    def __post_init__(self) -> None:
        if not self.base_url:
            raise ValueError("OllamaClient requires a non-empty base_url")
        if not self.base_url.startswith(("http://", "https://")):
            raise ValueError(
                f"Invalid Ollama base_url '{self.base_url}'; expected http(s) scheme."
            )
        self.base_url = self.base_url.rstrip("/")

        if self.max_retries < 0:
            raise ValueError("max_retries must be zero or positive")
        if self.backoff_factor < 0:
            raise ValueError("backoff_factor must be zero or positive")

    def chat(
        self,
        prompt: str,
        *,
        model: str,
        system_prompt: Optional[str] = None,
        history_messages: Optional[Sequence[dict]] = None,
        stream: bool = False,
        options: Optional[dict] = None,
    ) -> str:
        """Call ``/api/chat`` and return the assistant response text."""

        payload = {
            "model": model,
            "messages": self._build_messages(prompt, system_prompt, history_messages),
            "stream": bool(stream),
        }
        if options:
            payload["options"] = options

        response = self._post_json("api/chat", payload)
        message = response.get("message")
        if not isinstance(message, dict) or "content" not in message:
            raise OllamaClientError("Unexpected response payload from Ollama chat endpoint")
        return message["content"]

    def embed(self, texts: Sequence[str], *, model: str) -> List[List[float]]:
        """Call ``/api/embeddings`` for each input and return embeddings."""

        if isinstance(texts, str):  # type: ignore[unreachable]
            texts = [texts]

        embeddings: List[List[float]] = []
        for text in texts:
            payload = {"model": model, "prompt": text}
            response = self._post_json("api/embeddings", payload)
            vector = response.get("embedding")
            if not isinstance(vector, list):
                raise OllamaClientError("Ollama embeddings response missing 'embedding' list")
            if len(vector) == 0:
                # Reason: Empty embeddings break RAG retrieval; fail fast with diagnostic info.
                raise OllamaClientError(
                    f"Ollama returned empty embedding for text: {text[:100]}... Response: {response}"
                )
            embeddings.append([float(v) for v in vector])
        return embeddings

    def _build_messages(
        self,
        prompt: str,
        system_prompt: Optional[str],
        history: Optional[Sequence[dict]],
    ) -> List[dict]:
        messages: List[dict] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if history:
            for item in history:
                role = item.get("role") if isinstance(item, dict) else None
                content = item.get("content") if isinstance(item, dict) else None
                if role and content:
                    messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": prompt})
        return messages

    def _post_json(self, path: str, payload: dict) -> dict:
        url = urljoin(f"{self.base_url}/", path.lstrip("/"))
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        attempt = 0
        delay = self.backoff_factor
        while True:
            req = request.Request(
                url,
                data=body,
                headers={"Content-Type": "application/json", "Accept": "application/json"},
                method="POST",
            )
            try:
                with request.urlopen(req, timeout=self.timeout) as resp:
                    raw = resp.read().decode("utf-8")
                    if resp.status >= 400:
                        raise OllamaClientError(
                            f"Ollama request failed with HTTP {resp.status}: {raw}"
                        )
                    return json.loads(raw or "{}")
            except error.HTTPError as exc:
                content = exc.read().decode("utf-8", "ignore")
                if exc.code >= 500 and attempt < self.max_retries:
                    # Reason: backend returned transient error, retry with backoff.
                    time.sleep(delay)
                    attempt += 1
                    delay *= 2
                    continue
                raise OllamaClientError(
                    f"Ollama request failed with HTTP {exc.code}: {content or exc.reason}"
                ) from exc
            except error.URLError as exc:
                if attempt >= self.max_retries:
                    raise OllamaClientError(
                        f"Ollama at {url} is unreachable: {exc.reason}"
                    ) from exc
                time.sleep(delay)
                attempt += 1
                delay *= 2
