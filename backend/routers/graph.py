"""
Knowledge graph endpoints.
"""

import logging
from collections.abc import Mapping
from typing import Any

from fastapi import APIRouter, Request, HTTPException, status, Query

from backend.models.graph import GraphDataResponse, GraphNode, GraphEdge


router = APIRouter()
logger = logging.getLogger(__name__)


async def _kv_storage_get_all(storage: Any) -> dict[str, Any]:
    """Best-effort KV storage dump across LightRAG versions.

    LightRAG's KV storage API has evolved. Newer versions expose `get_all()`, while
    older versions (e.g. early `JsonKVStorage`) only exposed `all_keys()` +
    `get_by_ids()`.
    """
    if storage is None:
        return {}

    get_all = getattr(storage, "get_all", None)
    if callable(get_all):
        try:
            data = await get_all()
        except TypeError:
            data = get_all()
            if hasattr(data, "__await__"):
                data = await data

        if isinstance(data, Mapping):
            return dict(data)
        return {}

    all_keys = getattr(storage, "all_keys", None)
    get_by_ids = getattr(storage, "get_by_ids", None)
    if callable(all_keys) and callable(get_by_ids):
        keys = await all_keys()
        if not keys:
            return {}

        values = await get_by_ids(keys)
        if values is None:
            return {}

        try:
            return {k: v for k, v in zip(keys, values)}
        except TypeError:
            return {}

    items = getattr(storage, "items", None)
    if callable(items):
        try:
            return dict(items())
        except Exception:  # pylint: disable=broad-except
            return {}

    data_attr = getattr(storage, "_data", None)
    if isinstance(data_attr, Mapping):
        return dict(data_attr)

    return {}


@router.get("/data", response_model=GraphDataResponse)
async def get_graph_data(
    request: Request,
    limit: int = Query(
        default=100, ge=1, le=1000, description="Maximum number of nodes to return"
    ),
    include_metadata: bool = Query(
        default=False, description="Include detailed metadata"
    ),
):
    """
    Get knowledge graph data for visualization.

    Returns nodes (entities) and edges (relationships) from the LightRAG knowledge graph.
    """
    state = request.app.state

    try:
        # Get RAG instance
        rag = await state.rag_service.get_rag_instance()

        # Check if LightRAG is initialized
        if not rag.lightrag:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="RAG system not initialized",
            )

        nodes = []
        edges = []
        stats = {}

        # Extract graph data from LightRAG storage
        try:
            # Access the knowledge graph
            kg = rag.lightrag.chunk_entity_relation_graph

            # Collect unique entity names from full_entities storage
            # full_entities structure: {doc_id: {"entity_names": [...], "count": N}}
            entity_names_set = set()
            if rag.lightrag.full_entities:
                # Get all documents from full_entities storage
                full_entities_data = await _kv_storage_get_all(rag.lightrag.full_entities)

                # Extract entity names from each document
                for doc_id, doc_data in full_entities_data.items():
                    if doc_data and "entity_names" in doc_data:
                        entity_names_set.update(doc_data["entity_names"])

            # Get entity details from knowledge graph
            entity_count = 0
            for entity_name in entity_names_set:
                if entity_count >= limit:
                    break

                # Get entity node data from knowledge graph
                entity_data = await kg.get_node(entity_name)
                if entity_data:
                    # Parse entity data
                    entity_type = entity_data.get("entity_type", "unknown")
                    description = entity_data.get("description", "")

                    node = GraphNode(
                        id=entity_name,
                        label=entity_name,
                        type=entity_type,
                        description=description if include_metadata else None,
                        metadata={
                            "source_id": entity_data.get("source_id", ""),
                            "file_path": entity_data.get("file_path", ""),
                        }
                        if include_metadata
                        else {},
                    )
                    nodes.append(node)
                    entity_count += 1

            # Collect unique relation pairs from full_relations storage
            # full_relations structure: {doc_id: {"relation_pairs": [["src", "tgt"], ...], "count": N}}
            # Note: LightRAG stores relation_pairs as list of lists for JSON serialization
            relation_pairs_set = set()
            if rag.lightrag.full_relations:
                # Get all documents from full_relations storage
                full_relations_data = await _kv_storage_get_all(rag.lightrag.full_relations)

                # Extract relation pairs from each document
                for doc_id, doc_data in full_relations_data.items():
                    if doc_data and "relation_pairs" in doc_data:
                        # Convert each pair from list to tuple (lists are unhashable)
                        for pair in doc_data["relation_pairs"]:
                            if isinstance(pair, (list, tuple)) and len(pair) == 2:
                                relation_pairs_set.add(tuple(pair))

            # Get relationship details from knowledge graph
            edge_count = 0
            for src_id, tgt_id in relation_pairs_set:
                if edge_count >= limit * 2:  # Allow more edges than nodes
                    break

                # Get edge data from knowledge graph
                edge_data = await kg.get_edge(src_id, tgt_id)
                if edge_data:
                    description = edge_data.get("description", "")
                    weight = edge_data.get("weight", 1.0)

                    edge = GraphEdge(
                        source=src_id,
                        target=tgt_id,
                        label=description[:50] if description else "related_to",
                        weight=float(weight)
                        if isinstance(weight, (int, float))
                        else 1.0,
                        metadata={"full_description": description}
                        if include_metadata and description
                        else {},
                    )
                    edges.append(edge)
                    edge_count += 1

            # Calculate statistics
            stats = {
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "avg_degree": round(2 * len(edges) / len(nodes), 2) if nodes else 0,
                "graph_density": round(
                    2 * len(edges) / (len(nodes) * (len(nodes) - 1)), 4
                )
                if len(nodes) > 1
                else 0,
            }

            logger.info(f"Retrieved graph data: {len(nodes)} nodes, {len(edges)} edges")

        except Exception as e:
            logger.error(f"Error extracting graph data: {e}", exc_info=True)
            # Return empty graph with error in stats
            stats = {"error": str(e), "total_nodes": 0, "total_edges": 0}

        return GraphDataResponse(nodes=nodes, edges=edges, stats=stats)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get graph data: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get graph data: {str(e)}",
        )


