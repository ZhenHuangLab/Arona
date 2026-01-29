"""
Chat API Router - /api/chat

Implements the frozen contract from `_TASKs/T8_chat-ui-sessions-sqlite.md` (Phase P2).

Key constraints:
- Keep existing `/api/query/*` endpoints intact (new UI uses `/api/chat/*`).
- Avoid SQLite "database is locked": no DB connection is held while waiting on the LLM call.
- Idempotency: `request_id` is required for turns; completed + same payload replays cached result.
- Multimodal: accept `img_base64`, persist to disk, store only `img_path` in SQLite metadata.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import logging
import re
import time
import sqlite3
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional
from urllib.parse import quote

from fastapi import APIRouter, Body, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse

from backend.models.chat import (
    ChatMessage,
    ChatSession,
    CreateSessionRequest,
    DeleteSessionResponse,
    ErrorDetail,
    MessageListResponse,
    RetryAssistantRequest,
    UpdateMessageRequest,
    SessionListResponse,
    TurnRequest,
    TurnResponse,
    TurnStatus,
    UpdateSessionRequest,
)
from backend.services.chat_store import ChatStore, compute_payload_hash


logger = logging.getLogger(__name__)
router = APIRouter()

DEFAULT_CHAT_MODE = "hybrid"
MAX_QUERY_IMAGE_BYTES = 10 * 1024 * 1024

# Image extensions for extraction
_IMAGE_EXTENSIONS = frozenset(
    {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tiff"}
)

# Regex patterns for extracting image paths from retrieval prompt
_IMAGE_PATH_PATTERN = re.compile(
    r"^\s*Image Path:\s*(.*?)\s*$", re.IGNORECASE | re.MULTILINE
)
# Markdown image syntax: ![alt](url "optional title")
_MARKDOWN_IMAGE_PATTERN = re.compile(
    r"!\[[^\]]*\]\(\s*([^\s)]+)(?:\s+['\"][^)]*['\"])?\s*\)"
)
_REMOTE_MARKDOWN_IMAGE_PATTERN = re.compile(
    r"!\[([^\]]*)\]\(\s*(https?://[^\s)]+)(?:\s+['\"][^)]*['\"])?\s*\)",
    re.IGNORECASE,
)
_REMOTE_HTML_IMG_PATTERN = re.compile(r"<img\b[^>]*>", re.IGNORECASE)


def _sanitize_external_images_in_markdown(content: str) -> str:
    """
    Demote external image embeds (http/https) to plain links.

    Motivation:
    - LLMs may hallucinate image URLs (imgur/github/etc.), which renders as broken images.
    - For security and determinism, we prefer local `/api/files?path=...` images only.

    Behavior:
    - Converts `![](https://...)` to `[external image](https://...)`.
    - Converts `<img src="https://...">` to `[external image](https://...)`.
    - Skips fenced code blocks (``` / ~~~).
    """

    def _extract_html_attr(tag: str, name: str) -> str | None:
        m = re.search(
            rf"{name}\s*=\s*(\"([^\"]*)\"|'([^']*)'|([^\s>]+))",
            tag,
            flags=re.IGNORECASE,
        )
        return (m.group(2) or m.group(3) or m.group(4) or "").strip() or None

    def _rewrite_html_img(tag: str) -> str:
        src = _extract_html_attr(tag, "src")
        if not src:
            return tag
        if not src.lower().startswith(("http://", "https://")):
            return tag
        alt = _extract_html_attr(tag, "alt") or "external image"
        # Escape ']' in alt to avoid breaking markdown link syntax.
        safe_alt = alt.replace("]", "\\]")
        return f"[{safe_alt}]({src})"

    def _rewrite_line(line: str) -> str:
        line = _REMOTE_HTML_IMG_PATTERN.sub(lambda m: _rewrite_html_img(m.group(0)), line)

        def _rewrite_md(match: re.Match[str]) -> str:
            alt = (match.group(1) or "").strip() or "external image"
            url = match.group(2).strip()
            safe_alt = alt.replace("]", "\\]")
            return f"[{safe_alt}]({url})"

        return _REMOTE_MARKDOWN_IMAGE_PATTERN.sub(_rewrite_md, line)

    lines = content.splitlines()
    in_fence = False
    fence_token: str | None = None
    out: list[str] = []
    for line in lines:
        trimmed = line.lstrip()
        fence_match = re.match(r"^(```|~~~)", trimmed)
        if fence_match:
            token = fence_match.group(1)
            if not in_fence:
                in_fence = True
                fence_token = token
            elif fence_token == token:
                in_fence = False
                fence_token = None
            out.append(line)
            continue

        out.append(line if in_fence else _rewrite_line(line))

    return "\n".join(out)


def _normalize_extracted_image_path(raw: str) -> str:
    value = (raw or "").strip()
    if not value:
        return ""

    # Strip wrapping angle brackets: <...>
    if value.startswith("<") and value.endswith(">"):
        value = value[1:-1].strip()

    # Strip wrapping quotes: "..." or '...'
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        value = value[1:-1].strip()

    return value


def _has_image_extension(path_str: str) -> bool:
    # Ignore query strings/fragments (rare for local paths, but safe).
    clean = path_str.split("?", 1)[0].split("#", 1)[0]
    return Path(clean).suffix.lower() in _IMAGE_EXTENSIONS


def _extract_image_paths_from_prompt(prompt: str) -> list[str]:
    """
    Extract local image paths from a retrieval prompt.

    Matches:
    - Lines like 'Image Path: /path/to/image.png'
    - Markdown image syntax ![alt](path)

    Filters out remote URLs (http, https, data, blob).
    Returns deduplicated paths.
    """
    paths: list[str] = []

    # Extract from 'Image Path:' lines
    for match in _IMAGE_PATH_PATTERN.finditer(prompt):
        path = _normalize_extracted_image_path(match.group(1))
        if path:
            paths.append(path)

    # Extract from markdown image syntax
    for match in _MARKDOWN_IMAGE_PATTERN.finditer(prompt):
        path = _normalize_extracted_image_path(match.group(1))
        if path:
            paths.append(path)

    # Filter: only keep local paths (not http/https/data/blob)
    local_paths: list[str] = []
    seen: set[str] = set()
    for p in paths:
        p_lower = p.lower()
        if any(p_lower.startswith(prefix) for prefix in ("http://", "https://", "data:", "blob:")):
            continue
        if not _has_image_extension(p):
            continue
        # Deduplicate
        if p in seen:
            continue
        seen.add(p)
        local_paths.append(p)

    return local_paths


