"""
Pydantic models for API requests and responses.
"""

from backend.models.document import (
    DocumentUploadResponse,
    DocumentProcessRequest,
    DocumentProcessResponse,
    BatchProcessRequest,
    BatchProcessResponse,
    DocumentListResponse,
    DocumentDetailItem,
    DocumentDetailsResponse,
    DocumentDeleteResponse,
)
from backend.models.query import (
    QueryRequest,
    QueryResponse,
    MultimodalQueryRequest,
    MultimodalContent,
    ConversationRequest,
    ConversationResponse,
    ConversationMessage,
)
from backend.models.index_status import (
    IndexStatus,
    IndexStatusResponse,
    StatusEnum,
    TriggerIndexResponse,
)

__all__ = [
    "DocumentUploadResponse",
    "DocumentProcessRequest",
    "DocumentProcessResponse",
    "BatchProcessRequest",
    "BatchProcessResponse",
    "DocumentListResponse",
    "DocumentDetailItem",
    "DocumentDetailsResponse",
    "DocumentDeleteResponse",
    "QueryRequest",
    "QueryResponse",
    "MultimodalQueryRequest",
    "MultimodalContent",
    "ConversationRequest",
    "ConversationResponse",
    "ConversationMessage",
    "IndexStatus",
    "IndexStatusResponse",
    "StatusEnum",
    "TriggerIndexResponse",
]
