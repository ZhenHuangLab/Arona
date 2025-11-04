"""
Document management endpoints.
"""

import logging
import os
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import List

from fastapi import APIRouter, Request, UploadFile, File, HTTPException, status
from fastapi.responses import JSONResponse

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
from backend.models.index_status import (
    IndexStatus,
    IndexStatusResponse,
    StatusEnum,
    TriggerIndexResponse,
)
from backend.services.file_scanner import compute_file_hash


router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    request: Request,
    file: UploadFile = File(..., description="Document file to upload")
):
    """
    Upload a document file.
    
    Saves the file to the upload directory for later processing.
    """
    state = request.app.state
    
    try:
        # Create upload directory if it doesn't exist
        upload_dir = Path(state.config.upload_dir)
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Save uploaded file
        file_path = upload_dir / file.filename
        
        # Check if file already exists
        if file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"File '{file.filename}' already exists"
            )
        
        # Save file
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        file_size = file_path.stat().st_size

        logger.info(f"Uploaded file: {file.filename} ({file_size} bytes)")

        # Defensive: Create IndexStatus record (status=PENDING)
        # Reason: Track uploaded files for background indexing, but don't fail upload if status creation fails
        try:
            relative_path = str(file_path.relative_to(upload_dir))
            file_hash = compute_file_hash(str(file_path))
            last_modified = datetime.fromtimestamp(file_path.stat().st_mtime)

            index_status = IndexStatus(
                file_path=relative_path,
                file_hash=file_hash,
                status=StatusEnum.PENDING,
                indexed_at=None,
                error_message=None,
                file_size=file_size,
                last_modified=last_modified,
            )
            state.index_status_service.upsert_status(index_status)
            logger.debug(f"Created IndexStatus (PENDING) for {relative_path}")
        except Exception as status_error:
            # Log warning but don't fail the upload
            logger.warning(
                f"Failed to create IndexStatus for {file.filename}: {status_error}",
                exc_info=True
            )

        return DocumentUploadResponse(
            filename=file.filename,
            file_path=str(file_path),
            file_size=file_size,
            content_type=file.content_type,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload file: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file: {str(e)}"
        )


@router.post("/process", response_model=DocumentProcessResponse)
async def process_document(
    request: Request,
    req: DocumentProcessRequest
):
    """
    Process a document and add it to the knowledge base.
    
    The document must have been uploaded first via /upload endpoint.
    """
    state = request.app.state
    
    try:
        # Verify file exists
        file_path = Path(req.file_path)
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File not found: {req.file_path}"
            )
        
        # Process document
        result = await state.rag_service.process_document(
            file_path=req.file_path,
            output_dir=req.output_dir,
            parse_method=req.parse_method,
        )

        # Defensive: Update IndexStatus to INDEXED after successful processing
        # Reason: Track processing completion, but don't fail request if status update fails
        if result.get("status") == "success":
            try:
                upload_dir = Path(state.config.upload_dir)
                # Handle both absolute and relative paths
                if file_path.is_absolute():
                    relative_path = str(file_path.relative_to(upload_dir))
                else:
                    relative_path = str(file_path)

                # Get existing status to preserve file_hash and file_size
                existing_status = state.index_status_service.get_status(relative_path)
                if existing_status:
                    # Update existing status to INDEXED
                    updated_status = IndexStatus(
                        file_path=relative_path,
                        file_hash=existing_status.file_hash,
                        status=StatusEnum.INDEXED,
                        indexed_at=datetime.now(),
                        error_message=None,
                        file_size=existing_status.file_size,
                        last_modified=existing_status.last_modified,
                    )
                    state.index_status_service.upsert_status(updated_status)
                    logger.debug(f"Updated IndexStatus (INDEXED) for {relative_path}")
                else:
                    # No existing status, create new one
                    file_hash = compute_file_hash(str(file_path))
                    file_size = file_path.stat().st_size
                    last_modified = datetime.fromtimestamp(file_path.stat().st_mtime)

                    new_status = IndexStatus(
                        file_path=relative_path,
                        file_hash=file_hash,
                        status=StatusEnum.INDEXED,
                        indexed_at=datetime.now(),
                        error_message=None,
                        file_size=file_size,
                        last_modified=last_modified,
                    )
                    state.index_status_service.upsert_status(new_status)
                    logger.debug(f"Created IndexStatus (INDEXED) for {relative_path}")
            except Exception as status_error:
                # Log warning but don't fail the processing response
                logger.warning(
                    f"Failed to update IndexStatus for {req.file_path}: {status_error}",
                    exc_info=True
                )

        return DocumentProcessResponse(**result)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to process document: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process document: {str(e)}"
        )