def _convert_to_api_files_url(path: str, working_dir: str | None = None) -> str:
    """
    Convert a local image path to an /api/files?path=... URL.

    Prefer the shorthand `images/<basename>` for parsed_output images to:
    - avoid leaking absolute paths
    - be resilient to stale absolute paths embedded in stored chunks (e.g. docker `/app/...`)
    """
    normalized = path
    if normalized.lower().startswith("file://"):
        normalized = normalized[7:]
    p = Path(normalized)
    suffix = p.suffix.lower()

    # Use shorthand for common parsed_output patterns even if the absolute prefix
    # doesn't match the current machine (e.g. /app/rag_storage/...).
    if working_dir and suffix in _IMAGE_EXTENSIONS:
        normalized_lower = normalized.lower()
        if (
            "parsed_output" in normalized_lower
            or "/images/" in normalized_lower
            or normalized_lower.startswith("images/")
        ):
            return f"/api/files?path={quote(f'images/{p.name}', safe='')}"

        # If this is a real path under the current working_dir/parsed_output, also use shorthand.
        working_root = Path(working_dir)
        parsed_output = working_root / "parsed_output"
        try:
            rel = p.resolve().relative_to(parsed_output.resolve())
            if "images" in rel.parts:
                return f"/api/files?path={quote(f'images/{p.name}', safe='')}"
        except ValueError:
            pass

    # Fallback: use full path (URL-encoded)
    return f"/api/files?path={quote(str(p), safe='')}"


def _images_already_in_content(content: str, image_urls: list[str]) -> set[str]:
    """Check which image URLs are already present in the content."""
    already_present: set[str] = set()
    for url in image_urls:
        if url in content:
            already_present.add(url)
        # Also check for the unencoded basename
        basename = Path(url.split("path=")[-1]).name if "path=" in url else ""
        if basename and basename in content:
            already_present.add(url)
    return already_present


def _dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


async def _maybe_attach_retrieved_images(
    assistant_content: str,
    query: str,
    conversation_history: list[dict] | None,
    rag_service: Any,
    config: Any,
    mode: str = "hybrid",
) -> str:
    """
    If enabled in config, fetch retrieval data and attach images from retrieved chunks.

    Primary method: Use get_retrieval_data to get structured chunks, then extract
    "Image Path:" lines or markdown images from chunk content. This ensures we only
    attach images that come from the actually retrieved text chunks (e.g., image-derived
    chunks generated via VLM).

    Returns the (possibly modified) assistant content.
    """
    # Check if feature is enabled
    if not getattr(config, "chat_auto_attach_retrieved_images", True):
        return assistant_content

    max_images = getattr(config, "chat_max_retrieved_images", 4)
    if max_images <= 0:
        return assistant_content

    working_dir = getattr(config, "working_dir", None)

    # Primary method: Use get_retrieval_data for structured chunk access
    if hasattr(rag_service, "get_retrieval_data"):
        try:
            retrieval_data = await rag_service.get_retrieval_data(
                query=query,
                mode=mode,
                conversation_history=conversation_history,
            )
            image_paths = _extract_image_paths_from_retrieval_data(retrieval_data)
            if image_paths:
                logger.debug(
                    "Extracted %d image paths from retrieval data chunks",
                    len(image_paths),
                )
        except Exception as exc:
            logger.debug("Failed to get retrieval data for image extraction: %s", exc)
            image_paths = []
    else:
        image_paths = []

    # Fallback: use get_retrieval_prompt if available and no images found yet
    if not image_paths and hasattr(rag_service, "get_retrieval_prompt"):
        try:
            retrieval_prompt = await rag_service.get_retrieval_prompt(
                query=query,
                mode=mode,
                conversation_history=conversation_history,
            )
            if retrieval_prompt:
                image_paths = _extract_image_paths_from_prompt(retrieval_prompt)
                if image_paths:
                    logger.debug(
                        "Extracted %d image paths from retrieval prompt fallback",
                        len(image_paths),
                    )
        except Exception as exc:
            logger.debug("Failed to get retrieval prompt for image extraction: %s", exc)

    if not image_paths:
        return assistant_content

    # Convert to API URLs
    image_urls = [_convert_to_api_files_url(p, working_dir) for p in image_paths]
    image_urls = _dedupe_preserve_order(image_urls)

    # Filter out images already present in content
    already_present = _images_already_in_content(assistant_content, image_urls)
    image_urls = [url for url in image_urls if url not in already_present]
    image_urls = image_urls[:max_images]

    if not image_urls:
        return assistant_content

    # Build markdown section
    image_lines = [f"![检索图片]({url})" for url in image_urls]
    images_section = "\n\n---\n\n### 相关图片（来自检索）\n\n" + "\n\n".join(image_lines)

    return assistant_content + images_section


def _extract_image_paths_from_retrieval_data(retrieval_data: dict) -> list[str]:
    """
    Extract local image paths from structured retrieval data.

    Looks for 'Image Path:' lines or markdown images within the 'content' field
    of each retrieved chunk. This ensures we only get images from chunks that
    were actually retrieved and matched the query.

    Args:
        retrieval_data: Result from RAGService.get_retrieval_data()

    Returns:
        List of local image paths (deduplicated)
    """
    if not isinstance(retrieval_data, dict):
        return []

    # Handle both success and error responses
    if retrieval_data.get("status") != "success":
        return []

    data = retrieval_data.get("data", {})
    if not isinstance(data, dict):
        return []

    chunks = data.get("chunks", [])
    if not isinstance(chunks, list):
        return []

    all_paths: list[str] = []
    seen: set[str] = set()

    for chunk in chunks:
        if not isinstance(chunk, dict):
            continue
        content = chunk.get("content", "")
        if not content or not isinstance(content, str):
            continue

        # Extract image paths from this chunk's content
        chunk_paths = _extract_image_paths_from_prompt(content)
        for path in chunk_paths:
            if path not in seen:
                seen.add(path)
                all_paths.append(path)

    return all_paths


def _make_error(
    code: str, message: str, extra: Optional[dict[str, Any]] = None
) -> dict[str, Any]:
    return ErrorDetail(code=code, message=message, extra=extra).model_dump()


def _get_chat_store(request: Request) -> ChatStore:
    store = getattr(request.app.state, "chat_store", None)
    if store is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_make_error("STORAGE_ERROR", "Chat storage not initialized"),
        )
    return store


def _get_upload_dir(request: Request) -> Path:
    config = getattr(request.app.state, "config", None)
    upload_dir = getattr(config, "upload_dir", "uploads")
    return Path(upload_dir)


def _infer_image_extension_from_data_url(header: str) -> str:
    header = header.lower()
    if "image/jpeg" in header or "image/jpg" in header:
        return "jpg"
    if "image/png" in header:
        return "png"
    if "image/webp" in header:
        return "webp"
    if "image/gif" in header:
        return "gif"
    if "image/bmp" in header:
        return "bmp"
    if "image/tiff" in header or "image/tif" in header:
        return "tif"
    return "png"


