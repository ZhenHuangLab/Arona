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
import time
import sqlite3
from pathlib import Path
from typing import Any, Optional

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
