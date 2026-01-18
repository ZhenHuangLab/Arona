"""
Query endpoints for RAG operations.
"""

import logging
import base64
import hashlib
import time
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Request, HTTPException, status

from backend.models.query import (
    QueryRequest,
    QueryResponse,
    MultimodalQueryRequest,
    ConversationRequest,
    ConversationResponse,
    ConversationMessage,
)


router = APIRouter()
logger = logging.getLogger(__name__)


def _infer_image_extension_from_data_url(header: str) -> str:
    header = header.lower()
    if "image/jpeg" in header or "image/jpg" in header:
        return "jpg"
    if "image/png" in header:
        return "png"
    if "image/webp" in header:
        return "webp"
    if "image/gif" in header:
        return "gif"
    if "image/bmp" in header:
        return "bmp"
    if "image/tiff" in header or "image/tif" in header:
        return "tif"
    return "png"


def _save_query_image_base64_to_uploads(
    *,
    img_base64: str,
    upload_dir: Path,
    max_bytes: int = 10 * 1024 * 1024,
) -> str:
    """
    Persist a base64-encoded image to the backend upload directory and return its absolute path.

    Accepts either:
    - Raw base64 string
    - Data URL: data:image/png;base64,...
    """
    if not img_base64 or not isinstance(img_base64, str):
        raise ValueError("img_base64 must be a non-empty string")

    b64_payload = img_base64.strip()
    ext = "png"

    if b64_payload.startswith("data:"):
        try:
            header, b64_payload = b64_payload.split(",", 1)
        except ValueError as exc:
            raise ValueError("Invalid data URL format for img_base64") from exc
        ext = _infer_image_extension_from_data_url(header)

    try:
        image_bytes = base64.b64decode(b64_payload, validate=True)
    except Exception as exc:  # pylint: disable=broad-except
        raise ValueError("Invalid base64 payload for img_base64") from exc

    if not image_bytes:
        raise ValueError("Decoded img_base64 is empty")
    if len(image_bytes) > max_bytes:
        raise ValueError(
            f"Query image too large: {len(image_bytes)} bytes > {max_bytes} bytes"
        )

    query_dir = upload_dir / "query_images"
    query_dir.mkdir(parents=True, exist_ok=True)

    digest = hashlib.sha256(image_bytes).hexdigest()[:16]
    filename = f"query_{int(time.time())}_{digest}.{ext}"
    path = (query_dir / filename).resolve()

    path.write_bytes(image_bytes)
    return str(path)


