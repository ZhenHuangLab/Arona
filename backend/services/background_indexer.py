"""
Background Indexer Service - Automatic document detection and processing.

Periodically scans upload directory for new/modified files and triggers
RAG processing with status tracking.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from backend.config import BackendConfig
from backend.models.index_status import IndexStatus, StatusEnum
from backend.services.index_status_service import IndexStatusService
from backend.services.rag_service import RAGService
from backend.services.file_scanner import scan_upload_directory, FileMetadata


logger = logging.getLogger(__name__)


class BackgroundIndexer:
    """
    Background service for automatic document indexing.
    
    Scans upload directory periodically, detects new/modified files,
    and processes them through the RAG pipeline with status tracking.
    """
    
    def __init__(
        self,
        config: BackendConfig,
        rag_service: RAGService,
        index_status_service: IndexStatusService,
    ):
        """
        Initialize BackgroundIndexer.
        
        Args:
            config: Backend configuration
            rag_service: RAG service for document processing
            index_status_service: Service for status tracking
        """
        self.config = config
        self.rag_service = rag_service
        self.index_status_service = index_status_service
        self.upload_dir = Path(config.upload_dir)
        
        logger.info(
            f"BackgroundIndexer initialized: "
            f"enabled={config.auto_indexing_enabled}, "
            f"interval={config.indexing_scan_interval}s, "
            f"max_batch={config.indexing_max_files_per_batch}"
        )
    
    async def scan_and_update_status(self) -> None:
        """
        Scan upload directory and update status for new/modified files.
        
        Compares files in upload_dir with IndexStatus DB:
        - New files: Create status record with status=pending
        - Modified files (hash changed): Update status to pending
        - Unchanged files: No action
        """
        logger.debug("Starting upload directory scan...")
        
        try:
            # Scan upload directory for all files
            file_metadata_list = scan_upload_directory(self.upload_dir)
            logger.info(f"Found {len(file_metadata_list)} files in upload directory")
            
            # Get all existing status records
            existing_statuses = {
                status.file_path: status
                for status in self.index_status_service.list_all_status()
            }
            
            # Process each file
            for file_meta in file_metadata_list:
                existing_status = existing_statuses.get(file_meta.path)
                
                if existing_status is None:
                    # New file: Create pending status
                    new_status = IndexStatus(
                        file_path=file_meta.path,
                        file_hash=file_meta.hash,
                        status=StatusEnum.PENDING,
                        indexed_at=None,
                        error_message=None,
                        file_size=file_meta.size,
                        last_modified=file_meta.last_modified,
                    )
                    self.index_status_service.upsert_status(new_status)
                    logger.info(f"New file detected: {file_meta.path}")
                
                elif existing_status.file_hash != file_meta.hash:
                    # Modified file: Reset to pending
                    updated_status = IndexStatus(
                        file_path=file_meta.path,
                        file_hash=file_meta.hash,
                        status=StatusEnum.PENDING,
                        indexed_at=None,
                        error_message=None,
                        file_size=file_meta.size,
                        last_modified=file_meta.last_modified,
                    )
                    self.index_status_service.upsert_status(updated_status)
                    logger.info(
                        f"Modified file detected: {file_meta.path} "
                        f"(hash changed from {existing_status.file_hash[:8]}... "
                        f"to {file_meta.hash[:8]}...)"
                    )
            
            logger.debug("Upload directory scan completed")
        
        except Exception as e:
            logger.error(f"Error during directory scan: {e}", exc_info=True)
            raise
    
    async def process_pending_files(self) -> None:
        """
        Process pending files through RAG pipeline.
        
        Retrieves files with status=pending, processes them via RAG service,
        and updates status to indexed/failed. Implements rate limiting by
        processing max N files per iteration.
        """
        try:
            # Get all pending files
            all_statuses = self.index_status_service.list_all_status()
            pending_files = [
                status for status in all_statuses
                if status.status == StatusEnum.PENDING
            ]
            
            if not pending_files:
                logger.debug("No pending files to process")
                return
            
            # Apply rate limiting
            max_batch = self.config.indexing_max_files_per_batch
            files_to_process = pending_files[:max_batch]
            
            logger.info(
                f"Processing {len(files_to_process)} pending files "
                f"(total pending: {len(pending_files)})"
            )
            
            # Process each file
            for status in files_to_process:
                await self._process_single_file(status)
        
        except Exception as e:
            logger.error(f"Error during pending file processing: {e}", exc_info=True)
            raise
    
    async def _process_single_file(self, status: IndexStatus) -> None:
        """
        Process a single file through RAG pipeline.
        
        Implements atomic status update (pending → processing) to prevent
        concurrent processing. Updates status to indexed/failed based on result.
        
        Args:
            status: IndexStatus record for the file
        """
        file_path = self.upload_dir / status.file_path
        
        try:
            # Atomic status update: pending → processing
            # Reason: Prevents concurrent processing of the same file
            current_status = self.index_status_service.get_status(status.file_path)
            if current_status is None:
                logger.warning(f"File status disappeared: {status.file_path}")
                return
            
            if current_status.status != StatusEnum.PENDING:
                logger.debug(
                    f"Skipping file (status={current_status.status.value}): "
                    f"{status.file_path}"
                )
                return
            
            # Update to processing
            self.index_status_service.update_status_field(
                status.file_path,
                "status",
                StatusEnum.PROCESSING
            )
            logger.info(f"Processing file: {status.file_path}")
            
            # Process document through RAG pipeline
            result = await self.rag_service.process_document(
                file_path=str(file_path),
                parse_method="auto",
            )
            
            # Check result and update status
            if result.get("status") == "success":
                # Success: Update to indexed
                updated_status = IndexStatus(
                    file_path=status.file_path,
                    file_hash=status.file_hash,
                    status=StatusEnum.INDEXED,
                    indexed_at=datetime.now(),
                    error_message=None,
                    file_size=status.file_size,
                    last_modified=status.last_modified,
                )
                self.index_status_service.upsert_status(updated_status)
                logger.info(f"Successfully indexed: {status.file_path}")
            
            else:
                # Error: Update to failed
                error_msg = result.get("error", "Unknown error")
                updated_status = IndexStatus(
                    file_path=status.file_path,
                    file_hash=status.file_hash,
                    status=StatusEnum.FAILED,
                    indexed_at=None,
                    error_message=error_msg,
                    file_size=status.file_size,
                    last_modified=status.last_modified,
                )
                self.index_status_service.upsert_status(updated_status)
                logger.error(f"Failed to index {status.file_path}: {error_msg}")
        
        except Exception as e:
            # Unexpected error: Update to failed
            error_msg = f"{type(e).__name__}: {str(e)}"
            logger.error(
                f"Unexpected error processing {status.file_path}: {error_msg}",
                exc_info=True
            )
            
            try:
                updated_status = IndexStatus(
                    file_path=status.file_path,
                    file_hash=status.file_hash,
                    status=StatusEnum.FAILED,
                    indexed_at=None,
                    error_message=error_msg,
                    file_size=status.file_size,
                    last_modified=status.last_modified,
                )
                self.index_status_service.upsert_status(updated_status)
            except Exception as db_error:
                logger.error(
                    f"Failed to update status for {status.file_path}: {db_error}",
                    exc_info=True
                )
    
    async def run_periodic_scan(self) -> None:
        """
        Main background task loop.
        
        Periodically scans upload directory and processes pending files.
        Runs until cancelled (e.g., on application shutdown).
        """
        logger.info("Background indexer task started")
        
        try:
            while True:
                try:
                    # Scan for new/modified files
                    await self.scan_and_update_status()
                    
                    # Process pending files
                    await self.process_pending_files()
                
                except Exception as e:
                    # Log error but continue loop
                    # Reason: One iteration failure should not kill the background task
                    logger.error(
                        f"Error in background indexer iteration: {e}",
                        exc_info=True
                    )
                
                # Wait for next iteration
                await asyncio.sleep(self.config.indexing_scan_interval)
        
        except asyncio.CancelledError:
            # Graceful shutdown
            logger.info("Background indexer task cancelled, shutting down...")
            raise