@router.post("/upload-and-process", response_model=DocumentProcessResponse)
async def upload_and_process_document(
    request: Request,
    file: UploadFile = File(..., description="Document file to upload and process"),
    parse_method: str = "auto",
):
    """
    Upload and immediately process a document.
    
    Combines upload and process operations into a single endpoint.
    """
    state = request.app.state
    
    try:
        # Upload file
        upload_dir = Path(state.config.upload_dir)
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = upload_dir / file.filename
        
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        logger.info(f"Uploaded and processing file: {file.filename}")
        
        # Process document
        result = await state.rag_service.process_document(
            file_path=str(file_path),
            parse_method=parse_method,
        )

        # Defensive: Create IndexStatus record (status=INDEXED) after successful processing
        # Reason: Track processed files, but don't fail request if status creation fails
        if result.get("status") == "success":
            try:
                relative_path = str(file_path.relative_to(upload_dir))
                file_hash = compute_file_hash(str(file_path))
                file_size = file_path.stat().st_size
                last_modified = datetime.fromtimestamp(file_path.stat().st_mtime)

                index_status = IndexStatus(
                    file_path=relative_path,
                    file_hash=file_hash,
                    status=StatusEnum.INDEXED,
                    indexed_at=datetime.now(),
                    error_message=None,
                    file_size=file_size,
                    last_modified=last_modified,
                )
                state.index_status_service.upsert_status(index_status)
                logger.debug(f"Created IndexStatus (INDEXED) for {relative_path}")
            except Exception as status_error:
                # Log warning but don't fail the upload-and-process response
                logger.warning(
                    f"Failed to create IndexStatus for {file.filename}: {status_error}",
                    exc_info=True
                )

        return DocumentProcessResponse(**result)
    
    except Exception as e:
        logger.error(f"Failed to upload and process document: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload and process document: {str(e)}"
        )


@router.post("/batch-process", response_model=BatchProcessResponse)
async def batch_process_documents(
    request: Request,
    req: BatchProcessRequest
):
    """
    Process multiple documents from a folder.
    
    Processes all documents in the specified folder matching the given extensions.
    """
    state = request.app.state
    
    try:
        # Verify folder exists
        folder_path = Path(req.folder_path)
        if not folder_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Folder not found: {req.folder_path}"
            )
        
        # Get RAG instance
        rag = await state.rag_service.get_rag_instance()
        
        # Process folder
        logger.info(f"Batch processing folder: {req.folder_path}")
        
        await rag.process_folder_complete(
            folder_path=str(folder_path),
            output_dir=str(Path(state.config.working_dir) / "parsed_output"),
            file_extensions=req.file_extensions,
            recursive=req.recursive,
            max_workers=req.max_workers,
            parse_method=req.parse_method,
        )
        
        # TODO: Track individual file results
        # For now, return summary
        return BatchProcessResponse(
            total_files=0,  # Would need to track this
            successful=0,
            failed=0,
            results=[],
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to batch process documents: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to batch process documents: {str(e)}"
        )


@router.get("/list", response_model=DocumentListResponse)
async def list_documents(request: Request):
    """
    List all uploaded documents.

    Returns a list of all documents in the upload directory.
    """
    state = request.app.state

    try:
        upload_dir = Path(state.config.upload_dir)

        if not upload_dir.exists():
            return DocumentListResponse(documents=[], total=0)

        # List all files in upload directory
        documents = [
            str(f.relative_to(upload_dir))
            for f in upload_dir.rglob("*")
            if f.is_file()
        ]

        return DocumentListResponse(
            documents=documents,
            total=len(documents),
        )

    except Exception as e:
        logger.error(f"Failed to list documents: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list documents: {str(e)}"
        )


