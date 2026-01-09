"""
Pydantic models for query endpoints.
"""

from __future__ import annotations

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """Request model for RAG query."""
    
    query: str = Field(..., description="User query text", min_length=1)
    mode: str = Field(
        default="hybrid",
        description="Query mode: naive, local, global, or hybrid"
    )
    top_k: Optional[int] = Field(
        default=None,
        description="Number of top results to retrieve",
        ge=1,
        le=100
    )
    max_tokens: Optional[int] = Field(
        default=None,
        description="Maximum tokens in response",
        ge=1
    )
    temperature: Optional[float] = Field(
        default=None,
        description="Sampling temperature",
        ge=0.0,
        le=2.0
    )


class MultimodalContent(BaseModel):
    """Multimodal content item."""
    
    type: str = Field(..., description="Content type: image, table, or equation")
    
    # For images
    img_path: Optional[str] = Field(default=None, description="Path to image file")
    img_base64: Optional[str] = Field(default=None, description="Base64-encoded image")
    image_caption: Optional[str] = Field(default=None, description="Image caption")
    
    # For tables
    table_data: Optional[str] = Field(default=None, description="Table data (CSV or markdown)")
    table_caption: Optional[str] = Field(default=None, description="Table caption")
    
    # For equations
    latex: Optional[str] = Field(default=None, description="LaTeX equation")
    equation_caption: Optional[str] = Field(default=None, description="Equation caption")


class MultimodalQueryRequest(BaseModel):
    """Request model for multimodal RAG query."""
    
    query: str = Field(..., description="User query text", min_length=1)
    multimodal_content: Optional[List[MultimodalContent]] = Field(
        default=None,
        description="Optional multimodal content items"
    )
    mode: str = Field(
        default="hybrid",
        description="Query mode: naive, local, global, or hybrid"
    )
    top_k: Optional[int] = Field(
        default=None,
        description="Number of top results to retrieve",
        ge=1,
        le=100
    )
    max_tokens: Optional[int] = Field(
        default=None,
        description="Maximum tokens in response",
        ge=1
    )
    temperature: Optional[float] = Field(
        default=None,
        description="Sampling temperature",
        ge=0.0,
        le=2.0
    )


class QueryResponse(BaseModel):
    """Response model for RAG query."""
    
    query: str = Field(..., description="Original query text")
    response: str = Field(..., description="Generated response")
    mode: str = Field(..., description="Query mode used")
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional metadata about the query"
    )


class ConversationMessage(BaseModel):
    """Single message in a conversation."""
    
    role: str = Field(..., description="Message role: user or assistant")
    content: str = Field(..., description="Message content")
    timestamp: Optional[str] = Field(default=None, description="Message timestamp")


class ConversationRequest(BaseModel):
    """Request model for conversational query."""
    
    query: str = Field(..., description="User query text", min_length=1)
    multimodal_content: Optional[List[MultimodalContent]] = Field(
        default=None,
        description="Optional multimodal content items for this turn (e.g., query image)",
    )
    history: Optional[List[ConversationMessage]] = Field(
        default=None,
        description="Conversation history"
    )
    mode: str = Field(
        default="hybrid",
        description="Query mode: naive, local, global, or hybrid"
    )
    max_tokens: Optional[int] = Field(
        default=None,
        description="Maximum tokens in response",
        ge=1
    )
    temperature: Optional[float] = Field(
        default=None,
        description="Sampling temperature",
        ge=0.0,
        le=2.0
    )


class ConversationResponse(BaseModel):
    """Response model for conversational query."""
    
    query: str = Field(..., description="User query text")
    response: str = Field(..., description="Generated response")
    history: List[ConversationMessage] = Field(
        ...,
        description="Updated conversation history"
    )
