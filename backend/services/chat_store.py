"""
ChatStore - SQLite-based storage for chat sessions, messages, and turns.

Implements the frozen contract from T8_chat-ui-sessions-sqlite.md Phase P0.
Uses WAL mode, busy_timeout, and short-lived connections to avoid locking issues.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from backend.models.chat import (
    ChatMessage,
    ChatSession,
    ChatSessionWithStats,
    ChatTurn,
    MessageListResponse,
    MessageRole,
    SessionListResponse,
    TurnStatus,
)


logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

DEFAULT_SESSIONS_LIMIT = 20
MAX_SESSIONS_LIMIT = 100
DEFAULT_MESSAGES_LIMIT = 50
MAX_MESSAGES_LIMIT = 200
DEFAULT_BUSY_TIMEOUT_MS = 30000
SESSION_TITLE_MAX_LEN = 100
MESSAGE_PREVIEW_LEN = 50


# =============================================================================
# Cursor Helpers
# =============================================================================


def encode_cursor(timestamp_key: str, timestamp: str, id: str) -> str:
    """Encode (timestamp, id) as Base64 JSON cursor."""
    payload = json.dumps({timestamp_key: timestamp, "id": id}, separators=(",", ":"))
    return base64.urlsafe_b64encode(payload.encode("utf-8")).decode("utf-8")


def decode_cursor(cursor: str) -> tuple[str, str]:
    """
    Decode Base64 JSON cursor to (timestamp, id).

    Raises ValueError on invalid cursor.
    """
    try:
        payload = base64.urlsafe_b64decode(cursor.encode("utf-8")).decode("utf-8")
        data = json.loads(payload)
        timestamp = data.get("ts") or data.get("updated_at") or data.get("created_at")
        if not timestamp or "id" not in data:
            raise KeyError("missing required cursor fields")
        return str(timestamp), str(data["id"])
    except Exception as e:
        raise ValueError(f"Invalid cursor: {e}") from e


def compute_payload_hash(payload: dict[str, Any]) -> str:
    """Compute SHA256 hash of canonical JSON (sorted keys, no whitespace)."""
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def utc_now_iso() -> str:
    """Return current UTC time as ISO8601 string with milliseconds."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def build_fts5_query(raw_query: str) -> str:
    """
    Build a safe-ish FTS5 MATCH query from user input.

    We quote each whitespace-separated token and join with AND to reduce
    syntax errors from special characters.
    """
    tokens = [t for t in (raw_query or "").strip().split() if t]
    escaped = [t.replace('"', '""') for t in tokens]
    return " AND ".join(f'"{t}"' for t in escaped)


# =============================================================================
# ChatStore Class
# =============================================================================