def _decode_image_base64(*, img_base64: str) -> tuple[bytes, str]:
    """
    Decode a base64-encoded image.

    Accepts either raw base64 or data URLs: data:image/png;base64,...
    Returns (image_bytes, ext).
    """
    if not img_base64 or not isinstance(img_base64, str):
        raise ValueError("img_base64 must be a non-empty string")

    b64_payload = img_base64.strip()
    ext = "png"

    if b64_payload.startswith("data:"):
        try:
            header, b64_payload = b64_payload.split(",", 1)
        except ValueError as exc:
            raise ValueError("Invalid data URL format for img_base64") from exc
        ext = _infer_image_extension_from_data_url(header)

    try:
        image_bytes = base64.b64decode(b64_payload, validate=True)
    except Exception as exc:  # noqa: BLE001
        raise ValueError("Invalid base64 payload for img_base64") from exc

    if not image_bytes:
        raise ValueError("Decoded img_base64 is empty")
    if len(image_bytes) > MAX_QUERY_IMAGE_BYTES:
        raise ValueError(
            f"Query image too large: {len(image_bytes)} bytes > {MAX_QUERY_IMAGE_BYTES} bytes"
        )

    return image_bytes, ext


def _persist_query_image_bytes(
    *, image_bytes: bytes, upload_dir: Path, ext: str
) -> tuple[str, str]:
    """
    Persist image bytes to uploads/query_images and return (absolute_path, sha16).
    """
    query_dir = upload_dir / "query_images"
    query_dir.mkdir(parents=True, exist_ok=True)

    sha16 = hashlib.sha256(image_bytes).hexdigest()[:16]
    filename = f"query_{int(time.time())}_{sha16}.{ext}"
    path = (query_dir / filename).resolve()

    path.write_bytes(image_bytes)
    return str(path), sha16


def _compute_turn_payload_hash(
    *, body: TurnRequest, mode: str, image_sha16: Optional[str]
) -> str:
    payload: dict[str, Any] = {
        "query": body.query.strip(),
        "mode": mode,
        "max_tokens": body.max_tokens,
        "temperature": body.temperature,
        "history_limit": body.history_limit,
        "max_history_tokens": body.max_history_tokens,
    }
    if image_sha16:
        payload["img_sha16"] = image_sha16
        payload["img_mime_type"] = (
            body.multimodal_content.img_mime_type if body.multimodal_content else None
        )
    return compute_payload_hash(payload)


def _sse(data: dict[str, Any]) -> str:
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return f"data: {payload}\n\n"


# =============================================================================
# Sessions
# =============================================================================


@router.post(
    "/sessions", response_model=ChatSession, status_code=status.HTTP_201_CREATED
)
async def create_session(
    request: Request,
    body: CreateSessionRequest = Body(default_factory=CreateSessionRequest),
) -> ChatSession:
    store = _get_chat_store(request)
    title = body.title or "New Chat"
    try:
        return store.create_session(title=title, metadata=body.metadata)
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to create session: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_make_error("STORAGE_ERROR", "Failed to create session"),
        ) from exc


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
    cursor: Optional[str] = Query(default=None),
    q: Optional[str] = Query(default=None),
) -> SessionListResponse:
    store = _get_chat_store(request)
    try:
        return store.list_sessions(limit=limit, cursor=cursor, q=q)
    except ValueError as exc:
        msg = str(exc)
        if "INVALID_CURSOR" in msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=_make_error("INVALID_CURSOR", "Invalid or malformed cursor"),
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_make_error("BAD_REQUEST", msg),
        ) from exc
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to list sessions: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_make_error("STORAGE_ERROR", "Failed to list sessions"),
        ) from exc


@router.get("/search", response_model=SessionListResponse)
async def search_sessions(
    request: Request,
    q: str = Query(
        ..., min_length=1, description="Search query (title or message content)"
    ),
    limit: int = Query(default=20, ge=1, le=100),
    cursor: Optional[str] = Query(default=None),
) -> SessionListResponse:
    """
    Search chat sessions by title or message content.

    Implementation uses SQLite FTS5 when available; falls back to LIKE.
    """
    store = _get_chat_store(request)
    try:
        return store.search_sessions(q=q, limit=limit, cursor=cursor)
    except ValueError as exc:
        msg = str(exc)
        if "INVALID_CURSOR" in msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=_make_error("INVALID_CURSOR", "Invalid or malformed cursor"),
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_make_error("BAD_REQUEST", msg),
        ) from exc
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to search sessions: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_make_error("STORAGE_ERROR", "Failed to search sessions"),
        ) from exc


@router.get("/sessions/{session_id}", response_model=ChatSession)
async def get_session(request: Request, session_id: str) -> ChatSession:
    store = _get_chat_store(request)
    session = store.get_session(session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_make_error("SESSION_NOT_FOUND", f"Session {session_id} not found"),
        )
    return session


@router.patch("/sessions/{session_id}", response_model=ChatSession)
async def update_session(
    request: Request,
    session_id: str,
    body: UpdateSessionRequest,
) -> ChatSession:
    store = _get_chat_store(request)
    session = store.update_session(
        session_id=session_id, title=body.title, metadata=body.metadata
    )
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_make_error("SESSION_NOT_FOUND", f"Session {session_id} not found"),
        )
    return session


@router.delete("/sessions/{session_id}", response_model=DeleteSessionResponse)
async def delete_session(
    request: Request,
    session_id: str,
    hard: bool = Query(default=False),
) -> DeleteSessionResponse:
    store = _get_chat_store(request)

    session = store.get_session(session_id)
    if session is None:
        deleted_at = store.get_session_deleted_at(session_id)
        if deleted_at is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=_make_error(
                    "SESSION_NOT_FOUND", f"Session {session_id} not found"
                ),
            )
        return DeleteSessionResponse(
            id=session_id, deleted=True, hard=False, deleted_at=deleted_at
        )

    deleted = store.delete_session(session_id, hard=hard)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_make_error("SESSION_NOT_FOUND", f"Session {session_id} not found"),
        )

    deleted_at = None if hard else store.get_session_deleted_at(session_id)
    return DeleteSessionResponse(
        id=session_id, deleted=True, hard=hard, deleted_at=deleted_at
    )


# =============================================================================
# Messages
# =============================================================================


