"""
File scanner utility for detecting and tracking files in upload directory.

Provides MD5 hashing and metadata extraction for file change detection.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional


logger = logging.getLogger(__name__)


@dataclass
class FileMetadata:
    """
    Metadata for a file in the upload directory.
    
    Attributes:
        path: Relative file path from upload directory
        hash: MD5 hash of file content
        size: File size in bytes
        last_modified: File's last modification timestamp
        name: File name (without directory path)
    """
    
    path: str
    hash: str
    size: int
    last_modified: datetime
    name: str


def compute_file_hash(file_path: Path) -> str:
    """
    Compute MD5 hash of file content.
    
    Reads file in chunks to handle large files efficiently.
    
    Args:
        file_path: Path to file
        
    Returns:
        MD5 hash as hexadecimal string
        
    Raises:
        FileNotFoundError: If file does not exist
        PermissionError: If file cannot be read
        OSError: For other I/O errors
    """
    md5_hash = hashlib.md5()
    
    try:
        with open(file_path, "rb") as f:
            # Read in 64KB chunks for memory efficiency
            for chunk in iter(lambda: f.read(65536), b""):
                md5_hash.update(chunk)
        
        return md5_hash.hexdigest()
    
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        raise
    except PermissionError:
        logger.error(f"Permission denied reading file: {file_path}")
        raise
    except OSError as e:
        logger.error(f"I/O error reading file {file_path}: {e}")
        raise


def get_file_metadata(file_path: Path, upload_dir: Path) -> FileMetadata:
    """
    Extract metadata for a single file.
    
    Args:
        file_path: Absolute path to file
        upload_dir: Upload directory root (for computing relative path)
        
    Returns:
        FileMetadata object with hash, size, mtime, and name
        
    Raises:
        FileNotFoundError: If file does not exist
        PermissionError: If file cannot be accessed
        OSError: For other I/O errors
    """
    # Get file stats
    stat = file_path.stat()
    
    # Compute relative path from upload_dir
    try:
        relative_path = file_path.relative_to(upload_dir)
    except ValueError:
        # File is not under upload_dir
        logger.error(f"File {file_path} is not under upload_dir {upload_dir}")
        raise
    
    # Compute hash
    file_hash = compute_file_hash(file_path)
    
    # Extract metadata
    return FileMetadata(
        path=str(relative_path),
        hash=file_hash,
        size=stat.st_size,
        last_modified=datetime.fromtimestamp(stat.st_mtime),
        name=file_path.name,
    )


def scan_upload_directory(upload_dir: Path) -> List[FileMetadata]:
    """
    Scan upload directory and return metadata for all files.
    
    Recursively scans all subdirectories. Handles errors gracefully
    by logging and continuing with remaining files.
    
    Args:
        upload_dir: Path to upload directory
        
    Returns:
        List of FileMetadata objects for all accessible files
    """
    if not upload_dir.exists():
        logger.warning(f"Upload directory does not exist: {upload_dir}")
        return []
    
    if not upload_dir.is_dir():
        logger.error(f"Upload path is not a directory: {upload_dir}")
        return []
    
    metadata_list: List[FileMetadata] = []
    
    # Use rglob to recursively find all files
    for file_path in upload_dir.rglob("*"):
        # Skip directories
        if not file_path.is_file():
            continue
        
        # Skip hidden files and trash directory
        if any(part.startswith(".") for part in file_path.parts):
            logger.debug(f"Skipping hidden/trash file: {file_path}")
            continue
        
        try:
            metadata = get_file_metadata(file_path, upload_dir)
            metadata_list.append(metadata)
            logger.debug(f"Scanned file: {metadata.path} (hash={metadata.hash[:8]}...)")
        
        except FileNotFoundError:
            # File was deleted during scan
            logger.warning(f"File disappeared during scan: {file_path}")
            continue
        
        except PermissionError:
            # Cannot read file
            logger.warning(f"Permission denied for file: {file_path}")
            continue
        
        except OSError as e:
            # Other I/O error
            logger.warning(f"Error scanning file {file_path}: {e}")
            continue
    
    logger.info(f"Scanned {len(metadata_list)} files in {upload_dir}")
    return metadata_list

