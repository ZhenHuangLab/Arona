"""
Query endpoints for RAG operations.
"""

import logging
from datetime import datetime
from typing import Optional

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


@router.post("/", response_model=QueryResponse)
async def query(
    request: Request,
    req: QueryRequest
):
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
            query=req.query,
            mode=req.mode,
            **kwargs
        )

        # Defensive: LightRAG may return None on internal errors; surface a clear API error
        if not isinstance(response, str) or response is None:
            logger.error("RAG pipeline returned non-string response (%r); returning 500", type(response))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Query pipeline returned no response due to an internal error. Check backend logs."
            )

        return QueryResponse(
            query=req.query,
            response=response,
            mode=req.mode,
            metadata={
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
    
    except Exception as e:
        logger.error(f"Query failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query failed: {str(e)}"
        )


@router.post("/multimodal", response_model=QueryResponse)
async def multimodal_query(
    request: Request,
    req: MultimodalQueryRequest
):
    """
    Execute a multimodal RAG query.
    
    Supports queries with images, tables, and equations.
    """
    state = request.app.state
    
    try:
        # Convert multimodal content to dict format
        multimodal_content = None
        if req.multimodal_content:
            multimodal_content = [
                item.model_dump(exclude_none=True)
                for item in req.multimodal_content
            ]
        
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
            **kwargs
        )
        
        return QueryResponse(
            query=req.query,
            response=response,
            mode=req.mode,
            metadata={
                "timestamp": datetime.utcnow().isoformat(),
                "multimodal_items": len(multimodal_content) if multimodal_content else 0,
            }
        )
    
    except Exception as e:
        logger.error(f"Multimodal query failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Multimodal query failed: {str(e)}"
        )


@router.post("/conversation", response_model=ConversationResponse)
async def conversation_query(
    request: Request,
    req: ConversationRequest
):
    """
    Execute a conversational RAG query.
    
    Maintains conversation history for multi-turn interactions.
    """
    state = request.app.state
    
    try:
        # Convert history to LightRAG format
        history_messages = []
        if req.history:
            for msg in req.history:
                history_messages.append({
                    "role": msg.role,
                    "content": msg.content,
                })
        
        # Build kwargs
        kwargs = {}
        if req.max_tokens is not None:
            kwargs["max_tokens"] = req.max_tokens
        if req.temperature is not None:
            kwargs["temperature"] = req.temperature
        
        # Add history to kwargs
        if history_messages:
            kwargs["history_messages"] = history_messages
        
        # Execute query
        response = await state.rag_service.query(
            query=req.query,
            mode=req.mode,
            **kwargs
        )
        
        # Build updated history
        updated_history = list(req.history) if req.history else []
        
        # Add user message
        updated_history.append(ConversationMessage(
            role="user",
            content=req.query,
            timestamp=datetime.utcnow().isoformat(),
        ))
        
        # Add assistant response
        updated_history.append(ConversationMessage(
            role="assistant",
            content=response,
            timestamp=datetime.utcnow().isoformat(),
        ))
        
        return ConversationResponse(
            query=req.query,
            response=response,
            history=updated_history,
        )
    
    except Exception as e:
        logger.error(f"Conversation query failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Conversation query failed: {str(e)}"
        )