@router.get("/details", response_model=DocumentDetailsResponse)
async def get_document_details(request: Request):
    """
    Get detailed metadata for all uploaded documents.

    Returns comprehensive information including filename, size, upload date,
    status, and storage location for each document in the upload directory.

    Status determination:
    - "indexed": Document has been processed and indexed in LightRAG
    - "uploaded": Document exists but not yet processed
    - "processing": Document is currently being processed (future enhancement)
    """
    state = request.app.state

    try:
        upload_dir = Path(state.config.upload_dir)

        # Debug logging to diagnose path issues
        logger.info(f"[DEBUG] upload_dir config value: {state.config.upload_dir}")
        logger.info(f"[DEBUG] upload_dir resolved path: {upload_dir.resolve()}")
        logger.info(f"[DEBUG] upload_dir exists: {upload_dir.exists()}")

        if not upload_dir.exists():
            logger.warning(f"Upload directory does not exist: {upload_dir.resolve()}")
            return DocumentDetailsResponse(documents=[], total=0)

        # Get RAG instance to check processing status
        rag = await state.rag_service.get_rag_instance()

        # Get all processed document IDs from LightRAG
        processed_doc_ids = set()
        if rag.lightrag and rag.lightrag.doc_status:
            try:
                # Get all document status data from storage
                all_doc_status = await rag.lightrag.doc_status.get_all()
                for doc_id, doc_data in all_doc_status.items():
                    # Only consider documents with PROCESSED status
                    if doc_data.get("status") == "PROCESSED":
                        # Extract filename from file_path in doc_data
                        file_path = doc_data.get("file_path", "")
                        if file_path:
                            # file_path might be just filename or full path
                            filename = Path(file_path).name
                            processed_doc_ids.add(filename)
            except Exception as e:
                logger.warning(f"Error reading processed documents: {e}")

        # Collect detailed metadata for each file
        document_details = []

        for file_path in upload_dir.rglob("*"):
            # Skip directories and hidden files
            if not file_path.is_file() or file_path.name.startswith('.'):
                continue

            # Skip files in trash folder
            try:
                relative_path = file_path.relative_to(upload_dir)
                # Check if file is in .trash directory
                if '.trash' in relative_path.parts:
                    continue
            except ValueError:
                # File is not relative to upload_dir, skip it
                continue

            try:
                # Get file statistics
                stat = file_path.stat()

                # Calculate relative path from upload_dir
                relative_path_str = str(relative_path)

                # Determine status based on LightRAG processing
                status_value = "indexed" if file_path.name in processed_doc_ids else "uploaded"

                # Create document detail item
                detail = DocumentDetailItem(
                    filename=file_path.name,
                    file_path=relative_path_str,
                    file_size=stat.st_size,
                    upload_date=datetime.fromtimestamp(stat.st_mtime),
                    status=status_value,
                    storage_location=relative_path_str,
                )

                document_details.append(detail)

            except (OSError, ValueError) as e:
                # Log but continue processing other files
                logger.warning(f"Failed to get metadata for {file_path}: {e}")
                continue

        return DocumentDetailsResponse(
            documents=document_details,
            total=len(document_details),
        )

    except Exception as e:
        logger.error(f"Failed to get document details: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get document details: {str(e)}"
        )


@router.get("/processed")
async def list_processed_documents(request: Request):
    """
    List all RAG-processed documents with metadata.

    Returns information about documents that have been processed and indexed
    in the RAG knowledge base.
    """
    state = request.app.state

    try:
        # Get RAG instance
        rag = await state.rag_service.get_rag_instance()

        if not rag.lightrag:
            return {
                "documents": [],
                "total": 0,
                "message": "RAG system not initialized"
            }

        processed_docs = []

        # Get document status from LightRAG storage
        try:
            if rag.lightrag.doc_status:
                # Get all document status data from storage
                all_doc_status = await rag.lightrag.doc_status.get_all()
                for doc_id, doc_data in all_doc_status.items():
                    processed_docs.append({
                        "doc_id": doc_id,
                        "file_path": doc_data.get("file_path", ""),
                        "status": doc_data.get("status", "unknown"),
                        "chunks": doc_data.get("chunks", 0),
                        "processed_at": doc_data.get("processed_at", ""),
                    })
        except Exception as e:
            logger.warning(f"Error reading processed documents: {e}")

        return {
            "documents": processed_docs,
            "total": len(processed_docs),
            "working_dir": str(rag.lightrag.working_dir)
        }

    except Exception as e:
        logger.error(f"Failed to list processed documents: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list processed documents: {str(e)}"
        )


