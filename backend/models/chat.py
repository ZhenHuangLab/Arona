"""
Pydantic models for Chat API - sessions, messages, turns.

Follows the frozen contract from T8_chat-ui-sessions-sqlite.md Phase P0.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# =============================================================================
# Enums
# =============================================================================


class MessageRole(str, Enum):
    """Message role enum matching SQLite CHECK constraint."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class TurnStatus(str, Enum):
    """Turn status enum matching SQLite CHECK constraint."""

    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


# =============================================================================
# Core Domain Models
# =============================================================================


class ChatSession(BaseModel):
    """Chat session model."""

    id: str = Field(..., description="UUID of the session")
    title: str = Field(default="New Chat", max_length=100)
    user_id: Optional[str] = Field(default=None, description="Reserved for multi-user")
    created_at: str = Field(..., description="ISO8601 timestamp")
    updated_at: str = Field(..., description="ISO8601 timestamp")
    deleted_at: Optional[str] = Field(default=None, description="Soft delete timestamp")
    metadata: Optional[dict[str, Any]] = Field(
        default=None, description="Extension JSON"
    )


class ChatSessionWithStats(ChatSession):
    """Chat session with computed stats for list responses."""

    message_count: int = Field(default=0, description="Number of messages in session")
    last_message_preview: Optional[str] = Field(
        default=None, description="Preview of last message (truncated to 50 chars)"
    )


class ChatMessage(BaseModel):
    """Chat message model."""

    id: str = Field(..., description="UUID of the message")
    session_id: str = Field(..., description="UUID of parent session")
    role: MessageRole = Field(..., description="user, assistant, or system")
    content: str = Field(..., description="Message content")
    token_count: Optional[int] = Field(
        default=None, description="Token count for truncation"
    )
    user_id: Optional[str] = Field(default=None, description="Reserved for multi-user")
    created_at: str = Field(..., description="ISO8601 timestamp")
    metadata: Optional[dict[str, Any]] = Field(
        default=None, description="mode, img_path, error, sources, etc."
    )


class ChatTurn(BaseModel):
    """Chat turn model for idempotency tracking."""

    id: str = Field(..., description="request_id from client (UUID)")
    session_id: str = Field(..., description="UUID of parent session")
    payload_hash: str = Field(..., description="SHA256 of canonical request JSON")
    user_message_id: Optional[str] = Field(default=None)
    assistant_message_id: Optional[str] = Field(default=None)
    status: TurnStatus = Field(default=TurnStatus.PENDING)
    error_detail: Optional[str] = Field(default=None)
    created_at: str = Field(..., description="ISO8601 timestamp")
    completed_at: Optional[str] = Field(default=None)


# =============================================================================
# Request Models
# =============================================================================


class CreateSessionRequest(BaseModel):
    """Request body for POST /api/chat/sessions."""

    title: Optional[str] = Field(default="New Chat", max_length=100)
    metadata: Optional[dict[str, Any]] = Field(default=None)


class UpdateSessionRequest(BaseModel):
    """Request body for PATCH /api/chat/sessions/{session_id}."""

    title: Optional[str] = Field(default=None, max_length=100)
    metadata: Optional[dict[str, Any]] = Field(default=None)


class MultimodalContent(BaseModel):
    """Multimodal content for turn requests."""

    img_base64: Optional[str] = Field(
        default=None, description="Base64 image (will be persisted)"
    )
    img_mime_type: Optional[str] = Field(default=None, description="e.g., image/png")


class TurnRequest(BaseModel):
    """Request body for POST /api/chat/sessions/{session_id}/turn."""

    request_id: str = Field(..., description="UUID for idempotency (required)")
    query: str = Field(..., min_length=1, description="User message content")
    mode: str = Field(default="hybrid", description="Query mode")
    multimodal_content: Optional[MultimodalContent] = Field(default=None)
    max_tokens: Optional[int] = Field(default=None)
    temperature: Optional[float] = Field(default=None)
    history_limit: int = Field(
        default=20, description="Max recent messages for history"
    )
    max_history_tokens: int = Field(
        default=8000, description="Token budget for history"
    )


# =============================================================================
# Response Models
# =============================================================================


class SessionListResponse(BaseModel):
    """Response for GET /api/chat/sessions."""

    sessions: list[ChatSessionWithStats]
    next_cursor: Optional[str] = Field(
        default=None, description="Base64(JSON) cursor for next page"
    )
    has_more: bool = Field(default=False)


class MessageListResponse(BaseModel):
    """Response for GET /api/chat/sessions/{session_id}/messages."""

    messages: list[ChatMessage] = Field(
        ..., description="Messages in created_at ASC order"
    )
    next_cursor: Optional[str] = Field(
        default=None, description="Base64(JSON) cursor for loading older messages"
    )
    has_more: bool = Field(default=False)


class DeleteSessionResponse(BaseModel):
    """Response for DELETE /api/chat/sessions/{session_id}."""

    id: str
    deleted: bool = True
    hard: bool = False
    deleted_at: Optional[str] = Field(
        default=None, description="Timestamp for soft delete"
    )


class TurnResponse(BaseModel):
    """Response for POST /api/chat/sessions/{session_id}/turn."""

    turn_id: str = Field(..., description="Same as request_id")
    status: TurnStatus
    user_message: ChatMessage
    assistant_message: Optional[ChatMessage] = Field(default=None)
    error: Optional[dict[str, str]] = Field(default=None)


# =============================================================================
# Error Response Models
# =============================================================================


class ErrorDetail(BaseModel):
    """Unified error detail shape."""

    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable description")
    extra: Optional[dict[str, Any]] = Field(
        default=None, description="Additional context"
    )


class ErrorResponse(BaseModel):
    """Unified error response shape."""

    detail: ErrorDetail