@router.get("/sessions/{session_id}/messages", response_model=MessageListResponse)
async def list_messages(
    request: Request,
    session_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    cursor: Optional[str] = Query(default=None),
) -> MessageListResponse:
    store = _get_chat_store(request)
    try:
        return store.list_messages(session_id=session_id, limit=limit, cursor=cursor)
    except ValueError as exc:
        msg = str(exc)
        if "not found or deleted" in msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=_make_error(
                    "SESSION_NOT_FOUND", f"Session {session_id} not found"
                ),
            ) from exc
        if "INVALID_CURSOR" in msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=_make_error("INVALID_CURSOR", "Invalid or malformed cursor"),
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_make_error("BAD_REQUEST", msg),
        ) from exc
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to list messages: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_make_error("STORAGE_ERROR", "Failed to list messages"),
        ) from exc


@router.patch(
    "/sessions/{session_id}/messages/{message_id}",
    response_model=ChatMessage,
)
async def update_user_message(
    request: Request,
    session_id: str,
    message_id: str,
    body: UpdateMessageRequest,
) -> ChatMessage:
    """
    Update the *latest* user message content in-place.

    Constraints:
    - Only user messages can be edited.
    - Only the latest turn's user message can be edited to avoid branching history.
    """
    store = _get_chat_store(request)

    session = store.get_session(session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_make_error("SESSION_NOT_FOUND", f"Session {session_id} not found"),
        )

    msg = store.get_message(message_id)
    if msg is None or msg.session_id != session_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_make_error(
                "MESSAGE_NOT_FOUND", f"Message {message_id} not found in session"
            ),
        )
    if msg.role.value != "user":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_make_error("BAD_REQUEST", "Only user messages can be edited"),
        )

    content = (body.content or "").strip()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_make_error("EMPTY_QUERY", "Message content cannot be empty"),
        )

    # Enforce: only edit latest turn's user message (pair of latest assistant).
    latest = store.get_latest_message(session_id)
    if latest is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_make_error("NOT_LATEST_MESSAGE", "Session has no messages"),
        )
    if latest.role.value != "assistant":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_make_error(
                "NOT_LATEST_MESSAGE",
                "Can only edit the latest user message when the latest assistant message exists",
            ),
        )

    latest_turn_id = None
    if latest.metadata and isinstance(latest.metadata, dict):
        latest_turn_id = latest.metadata.get("request_id")
    if not latest_turn_id or not isinstance(latest_turn_id, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_make_error(
                "MISSING_REQUEST_ID",
                "Latest assistant message is missing request_id metadata",
            ),
        )

    turn = store.get_turn(latest_turn_id)
    if (
        turn is None
        or turn.session_id != session_id
        or turn.user_message_id != message_id
        or turn.assistant_message_id != latest.id
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_make_error(
                "NOT_LATEST_MESSAGE",
                "Can only edit the latest turn's user message",
            ),
        )

    updated = store.update_message(message_id, content=content, metadata=msg.metadata)
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_make_error("STORAGE_ERROR", "Failed to update message"),
        )

    return updated


# =============================================================================
# Turn
# =============================================================================