class ChatStore:
    """
    SQLite-based storage for chat sessions, messages, and turns.

    Each operation creates a fresh connection to avoid cross-thread issues
    and long-held locks. WAL mode and busy_timeout are set on each connection.
    """

    def __init__(
        self,
        db_path: str = "backend/data/chat.db",
        busy_timeout_ms: int = DEFAULT_BUSY_TIMEOUT_MS,
    ):
        """
        Initialize ChatStore.

        Args:
            db_path: Path to SQLite database file.
            busy_timeout_ms: SQLite busy timeout in milliseconds.
        """
        self.db_path = db_path
        self.busy_timeout_ms = busy_timeout_ms

        # Ensure data directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        # Initialize database schema
        self.init_db()

        logger.info(f"ChatStore initialized with database: {db_path}")

    def _get_connection(self) -> sqlite3.Connection:
        """
        Create a new short-lived connection with proper PRAGMA settings.

        Returns:
            SQLite connection configured for WAL mode with row factory.
        """
        conn = sqlite3.connect(self.db_path, timeout=self.busy_timeout_ms / 1000.0)
        conn.row_factory = sqlite3.Row

        # Execute PRAGMA on every connection
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute(f"PRAGMA busy_timeout = {self.busy_timeout_ms}")

        return conn

    def init_db(self) -> None:
        """
        Initialize database schema.

        Creates tables and indexes if they don't exist.
        """
        conn = self._get_connection()
        try:
            # Table: chat_sessions
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    id              TEXT PRIMARY KEY,
                    title           TEXT NOT NULL DEFAULT 'New Chat',
                    user_id         TEXT NULL,
                    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                    updated_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                    deleted_at      TEXT NULL,
                    metadata_json   TEXT NULL
                )
            """)

            # Indexes for chat_sessions
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_updated
                ON chat_sessions(updated_at DESC)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_active
                ON chat_sessions(updated_at DESC) WHERE deleted_at IS NULL
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_user
                ON chat_sessions(user_id, updated_at DESC) WHERE user_id IS NOT NULL
            """)

            # Table: chat_messages
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id              TEXT PRIMARY KEY,
                    session_id      TEXT NOT NULL,
                    role            TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
                    content         TEXT NOT NULL,
                    token_count     INTEGER NULL,
                    user_id         TEXT NULL,
                    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                    metadata_json   TEXT NULL,
                    FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
                )
            """)

            # Index for chat_messages
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_session_created
                ON chat_messages(session_id, created_at DESC)
            """)

            # Optional: FTS5 virtual table for message content search (Phase P7).
            #
            # Notes:
            # - Some SQLite builds may not include FTS5; this is best-effort.
            # - We keep a separate FTS table synced via triggers.
            try:
                conn.execute("""
                    CREATE VIRTUAL TABLE IF NOT EXISTS chat_messages_fts USING fts5(
                        content,
                        session_id UNINDEXED,
                        message_id UNINDEXED,
                        created_at UNINDEXED
                    )
                """)
                conn.execute("""
                    CREATE TRIGGER IF NOT EXISTS chat_messages_fts_ai
                    AFTER INSERT ON chat_messages
                    BEGIN
                        INSERT INTO chat_messages_fts(rowid, content, session_id, message_id, created_at)
                        VALUES (new.rowid, new.content, new.session_id, new.id, new.created_at);
                    END
                """)
                conn.execute("""
                    CREATE TRIGGER IF NOT EXISTS chat_messages_fts_ad
                    AFTER DELETE ON chat_messages
                    BEGIN
                        DELETE FROM chat_messages_fts WHERE rowid = old.rowid;
                    END
                """)
                conn.execute("""
                    CREATE TRIGGER IF NOT EXISTS chat_messages_fts_au
                    AFTER UPDATE ON chat_messages
                    BEGIN
                        DELETE FROM chat_messages_fts WHERE rowid = old.rowid;
                        INSERT INTO chat_messages_fts(rowid, content, session_id, message_id, created_at)
                        VALUES (new.rowid, new.content, new.session_id, new.id, new.created_at);
                    END
                """)

                # Backfill existing rows (safe when upgrading an existing DB).
                conn.execute("""
                    INSERT INTO chat_messages_fts(rowid, content, session_id, message_id, created_at)
                    SELECT rowid, content, session_id, id, created_at
                    FROM chat_messages
                    WHERE rowid NOT IN (SELECT rowid FROM chat_messages_fts)
                """)
            except sqlite3.OperationalError as e:
                logger.info("FTS5 not available; skipping chat_messages_fts init: %s", e)

            # Table: chat_turns
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chat_turns (
                    id                      TEXT PRIMARY KEY,
                    session_id              TEXT NOT NULL,
                    payload_hash            TEXT NOT NULL,
                    user_message_id         TEXT NULL,
                    assistant_message_id    TEXT NULL,
                    status                  TEXT NOT NULL DEFAULT 'pending'
                        CHECK(status IN ('pending', 'completed', 'failed')),
                    error_detail            TEXT NULL,
                    created_at              TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                    completed_at            TEXT NULL,
                    FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE,
                    FOREIGN KEY (user_message_id) REFERENCES chat_messages(id) ON DELETE SET NULL,
                    FOREIGN KEY (assistant_message_id) REFERENCES chat_messages(id) ON DELETE SET NULL
                )
            """)

            # Index for chat_turns
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_turns_session
                ON chat_turns(session_id, created_at DESC)
            """)

            conn.commit()
            logger.info("ChatStore database schema initialized")

        except sqlite3.Error as e:
            logger.error(f"Failed to initialize ChatStore database: {e}", exc_info=True)
            raise
        finally:
            conn.close()

    # =========================================================================
    # Session CRUD
    # =========================================================================

    def create_session(
        self,
        title: str = "New Chat",
        metadata: Optional[dict[str, Any]] = None,
        user_id: Optional[str] = None,
    ) -> ChatSession:
        """
        Create a new chat session.

        Args:
            title: Session title (max 100 chars).
            metadata: Optional metadata dict.
            user_id: Optional user ID (reserved for multi-user).

        Returns:
            Created ChatSession.
        """
        session_id = str(uuid.uuid4())
        now = utc_now_iso()
        title = title[:SESSION_TITLE_MAX_LEN] if title else "New Chat"
        metadata_json = json.dumps(metadata) if metadata else None

        conn = self._get_connection()
        try:
            conn.execute(
                """
                INSERT INTO chat_sessions (id, title, user_id, created_at, updated_at, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (session_id, title, user_id, now, now, metadata_json),
            )
            conn.commit()

            logger.debug(f"Created session {session_id}: {title}")

            return ChatSession(
                id=session_id,
                title=title,
                user_id=user_id,
                created_at=now,
                updated_at=now,
                deleted_at=None,
                metadata=metadata,
            )

        except sqlite3.Error as e:
            logger.error(f"Failed to create session: {e}", exc_info=True)
            raise
        finally:
            conn.close()

    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """
        Get a session by ID.

        Args:
            session_id: UUID of the session.

        Returns:
            ChatSession if found and not deleted, None otherwise.
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT id, title, user_id, created_at, updated_at, deleted_at, metadata_json
                FROM chat_sessions
                WHERE id = ? AND deleted_at IS NULL
                """,
                (session_id,),
            )
            row = cursor.fetchone()

            if row is None:
                return None

            return self._row_to_session(row)

        except sqlite3.Error as e:
            logger.error(f"Failed to get session {session_id}: {e}", exc_info=True)
            raise
        finally:
            conn.close()

    def list_sessions(
        self,
        limit: int = DEFAULT_SESSIONS_LIMIT,
        cursor: Optional[str] = None,
        q: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> SessionListResponse:
        """
        List sessions with pagination and optional search.

        Args:
            limit: Max sessions to return (1-100).
            cursor: Base64 JSON cursor from previous response.
            q: Search query for title (LIKE %q%).
            user_id: Filter by user_id (reserved for multi-user).

        Returns:
            SessionListResponse with sessions, next_cursor, has_more.
        """
        limit = max(1, min(limit, MAX_SESSIONS_LIMIT))
        # Fetch one extra to determine has_more
        fetch_limit = limit + 1

        conn = self._get_connection()
        try:
            # Build query dynamically
            conditions = ["deleted_at IS NULL"]
            params: list[Any] = []

            if cursor:
                try:
                    cursor_ts, cursor_id = decode_cursor(cursor)
                    # (updated_at, id) < (cursor_ts, cursor_id) for DESC order
                    conditions.append("(updated_at, id) < (?, ?)")
                    params.extend([cursor_ts, cursor_id])
                except ValueError as e:
                    raise ValueError(f"INVALID_CURSOR: {e}") from e

            if q:
                conditions.append("title LIKE ?")
                params.append(f"%{q}%")

            if user_id:
                conditions.append("user_id = ?")
                params.append(user_id)

            where_clause = " AND ".join(conditions)
            params.append(fetch_limit)

            query = f"""
                SELECT s.id, s.title, s.user_id, s.created_at, s.updated_at,
                       s.deleted_at, s.metadata_json,
                       (SELECT COUNT(*) FROM chat_messages m WHERE m.session_id = s.id) as message_count,
                       (SELECT content FROM chat_messages m
                        WHERE m.session_id = s.id
                        ORDER BY m.created_at DESC LIMIT 1) as last_message
                FROM chat_sessions s
                WHERE {where_clause}
                ORDER BY s.updated_at DESC, s.id DESC
                LIMIT ?
            """

            cursor_result = conn.execute(query, params)
            rows = cursor_result.fetchall()

            # Determine has_more
            has_more = len(rows) > limit
            if has_more:
                rows = rows[:limit]

            sessions = []
            for row in rows:
                session = self._row_to_session_with_stats(row)
                sessions.append(session)

            # Build next_cursor from last session
            next_cursor = None
            if has_more and sessions:
                last = sessions[-1]
                next_cursor = encode_cursor("updated_at", last.updated_at, last.id)

            return SessionListResponse(
                sessions=sessions,
                next_cursor=next_cursor,
                has_more=has_more,
            )

        except sqlite3.Error as e:
            logger.error(f"Failed to list sessions: {e}", exc_info=True)
            raise
        finally:
            conn.close()

    def search_sessions(
        self,
        q: str,
        limit: int = DEFAULT_SESSIONS_LIMIT,
        cursor: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> SessionListResponse:
        """
        Search sessions by title or message content.

        Uses FTS5 on chat_messages content when available; falls back to LIKE.

        Cursor pagination follows the same convention as list_sessions:
        ordered by (updated_at DESC, id DESC) with cursor encoded from the last row.
        """
        query_text = (q or "").strip()
        if not query_text:
            return self.list_sessions(limit=limit, cursor=cursor, q=None, user_id=user_id)

        limit = max(1, min(limit, MAX_SESSIONS_LIMIT))
        fetch_limit = limit + 1

        conn = self._get_connection()
        try:
            conditions = ["s.deleted_at IS NULL"]
            params: list[Any] = []

            if cursor:
                try:
                    cursor_ts, cursor_id = decode_cursor(cursor)
                    conditions.append("(s.updated_at, s.id) < (?, ?)")
                    params.extend([cursor_ts, cursor_id])
                except ValueError as e:
                    raise ValueError(f"INVALID_CURSOR: {e}") from e

            if user_id:
                conditions.append("s.user_id = ?")
                params.append(user_id)

            where_clause = " AND ".join(conditions)
            like_q = f"%{query_text}%"

            # Prefer FTS5 when available.
            fts_q = build_fts5_query(query_text)
            if not fts_q:
                fts_q = f'"{query_text.replace(chr(34), chr(34) * 2)}"'

            base_select = f"""
                SELECT s.id, s.title, s.user_id, s.created_at, s.updated_at,
                       s.deleted_at, s.metadata_json,
                       (SELECT COUNT(*) FROM chat_messages m WHERE m.session_id = s.id) as message_count,
                       (SELECT content FROM chat_messages m
                        WHERE m.session_id = s.id
                        ORDER BY m.created_at DESC LIMIT 1) as last_message
                FROM chat_sessions s
                WHERE {where_clause}
                  AND (
                    s.title LIKE ?
                    OR EXISTS (
                        SELECT 1
                        FROM chat_messages_fts f
                        WHERE f.session_id = s.id
                          AND f.content MATCH ?
                    )
                  )
                ORDER BY s.updated_at DESC, s.id DESC
                LIMIT ?
            """

            try:
                cursor_result = conn.execute(
                    base_select,
                    [*params, like_q, fts_q, fetch_limit],
                )
            except sqlite3.OperationalError:
                # Fallback to LIKE search on chat_messages when FTS5 is unavailable.
                fallback_select = f"""
                    SELECT s.id, s.title, s.user_id, s.created_at, s.updated_at,
                           s.deleted_at, s.metadata_json,
                           (SELECT COUNT(*) FROM chat_messages m WHERE m.session_id = s.id) as message_count,
                           (SELECT content FROM chat_messages m
                            WHERE m.session_id = s.id
                            ORDER BY m.created_at DESC LIMIT 1) as last_message
                    FROM chat_sessions s
                    WHERE {where_clause}
                      AND (
                        s.title LIKE ?
                        OR EXISTS (
                            SELECT 1
                            FROM chat_messages m
                            WHERE m.session_id = s.id
                              AND m.content LIKE ?
                        )
                      )
                    ORDER BY s.updated_at DESC, s.id DESC
                    LIMIT ?
                """
                cursor_result = conn.execute(
                    fallback_select,
                    [*params, like_q, like_q, fetch_limit],
                )

            rows = cursor_result.fetchall()

            has_more = len(rows) > limit
            if has_more:
                rows = rows[:limit]

            sessions = [self._row_to_session_with_stats(row) for row in rows]

            next_cursor = None
            if has_more and sessions:
                last = sessions[-1]
                next_cursor = encode_cursor("updated_at", last.updated_at, last.id)

            return SessionListResponse(
                sessions=sessions,
                next_cursor=next_cursor,
                has_more=has_more,
            )

        except sqlite3.Error as e:
            logger.error("Failed to search sessions: %s", e, exc_info=True)
            raise
        finally:
            conn.close()

    def update_session(
        self,
        session_id: str,
        title: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Optional[ChatSession]:
        """
        Update a session's title and/or metadata.

        Args:
            session_id: UUID of the session.
            title: New title (optional).
            metadata: New metadata to merge (optional).

        Returns:
            Updated ChatSession, or None if not found.
        """
        if title is None and metadata is None:
            return self.get_session(session_id)

        conn = self._get_connection()
        try:
            # Get existing session
            cursor = conn.execute(
                """
                SELECT id, title, user_id, created_at, updated_at, deleted_at, metadata_json
                FROM chat_sessions
                WHERE id = ? AND deleted_at IS NULL
                """,
                (session_id,),
            )
            row = cursor.fetchone()

            if row is None:
                return None

            # Build update
            now = utc_now_iso()
            new_title = title[:SESSION_TITLE_MAX_LEN] if title else row["title"]

            # Merge metadata
            existing_metadata = json.loads(row["metadata_json"]) if row["metadata_json"] else {}
            if metadata:
                existing_metadata.update(metadata)
            new_metadata_json = json.dumps(existing_metadata) if existing_metadata else None

            conn.execute(
                """
                UPDATE chat_sessions
                SET title = ?, metadata_json = ?, updated_at = ?
                WHERE id = ?
                """,
                (new_title, new_metadata_json, now, session_id),
            )
            conn.commit()

            logger.debug(f"Updated session {session_id}")

            return ChatSession(
                id=session_id,
                title=new_title,
                user_id=row["user_id"],
                created_at=row["created_at"],
                updated_at=now,
                deleted_at=None,
                metadata=existing_metadata if existing_metadata else None,
            )

        except sqlite3.Error as e:
            logger.error(f"Failed to update session {session_id}: {e}", exc_info=True)
            raise
        finally:
            conn.close()

    def delete_session(self, session_id: str, hard: bool = False) -> bool:
        """
        Delete a session (soft delete by default, hard delete optional).

        Args:
            session_id: UUID of the session.
            hard: If True, physically delete; otherwise soft delete.

        Returns:
            True if session was found and deleted, False otherwise.
        """
        conn = self._get_connection()
        try:
            if hard:
                # Hard delete - CASCADE will delete messages and turns
                cursor = conn.execute(
                    "DELETE FROM chat_sessions WHERE id = ?",
                    (session_id,),
                )
            else:
                # Soft delete - set deleted_at
                now = utc_now_iso()
                cursor = conn.execute(
                    """
                    UPDATE chat_sessions
                    SET deleted_at = ?
                    WHERE id = ? AND deleted_at IS NULL
                    """,
                    (now, session_id),
                )

            conn.commit()
            deleted = cursor.rowcount > 0

            if deleted:
                logger.debug(f"{'Hard' if hard else 'Soft'} deleted session {session_id}")

            return deleted

        except sqlite3.Error as e:
            logger.error(f"Failed to delete session {session_id}: {e}", exc_info=True)
            raise
        finally:
            conn.close()

    def get_session_deleted_at(self, session_id: str) -> Optional[str]:
        """Get the deleted_at timestamp for a session (for delete response)."""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT deleted_at FROM chat_sessions WHERE id = ?",
                (session_id,),
            )
            row = cursor.fetchone()
            return row["deleted_at"] if row else None
        finally:
            conn.close()

    # =========================================================================
    # Message CRUD
    # =========================================================================

    def append_message(
        self,
        session_id: str,
        role: str,
        content: str,
        token_count: Optional[int] = None,
        metadata: Optional[dict[str, Any]] = None,
        user_id: Optional[str] = None,
    ) -> ChatMessage:
        """
        Append a message to a session.

        Also updates the session's updated_at timestamp.

        Args:
            session_id: UUID of the parent session.
            role: Message role (user, assistant, system).
            content: Message content.
            token_count: Optional token count for truncation.
            metadata: Optional metadata dict.
            user_id: Optional user ID.

        Returns:
            Created ChatMessage.

        Raises:
            ValueError: If session doesn't exist or is deleted.
        """
        message_id = str(uuid.uuid4())
        now = utc_now_iso()
        metadata_json = json.dumps(metadata) if metadata else None

        conn = self._get_connection()
        try:
            # Verify session exists and is not deleted
            cursor = conn.execute(
                "SELECT id FROM chat_sessions WHERE id = ? AND deleted_at IS NULL",
                (session_id,),
            )
            if cursor.fetchone() is None:
                raise ValueError(f"Session {session_id} not found or deleted")

            # Insert message
            conn.execute(
                """
                INSERT INTO chat_messages
                (id, session_id, role, content, token_count, user_id, created_at, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (message_id, session_id, role, content, token_count, user_id, now, metadata_json),
            )

            # Update session's updated_at
            conn.execute(
                "UPDATE chat_sessions SET updated_at = ? WHERE id = ?",
                (now, session_id),
            )

            conn.commit()

            logger.debug(f"Appended {role} message {message_id} to session {session_id}")

            return ChatMessage(
                id=message_id,
                session_id=session_id,
                role=MessageRole(role),
                content=content,
                token_count=token_count,
                user_id=user_id,
                created_at=now,
                metadata=metadata,
            )

        except sqlite3.Error as e:
            logger.error(f"Failed to append message to session {session_id}: {e}", exc_info=True)
            raise
        finally:
            conn.close()

    def get_message(self, message_id: str) -> Optional[ChatMessage]:
        """
        Get a message by ID.

        Args:
            message_id: UUID of the message.

        Returns:
            ChatMessage if found, None otherwise.
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT id, session_id, role, content, token_count, user_id,
                       created_at, metadata_json
                FROM chat_messages
                WHERE id = ?
                """,
                (message_id,),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return self._row_to_message(row)
        except sqlite3.Error as e:
            logger.error(f"Failed to get message {message_id}: {e}", exc_info=True)
            raise
        finally:
            conn.close()

    def list_messages(
        self,
        session_id: str,
        limit: int = DEFAULT_MESSAGES_LIMIT,
        cursor: Optional[str] = None,
    ) -> MessageListResponse:
        """
        List messages for a session with pagination.

        Messages are queried DESC for cursor pagination but returned in ASC order.

        Args:
            session_id: UUID of the session.
            limit: Max messages to return (1-200).
            cursor: Base64 JSON cursor for loading older messages.

        Returns:
            MessageListResponse with messages (ASC order), next_cursor, has_more.
        """
        limit = max(1, min(limit, MAX_MESSAGES_LIMIT))
        fetch_limit = limit + 1

        conn = self._get_connection()
        try:
            # Verify session exists and is not deleted
            check_cursor = conn.execute(
                "SELECT id FROM chat_sessions WHERE id = ? AND deleted_at IS NULL",
                (session_id,),
            )
            if check_cursor.fetchone() is None:
                raise ValueError(f"Session {session_id} not found or deleted")

            conditions = ["session_id = ?"]
            params: list[Any] = [session_id]

            if cursor:
                try:
                    cursor_ts, cursor_id = decode_cursor(cursor)
                    # (created_at, id) < (cursor_ts, cursor_id) for DESC query
                    conditions.append("(created_at, id) < (?, ?)")
                    params.extend([cursor_ts, cursor_id])
                except ValueError as e:
                    raise ValueError(f"INVALID_CURSOR: {e}") from e

            where_clause = " AND ".join(conditions)
            params.append(fetch_limit)

            # Query DESC for pagination
            query = f"""
                SELECT id, session_id, role, content, token_count, user_id,
                       created_at, metadata_json
                FROM chat_messages
                WHERE {where_clause}
                ORDER BY created_at DESC, id DESC
                LIMIT ?
            """

            result_cursor = conn.execute(query, params)
            rows = result_cursor.fetchall()

            # Determine has_more
            has_more = len(rows) > limit
            if has_more:
                rows = rows[:limit]

            # Convert rows to messages
            messages = [self._row_to_message(row) for row in rows]

            # Build next_cursor from oldest message in this batch
            next_cursor = None
            if has_more and messages:
                oldest = messages[-1]  # Last in DESC order = oldest
                next_cursor = encode_cursor("created_at", oldest.created_at, oldest.id)

            # Reverse to ASC order for response
            messages.reverse()

            return MessageListResponse(
                messages=messages,
                next_cursor=next_cursor,
                has_more=has_more,
            )

        except sqlite3.Error as e:
            logger.error(f"Failed to list messages for session {session_id}: {e}", exc_info=True)
            raise
        finally:
            conn.close()

    def get_recent_messages(
        self,
        session_id: str,
        limit: int = 20,
        max_tokens: Optional[int] = None,
    ) -> list[ChatMessage]:
        """
        Get recent messages for history assembly.

        Returns messages in ASC order (oldest first) for conversation history.

        Args:
            session_id: UUID of the session.
            limit: Max messages to return.
            max_tokens: Optional token budget (truncate from oldest if exceeded).

        Returns:
            List of ChatMessage in ASC order.
        """
        conn = self._get_connection()
        try:
            # Query most recent messages DESC, then reverse
            cursor = conn.execute(
                """
                SELECT id, session_id, role, content, token_count, user_id,
                       created_at, metadata_json
                FROM chat_messages
                WHERE session_id = ?
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (session_id, limit),
            )
            rows = cursor.fetchall()

            messages = [self._row_to_message(row) for row in rows]

            # Reverse to ASC order
            messages.reverse()

            # Apply token budget if specified
            if max_tokens and messages:
                total_tokens = 0
                truncated = []
                # Process from newest to oldest
                for msg in reversed(messages):
                    msg_tokens = msg.token_count or 0
                    if total_tokens + msg_tokens <= max_tokens:
                        truncated.insert(0, msg)
                        total_tokens += msg_tokens
                    else:
                        break
                messages = truncated

            return messages

        except sqlite3.Error as e:
            logger.error(f"Failed to get recent messages for session {session_id}: {e}", exc_info=True)
            raise
        finally:
            conn.close()

    def delete_messages_by_session(self, session_id: str) -> int:
        """
        Delete all messages for a session.

        Args:
            session_id: UUID of the session.

        Returns:
            Number of messages deleted.
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "DELETE FROM chat_messages WHERE session_id = ?",
                (session_id,),
            )
            conn.commit()
            count = cursor.rowcount
            logger.debug(f"Deleted {count} messages from session {session_id}")
            return count

        except sqlite3.Error as e:
            logger.error(f"Failed to delete messages for session {session_id}: {e}", exc_info=True)
            raise
        finally:
            conn.close()

    # =========================================================================
    # Turn Helpers (Idempotency)
    # =========================================================================

    def get_turn(self, turn_id: str) -> Optional[ChatTurn]:
        """
        Get a turn by request_id.

        Args:
            turn_id: The request_id (UUID).

        Returns:
            ChatTurn if found, None otherwise.
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT id, session_id, payload_hash, user_message_id, assistant_message_id,
                       status, error_detail, created_at, completed_at
                FROM chat_turns
                WHERE id = ?
                """,
                (turn_id,),
            )
            row = cursor.fetchone()

            if row is None:
                return None

            return self._row_to_turn(row)

        except sqlite3.Error as e:
            logger.error(f"Failed to get turn {turn_id}: {e}", exc_info=True)
            raise
        finally:
            conn.close()

    def create_turn(
        self,
        turn_id: str,
        session_id: str,
        payload_hash: str,
    ) -> ChatTurn:
        """
        Create a new turn with status=pending.

        Args:
            turn_id: The request_id from client.
            session_id: UUID of the parent session.
            payload_hash: SHA256 hash of canonical request JSON.

        Returns:
            Created ChatTurn.
        """
        now = utc_now_iso()

        conn = self._get_connection()
        try:
            conn.execute(
                """
                INSERT INTO chat_turns (id, session_id, payload_hash, status, created_at)
                VALUES (?, ?, ?, 'pending', ?)
                """,
                (turn_id, session_id, payload_hash, now),
            )
            conn.commit()

            logger.debug(f"Created turn {turn_id} for session {session_id}")

            return ChatTurn(
                id=turn_id,
                session_id=session_id,
                payload_hash=payload_hash,
                user_message_id=None,
                assistant_message_id=None,
                status=TurnStatus.PENDING,
                error_detail=None,
                created_at=now,
                completed_at=None,
            )

        except sqlite3.Error as e:
            logger.error(f"Failed to create turn {turn_id}: {e}", exc_info=True)
            raise
        finally:
            conn.close()

    def complete_turn(
        self,
        turn_id: str,
        user_message_id: str,
        assistant_message_id: str,
    ) -> None:
        """
        Mark a turn as completed with message IDs.

        Args:
            turn_id: The request_id.
            user_message_id: UUID of the user message.
            assistant_message_id: UUID of the assistant message.
        """
        now = utc_now_iso()

        conn = self._get_connection()
        try:
            conn.execute(
                """
                UPDATE chat_turns
                SET status = 'completed',
                    user_message_id = ?,
                    assistant_message_id = ?,
                    completed_at = ?
                WHERE id = ?
                """,
                (user_message_id, assistant_message_id, now, turn_id),
            )
            conn.commit()
            logger.debug(f"Completed turn {turn_id}")

        except sqlite3.Error as e:
            logger.error(f"Failed to complete turn {turn_id}: {e}", exc_info=True)
            raise
        finally:
            conn.close()

    def fail_turn(self, turn_id: str, error_detail: str) -> None:
        """
        Mark a turn as failed with error detail.

        Args:
            turn_id: The request_id.
            error_detail: Error description.
        """
        now = utc_now_iso()

        conn = self._get_connection()
        try:
            conn.execute(
                """
                UPDATE chat_turns
                SET status = 'failed',
                    error_detail = ?,
                    completed_at = ?
                WHERE id = ?
                """,
                (error_detail, now, turn_id),
            )
            conn.commit()
            logger.debug(f"Failed turn {turn_id}: {error_detail}")

        except sqlite3.Error as e:
            logger.error(f"Failed to fail turn {turn_id}: {e}", exc_info=True)
            raise
        finally:
            conn.close()

    def update_turn_user_message(self, turn_id: str, user_message_id: str) -> None:
        """
        Update turn with user_message_id (before LLM call).

        Args:
            turn_id: The request_id.
            user_message_id: UUID of the user message.
        """
        conn = self._get_connection()
        try:
            conn.execute(
                "UPDATE chat_turns SET user_message_id = ? WHERE id = ?",
                (user_message_id, turn_id),
            )
            conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Failed to update turn {turn_id} user message: {e}", exc_info=True)
            raise
        finally:
            conn.close()

    # =========================================================================
    # Row Conversion Helpers
    # =========================================================================

    def _row_to_session(self, row: sqlite3.Row) -> ChatSession:
        """Convert SQLite row to ChatSession."""
        metadata = json.loads(row["metadata_json"]) if row["metadata_json"] else None
        return ChatSession(
            id=row["id"],
            title=row["title"],
            user_id=row["user_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            deleted_at=row["deleted_at"],
            metadata=metadata,
        )

    def _row_to_session_with_stats(self, row: sqlite3.Row) -> ChatSessionWithStats:
        """Convert SQLite row (with stats) to ChatSessionWithStats."""
        metadata = json.loads(row["metadata_json"]) if row["metadata_json"] else None
        last_message = row["last_message"]
        preview = None
        if last_message:
            preview = last_message[:MESSAGE_PREVIEW_LEN]
            if len(last_message) > MESSAGE_PREVIEW_LEN:
                preview += "..."

        return ChatSessionWithStats(
            id=row["id"],
            title=row["title"],
            user_id=row["user_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            deleted_at=row["deleted_at"],
            metadata=metadata,
            message_count=row["message_count"],
            last_message_preview=preview,
        )

    def _row_to_message(self, row: sqlite3.Row) -> ChatMessage:
        """Convert SQLite row to ChatMessage."""
        metadata = json.loads(row["metadata_json"]) if row["metadata_json"] else None
        return ChatMessage(
            id=row["id"],
            session_id=row["session_id"],
            role=MessageRole(row["role"]),
            content=row["content"],
            token_count=row["token_count"],
            user_id=row["user_id"],
            created_at=row["created_at"],
            metadata=metadata,
        )

    def _row_to_turn(self, row: sqlite3.Row) -> ChatTurn:
        """Convert SQLite row to ChatTurn."""
        return ChatTurn(
            id=row["id"],
            session_id=row["session_id"],
            payload_hash=row["payload_hash"],
            user_message_id=row["user_message_id"],
            assistant_message_id=row["assistant_message_id"],
            status=TurnStatus(row["status"]),
            error_detail=row["error_detail"],
            created_at=row["created_at"],
            completed_at=row["completed_at"],
        )
