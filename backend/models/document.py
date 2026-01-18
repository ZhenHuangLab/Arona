"""
Pydantic models for document endpoints.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class DocumentUploadResponse(BaseModel):
    """Response model for document upload."""

    filename: str = Field(..., description="Uploaded filename")
    file_path: str = Field(..., description="Saved file path")
    file_size: int = Field(..., description="File size in bytes")
    content_type: Optional[str] = Field(default=None, description="MIME content type")


class DocumentProcessRequest(BaseModel):
    """Request model for document processing."""

    file_path: str = Field(..., description="Path to document file")
    parse_method: str = Field(
        default="auto", description="Parsing method: auto, ocr, or txt"
    )
    output_dir: Optional[str] = Field(
        default=None, description="Optional output directory for parsed content"
    )


class DocumentProcessResponse(BaseModel):
    """Response model for document processing."""

    status: str = Field(..., description="Processing status: success or error")
    file_path: str = Field(..., description="Processed file path")
    output_dir: Optional[str] = Field(default=None, description="Output directory")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    metadata: Optional[dict] = Field(default=None, description="Processing metadata")


class BatchProcessRequest(BaseModel):
    """Request model for batch document processing."""

    folder_path: str = Field(..., description="Path to folder containing documents")
    file_extensions: Optional[List[str]] = Field(
        default=None, description="File extensions to process (e.g., ['.pdf', '.docx'])"
    )
    recursive: bool = Field(
        default=False, description="Whether to process subdirectories recursively"
    )
    max_workers: int = Field(
        default=4, description="Maximum number of parallel workers", ge=1, le=16
    )
    parse_method: str = Field(
        default="auto", description="Parsing method: auto, ocr, or txt"
    )


class BatchProcessResponse(BaseModel):
    """Response model for batch document processing."""

    total_files: int = Field(..., description="Total number of files processed")
    successful: int = Field(..., description="Number of successfully processed files")
    failed: int = Field(..., description="Number of failed files")
    results: List[DocumentProcessResponse] = Field(
        ..., description="Individual processing results"
    )


class DocumentListResponse(BaseModel):
    """Response model for listing documents."""

    documents: List[str] = Field(..., description="List of document paths")
    total: int = Field(..., description="Total number of documents")


class DocumentDetailItem(BaseModel):
    """Detailed metadata for a single document."""

    filename: str = Field(..., description="Document filename")
    file_path: str = Field(..., description="Relative file path from upload directory")
    file_size: int = Field(..., description="File size in bytes")
    upload_date: datetime = Field(..., description="File upload/modification timestamp")
    status: str = Field(
        ..., description="Document status (e.g., 'indexed', 'processing')"
    )
    storage_location: str = Field(
        ..., description="Storage location relative to upload directory"
    )


class DocumentDetailsResponse(BaseModel):
    """Response model for detailed document listing."""

    documents: List[DocumentDetailItem] = Field(
        ..., description="List of documents with metadata"
    )
    total: int = Field(..., description="Total number of documents")


class DocumentDeleteResponse(BaseModel):
    """Response model for document deletion (soft delete)."""

    status: str = Field(..., description="Deletion status: 'success' or 'error'")
    message: str = Field(..., description="Human-readable status message")
    trash_location: str = Field(
        ..., description="Path where file was moved in trash folder"
    )
    original_path: str = Field(..., description="Original file path before deletion")
