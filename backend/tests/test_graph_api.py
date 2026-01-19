"""
Tests for Graph API Router (/api/graph).

These endpoints rely on LightRAG storages. LightRAG's KV storage API has changed
over time: some versions expose `get_all()`, while earlier versions used
`all_keys()` + `get_by_ids()`. This test ensures our graph endpoints work with
the legacy shape too.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.routers.graph import router


class LegacyKVStorage:
    """KV storage that mimics older LightRAG JsonKVStorage (no get_all)."""

    def __init__(self, data: dict[str, Any]):
        self._data = dict(data)

    async def all_keys(self) -> list[str]:
        return list(self._data.keys())

    async def get_by_ids(self, ids: list[str], fields: Any = None):  # noqa: ARG002
        return [self._data.get(id_) for id_ in ids]


class ModernKVStorage:
    """KV storage that exposes get_all() (newer LightRAG versions)."""

    def __init__(self, data: dict[str, Any]):
        self._data = dict(data)

    async def get_all(self) -> dict[str, Any]:
        return dict(self._data)


class MockKG:
    """Minimal knowledge graph storage used by backend/routers/graph.py."""

    def __init__(
        self,
        nodes: dict[str, dict[str, Any]],
        edges: dict[tuple[str, str], dict[str, Any]],
    ):
        self._nodes = dict(nodes)
        self._edges = dict(edges)

    async def get_node(self, node_id: str) -> dict[str, Any] | None:
        return self._nodes.get(node_id)

    async def get_edge(self, src_id: str, tgt_id: str) -> dict[str, Any] | None:
        return self._edges.get((src_id, tgt_id)) or self._edges.get((tgt_id, src_id))


class MockRAGService:
    def __init__(self, rag_instance: Any):
        self._rag_instance = rag_instance

    async def get_rag_instance(self):
        return self._rag_instance


@pytest.fixture
def app_with_legacy_kv() -> FastAPI:
    kg = MockKG(
        nodes={
            "A": {
                "entity_type": "concept",
                "description": "Entity A",
                "source_id": "chunk-a",
                "file_path": "/tmp/a.pdf",
            },
            "B": {
                "entity_type": "concept",
                "description": "Entity B",
                "source_id": "chunk-b",
                "file_path": "/tmp/b.pdf",
            },
            "C": {
                "entity_type": "concept",
                "description": "Entity C",
                "source_id": "chunk-c",
                "file_path": "/tmp/c.pdf",
            },
        },
        edges={
            ("A", "B"): {"description": "A related to B", "weight": 2.0},
            ("B", "C"): {"description": "B related to C", "weight": 1.0},
        },
    )

    full_entities = LegacyKVStorage(
        {
            "doc1": {"entity_names": ["A", "B"], "count": 2},
            "doc2": {"entity_names": ["B", "C"], "count": 2},
        }
    )
    full_relations = LegacyKVStorage(
        {
            "doc1": {"relation_pairs": [["A", "B"], ["B", "C"]], "count": 2},
        }
    )

    lightrag = SimpleNamespace(
        chunk_entity_relation_graph=kg,
        full_entities=full_entities,
        full_relations=full_relations,
        working_dir="/tmp/rag_storage",
    )
    rag = SimpleNamespace(lightrag=lightrag)

    app = FastAPI()
    app.state.rag_service = MockRAGService(rag)
    app.include_router(router, prefix="/api/graph")
    return app


@pytest.fixture
def client(app_with_legacy_kv: FastAPI) -> TestClient:
    return TestClient(app_with_legacy_kv)


def test_graph_data_works_with_legacy_kv_api(client: TestClient):
    resp = client.get("/api/graph/data?limit=100&include_metadata=false")
    assert resp.status_code == 200
    data = resp.json()

    node_ids = {node["id"] for node in data["nodes"]}
    assert node_ids == {"A", "B", "C"}

    edge_pairs = {(edge["source"], edge["target"]) for edge in data["edges"]}
    assert edge_pairs == {("A", "B"), ("B", "C")}

    # Stats should be computed without an error field
    assert data["stats"]["total_nodes"] == 3
    assert data["stats"]["total_edges"] == 2
    assert "error" not in data["stats"]


def test_graph_stats_works_with_legacy_kv_api(client: TestClient):
    resp = client.get("/api/graph/stats")
    assert resp.status_code == 200
    data = resp.json()

    assert data["initialized"] is True
    assert data["total_entities"] == 3
    assert data["total_relations"] == 2
    assert data["working_dir"] == "/tmp/rag_storage"


def test_graph_data_works_with_modern_get_all_kv_api(tmp_path):
    kg = MockKG(
        nodes={
            "X": {"entity_type": "concept", "description": "Entity X"},
            "Y": {"entity_type": "concept", "description": "Entity Y"},
        },
        edges={
            ("X", "Y"): {"description": "X related to Y", "weight": 1.0},
        },
    )

    full_entities = ModernKVStorage({"doc1": {"entity_names": ["X", "Y"]}})
    full_relations = ModernKVStorage({"doc1": {"relation_pairs": [["X", "Y"]]}})

    lightrag = SimpleNamespace(
        chunk_entity_relation_graph=kg,
        full_entities=full_entities,
        full_relations=full_relations,
        working_dir=str(tmp_path / "rag_storage"),
    )
    rag = SimpleNamespace(lightrag=lightrag)

    app = FastAPI()
    app.state.rag_service = MockRAGService(rag)
    app.include_router(router, prefix="/api/graph")
    client = TestClient(app)

    resp = client.get("/api/graph/data?limit=100&include_metadata=false")
    assert resp.status_code == 200
    data = resp.json()

    assert {node["id"] for node in data["nodes"]} == {"X", "Y"}
    assert {(edge["source"], edge["target"]) for edge in data["edges"]} == {("X", "Y")}
    assert data["stats"]["total_nodes"] == 2
    assert data["stats"]["total_edges"] == 1
    assert "error" not in data["stats"]

