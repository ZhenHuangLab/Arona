"""
Graph data models for knowledge graph visualization.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class GraphNode(BaseModel):
    """Knowledge graph node (entity)."""
    id: str = Field(..., description="Unique node identifier")
    label: str = Field(..., description="Node display label")
    type: str = Field(default="entity", description="Node type")
    description: Optional[str] = Field(None, description="Node description")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class GraphEdge(BaseModel):
    """Knowledge graph edge (relationship)."""
    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    label: str = Field(..., description="Relationship label")
    weight: float = Field(default=1.0, description="Edge weight/strength")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class GraphDataResponse(BaseModel):
    """Knowledge graph data response."""
    nodes: List[GraphNode] = Field(default_factory=list, description="Graph nodes")
    edges: List[GraphEdge] = Field(default_factory=list, description="Graph edges")
    stats: Dict[str, Any] = Field(default_factory=dict, description="Graph statistics")
    
    class Config:
        json_schema_extra = {
            "example": {
                "nodes": [
                    {
                        "id": "entity_1",
                        "label": "Machine Learning",
                        "type": "concept",
                        "description": "A field of AI focused on learning from data"
                    }
                ],
                "edges": [
                    {
                        "source": "entity_1",
                        "target": "entity_2",
                        "label": "related_to",
                        "weight": 0.85
                    }
                ],
                "stats": {
                    "total_nodes": 150,
                    "total_edges": 320,
                    "avg_degree": 4.27
                }
            }
        }

