"""
Tests for ChatStore - SQLite-based chat session, message, and turn storage.

Covers:
- Session CRUD (create, get, list, update, delete)
- Soft delete filtering
- Message append/list with pagination
- Turn idempotency helpers
- Light concurrency check
"""

import os
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from backend.services.chat_store import (
    ChatStore,
    compute_payload_hash,
    decode_cursor,
    encode_cursor,
)
from backend.models.chat import TurnStatus


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def chat_store():
    """Create ChatStore with temp DB for test isolation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_chat.db")
        store = ChatStore(db_path=db_path)
        yield store


@pytest.fixture
def session_with_messages(chat_store):
    """Create a session with some messages for testing."""
    session = chat_store.create_session(title="Test Session")
    messages = []
    for i in range(5):
        msg = chat_store.append_message(
            session_id=session.id,
            role="user" if i % 2 == 0 else "assistant",
            content=f"Message {i}",
            token_count=10,
        )
        messages.append(msg)
        # Small delay to ensure distinct timestamps
        time.sleep(0.01)
    return session, messages


# =============================================================================
# Cursor Tests
# =============================================================================


class TestCursor:
    """Test cursor encoding/decoding."""

    def test_encode_decode_roundtrip(self):
        """Cursor should roundtrip correctly."""
        ts = "2024-01-15T10:30:00.123Z"
        id_ = "abc-123-def"
        cursor = encode_cursor("updated_at", ts, id_)
        decoded_ts, decoded_id = decode_cursor(cursor)
        assert decoded_ts == ts
        assert decoded_id == id_

    def test_decode_invalid_cursor(self):
        """Invalid cursor should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid cursor"):
            decode_cursor("not-valid-base64!!!")

    def test_decode_malformed_json(self):
        """Malformed JSON in cursor should raise ValueError."""
        import base64

        bad_cursor = base64.urlsafe_b64encode(b"not json").decode()
        with pytest.raises(ValueError, match="Invalid cursor"):
            decode_cursor(bad_cursor)


class TestPayloadHash:
    """Test payload hash computation."""

    def test_compute_payload_hash_deterministic(self):
        """Same payload should produce same hash."""
        payload = {"query": "hello", "mode": "hybrid"}
        hash1 = compute_payload_hash(payload)
        hash2 = compute_payload_hash(payload)
        assert hash1 == hash2

    def test_compute_payload_hash_key_order_independent(self):
        """Hash should be independent of key order."""
        payload1 = {"a": 1, "b": 2}
        payload2 = {"b": 2, "a": 1}
        assert compute_payload_hash(payload1) == compute_payload_hash(payload2)

    def test_compute_payload_hash_different_values(self):
        """Different values should produce different hashes."""
        hash1 = compute_payload_hash({"query": "hello"})
        hash2 = compute_payload_hash({"query": "world"})
        assert hash1 != hash2


# =============================================================================
# Session CRUD Tests
# =============================================================================