@router.post("/sessions/{session_id}/turn", response_model=TurnResponse)
async def create_turn(
    request: Request,
    session_id: str,
    body: TurnRequest,
) -> TurnResponse:
    """
    Execute a chat turn (user message -> assistant response).

    Idempotent behavior:
    - If request_id exists and status=completed and payload_hash matches: return cached messages.
    - If request_id exists and status=pending: 409.
    - If request_id exists and payload_hash differs: 409.
    """
    store = _get_chat_store(request)
    rag_service = getattr(request.app.state, "rag_service", None)

    request_id = (body.request_id or "").strip()
    if not request_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_make_error("MISSING_REQUEST_ID", "request_id is required"),
        )

    query = (body.query or "").strip()
    if not query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_make_error("EMPTY_QUERY", "Query cannot be empty"),
        )

    session = store.get_session(session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_make_error("SESSION_NOT_FOUND", f"Session {session_id} not found"),
        )

    # User requirement override: ignore per-request mode and always use hybrid.
    mode = DEFAULT_CHAT_MODE

    # Multimodal: decode + persist image, and use img sha for idempotency hash.
    img_path: Optional[str] = None
    img_sha16: Optional[str] = None
    if body.multimodal_content and body.multimodal_content.img_base64:
        upload_dir = _get_upload_dir(request)
        try:
            image_bytes, ext = _decode_image_base64(
                img_base64=body.multimodal_content.img_base64
            )
            img_path, img_sha16 = _persist_query_image_bytes(
                image_bytes=image_bytes, upload_dir=upload_dir, ext=ext
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=_make_error("MULTIMODAL_INVALID", str(exc)),
            ) from exc

    payload_hash = _compute_turn_payload_hash(
        body=body, mode=mode, image_sha16=img_sha16
    )

    existing = store.get_turn(request_id)
    if existing is not None:
        if existing.payload_hash != payload_hash:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=_make_error(
                    "IDEMPOTENCY_CONFLICT",
                    "request_id exists but payload differs",
                    extra={
                        "existing_status": existing.status.value,
                        "expected_hash": existing.payload_hash,
                        "received_hash": payload_hash,
                    },
                ),
            )

        if existing.status == TurnStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=_make_error(
                    "IDEMPOTENCY_CONFLICT",
                    "Turn is currently in progress",
                    extra={"existing_status": existing.status.value},
                ),
            )

        user_message = (
            store.get_message(existing.user_message_id)
            if existing.user_message_id
            else None
        )
        assistant_message = (
            store.get_message(existing.assistant_message_id)
            if existing.assistant_message_id
            else None
        )

        if user_message is None:
            # This should not happen if the DB is consistent; surface a clear server error.
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=_make_error(
                    "STORAGE_ERROR",
                    "Turn record exists but referenced user message is missing",
                    extra={"turn_id": request_id},
                ),
            )

        return TurnResponse(
            turn_id=request_id,
            status=existing.status,
            user_message=user_message,
            assistant_message=assistant_message,
            error=(
                {
                    "code": "LLM_ERROR",
                    "message": existing.error_detail or "Unknown error",
                }
                if existing.status == TurnStatus.FAILED
                else None
            ),
        )

    # Create turn row (pending). Handle concurrent duplicate creation gracefully.
    try:
        store.create_turn(request_id, session_id, payload_hash)
    except sqlite3.IntegrityError:
        existing = store.get_turn(request_id)
        if existing is None:
            raise
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_make_error(
                "IDEMPOTENCY_CONFLICT",
                "Turn was created concurrently",
                extra={"existing_status": existing.status.value},
            ),
        )

    user_metadata: dict[str, Any] = {"mode": mode, "request_id": request_id}
    if img_path:
        user_metadata["img_path"] = img_path
        if body.multimodal_content and body.multimodal_content.img_mime_type:
            user_metadata["img_mime_type"] = body.multimodal_content.img_mime_type

    # Write user message (short transaction).
    try:
        user_message = store.append_message(
            session_id=session_id,
            role="user",
            content=query,
            metadata=user_metadata,
        )
        store.update_turn_user_message(request_id, user_message.id)
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to write user message: %s", exc, exc_info=True)
        try:
            store.fail_turn(request_id, f"Failed to write user message: {exc}")
        except Exception:  # noqa: BLE001
            logger.warning("Failed to mark turn failed after write-user error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_make_error("STORAGE_ERROR", "Failed to write user message"),
        ) from exc

    # Assemble history outside of any DB transaction.
    try:
        recent = store.get_recent_messages(
            session_id=session_id,
            limit=body.history_limit,
            max_tokens=body.max_history_tokens,
        )
        conversation_history = [
            {"role": msg.role.value, "content": msg.content}
            for msg in recent
            if msg.id != user_message.id
        ]
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to load history: %s", exc)
        conversation_history = []

    # Call RAG service (no DB lock held!).
    if rag_service is None:
        llm_error = "RAG service not available"
        assistant_content = None
    else:
        kwargs: dict[str, Any] = {}
        if body.max_tokens is not None:
            kwargs["max_tokens"] = body.max_tokens
        if body.temperature is not None:
            kwargs["temperature"] = body.temperature
        if conversation_history:
            kwargs["conversation_history"] = conversation_history

        try:
            if img_path and hasattr(rag_service, "query_with_multimodal"):
                assistant_content = await rag_service.query_with_multimodal(
                    query=query,
                    multimodal_content=[{"type": "image", "img_path": img_path}],
                    mode=mode,
                    bypass_cache=True,
                    **kwargs,
                )
            else:
                assistant_content = await rag_service.query(
                    query=query, mode=mode, bypass_cache=True, **kwargs
                )
            llm_error = None
        except Exception as exc:  # noqa: BLE001
            logger.error("RAG service query failed: %s", exc, exc_info=True)
            assistant_content = None
            llm_error = str(exc)

    if not isinstance(assistant_content, str) or assistant_content is None:
        error_detail = llm_error or "Query pipeline returned no response"
        try:
            store.fail_turn(request_id, error_detail)
        except Exception:  # noqa: BLE001
            logger.warning("Failed to mark turn failed after LLM error")
        return TurnResponse(
            turn_id=request_id,
            status=TurnStatus.FAILED,
            user_message=user_message,
            assistant_message=None,
            error={"code": "LLM_ERROR", "message": error_detail},
        )

    assistant_content = _sanitize_external_images_in_markdown(assistant_content)

    # Auto-attach retrieved images (if enabled)
    config = getattr(request.app.state, "config", None)
    if config and rag_service:
        assistant_content = await _maybe_attach_retrieved_images(
            assistant_content=assistant_content,
            query=query,
            conversation_history=conversation_history,
            rag_service=rag_service,
            config=config,
            mode=mode,
        )

    # Write assistant message + complete turn (short transaction).
    try:
        assistant_message = store.append_message(
            session_id=session_id,
            role="assistant",
            content=assistant_content,
            metadata={"mode": mode, "request_id": request_id},
        )
        store.complete_turn(request_id, user_message.id, assistant_message.id)

        # Update title only when still default (do not override user rename).
        if session.title == "New Chat":
            store.update_session(session_id, title=query)

        return TurnResponse(
            turn_id=request_id,
            status=TurnStatus.COMPLETED,
            user_message=user_message,
            assistant_message=assistant_message,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to persist assistant message: %s", exc, exc_info=True)
        try:
            store.fail_turn(request_id, f"Failed to write assistant message: {exc}")
        except Exception:  # noqa: BLE001
            logger.warning("Failed to mark turn failed after write-assistant error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_make_error("STORAGE_ERROR", "Failed to write assistant message"),
        ) from exc


@router.post("/sessions/{session_id}/turn:stream")
async def create_turn_stream(
    request: Request,
    session_id: str,
    body: TurnRequest,
) -> StreamingResponse:
    """
    Execute a chat turn with SSE streaming output.

    Event schema (SSE `data:` JSON):
    - {"type": "delta", "delta": "<text chunk>"}
    - {"type": "final", "response": <TurnResponse JSON>}

    Note: If the underlying provider doesn't support true streaming, this may
    yield a single delta containing the full response.
    """
    store = _get_chat_store(request)
    rag_service = getattr(request.app.state, "rag_service", None)

    request_id = (body.request_id or "").strip()
    if not request_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_make_error("MISSING_REQUEST_ID", "request_id is required"),
        )

    query = (body.query or "").strip()
    if not query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_make_error("EMPTY_QUERY", "Query cannot be empty"),
        )

    session = store.get_session(session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_make_error("SESSION_NOT_FOUND", f"Session {session_id} not found"),
        )

    # User requirement override: ignore per-request mode and always use hybrid.
    mode = DEFAULT_CHAT_MODE

    # Multimodal: decode + persist image, and use img sha for idempotency hash.
    img_path: Optional[str] = None
    img_sha16: Optional[str] = None
    if body.multimodal_content and body.multimodal_content.img_base64:
        upload_dir = _get_upload_dir(request)
        try:
            image_bytes, ext = _decode_image_base64(
                img_base64=body.multimodal_content.img_base64
            )
            img_path, img_sha16 = _persist_query_image_bytes(
                image_bytes=image_bytes, upload_dir=upload_dir, ext=ext
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=_make_error("MULTIMODAL_INVALID", str(exc)),
            ) from exc

    payload_hash = _compute_turn_payload_hash(
        body=body, mode=mode, image_sha16=img_sha16
    )

    existing = store.get_turn(request_id)
    if existing is not None:
        if existing.payload_hash != payload_hash:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=_make_error(
                    "IDEMPOTENCY_CONFLICT",
                    "request_id exists but payload differs",
                    extra={
                        "existing_status": existing.status.value,
                        "expected_hash": existing.payload_hash,
                        "received_hash": payload_hash,
                    },
                ),
            )

        if existing.status == TurnStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=_make_error(
                    "IDEMPOTENCY_CONFLICT",
                    "Turn is currently in progress",
                    extra={"existing_status": existing.status.value},
                ),
            )

        user_message = (
            store.get_message(existing.user_message_id)
            if existing.user_message_id
            else None
        )
        assistant_message = (
            store.get_message(existing.assistant_message_id)
            if existing.assistant_message_id
            else None
        )

        if user_message is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=_make_error(
                    "STORAGE_ERROR",
                    "Turn record exists but referenced user message is missing",
                    extra={"turn_id": request_id},
                ),
            )

        cached = TurnResponse(
            turn_id=request_id,
            status=existing.status,
            user_message=user_message,
            assistant_message=assistant_message,
            error=(
                {
                    "code": "LLM_ERROR",
                    "message": existing.error_detail or "Unknown error",
                }
                if existing.status == TurnStatus.FAILED
                else None
            ),
        )

        async def _replay() -> Any:
            if assistant_message is not None and assistant_message.content:
                yield _sse({"type": "delta", "delta": assistant_message.content})
            yield _sse({"type": "final", "response": cached.model_dump()})

        return StreamingResponse(
            _replay(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    # Create turn row (pending). Handle concurrent duplicate creation gracefully.
    try:
        store.create_turn(request_id, session_id, payload_hash)
    except sqlite3.IntegrityError:
        existing = store.get_turn(request_id)
        if existing is None:
            raise
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_make_error(
                "IDEMPOTENCY_CONFLICT",
                "Turn was created concurrently",
                extra={"existing_status": existing.status.value},
            ),
        )

    user_metadata: dict[str, Any] = {"mode": mode, "request_id": request_id}
    if img_path:
        user_metadata["img_path"] = img_path
        if body.multimodal_content and body.multimodal_content.img_mime_type:
            user_metadata["img_mime_type"] = body.multimodal_content.img_mime_type

    # Write user message (short transaction).
    try:
        user_message = store.append_message(
            session_id=session_id,
            role="user",
            content=query,
            metadata=user_metadata,
        )
        store.update_turn_user_message(request_id, user_message.id)
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to write user message: %s", exc, exc_info=True)
        try:
            store.fail_turn(request_id, f"Failed to write user message: {exc}")
        except Exception:  # noqa: BLE001
            logger.warning("Failed to mark turn failed after write-user error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_make_error("STORAGE_ERROR", "Failed to write user message"),
        ) from exc

    # Assemble history outside of any DB transaction.
    try:
        recent = store.get_recent_messages(
            session_id=session_id,
            limit=body.history_limit,
            max_tokens=body.max_history_tokens,
        )
        conversation_history = [
            {"role": msg.role.value, "content": msg.content}
            for msg in recent
            if msg.id != user_message.id
        ]
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to load history: %s", exc)
        conversation_history = []

    kwargs: dict[str, Any] = {}
    if body.max_tokens is not None:
        kwargs["max_tokens"] = body.max_tokens
    if body.temperature is not None:
        kwargs["temperature"] = body.temperature
    if conversation_history:
        kwargs["conversation_history"] = conversation_history

    async def _run() -> Any:
        assistant_parts: list[str] = []
        llm_error: Optional[str] = None
        cancelled = False

        try:
            if rag_service is None:
                llm_error = "RAG service not available"
            elif img_path and hasattr(rag_service, "query_with_multimodal"):
                # Multimodal streaming is not guaranteed; fall back to one-shot.
                assistant_content = await rag_service.query_with_multimodal(
                    query=query,
                    multimodal_content=[{"type": "image", "img_path": img_path}],
                    mode=mode,
                    bypass_cache=True,
                    **kwargs,
                )
                if isinstance(assistant_content, str) and assistant_content:
                    assistant_parts.append(assistant_content)
                    yield _sse({"type": "delta", "delta": assistant_content})
                else:
                    llm_error = "Query pipeline returned no response"
            else:
                # Prefer a dedicated streaming API if present; otherwise try lightrag stream=True.
                if hasattr(rag_service, "query_stream"):
                    stream_iter = rag_service.query_stream(
                        query=query, mode=mode, bypass_cache=True, **kwargs
                    )
                else:
                    stream_iter = None

                if stream_iter is None:
                    assistant_content = await rag_service.query(
                        query=query, mode=mode, bypass_cache=True, **kwargs
                    )
                    if isinstance(assistant_content, str) and assistant_content:
                        assistant_parts.append(assistant_content)
                        yield _sse({"type": "delta", "delta": assistant_content})
                    else:
                        llm_error = "Query pipeline returned no response"
                else:
                    async for chunk in stream_iter:
                        if await request.is_disconnected():
                            llm_error = "Client disconnected"
                            cancelled = True
                            break
                        text = str(chunk or "")
                        if not text:
                            continue
                        assistant_parts.append(text)
                        yield _sse({"type": "delta", "delta": text})

        except asyncio.CancelledError:
            llm_error = "Cancelled"
            cancelled = True
        except Exception as exc:  # noqa: BLE001
            logger.error("RAG service stream failed: %s", exc, exc_info=True)
            llm_error = str(exc)

        assistant_content = "".join(assistant_parts) if assistant_parts else None

        if cancelled:
            error_detail = llm_error or "Cancelled"
            try:
                store.fail_turn(request_id, error_detail)
            except Exception:  # noqa: BLE001
                logger.warning("Failed to mark turn failed after cancellation")

            final = TurnResponse(
                turn_id=request_id,
                status=TurnStatus.FAILED,
                user_message=user_message,
                assistant_message=None,
                error={"code": "LLM_ERROR", "message": error_detail},
            )
            yield _sse({"type": "final", "response": final.model_dump()})
            return

        if not isinstance(assistant_content, str) or assistant_content is None:
            error_detail = llm_error or "Query pipeline returned no response"
            try:
                store.fail_turn(request_id, error_detail)
            except Exception:  # noqa: BLE001
                logger.warning("Failed to mark turn failed after LLM error")

            final = TurnResponse(
                turn_id=request_id,
                status=TurnStatus.FAILED,
                user_message=user_message,
                assistant_message=None,
                error={"code": "LLM_ERROR", "message": error_detail},
            )
            yield _sse({"type": "final", "response": final.model_dump()})
            return

        assistant_content = _sanitize_external_images_in_markdown(assistant_content)

        # Auto-attach retrieved images (if enabled)
        config = getattr(request.app.state, "config", None)
        if config and rag_service:
            assistant_content = await _maybe_attach_retrieved_images(
                assistant_content=assistant_content,
                query=query,
                conversation_history=conversation_history,
                rag_service=rag_service,
                config=config,
                mode=mode,
            )

        # Write assistant message + complete turn (short transaction).
        try:
            assistant_message = store.append_message(
                session_id=session_id,
                role="assistant",
                content=assistant_content,
                metadata={"mode": mode, "request_id": request_id},
            )
            store.complete_turn(request_id, user_message.id, assistant_message.id)

            # Update title only when still default (do not override user rename).
            if session.title == "New Chat":
                store.update_session(session_id, title=query)

            final = TurnResponse(
                turn_id=request_id,
                status=TurnStatus.COMPLETED,
                user_message=user_message,
                assistant_message=assistant_message,
                error=None,
            )
            yield _sse({"type": "final", "response": final.model_dump()})
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "Failed to persist assistant message (stream): %s", exc, exc_info=True
            )
            try:
                store.fail_turn(request_id, f"Failed to write assistant message: {exc}")
            except Exception:  # noqa: BLE001
                logger.warning("Failed to mark turn failed after write-assistant error")

            final = TurnResponse(
                turn_id=request_id,
                status=TurnStatus.FAILED,
                user_message=user_message,
                assistant_message=None,
                error={
                    "code": "STORAGE_ERROR",
                    "message": "Failed to write assistant message",
                },
            )
            yield _sse({"type": "final", "response": final.model_dump()})

    return StreamingResponse(
        _run(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# =============================================================================
# Message Retry (Regenerate)
# =============================================================================


@router.post(
    "/sessions/{session_id}/messages/{assistant_message_id}/retry",
    response_model=ChatMessage,
)
async def retry_assistant_message(
    request: Request,
    session_id: str,
    assistant_message_id: str,
    body: RetryAssistantRequest = Body(default_factory=RetryAssistantRequest),
) -> ChatMessage:
    """
    Regenerate an assistant message by re-running the underlying user prompt.

    Notes:
    - For now, we only allow retrying the *latest* message in the session to avoid
      creating inconsistent histories (branching is not yet modeled in storage).
    - Retry history is stored in the assistant message metadata as:
      - metadata.variants: string[]
      - metadata.variant_index: number (0-based active index)
    """
    store = _get_chat_store(request)
    rag_service = getattr(request.app.state, "rag_service", None)

    session = store.get_session(session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_make_error("SESSION_NOT_FOUND", f"Session {session_id} not found"),
        )

    assistant_message = store.get_message(assistant_message_id)
    if assistant_message is None or assistant_message.session_id != session_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_make_error(
                "MESSAGE_NOT_FOUND",
                f"Assistant message {assistant_message_id} not found",
            ),
        )
    if assistant_message.role.value != "assistant":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_make_error("BAD_REQUEST", "Only assistant messages can be retried"),
        )

    latest = store.get_latest_message(session_id)
    if latest is None or latest.id != assistant_message_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_make_error(
                "NOT_LATEST_MESSAGE",
                "Can only retry the latest assistant message in the session",
            ),
        )

    turn_id = None
    if assistant_message.metadata and isinstance(assistant_message.metadata, dict):
        turn_id = assistant_message.metadata.get("request_id")
    if not turn_id or not isinstance(turn_id, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_make_error(
                "MISSING_REQUEST_ID",
                "Assistant message is missing request_id metadata (cannot retry)",
            ),
        )

    turn = store.get_turn(turn_id)
    if turn is None or turn.session_id != session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_make_error(
                "TURN_NOT_FOUND",
                "Turn not found for assistant message (cannot retry)",
            ),
        )
    if not turn.user_message_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_make_error(
                "STORAGE_ERROR",
                "Turn record missing user_message_id (cannot retry)",
                extra={"turn_id": turn_id},
            ),
        )

    user_message = store.get_message(turn.user_message_id)
    if user_message is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_make_error(
                "STORAGE_ERROR",
                "Referenced user message is missing (cannot retry)",
                extra={"turn_id": turn_id},
            ),
        )

    query = (user_message.content or "").strip()
    if not query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_make_error("EMPTY_QUERY", "Query cannot be empty"),
        )

    # User requirement override: ignore per-request mode and always use hybrid.
    mode = DEFAULT_CHAT_MODE

    # Assemble history up to (but excluding) this user message.
    try:
        history_msgs = store.get_messages_before(
            session_id=session_id,
            before_message_id=user_message.id,
            limit=body.history_limit,
            max_tokens=body.max_history_tokens,
        )
        conversation_history = [
            {"role": msg.role.value, "content": msg.content} for msg in history_msgs
        ]
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to load history for retry: %s", exc)
        conversation_history = []

    if rag_service is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_make_error("LLM_ERROR", "RAG service not available"),
        )

    kwargs: dict[str, Any] = {}
    if body.max_tokens is not None:
        kwargs["max_tokens"] = body.max_tokens
    if body.temperature is not None:
        kwargs["temperature"] = body.temperature
    if conversation_history:
        kwargs["conversation_history"] = conversation_history

    # Multimodal: re-use persisted image path from the original user message if present.
    img_path = None
    if user_message.metadata and isinstance(user_message.metadata, dict):
        img_path = user_message.metadata.get("img_path")

    try:
        if img_path and hasattr(rag_service, "query_with_multimodal"):
            assistant_content = await rag_service.query_with_multimodal(
                query=query,
                multimodal_content=[{"type": "image", "img_path": img_path}],
                mode=mode,
                bypass_cache=True,
                **kwargs,
            )
        else:
            assistant_content = await rag_service.query(
                query=query, mode=mode, bypass_cache=True, **kwargs
            )
    except Exception as exc:  # noqa: BLE001
        logger.error("RAG service retry failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_make_error("LLM_ERROR", str(exc)),
        ) from exc

    if not isinstance(assistant_content, str) or not assistant_content:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_make_error("LLM_ERROR", "Query pipeline returned no response"),
        )

    assistant_content = _sanitize_external_images_in_markdown(assistant_content)

    # Auto-attach retrieved images (if enabled)
    config = getattr(request.app.state, "config", None)
    if config and rag_service:
        assistant_content = await _maybe_attach_retrieved_images(
            assistant_content=assistant_content,
            query=query,
            conversation_history=conversation_history,
            rag_service=rag_service,
            config=config,
            mode=mode,
        )

    # Update assistant message in-place, keeping a variants history in metadata.
    meta = dict(assistant_message.metadata or {})
    variants = meta.get("variants")
    if not isinstance(variants, list) or not all(isinstance(v, str) for v in variants):
        variants = [assistant_message.content]

    variants.append(assistant_content)
    meta["variants"] = variants
    meta["variant_index"] = len(variants) - 1

    updated = store.update_message(
        assistant_message_id, content=assistant_content, metadata=meta
    )
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_make_error("STORAGE_ERROR", "Failed to update assistant message"),
        )

    return updated


