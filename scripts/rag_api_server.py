#!/usr/bin/env python3
"""
RAG-Anything REST API Server

Provides HTTP endpoints for corpus management, document ingestion, and RAG queries.
This server bridges Open WebUI's rag_anything_connector extension to the underlying
RAG-Anything/LightRAG functionality.

Usage:
    python scripts/rag_api_server.py --host 0.0.0.0 --port 8001

Environment Variables:
    RAG_SHARED_ROOT: Root directory for RAG storage (default: ~/rag-data)
    OLLAMA_HOST: Ollama service endpoint (required)
    RERANKER_MODEL_PATH: Path to FlagEmbedding weights
    OLLAMA_GENERATE_MODEL: Model for text generation
    OLLAMA_EMBED_MODEL: Model for embeddings
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

# Ensure project root is on path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Pydantic models for API
class CorpusCreate(BaseModel):
    name: str = Field(..., description="Human-readable corpus name")


class CorpusResponse(BaseModel):
    id: str
    name: str
    document_count: int = 0
    created_at: Optional[str] = None


class PreviewRequest(BaseModel):
    query: str
    limit: int = Field(default=5, ge=1, le=50)


class PreviewResult(BaseModel):
    score: float
    document_id: str
    snippet: str


class PreviewResponse(BaseModel):
    reranked: List[PreviewResult]


class GraphResponse(BaseModel):
    nodes: int
    edges: int
    sample_relationships: List[Dict[str, Any]]


# Global state
class AppState:
    """Shared application state."""
    rag_storage_root: Path
    ollama_host: str
    reranker_path: Optional[Path]
    generate_model: str
    embed_model: str
    embed_dim: int


app = FastAPI(
    title="RAG-Anything API",
    description="REST API for RAG corpus management and querying",
    version="1.0.0",
)
state = AppState()


@app.on_event("startup")
async def startup_event():
    """Initialize application state on startup."""
    # Load configuration from environment
    state.rag_storage_root = Path(os.getenv("RAG_SHARED_ROOT", Path.home() / "rag-data"))
    state.ollama_host = os.getenv("OLLAMA_HOST", "")
    
    reranker_path_str = os.getenv("RERANKER_MODEL_PATH")
    state.reranker_path = Path(reranker_path_str) if reranker_path_str else None
    
    state.generate_model = os.getenv("OLLAMA_GENERATE_MODEL", "qwen3:32b")
    state.embed_model = os.getenv("OLLAMA_EMBED_MODEL", "qwen3-embedding:8b")
    state.embed_dim = int(os.getenv("OLLAMA_EMBED_DIM", "4096"))
    
    # Create storage directory if needed
    state.rag_storage_root.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"RAG storage root: {state.rag_storage_root}")
    logger.info(f"Ollama host: {state.ollama_host or 'NOT SET'}")
    logger.info(f"Reranker path: {state.reranker_path}")
    logger.info(f"Generate model: {state.generate_model}")
    logger.info(f"Embed model: {state.embed_model}")
    
    if not state.ollama_host:
        logger.warning("OLLAMA_HOST not set - queries will fail")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "ollama_configured": bool(state.ollama_host),
        "storage_root": str(state.rag_storage_root),
    }


@app.get("/api/corpora", response_model=List[CorpusResponse])
async def list_corpora():
    """List all available corpora."""
    try:
        corpora = []
        
        # Scan storage root for corpus directories
        if state.rag_storage_root.exists():
            for corpus_dir in state.rag_storage_root.iterdir():
                if corpus_dir.is_dir():
                    # Count documents (simplified - could be enhanced)
                    doc_count = 0
                    input_dir = corpus_dir / "input"
                    if input_dir.exists():
                        doc_count = len(list(input_dir.glob("*")))
                    
                    corpora.append(CorpusResponse(
                        id=corpus_dir.name,
                        name=corpus_dir.name,
                        document_count=doc_count,
                    ))
        
        return corpora
    except Exception as e:
        logger.error(f"Failed to list corpora: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list corpora: {str(e)}"
        )


@app.post("/api/corpora", response_model=CorpusResponse, status_code=status.HTTP_201_CREATED)
async def create_corpus(request: CorpusCreate):
    """Create a new corpus."""
    try:
        # Sanitize corpus name to create a valid directory name
        corpus_id = request.name.lower().replace(" ", "_").replace("/", "_")
        corpus_path = state.rag_storage_root / corpus_id
        
        if corpus_path.exists():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Corpus '{corpus_id}' already exists"
            )
        
        # Create corpus directory structure
        corpus_path.mkdir(parents=True, exist_ok=False)
        (corpus_path / "input").mkdir(exist_ok=True)
        (corpus_path / "rag_storage").mkdir(exist_ok=True)
        
        # Write metadata
        metadata = {
            "id": corpus_id,
            "name": request.name,
            "created_at": None,  # Could add timestamp
        }
        with open(corpus_path / "metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Created corpus: {corpus_id}")
        
        return CorpusResponse(
            id=corpus_id,
            name=request.name,
            document_count=0,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create corpus: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create corpus: {str(e)}"
        )


@app.delete("/api/corpora/{corpus_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_corpus(corpus_id: str):
    """Delete a corpus and all its data."""
    try:
        corpus_path = state.rag_storage_root / corpus_id
        
        if not corpus_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Corpus '{corpus_id}' not found"
            )
        
        # Delete corpus directory recursively
        import shutil
        shutil.rmtree(corpus_path)
        
        logger.info(f"Deleted corpus: {corpus_id}")
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete corpus: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete corpus: {str(e)}"
        )


@app.post("/api/corpora/{corpus_id}/preview", response_model=PreviewResponse)
async def preview_embedding(corpus_id: str, request: PreviewRequest):
    """Preview embedding and reranking results for a query."""
    try:
        corpus_path = state.rag_storage_root / corpus_id
        
        if not corpus_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Corpus '{corpus_id}' not found"
            )
        
        # For now, return a placeholder response
        # TODO: Implement actual RAG query with reranking
        logger.warning(f"Preview for corpus '{corpus_id}' - not fully implemented yet")
        
        return PreviewResponse(
            reranked=[
                PreviewResult(
                    score=0.95,
                    document_id="placeholder",
                    snippet=f"Preview results for query: '{request.query}' (not yet implemented)"
                )
            ]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to preview embedding: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to preview embedding: {str(e)}"
        )


@app.get("/api/corpora/{corpus_id}/graph", response_model=GraphResponse)
async def get_graph_snapshot(corpus_id: str, limit: int = 50):
    """Get a snapshot of the LightRAG knowledge graph."""
    try:
        corpus_path = state.rag_storage_root / corpus_id
        
        if not corpus_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Corpus '{corpus_id}' not found"
            )
        
        # For now, return a placeholder response
        # TODO: Implement actual graph extraction from LightRAG storage
        logger.warning(f"Graph snapshot for corpus '{corpus_id}' - not fully implemented yet")
        
        return GraphResponse(
            nodes=0,
            edges=0,
            sample_relationships=[],
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get graph snapshot: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get graph snapshot: {str(e)}"
        )


def main():
    """Run the API server."""
    parser = argparse.ArgumentParser(description="RAG-Anything REST API Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8001, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    args = parser.parse_args()
    
    logger.info(f"Starting RAG-Anything API server on {args.host}:{args.port}")
    
    uvicorn.run(
        "rag_api_server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
    )


if __name__ == "__main__":
    main()