class TestSessionCRUD:
    """Test session create/read/update/delete operations."""

    def test_create_session_default_title(self, chat_store):
        """Create session with default title."""
        session = chat_store.create_session()
        assert session.id is not None
        assert session.title == "New Chat"
        assert session.deleted_at is None
        assert session.created_at is not None
        assert session.updated_at is not None

    def test_create_session_custom_title(self, chat_store):
        """Create session with custom title."""
        session = chat_store.create_session(title="My Chat")
        assert session.title == "My Chat"

    def test_create_session_with_metadata(self, chat_store):
        """Create session with metadata."""
        metadata = {"theme": "dark", "language": "en"}
        session = chat_store.create_session(title="Test", metadata=metadata)
        assert session.metadata == metadata

    def test_create_session_title_truncation(self, chat_store):
        """Long titles should be truncated to 100 chars."""
        long_title = "A" * 150
        session = chat_store.create_session(title=long_title)
        assert len(session.title) == 100

    def test_get_session(self, chat_store):
        """Get existing session by ID."""
        created = chat_store.create_session(title="Test")
        fetched = chat_store.get_session(created.id)
        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.title == created.title

    def test_get_session_not_found(self, chat_store):
        """Get non-existent session returns None."""
        result = chat_store.get_session("non-existent-id")
        assert result is None

    def test_get_session_soft_deleted_returns_none(self, chat_store):
        """Get soft-deleted session returns None."""
        session = chat_store.create_session()
        chat_store.delete_session(session.id, hard=False)
        result = chat_store.get_session(session.id)
        assert result is None

    def test_update_session_title(self, chat_store):
        """Update session title."""
        session = chat_store.create_session(title="Original")
        updated = chat_store.update_session(session.id, title="Updated")
        assert updated is not None
        assert updated.title == "Updated"
        assert updated.updated_at > session.updated_at

    def test_update_session_metadata_merge(self, chat_store):
        """Update session metadata merges with existing."""
        session = chat_store.create_session(metadata={"a": 1, "b": 2})
        updated = chat_store.update_session(session.id, metadata={"b": 3, "c": 4})
        assert updated.metadata == {"a": 1, "b": 3, "c": 4}

    def test_update_session_not_found(self, chat_store):
        """Update non-existent session returns None."""
        result = chat_store.update_session("non-existent", title="New")
        assert result is None

    def test_delete_session_soft(self, chat_store):
        """Soft delete sets deleted_at."""
        session = chat_store.create_session()
        result = chat_store.delete_session(session.id, hard=False)
        assert result is True

        # Session should not appear in get
        assert chat_store.get_session(session.id) is None

        # But deleted_at should be set
        deleted_at = chat_store.get_session_deleted_at(session.id)
        assert deleted_at is not None

    def test_delete_session_hard(self, chat_store):
        """Hard delete removes from database."""
        session = chat_store.create_session()
        result = chat_store.delete_session(session.id, hard=True)
        assert result is True

        # Session should be completely gone
        deleted_at = chat_store.get_session_deleted_at(session.id)
        assert deleted_at is None

    def test_delete_session_not_found(self, chat_store):
        """Delete non-existent session returns False."""
        result = chat_store.delete_session("non-existent")
        assert result is False


# =============================================================================
# List Sessions Tests
# =============================================================================


class TestListSessions:
    """Test session listing with pagination and search."""

    def test_list_sessions_empty(self, chat_store):
        """List sessions when none exist."""
        result = chat_store.list_sessions()
        assert result.sessions == []
        assert result.next_cursor is None
        assert result.has_more is False

    def test_list_sessions_basic(self, chat_store):
        """List sessions returns created sessions."""
        s1 = chat_store.create_session(title="Session 1")
        time.sleep(0.01)
        s2 = chat_store.create_session(title="Session 2")

        result = chat_store.list_sessions()
        assert len(result.sessions) == 2
        # Should be in DESC order (newest first)
        assert result.sessions[0].id == s2.id
        assert result.sessions[1].id == s1.id

    def test_list_sessions_excludes_soft_deleted(self, chat_store):
        """List sessions excludes soft-deleted sessions."""
        s1 = chat_store.create_session(title="Active")
        s2 = chat_store.create_session(title="Deleted")
        chat_store.delete_session(s2.id, hard=False)

        result = chat_store.list_sessions()
        assert len(result.sessions) == 1
        assert result.sessions[0].id == s1.id

    def test_list_sessions_pagination(self, chat_store):
        """List sessions supports cursor pagination."""
        # Create 5 sessions
        sessions = []
        for i in range(5):
            s = chat_store.create_session(title=f"Session {i}")
            sessions.append(s)
            time.sleep(0.01)

        # First page (limit 2)
        page1 = chat_store.list_sessions(limit=2)
        assert len(page1.sessions) == 2
        assert page1.has_more is True
        assert page1.next_cursor is not None

        # Second page
        page2 = chat_store.list_sessions(limit=2, cursor=page1.next_cursor)
        assert len(page2.sessions) == 2
        assert page2.has_more is True

        # Third page
        page3 = chat_store.list_sessions(limit=2, cursor=page2.next_cursor)
        assert len(page3.sessions) == 1
        assert page3.has_more is False
        assert page3.next_cursor is None

        # All sessions should be unique
        all_ids = [s.id for s in page1.sessions + page2.sessions + page3.sessions]
        assert len(set(all_ids)) == 5

    def test_list_sessions_search(self, chat_store):
        """List sessions supports title search."""
        chat_store.create_session(title="Hello World")
        chat_store.create_session(title="Goodbye World")
        chat_store.create_session(title="Something Else")

        result = chat_store.list_sessions(q="World")
        assert len(result.sessions) == 2

        result = chat_store.list_sessions(q="Hello")
        assert len(result.sessions) == 1

    def test_list_sessions_with_message_stats(self, chat_store, session_with_messages):
        """List sessions includes message count and preview."""
        session, messages = session_with_messages

        result = chat_store.list_sessions()
        assert len(result.sessions) == 1
        assert result.sessions[0].message_count == 5
        assert result.sessions[0].last_message_preview is not None

    def test_list_sessions_invalid_cursor(self, chat_store):
        """Invalid cursor raises ValueError."""
        with pytest.raises(ValueError, match="INVALID_CURSOR"):
            chat_store.list_sessions(cursor="invalid!!!")


