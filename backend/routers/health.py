"""
Health check endpoints.
"""

from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Dict, Any


router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    rag_initialized: bool
    models: Dict[str, Any]


@router.get("/health", response_model=HealthResponse)
async def health_check(request: Request):
    """
    Health check endpoint.

    Returns service status and configuration.
    """
    state = request.app.state

    rag_status = await state.rag_service.get_status()

    return HealthResponse(
        status="healthy",
        version="2.0.0",
        rag_initialized=rag_status["initialized"],
        models=rag_status["models"],
    )


@router.get("/ready")
async def readiness_check(request: Request):
    """
    Readiness check endpoint.

    Returns whether the service is ready to accept requests.
    """
    state = request.app.state
    rag_status = await state.rag_service.get_status()

    return {
        "ready": rag_status["initialized"],
        "status": "ready" if rag_status["initialized"] else "initializing",
    }