@router.post("/", response_model=QueryResponse)
async def query(request: Request, req: QueryRequest):
    """
    Execute a RAG query.

    Performs retrieval-augmented generation on the knowledge base.
    """
    state = request.app.state

    try:
        # Build kwargs from optional parameters
        kwargs = {}
        if req.top_k is not None:
            kwargs["top_k"] = req.top_k
        if req.max_tokens is not None:
            kwargs["max_tokens"] = req.max_tokens
        if req.temperature is not None:
            kwargs["temperature"] = req.temperature

        # Execute query
        response = await state.rag_service.query(
            query=req.query, mode=req.mode, **kwargs
        )

        # Defensive: LightRAG may return None on internal errors; surface a clear API error
        if not isinstance(response, str) or response is None:
            logger.error(
                "RAG pipeline returned non-string response (%r); returning 500",
                type(response),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Query pipeline returned no response due to an internal error. Check backend logs.",
            )

        return QueryResponse(
            query=req.query,
            response=response,
            mode=req.mode,
            metadata={
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

    except Exception as e:
        logger.error(f"Query failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query failed: {str(e)}",
        )


@router.post("/multimodal", response_model=QueryResponse)
async def multimodal_query(request: Request, req: MultimodalQueryRequest):
    """
    Execute a multimodal RAG query.

    Supports queries with images, tables, and equations.
    """
    state = request.app.state

    try:
        # Convert multimodal content to dict format
        multimodal_content = None
        if req.multimodal_content:
            upload_dir = Path(state.config.upload_dir)
            upload_dir.mkdir(parents=True, exist_ok=True)

            multimodal_content = []
            for item in req.multimodal_content:
                payload = item.model_dump(exclude_none=True)

                # Allow clients to send query images as base64; persist to disk so the
                # retrieval pipeline can consume them via Image Path markers.
                if (
                    payload.get("type") in {"image", "table"}
                    and payload.get("img_base64")
                    and not payload.get("img_path")
                ):
                    try:
                        payload["img_path"] = _save_query_image_base64_to_uploads(
                            img_base64=payload["img_base64"],
                            upload_dir=upload_dir,
                        )
                        payload.pop("img_base64", None)
                    except ValueError as exc:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Invalid img_base64 for multimodal query: {exc}",
                        ) from exc

                multimodal_content.append(payload)

        # Build kwargs from optional parameters
        kwargs = {}
        if req.top_k is not None:
            kwargs["top_k"] = req.top_k
        if req.max_tokens is not None:
            kwargs["max_tokens"] = req.max_tokens
        if req.temperature is not None:
            kwargs["temperature"] = req.temperature

        # Execute multimodal query
        response = await state.rag_service.query_with_multimodal(
            query=req.query,
            multimodal_content=multimodal_content,
            mode=req.mode,
            **kwargs,
        )

        return QueryResponse(
            query=req.query,
            response=response,
            mode=req.mode,
            metadata={
                "timestamp": datetime.utcnow().isoformat(),
                "multimodal_items": len(multimodal_content)
                if multimodal_content
                else 0,
            },
        )

    except Exception as e:
        logger.error(f"Multimodal query failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Multimodal query failed: {str(e)}",
        )


@router.post("/conversation", response_model=ConversationResponse)
async def conversation_query(request: Request, req: ConversationRequest):
    """
    Execute a conversational RAG query.

    Maintains conversation history for multi-turn interactions.
    """
    state = request.app.state

    try:
        # Convert history to LightRAG QueryParam format
        conversation_history = []
        if req.history:
            for msg in req.history:
                conversation_history.append(
                    {
                        "role": msg.role,
                        "content": msg.content,
                    }
                )

        # Convert multimodal content to dict format (optional)
        multimodal_content = None
        if req.multimodal_content:
            upload_dir = Path(state.config.upload_dir)
            upload_dir.mkdir(parents=True, exist_ok=True)

            multimodal_content = []
            for item in req.multimodal_content:
                payload = item.model_dump(exclude_none=True)

                if (
                    payload.get("type") in {"image", "table"}
                    and payload.get("img_base64")
                    and not payload.get("img_path")
                ):
                    try:
                        payload["img_path"] = _save_query_image_base64_to_uploads(
                            img_base64=payload["img_base64"],
                            upload_dir=upload_dir,
                        )
                        payload.pop("img_base64", None)
                    except ValueError as exc:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Invalid img_base64 for conversation query: {exc}",
                        ) from exc

                multimodal_content.append(payload)

        # Build kwargs
        kwargs = {}
        if req.max_tokens is not None:
            kwargs["max_tokens"] = req.max_tokens
        if req.temperature is not None:
            kwargs["temperature"] = req.temperature

        # Add history to kwargs (LightRAG QueryParam expects conversation_history)
        if conversation_history:
            kwargs["conversation_history"] = conversation_history

        # Execute query (multimodal-aware when content is provided)
        if multimodal_content:
            response = await state.rag_service.query_with_multimodal(
                query=req.query,
                multimodal_content=multimodal_content,
                mode=req.mode,
                **kwargs,
            )
        else:
            response = await state.rag_service.query(
                query=req.query, mode=req.mode, **kwargs
            )

        # Build updated history
        updated_history = list(req.history) if req.history else []

        # Add user message
        updated_history.append(
            ConversationMessage(
                role="user",
                content=req.query,
                timestamp=datetime.utcnow().isoformat(),
            )
        )

        # Add assistant response
        updated_history.append(
            ConversationMessage(
                role="assistant",
                content=response,
                timestamp=datetime.utcnow().isoformat(),
            )
        )

        return ConversationResponse(
            query=req.query,
            response=response,
            mode=req.mode,
            history=updated_history,
        )

    except Exception as e:
        logger.error(f"Conversation query failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Conversation query failed: {str(e)}",
        )