# =============================================================================
# Message CRUD Tests
# =============================================================================


class TestMessageCRUD:
    """Test message append and list operations."""

    def test_append_message(self, chat_store):
        """Append message to session."""
        session = chat_store.create_session()
        message = chat_store.append_message(
            session_id=session.id,
            role="user",
            content="Hello!",
        )
        assert message.id is not None
        assert message.session_id == session.id
        assert message.role.value == "user"
        assert message.content == "Hello!"

    def test_append_message_updates_session_updated_at(self, chat_store):
        """Appending message updates session's updated_at."""
        session = chat_store.create_session()
        original_updated = session.updated_at

        time.sleep(0.02)
        chat_store.append_message(session.id, "user", "Hello")

        updated_session = chat_store.get_session(session.id)
        assert updated_session.updated_at > original_updated

    def test_append_message_with_metadata(self, chat_store):
        """Append message with metadata."""
        session = chat_store.create_session()
        metadata = {"mode": "hybrid", "sources": ["doc1", "doc2"]}
        message = chat_store.append_message(
            session_id=session.id,
            role="assistant",
            content="Response",
            metadata=metadata,
        )
        assert message.metadata == metadata

    def test_append_message_with_token_count(self, chat_store):
        """Append message with token count."""
        session = chat_store.create_session()
        message = chat_store.append_message(
            session_id=session.id,
            role="user",
            content="Hello",
            token_count=5,
        )
        assert message.token_count == 5

    def test_append_message_to_deleted_session_fails(self, chat_store):
        """Appending to deleted session raises ValueError."""
        session = chat_store.create_session()
        chat_store.delete_session(session.id)

        with pytest.raises(ValueError, match="not found or deleted"):
            chat_store.append_message(session.id, "user", "Hello")

    def test_append_message_to_nonexistent_session_fails(self, chat_store):
        """Appending to non-existent session raises ValueError."""
        with pytest.raises(ValueError, match="not found or deleted"):
            chat_store.append_message("fake-id", "user", "Hello")

    def test_list_messages_empty(self, chat_store):
        """List messages for empty session."""
        session = chat_store.create_session()
        result = chat_store.list_messages(session.id)
        assert result.messages == []
        assert result.has_more is False

    def test_list_messages_returns_asc_order(self, chat_store, session_with_messages):
        """List messages returns in created_at ASC order."""
        session, messages = session_with_messages

        result = chat_store.list_messages(session.id)
        assert len(result.messages) == 5

        # Should be in ASC order (oldest first)
        for i, msg in enumerate(result.messages):
            assert msg.content == f"Message {i}"

    def test_list_messages_pagination(self, chat_store, session_with_messages):
        """List messages supports cursor pagination."""
        session, messages = session_with_messages

        # First page (limit 2, gets newest 2)
        page1 = chat_store.list_messages(session.id, limit=2)
        assert len(page1.messages) == 2
        assert page1.has_more is True
        assert page1.next_cursor is not None
        # Page1 should contain messages 3,4 (newest) in ASC order
        assert page1.messages[0].content == "Message 3"
        assert page1.messages[1].content == "Message 4"

        # Second page (older messages)
        page2 = chat_store.list_messages(session.id, limit=2, cursor=page1.next_cursor)
        assert len(page2.messages) == 2
        assert page2.has_more is True
        # Page2 should contain messages 1,2 in ASC order
        assert page2.messages[0].content == "Message 1"
        assert page2.messages[1].content == "Message 2"

        # Third page
        page3 = chat_store.list_messages(session.id, limit=2, cursor=page2.next_cursor)
        assert len(page3.messages) == 1
        assert page3.has_more is False
        assert page3.messages[0].content == "Message 0"

    def test_list_messages_deleted_session_fails(self, chat_store):
        """List messages for deleted session raises ValueError."""
        session = chat_store.create_session()
        chat_store.delete_session(session.id)

        with pytest.raises(ValueError, match="not found or deleted"):
            chat_store.list_messages(session.id)

    def test_get_recent_messages(self, chat_store, session_with_messages):
        """Get recent messages for history assembly."""
        session, messages = session_with_messages

        recent = chat_store.get_recent_messages(session.id, limit=3)
        assert len(recent) == 3
        # Should be in ASC order (oldest first of the recent 3)
        assert recent[0].content == "Message 2"
        assert recent[1].content == "Message 3"
        assert recent[2].content == "Message 4"

    def test_delete_messages_by_session(self, chat_store, session_with_messages):
        """Delete all messages for a session."""
        session, messages = session_with_messages

        count = chat_store.delete_messages_by_session(session.id)
        assert count == 5

        result = chat_store.list_messages(session.id)
        assert len(result.messages) == 0

    def test_update_message_updates_session_updated_at(self, chat_store):
        session = chat_store.create_session()
        msg = chat_store.append_message(session.id, "assistant", "Hello", metadata={"v": 1})
        before = chat_store.get_session(session.id).updated_at

        time.sleep(0.02)
        updated = chat_store.update_message(msg.id, content="Hello v2", metadata={"v": 2})
        assert updated is not None
        assert updated.content == "Hello v2"
        assert updated.metadata == {"v": 2}

        after = chat_store.get_session(session.id).updated_at
        assert after > before

    def test_get_latest_message(self, chat_store):
        session = chat_store.create_session()
        m1 = chat_store.append_message(session.id, "user", "First")
        time.sleep(0.01)
        m2 = chat_store.append_message(session.id, "assistant", "Second")

        latest = chat_store.get_latest_message(session.id)
        assert latest is not None
        assert latest.id == m2.id

    def test_get_messages_before(self, chat_store):
        session = chat_store.create_session()
        m1 = chat_store.append_message(session.id, "user", "M1")
        time.sleep(0.01)
        m2 = chat_store.append_message(session.id, "assistant", "M2")
        time.sleep(0.01)
        m3 = chat_store.append_message(session.id, "user", "M3")

        before_m3 = chat_store.get_messages_before(
            session_id=session.id, before_message_id=m3.id, limit=10
        )
        assert [m.content for m in before_m3] == ["M1", "M2"]

        before_m2 = chat_store.get_messages_before(
            session_id=session.id, before_message_id=m2.id, limit=10
        )
        assert [m.content for m in before_m2] == ["M1"]