@router.get("/stats")
async def get_graph_stats(request: Request):
    """
    Get knowledge graph statistics without full data.

    Returns summary statistics about the knowledge graph.
    """
    state = request.app.state

    try:
        rag = await state.rag_service.get_rag_instance()

        if not rag.lightrag:
            return {"initialized": False, "total_entities": 0, "total_relations": 0}

        # Count entities and relations
        entity_count = 0
        relation_count = 0

        try:
            # Count unique entities from full_entities storage
            if rag.lightrag.full_entities:
                full_entities_data = await _kv_storage_get_all(rag.lightrag.full_entities)
                entity_names_set = set()
                for doc_data in full_entities_data.values():
                    if doc_data and "entity_names" in doc_data:
                        entity_names_set.update(doc_data["entity_names"])
                entity_count = len(entity_names_set)

            # Count unique relations from full_relations storage
            if rag.lightrag.full_relations:
                full_relations_data = await _kv_storage_get_all(rag.lightrag.full_relations)
                relation_pairs_set = set()
                for doc_data in full_relations_data.values():
                    if doc_data and "relation_pairs" in doc_data:
                        # Convert each pair from list to tuple (lists are unhashable)
                        for pair in doc_data["relation_pairs"]:
                            if isinstance(pair, (list, tuple)) and len(pair) == 2:
                                relation_pairs_set.add(tuple(pair))
                relation_count = len(relation_pairs_set)
        except Exception as e:
            logger.warning(f"Error counting graph elements: {e}")

        return {
            "initialized": True,
            "total_entities": entity_count,
            "total_relations": relation_count,
            "working_dir": str(rag.lightrag.working_dir),
        }

    except Exception as e:
        logger.error(f"Failed to get graph stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get graph stats: {str(e)}",
        )
