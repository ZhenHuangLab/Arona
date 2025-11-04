"""
RAG-Anything Backend API Server

FastAPI application providing REST API for RAG operations.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from dotenv import load_dotenv

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load environment variables from .env.backend
# Reason: Backend needs to load configuration before importing config module
env_file = PROJECT_ROOT / ".env.backend"
if env_file.exists():
    load_dotenv(dotenv_path=env_file, override=False)
    logging.info(f"Loaded environment from {env_file}")

from backend.config import BackendConfig
from backend.services.rag_service import RAGService
from backend.routers import documents, query, health, graph, config


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting RAG-Anything backend server...")

    # Load configuration from environment
    config = BackendConfig.from_env()

    # Create upload directory
    Path(config.upload_dir).mkdir(parents=True, exist_ok=True)
    Path(config.working_dir).mkdir(parents=True, exist_ok=True)

    # Initialize RAG service
    rag_service = RAGService(config)

    # Store in app state
    app.state.config = config
    app.state.rag_service = rag_service

    logger.info("Backend server started successfully")
    logger.info(f"Working directory: {config.working_dir}")
    logger.info(f"Upload directory: {config.upload_dir}")

    yield

    # Shutdown
    logger.info("Shutting down RAG-Anything backend server...")


# Create FastAPI app
app = FastAPI(
    title="RAG-Anything API",
    description="REST API for multimodal RAG operations",
    version="2.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(documents.router, prefix="/api/documents", tags=["Documents"])
app.include_router(query.router, prefix="/api/query", tags=["Query"])
app.include_router(graph.router, prefix="/api/graph", tags=["Graph"])
app.include_router(config.router, prefix="/api/config", tags=["Configuration"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "RAG-Anything API",
        "version": "2.0.0",
        "status": "running",
    }


def main():
    """Run the API server."""
    import argparse
    
    parser = argparse.ArgumentParser(description="RAG-Anything Backend API Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    args = parser.parse_args()
    
    logger.info(f"Starting server on {args.host}:{args.port}")
    
    uvicorn.run(
        "backend.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
    )


if __name__ == "__main__":
    main()

