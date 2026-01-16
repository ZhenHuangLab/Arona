"""
Tests for Chat API Router (/api/chat).

NOTE: Does NOT import backend.main (requires model env vars).
Instead creates a minimal FastAPI app with:
- app.state.chat_store: temp ChatStore DB
- app.state.rag_service: lightweight async mock
- app.state.config: SimpleNamespace with upload_dir
"""

from __future__ import annotations

import os
import tempfile
import uuid
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Optional

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.routers.chat import router
from backend.services.chat_store import ChatStore


# =============================================================================
# Test Fixtures
# =============================================================================


class MockRAGService:
    """Lightweight mock RAG service for testing."""

    def __init__(self, response: str = "This is a mock response."):
        self.response = response
        self.call_count = 0
        self.last_query = None
        self.should_fail = False
        self.fail_message = "Mock error"

    async def query(
        self,
        query: str,
        mode: str = "hybrid",
        **kwargs: Any,
    ) -> str:
        """Mock query method."""
        self.call_count += 1
        self.last_query = query
        if self.should_fail:
            raise RuntimeError(self.fail_message)
        return self.response

    async def query_stream(
        self,
        query: str,
        mode: str = "hybrid",
        **kwargs: Any,
    ):
        """Mock streaming query method."""
        self.call_count += 1
        self.last_query = query
        if self.should_fail:
            raise RuntimeError(self.fail_message)

        parts = [self.response[i : i + 5] for i in range(0, len(self.response), 5)]
        for part in parts:
            yield part

    async def query_with_multimodal(
        self,
        query: str,
        multimodal_content: Optional[list] = None,
        mode: str = "hybrid",
        **kwargs: Any,
    ) -> str:
        """Mock multimodal query method."""
        self.call_count += 1
        self.last_query = query
        if self.should_fail:
            raise RuntimeError(self.fail_message)
        return f"{self.response} (with image)"


@pytest.fixture
def temp_db_path(tmp_path: Path) -> str:
    """Create a temporary database path."""
    return str(tmp_path / "test_chat.db")


@pytest.fixture
def temp_upload_dir(tmp_path: Path) -> str:
    """Create a temporary upload directory."""
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    return str(upload_dir)


@pytest.fixture
def chat_store(temp_db_path: str) -> ChatStore:
    """Create a ChatStore with temporary database."""
    return ChatStore(db_path=temp_db_path)


@pytest.fixture
def mock_rag_service() -> MockRAGService:
    """Create a mock RAG service."""
    return MockRAGService()


@pytest.fixture
def mock_config(temp_upload_dir: str) -> SimpleNamespace:
    """Create a mock config with upload_dir."""
    return SimpleNamespace(upload_dir=temp_upload_dir)