@router.delete("/delete/{filename}", response_model=DocumentDeleteResponse)
async def delete_document(
    request: Request,
    filename: str
):
    """
    Soft delete a document by moving it to trash folder.

    Instead of permanently deleting the file, it is moved to a .trash/ folder
    with a timestamp appended to prevent collisions. This provides a safety net
    for accidental deletions.

    Args:
        filename: Name of the file to delete (must not contain path separators)

    Returns:
        DocumentDeleteResponse with status, message, trash location, and original path

    Raises:
        HTTPException 400: Invalid filename (contains path separators or is empty)
        HTTPException 404: File not found
        HTTPException 403: Permission denied
        HTTPException 500: Other server errors
    """
    state = request.app.state

    try:
        # Security: Validate filename to prevent directory traversal attacks
        # Use os.path.basename to ensure no path components are included
        safe_filename = os.path.basename(filename)

        if not safe_filename or safe_filename != filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid filename: must not contain path separators"
            )

        if safe_filename.startswith('.'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid filename: hidden files cannot be deleted via API"
            )

        # Build paths
        upload_dir = Path(state.config.upload_dir)
        original_file_path = upload_dir / safe_filename

        # Check if file exists
        if not original_file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File not found: {safe_filename}"
            )

        if not original_file_path.is_file():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Not a file: {safe_filename}"
            )

        # Create trash directory if it doesn't exist
        trash_dir = upload_dir / ".trash"
        trash_dir.mkdir(parents=True, exist_ok=True)

        # Generate timestamp for unique trash filename
        timestamp = int(time.time())
        trash_filename = f"{timestamp}_{safe_filename}"
        trash_file_path = trash_dir / trash_filename

        # Move file to trash
        shutil.move(str(original_file_path), str(trash_file_path))

        logger.info(f"Moved file to trash: {safe_filename} -> {trash_filename}")

        return DocumentDeleteResponse(
            status="success",
            message=f"File '{safe_filename}' moved to trash successfully",
            trash_location=str(trash_file_path.relative_to(upload_dir)),
            original_path=safe_filename,
        )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise

    except PermissionError as e:
        logger.error(f"Permission denied when deleting file: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied: cannot delete file '{filename}'"
        )

    except Exception as e:
        logger.error(f"Failed to delete document: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete document: {str(e)}"
        )


@router.get("/index-status", response_model=List[IndexStatusResponse])
async def get_index_status(request: Request):
    """
    Get indexing status for all documents.

    Returns a list of all documents in the upload directory with their
    current indexing status (pending/processing/indexed/failed).

    Returns:
        List[IndexStatusResponse]: List of document statuses
    """
    state = request.app.state

    try:
        # Get all index statuses from database
        all_statuses = state.index_status_service.list_all_status()

        # Convert to response models
        response = [
            IndexStatusResponse(
                file_path=status.file_path,
                file_hash=status.file_hash,
                status=status.status,
                indexed_at=status.indexed_at,
                error_message=status.error_message,
                file_size=status.file_size,
                last_modified=status.last_modified,
            )
            for status in all_statuses
        ]

        logger.debug(f"Retrieved {len(response)} index status records")
        return response

    except Exception as e:
        logger.error(f"Failed to get index status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get index status: {str(e)}"
        )


@router.post("/trigger-index", response_model=TriggerIndexResponse)
async def trigger_index(request: Request):
    """
    Manually trigger index scan and processing.

    Scans the upload directory for new/modified files, updates their status,
    and triggers background processing for pending files.

    Returns:
        TriggerIndexResponse: Summary of scan results and processing status
    """
    state = request.app.state

    try:
        # Check if background indexer is available
        if not hasattr(state, 'background_indexer') or state.background_indexer is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Background indexer is not enabled. Set AUTO_INDEXING_ENABLED=true in configuration."
            )

        indexer = state.background_indexer

        # Scan upload directory and update status
        # Reason: This is fast (just file scanning and DB updates), safe to await
        await indexer.scan_and_update_status()

        # Get all statuses to count by status
        all_statuses = state.index_status_service.list_all_status()

        # Count files by status
        files_scanned = len(all_statuses)
        files_pending = sum(1 for s in all_statuses if s.status == StatusEnum.PENDING)
        files_processing = sum(1 for s in all_statuses if s.status == StatusEnum.PROCESSING)

        # Trigger background processing (don't await - let it run in background)
        # Reason: Processing can take time, don't block HTTP response
        import asyncio
        asyncio.create_task(indexer.process_pending_files())

        # Build response message
        message = f"Scan complete. Found {files_scanned} files total, {files_pending} pending processing."
        if files_processing > 0:
            message += f" {files_processing} files currently processing."

        logger.info(
            f"Manual index trigger: scanned={files_scanned}, "
            f"pending={files_pending}, processing={files_processing}"
        )

        return TriggerIndexResponse(
            files_scanned=files_scanned,
            files_pending=files_pending,
            files_processing=files_processing,
            message=message,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to trigger index: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger index: {str(e)}"
        )

