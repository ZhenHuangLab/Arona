"""
Pydantic models for document indexing status tracking.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class StatusEnum(str, Enum):
    """Document indexing status values."""
    
    PENDING = "pending"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"


class IndexStatus(BaseModel):
    """
    Internal model for document index status.
    
    Tracks the indexing state of documents in the upload directory.
    """
    
    file_path: str = Field(
        ...,
        description="Relative file path from upload directory (primary key)"
    )
    file_hash: str = Field(
        ...,
        description="MD5 hash of file content for change detection"
    )
    status: StatusEnum = Field(
        ...,
        description="Current indexing status"
    )
    indexed_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp when indexing completed (None if not indexed)"
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Error details if status is failed"
    )
    file_size: int = Field(
        ...,
        description="File size in bytes",
        ge=0
    )
    last_modified: datetime = Field(
        ...,
        description="File's last modification timestamp"
    )


class IndexStatusResponse(BaseModel):
    """
    API response model for document index status.
    
    Returned by GET /api/documents/index-status endpoint.
    """
    
    file_path: str = Field(
        ...,
        description="Relative file path from upload directory"
    )
    file_hash: str = Field(
        ...,
        description="MD5 hash of file content"
    )
    status: StatusEnum = Field(
        ...,
        description="Current indexing status"
    )
    indexed_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp when indexing completed"
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Error details if status is failed"
    )
    file_size: int = Field(
        ...,
        description="File size in bytes"
    )
    last_modified: datetime = Field(
        ...,
        description="File's last modification timestamp"
    )