@pytest.fixture
def app(chat_store: ChatStore, mock_rag_service: MockRAGService, mock_config: SimpleNamespace) -> FastAPI:
    """Create a minimal FastAPI app for testing."""
    app = FastAPI()
    app.state.chat_store = chat_store
    app.state.rag_service = mock_rag_service
    app.state.config = mock_config
    app.include_router(router, prefix="/api/chat")
    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create a test client."""
    return TestClient(app)


# =============================================================================
# Session CRUD Tests
# =============================================================================


class TestCreateSession:
    """Tests for POST /sessions."""

    def test_create_session_default_title(self, client: TestClient):
        """Create session with default title."""
        response = client.post("/api/chat/sessions", json={})
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["title"] == "New Chat"
        assert data["deleted_at"] is None

    def test_create_session_custom_title(self, client: TestClient):
        """Create session with custom title."""
        response = client.post("/api/chat/sessions", json={"title": "My Test Chat"})
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "My Test Chat"

    def test_create_session_with_metadata(self, client: TestClient):
        """Create session with metadata."""
        metadata = {"key": "value", "nested": {"a": 1}}
        response = client.post(
            "/api/chat/sessions",
            json={"title": "With Metadata", "metadata": metadata},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["metadata"] == metadata

    def test_create_session_long_title_rejected(self, client: TestClient):
        """Long title (> 100 chars) should be rejected by validation."""
        long_title = "x" * 150
        response = client.post("/api/chat/sessions", json={"title": long_title})
        # Pydantic rejects titles > 100 chars with 422
        assert response.status_code == 422


class TestListSessions:
    """Tests for GET /sessions."""

    def test_list_sessions_empty(self, client: TestClient):
        """List sessions when none exist."""
        response = client.get("/api/chat/sessions")
        assert response.status_code == 200
        data = response.json()
        assert data["sessions"] == []
        assert data["has_more"] is False
        assert data["next_cursor"] is None

    def test_list_sessions_with_data(self, client: TestClient):
        """List sessions with data."""
        # Create a few sessions
        for i in range(3):
            client.post("/api/chat/sessions", json={"title": f"Chat {i}"})

        response = client.get("/api/chat/sessions")
        assert response.status_code == 200
        data = response.json()
        assert len(data["sessions"]) == 3

    def test_list_sessions_pagination(self, client: TestClient):
        """List sessions with pagination."""
        # Create 5 sessions
        for i in range(5):
            client.post("/api/chat/sessions", json={"title": f"Chat {i}"})

        # Get first page (limit=2)
        response = client.get("/api/chat/sessions?limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["sessions"]) == 2
        assert data["has_more"] is True
        assert data["next_cursor"] is not None

        # Get next page
        response = client.get(f"/api/chat/sessions?limit=2&cursor={data['next_cursor']}")
        assert response.status_code == 200
        data2 = response.json()
        assert len(data2["sessions"]) == 2
        assert data2["has_more"] is True

    def test_list_sessions_search(self, client: TestClient):
        """List sessions with search filter."""
        client.post("/api/chat/sessions", json={"title": "Hello World"})
        client.post("/api/chat/sessions", json={"title": "Goodbye World"})
        client.post("/api/chat/sessions", json={"title": "Something Else"})

        response = client.get("/api/chat/sessions?q=World")
        assert response.status_code == 200
        data = response.json()
        assert len(data["sessions"]) == 2

    def test_list_sessions_invalid_cursor(self, client: TestClient):
        """Invalid cursor should return 400."""
        response = client.get("/api/chat/sessions?cursor=invalid-base64")
        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["code"] == "INVALID_CURSOR"


class TestSearchSessions:
    """Tests for GET /search."""

    def test_search_matches_message_content(self, client: TestClient):
        """Search should match sessions by chat message content (not only title)."""
        # Create two sessions with non-default titles to avoid auto-title updates.
        s1 = client.post("/api/chat/sessions", json={"title": "Session One"}).json()
        s2 = client.post("/api/chat/sessions", json={"title": "Session Two"}).json()

        # Create turns so messages exist in each session.
        client.post(
            f"/api/chat/sessions/{s1['id']}/turn",
            json={"request_id": str(uuid.uuid4()), "query": "needle term in message"},
        )
        client.post(
            f"/api/chat/sessions/{s2['id']}/turn",
            json={"request_id": str(uuid.uuid4()), "query": "haystack term"},
        )

        resp = client.get("/api/chat/search?q=needle")
        assert resp.status_code == 200
        data = resp.json()
        ids = [s["id"] for s in data["sessions"]]
        assert s1["id"] in ids
        assert s2["id"] not in ids

    def test_search_invalid_cursor(self, client: TestClient):
        resp = client.get("/api/chat/search?q=test&cursor=invalid-base64")
        assert resp.status_code == 400
        data = resp.json()
        assert data["detail"]["code"] == "INVALID_CURSOR"


class TestGetSession:
    """Tests for GET /sessions/{session_id}."""

    def test_get_session_exists(self, client: TestClient):
        """Get an existing session."""
        create_resp = client.post("/api/chat/sessions", json={"title": "Test"})
        session_id = create_resp.json()["id"]

        response = client.get(f"/api/chat/sessions/{session_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == session_id
        assert data["title"] == "Test"

    def test_get_session_not_found(self, client: TestClient):
        """Get non-existent session should return 404."""
        fake_id = str(uuid.uuid4())
        response = client.get(f"/api/chat/sessions/{fake_id}")
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["code"] == "SESSION_NOT_FOUND"


class TestUpdateSession:
    """Tests for PATCH /sessions/{session_id}."""

    def test_update_session_title(self, client: TestClient):
        """Update session title."""
        create_resp = client.post("/api/chat/sessions", json={"title": "Original"})
        session_id = create_resp.json()["id"]

        response = client.patch(
            f"/api/chat/sessions/{session_id}",
            json={"title": "Updated"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated"

    def test_update_session_not_found(self, client: TestClient):
        """Update non-existent session should return 404."""
        fake_id = str(uuid.uuid4())
        response = client.patch(
            f"/api/chat/sessions/{fake_id}",
            json={"title": "Updated"},
        )
        assert response.status_code == 404


class TestDeleteSession:
    """Tests for DELETE /sessions/{session_id}."""

    def test_delete_session_soft(self, client: TestClient):
        """Soft delete a session."""
        create_resp = client.post("/api/chat/sessions", json={"title": "ToDelete"})
        session_id = create_resp.json()["id"]

        response = client.delete(f"/api/chat/sessions/{session_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == session_id
        assert data["deleted"] is True
        assert data["hard"] is False
        assert data["deleted_at"] is not None

        # Session should no longer be found
        get_resp = client.get(f"/api/chat/sessions/{session_id}")
        assert get_resp.status_code == 404

    def test_delete_session_hard(self, client: TestClient):
        """Hard delete a session."""
        create_resp = client.post("/api/chat/sessions", json={"title": "ToDelete"})
        session_id = create_resp.json()["id"]

        response = client.delete(f"/api/chat/sessions/{session_id}?hard=true")
        assert response.status_code == 200
        data = response.json()
        assert data["hard"] is True
        assert data["deleted_at"] is None

    def test_delete_session_not_found(self, client: TestClient):
        """Delete non-existent session should return 404."""
        fake_id = str(uuid.uuid4())
        response = client.delete(f"/api/chat/sessions/{fake_id}")
        assert response.status_code == 404


# =============================================================================
# Message Listing Tests
# =============================================================================


class TestListMessages:
    """Tests for GET /sessions/{session_id}/messages."""

    def test_list_messages_empty(self, client: TestClient):
        """List messages for session with no messages."""
        create_resp = client.post("/api/chat/sessions", json={})
        session_id = create_resp.json()["id"]

        response = client.get(f"/api/chat/sessions/{session_id}/messages")
        assert response.status_code == 200
        data = response.json()
        assert data["messages"] == []
        assert data["has_more"] is False

    def test_list_messages_after_turn(self, client: TestClient):
        """List messages after a turn."""
        create_resp = client.post("/api/chat/sessions", json={})
        session_id = create_resp.json()["id"]

        # Execute a turn
        turn_resp = client.post(
            f"/api/chat/sessions/{session_id}/turn",
            json={"request_id": str(uuid.uuid4()), "query": "Hello"},
        )
        assert turn_resp.status_code == 200

        # List messages
        response = client.get(f"/api/chat/sessions/{session_id}/messages")
        assert response.status_code == 200
        data = response.json()
        assert len(data["messages"]) == 2  # user + assistant
        assert data["messages"][0]["role"] == "user"
        assert data["messages"][1]["role"] == "assistant"

    def test_list_messages_pagination(self, client: TestClient):
        """List messages supports cursor pagination (older messages)."""
        create_resp = client.post("/api/chat/sessions", json={})
        session_id = create_resp.json()["id"]

        # Create 2 turns => 4 messages
        client.post(
            f"/api/chat/sessions/{session_id}/turn",
            json={"request_id": str(uuid.uuid4()), "query": "Turn 1"},
        )
        client.post(
            f"/api/chat/sessions/{session_id}/turn",
            json={"request_id": str(uuid.uuid4()), "query": "Turn 2"},
        )

        page1 = client.get(f"/api/chat/sessions/{session_id}/messages?limit=2")
        assert page1.status_code == 200
        data1 = page1.json()
        assert len(data1["messages"]) == 2
        assert data1["has_more"] is True
        assert data1["next_cursor"] is not None
        # Newest turn messages should be returned, but in ASC order within the page
        assert data1["messages"][0]["content"] == "Turn 2"

        page2 = client.get(
            f"/api/chat/sessions/{session_id}/messages?limit=2&cursor={data1['next_cursor']}"
        )
        assert page2.status_code == 200
        data2 = page2.json()
        assert len(data2["messages"]) == 2
        assert data2["has_more"] is False
        assert data2["next_cursor"] is None
        assert data2["messages"][0]["content"] == "Turn 1"

    def test_list_messages_session_not_found(self, client: TestClient):
        """List messages for non-existent session should return 404."""
        fake_id = str(uuid.uuid4())
        response = client.get(f"/api/chat/sessions/{fake_id}/messages")
        assert response.status_code == 404


# =============================================================================
# Turn API Tests
# =============================================================================


class TestTurnAPI:
    """Tests for POST /sessions/{session_id}/turn."""

    def test_turn_success(self, client: TestClient, mock_rag_service: MockRAGService):
        """Successful turn creates user and assistant messages."""
        create_resp = client.post("/api/chat/sessions", json={})
        session_id = create_resp.json()["id"]

        request_id = str(uuid.uuid4())
        response = client.post(
            f"/api/chat/sessions/{session_id}/turn",
            json={"request_id": request_id, "query": "What is RAG?"},
        )
        assert response.status_code == 200
        data = response.json()

        assert data["turn_id"] == request_id
        assert data["status"] == "completed"
        assert data["user_message"]["role"] == "user"
        assert data["user_message"]["content"] == "What is RAG?"
        assert data["assistant_message"]["role"] == "assistant"
        assert "mock response" in data["assistant_message"]["content"].lower()
        assert data["error"] is None

    def test_turn_missing_request_id(self, client: TestClient):
        """Turn without request_id should return 400."""
        create_resp = client.post("/api/chat/sessions", json={})
        session_id = create_resp.json()["id"]

        response = client.post(
            f"/api/chat/sessions/{session_id}/turn",
            json={"query": "Hello"},
        )
        assert response.status_code == 422  # Pydantic validation

    def test_turn_empty_query(self, client: TestClient):
        """Turn with empty query should return 400."""
        create_resp = client.post("/api/chat/sessions", json={})
        session_id = create_resp.json()["id"]

        response = client.post(
            f"/api/chat/sessions/{session_id}/turn",
            json={"request_id": str(uuid.uuid4()), "query": "   "},
        )
        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["code"] == "EMPTY_QUERY"

    def test_turn_session_not_found(self, client: TestClient):
        """Turn for non-existent session should return 404."""
        fake_id = str(uuid.uuid4())
        response = client.post(
            f"/api/chat/sessions/{fake_id}/turn",
            json={"request_id": str(uuid.uuid4()), "query": "Hello"},
        )
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["code"] == "SESSION_NOT_FOUND"


class TestTurnIdempotency:
    """Tests for turn idempotency."""

    def test_idempotent_replay_completed(self, client: TestClient):
        """Same request_id with same payload returns cached result."""
        create_resp = client.post("/api/chat/sessions", json={})
        session_id = create_resp.json()["id"]

        request_id = str(uuid.uuid4())
        payload = {"request_id": request_id, "query": "Hello World"}

        # First request
        resp1 = client.post(f"/api/chat/sessions/{session_id}/turn", json=payload)
        assert resp1.status_code == 200
        data1 = resp1.json()

        # Second request with same request_id and payload
        resp2 = client.post(f"/api/chat/sessions/{session_id}/turn", json=payload)
        assert resp2.status_code == 200
        data2 = resp2.json()

        # Should return same result
        assert data1["turn_id"] == data2["turn_id"]
        assert data1["user_message"]["id"] == data2["user_message"]["id"]
        assert data1["assistant_message"]["id"] == data2["assistant_message"]["id"]

    def test_idempotency_conflict_different_payload(self, client: TestClient):
        """Same request_id with different payload returns 409."""
        create_resp = client.post("/api/chat/sessions", json={})
        session_id = create_resp.json()["id"]

        request_id = str(uuid.uuid4())

        # First request
        resp1 = client.post(
            f"/api/chat/sessions/{session_id}/turn",
            json={"request_id": request_id, "query": "Hello"},
        )
        assert resp1.status_code == 200

        # Second request with same request_id but different payload
        resp2 = client.post(
            f"/api/chat/sessions/{session_id}/turn",
            json={"request_id": request_id, "query": "Goodbye"},  # Different query
        )
        assert resp2.status_code == 409
        data = resp2.json()
        assert data["detail"]["code"] == "IDEMPOTENCY_CONFLICT"


class TestTurnFailure:
    """Tests for turn failure handling."""

    def test_turn_rag_service_failure(self, client: TestClient, mock_rag_service: MockRAGService):
        """RAG service failure should return failed turn."""
        create_resp = client.post("/api/chat/sessions", json={})
        session_id = create_resp.json()["id"]

        # Configure mock to fail
        mock_rag_service.should_fail = True
        mock_rag_service.fail_message = "LLM timeout"

        response = client.post(
            f"/api/chat/sessions/{session_id}/turn",
            json={"request_id": str(uuid.uuid4()), "query": "Hello"},
        )
        assert response.status_code == 200  # Turn returns 200 with failed status
        data = response.json()

        assert data["status"] == "failed"
        assert data["user_message"] is not None  # User message was still written
        # Assistant message might be error placeholder or None
        assert data["error"] is not None
        assert data["error"]["code"] == "LLM_ERROR"


class TestTurnFailedReplay:
    """Tests for replaying failed turns (idempotency)."""

    def test_failed_turn_replay_returns_same_error(self, client: TestClient, mock_rag_service: MockRAGService):
        create_resp = client.post("/api/chat/sessions", json={})
        session_id = create_resp.json()["id"]

        mock_rag_service.should_fail = True
        mock_rag_service.fail_message = "LLM timeout"

        request_id = str(uuid.uuid4())
        payload = {"request_id": request_id, "query": "Hello"}

        resp1 = client.post(f"/api/chat/sessions/{session_id}/turn", json=payload)
        assert resp1.status_code == 200
        data1 = resp1.json()
        assert data1["status"] == "failed"
        assert data1["assistant_message"] is None
        assert data1["error"]["message"] == "LLM timeout"
        calls_after_first = mock_rag_service.call_count

        # Replay with the exact same request_id and payload should be cached
        resp2 = client.post(f"/api/chat/sessions/{session_id}/turn", json=payload)
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert data2["status"] == "failed"
        assert data2["error"]["message"] == "LLM timeout"
        assert data2["user_message"]["id"] == data1["user_message"]["id"]
        assert mock_rag_service.call_count == calls_after_first  # no extra LLM call


class TestTurnModeOverride:
    """Tests for mode override (always uses hybrid)."""

    def test_mode_ignored_uses_hybrid(self, client: TestClient, mock_rag_service: MockRAGService):
        """Mode parameter should be ignored; always uses hybrid."""
        create_resp = client.post("/api/chat/sessions", json={})
        session_id = create_resp.json()["id"]

        # Request with mode=naive (should be ignored)
        response = client.post(
            f"/api/chat/sessions/{session_id}/turn",
            json={
                "request_id": str(uuid.uuid4()),
                "query": "Hello",
                "mode": "naive",  # This should be ignored
            },
        )
        assert response.status_code == 200
        data = response.json()

        # Check that metadata shows hybrid mode was used
        assert data["user_message"]["metadata"]["mode"] == "hybrid"


class TestTurnMultimodal:
    """Tests for multimodal turn behavior (img_base64 persisted to disk)."""

    def test_turn_with_img_base64_persists_file(self, client: TestClient, mock_config: SimpleNamespace):
        create_resp = client.post("/api/chat/sessions", json={})
        session_id = create_resp.json()["id"]

        # Minimal 1x1 png (base64) - any valid bytes are fine for this test
        img_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/w8AAn8B9n0oWQAAAABJRU5ErkJggg=="

        resp = client.post(
            f"/api/chat/sessions/{session_id}/turn",
            json={
                "request_id": str(uuid.uuid4()),
                "query": "What is in this image?",
                "multimodal_content": {"img_base64": img_base64, "img_mime_type": "image/png"},
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert data["user_message"]["metadata"]["img_path"]

        img_path = data["user_message"]["metadata"]["img_path"]
        assert isinstance(img_path, str)
        assert str(Path(mock_config.upload_dir).resolve()) in img_path
        assert Path(img_path).exists()

    def test_turn_with_invalid_img_base64_returns_400(self, client: TestClient):
        create_resp = client.post("/api/chat/sessions", json={})
        session_id = create_resp.json()["id"]

        resp = client.post(
            f"/api/chat/sessions/{session_id}/turn",
            json={
                "request_id": str(uuid.uuid4()),
                "query": "Hello",
                "multimodal_content": {"img_base64": "not-base64!!!", "img_mime_type": "image/png"},
            },
        )
        assert resp.status_code == 400
        assert resp.json()["detail"]["code"] == "MULTIMODAL_INVALID"


class TestTurnStreamAPI:
    """Tests for POST /sessions/{session_id}/turn:stream."""

    def test_turn_stream_success(self, client: TestClient, mock_rag_service: MockRAGService):
        create_resp = client.post("/api/chat/sessions", json={"title": "Stream Test"})
        session_id = create_resp.json()["id"]

        request_id = str(uuid.uuid4())
        deltas: list[str] = []
        final: dict[str, Any] | None = None

        with client.stream(
            "POST",
            f"/api/chat/sessions/{session_id}/turn:stream",
            json={"request_id": request_id, "query": "Stream this"},
        ) as resp:
            assert resp.status_code == 200
            assert resp.headers["content-type"].startswith("text/event-stream")

            for raw_line in resp.iter_lines():
                if not raw_line:
                    continue
                line = raw_line.decode("utf-8") if isinstance(raw_line, (bytes, bytearray)) else raw_line
                assert line.startswith("data: ")
                payload = json.loads(line[len("data: ") :])
                if payload.get("type") == "delta":
                    deltas.append(payload.get("delta", ""))
                elif payload.get("type") == "final":
                    final = payload.get("response")

        assert final is not None
        assert final["turn_id"] == request_id
        assert final["status"] == "completed"
        assert final["assistant_message"]["role"] == "assistant"
        assert final["assistant_message"]["content"] == "".join(deltas)
        assert mock_rag_service.call_count == 1


# =============================================================================
# Session Title Auto-Update Tests
# =============================================================================


class TestSessionTitleAutoUpdate:
    """Tests for automatic session title update on first message."""

    def test_first_turn_updates_title(self, client: TestClient):
        """First turn should auto-update session title from query."""
        create_resp = client.post("/api/chat/sessions", json={})
        session_id = create_resp.json()["id"]
        assert create_resp.json()["title"] == "New Chat"

        # First turn
        client.post(
            f"/api/chat/sessions/{session_id}/turn",
            json={"request_id": str(uuid.uuid4()), "query": "How do I use Python?"},
        )

        # Check session title was updated
        get_resp = client.get(f"/api/chat/sessions/{session_id}")
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data["title"] == "How do I use Python?"


# =============================================================================
# Integration Flow Tests
# =============================================================================


class TestIntegrationFlow:
    """End-to-end integration flow tests."""

    def test_full_conversation_flow(self, client: TestClient):
        """Test full conversation: create session -> multiple turns -> list messages."""
        # Create session
        create_resp = client.post("/api/chat/sessions", json={"title": "Test Conversation"})
        assert create_resp.status_code == 201
        session_id = create_resp.json()["id"]

        # First turn
        turn1_resp = client.post(
            f"/api/chat/sessions/{session_id}/turn",
            json={"request_id": str(uuid.uuid4()), "query": "What is machine learning?"},
        )
        assert turn1_resp.status_code == 200

        # Second turn
        turn2_resp = client.post(
            f"/api/chat/sessions/{session_id}/turn",
            json={"request_id": str(uuid.uuid4()), "query": "Give me an example."},
        )
        assert turn2_resp.status_code == 200

        # List all messages
        msgs_resp = client.get(f"/api/chat/sessions/{session_id}/messages")
        assert msgs_resp.status_code == 200
        messages = msgs_resp.json()["messages"]
        assert len(messages) == 4  # 2 user + 2 assistant

        # Verify order (ASC by created_at)
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"
        assert messages[2]["role"] == "user"
        assert messages[3]["role"] == "assistant"

    def test_multiple_sessions_isolation(self, client: TestClient):
        """Test that messages are isolated between sessions."""
        # Create two sessions
        session1_resp = client.post("/api/chat/sessions", json={"title": "Session 1"})
        session1_id = session1_resp.json()["id"]

        session2_resp = client.post("/api/chat/sessions", json={"title": "Session 2"})
        session2_id = session2_resp.json()["id"]

        # Add turns to each session
        client.post(
            f"/api/chat/sessions/{session1_id}/turn",
            json={"request_id": str(uuid.uuid4()), "query": "Session 1 question"},
        )
        client.post(
            f"/api/chat/sessions/{session2_id}/turn",
            json={"request_id": str(uuid.uuid4()), "query": "Session 2 question"},
        )

        # Verify messages are isolated
        msgs1_resp = client.get(f"/api/chat/sessions/{session1_id}/messages")
        msgs1 = msgs1_resp.json()["messages"]
        assert len(msgs1) == 2
        assert "Session 1" in msgs1[0]["content"]

        msgs2_resp = client.get(f"/api/chat/sessions/{session2_id}/messages")
        msgs2 = msgs2_resp.json()["messages"]
        assert len(msgs2) == 2
        assert "Session 2" in msgs2[0]["content"]