# =============================================================================
# Turn Idempotency Tests
# =============================================================================


class TestTurnIdempotency:
    """Test turn creation, retrieval, and status updates."""

    def test_create_and_get_turn(self, chat_store):
        """Create turn and retrieve it."""
        session = chat_store.create_session()
        turn_id = "test-request-123"
        payload_hash = compute_payload_hash({"query": "hello"})

        turn = chat_store.create_turn(turn_id, session.id, payload_hash)
        assert turn.id == turn_id
        assert turn.session_id == session.id
        assert turn.payload_hash == payload_hash
        assert turn.status == TurnStatus.PENDING

        # Retrieve
        fetched = chat_store.get_turn(turn_id)
        assert fetched is not None
        assert fetched.id == turn_id
        assert fetched.status == TurnStatus.PENDING

    def test_get_turn_not_found(self, chat_store):
        """Get non-existent turn returns None."""
        result = chat_store.get_turn("non-existent")
        assert result is None

    def test_complete_turn(self, chat_store):
        """Complete turn with message IDs."""
        session = chat_store.create_session()
        turn_id = "test-request-456"
        payload_hash = compute_payload_hash({"query": "hello"})

        # Create actual messages to satisfy FK constraints
        user_msg = chat_store.append_message(session.id, "user", "Hello")
        assistant_msg = chat_store.append_message(session.id, "assistant", "Hi there")

        chat_store.create_turn(turn_id, session.id, payload_hash)
        chat_store.complete_turn(turn_id, user_msg.id, assistant_msg.id)

        turn = chat_store.get_turn(turn_id)
        assert turn.status == TurnStatus.COMPLETED
        assert turn.user_message_id == user_msg.id
        assert turn.assistant_message_id == assistant_msg.id
        assert turn.completed_at is not None

    def test_fail_turn(self, chat_store):
        """Fail turn with error detail."""
        session = chat_store.create_session()
        turn_id = "test-request-789"
        payload_hash = compute_payload_hash({"query": "hello"})

        chat_store.create_turn(turn_id, session.id, payload_hash)
        chat_store.fail_turn(turn_id, "LLM error: timeout")

        turn = chat_store.get_turn(turn_id)
        assert turn.status == TurnStatus.FAILED
        assert turn.error_detail == "LLM error: timeout"
        assert turn.completed_at is not None

    def test_same_request_id_returns_same_record(self, chat_store):
        """Same request_id should return same turn record (idempotency check)."""
        session = chat_store.create_session()
        turn_id = "idempotent-request"
        payload_hash = compute_payload_hash({"query": "hello"})

        # Create turn
        turn1 = chat_store.create_turn(turn_id, session.id, payload_hash)

        # Get should return same record
        turn2 = chat_store.get_turn(turn_id)
        assert turn2.id == turn1.id
        assert turn2.payload_hash == turn1.payload_hash
        assert turn2.created_at == turn1.created_at


# =============================================================================
# Concurrency Tests
# =============================================================================


class TestConcurrency:
    """Light concurrency tests to verify WAL mode works."""

    def test_concurrent_session_creates(self, chat_store):
        """Concurrent session creates should not cause lock errors."""

        def create_session(i):
            return chat_store.create_session(title=f"Session {i}")

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(create_session, i) for i in range(10)]
            results = [f.result() for f in futures]

        assert len(results) == 10
        assert len(set(s.id for s in results)) == 10  # All unique IDs

    def test_concurrent_message_appends(self, chat_store):
        """Concurrent message appends should not cause lock errors."""
        session = chat_store.create_session()

        def append_message(i):
            return chat_store.append_message(
                session_id=session.id,
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i}",
            )

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(append_message, i) for i in range(10)]
            results = [f.result() for f in futures]

        assert len(results) == 10
        assert len(set(m.id for m in results)) == 10  # All unique IDs

        # Verify all messages are in the session
        all_messages = chat_store.list_messages(session.id, limit=100)
        assert len(all_messages.messages) == 10