# =============================================================================
# Message Retry (Regenerate) - Streaming
# =============================================================================


@router.post(
    "/sessions/{session_id}/messages/{assistant_message_id}/retry:stream",
)
async def retry_assistant_message_stream(
    request: Request,
    session_id: str,
    assistant_message_id: str,
    body: RetryAssistantRequest = Body(default_factory=RetryAssistantRequest),
) -> StreamingResponse:
    """
    Regenerate an assistant message via SSE streaming.

    Emits:
    - {"type":"delta","delta":"..."} for each chunk
    - {"type":"final","message":{...ChatMessage...}} when complete
    - {"type":"error","error":{"code":"...","message":"..."}} on failure
    """
    store = _get_chat_store(request)
    rag_service = getattr(request.app.state, "rag_service", None)

    # Validation (same as non-streaming)
    session = store.get_session(session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_make_error("SESSION_NOT_FOUND", f"Session {session_id} not found"),
        )

    assistant_message = store.get_message(assistant_message_id)
    if assistant_message is None or assistant_message.session_id != session_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_make_error(
                "MESSAGE_NOT_FOUND",
                f"Assistant message {assistant_message_id} not found",
            ),
        )
    if assistant_message.role.value != "assistant":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_make_error("BAD_REQUEST", "Only assistant messages can be retried"),
        )

    latest = store.get_latest_message(session_id)
    if latest is None or latest.id != assistant_message_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_make_error(
                "NOT_LATEST_MESSAGE",
                "Can only retry the latest assistant message in the session",
            ),
        )

    turn_id = None
    if assistant_message.metadata and isinstance(assistant_message.metadata, dict):
        turn_id = assistant_message.metadata.get("request_id")
    if not turn_id or not isinstance(turn_id, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_make_error(
                "MISSING_REQUEST_ID",
                "Assistant message is missing request_id metadata (cannot retry)",
            ),
        )

    turn = store.get_turn(turn_id)
    if turn is None or turn.session_id != session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_make_error(
                "TURN_NOT_FOUND",
                "Turn not found for assistant message (cannot retry)",
            ),
        )
    if not turn.user_message_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_make_error(
                "STORAGE_ERROR",
                "Turn record missing user_message_id (cannot retry)",
                extra={"turn_id": turn_id},
            ),
        )

    user_message = store.get_message(turn.user_message_id)
    if user_message is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_make_error(
                "STORAGE_ERROR",
                "Referenced user message is missing (cannot retry)",
                extra={"turn_id": turn_id},
            ),
        )

    query = (user_message.content or "").strip()
    if not query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_make_error("EMPTY_QUERY", "Query cannot be empty"),
        )

    mode = DEFAULT_CHAT_MODE

    # Assemble history
    try:
        history_msgs = store.get_messages_before(
            session_id=session_id,
            before_message_id=user_message.id,
            limit=body.history_limit,
            max_tokens=body.max_history_tokens,
        )
        conversation_history = [
            {"role": msg.role.value, "content": msg.content} for msg in history_msgs
        ]
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to load history for retry stream: %s", exc)
        conversation_history = []

    if rag_service is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_make_error("LLM_ERROR", "RAG service not available"),
        )

    kwargs: dict[str, Any] = {}
    if body.max_tokens is not None:
        kwargs["max_tokens"] = body.max_tokens
    if body.temperature is not None:
        kwargs["temperature"] = body.temperature
    if conversation_history:
        kwargs["conversation_history"] = conversation_history

    # Multimodal: re-use persisted image path from the original user message if present.
    img_path = None
    if user_message.metadata and isinstance(user_message.metadata, dict):
        img_path = user_message.metadata.get("img_path")

    # Capture values for streaming generator closure
    _store = store
    _assistant_message = assistant_message
    _assistant_message_id = assistant_message_id

    async def _run() -> AsyncGenerator[str, None]:
        assistant_parts: list[str] = []
        llm_error: str | None = None
        cancelled = False

        try:
            if img_path and hasattr(rag_service, "query_with_multimodal_stream"):
                stream_iter = rag_service.query_with_multimodal_stream(
                    query=query,
                    multimodal_content=[{"type": "image", "img_path": img_path}],
                    mode=mode,
                    bypass_cache=True,
                    **kwargs,
                )
            elif img_path and hasattr(rag_service, "query_with_multimodal"):
                # Fallback: non-streaming multimodal
                assistant_content = await rag_service.query_with_multimodal(
                    query=query,
                    multimodal_content=[{"type": "image", "img_path": img_path}],
                    mode=mode,
                    bypass_cache=True,
                    **kwargs,
                )
                if isinstance(assistant_content, str) and assistant_content:
                    assistant_parts.append(assistant_content)
                    yield _sse({"type": "delta", "delta": assistant_content})
                else:
                    llm_error = "Query pipeline returned no response"
                stream_iter = None
            elif hasattr(rag_service, "query_stream"):
                stream_iter = rag_service.query_stream(
                    query=query, mode=mode, bypass_cache=True, **kwargs
                )
            else:
                stream_iter = None

            if stream_iter is None and not assistant_parts and not llm_error:
                assistant_content = await rag_service.query(
                    query=query, mode=mode, bypass_cache=True, **kwargs
                )
                if isinstance(assistant_content, str) and assistant_content:
                    assistant_parts.append(assistant_content)
                    yield _sse({"type": "delta", "delta": assistant_content})
                else:
                    llm_error = "Query pipeline returned no response"
            elif stream_iter is not None:
                async for chunk in stream_iter:
                    if await request.is_disconnected():
                        llm_error = "Client disconnected"
                        cancelled = True
                        break
                    text = str(chunk or "")
                    if not text:
                        continue
                    assistant_parts.append(text)
                    yield _sse({"type": "delta", "delta": text})

        except asyncio.CancelledError:
            llm_error = "Cancelled"
            cancelled = True
        except Exception as exc:  # noqa: BLE001
            logger.error("RAG service retry stream failed: %s", exc, exc_info=True)
            llm_error = str(exc)

        assistant_content = "".join(assistant_parts) if assistant_parts else None

        if cancelled or not isinstance(assistant_content, str) or not assistant_content:
            error_msg = llm_error or "Query pipeline returned no response"
            yield _sse({"type": "error", "error": {"code": "LLM_ERROR", "message": error_msg}})
            return

        assistant_content = _sanitize_external_images_in_markdown(assistant_content)

        # Auto-attach retrieved images (if enabled)
        config = getattr(request.app.state, "config", None)
        if config and rag_service:
            assistant_content = await _maybe_attach_retrieved_images(
                assistant_content=assistant_content,
                query=query,
                conversation_history=conversation_history,
                rag_service=rag_service,
                config=config,
                mode=mode,
            )

        # Update assistant message in-place, keeping a variants history in metadata.
        meta = dict(_assistant_message.metadata or {})
        variants = meta.get("variants")
        if not isinstance(variants, list) or not all(isinstance(v, str) for v in variants):
            variants = [_assistant_message.content]

        variants.append(assistant_content)
        meta["variants"] = variants
        meta["variant_index"] = len(variants) - 1

        updated = _store.update_message(
            _assistant_message_id, content=assistant_content, metadata=meta
        )
        if updated is None:
            yield _sse({"type": "error", "error": {"code": "STORAGE_ERROR", "message": "Failed to update assistant message"}})
            return

        yield _sse({"type": "final", "message": updated.model_dump()})

    return StreamingResponse(
        _run(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
