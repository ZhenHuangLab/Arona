"""
Index Status Service - SQLite-based CRUD operations for document indexing status.

Provides persistent storage for tracking which documents have been indexed,
their current status, and associated metadata.
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from backend.models.index_status import IndexStatus, StatusEnum


logger = logging.getLogger(__name__)


class IndexStatusService:
    """
    Service for managing document index status in SQLite.

    Provides CRUD operations with atomic upserts and fail-fast error handling.
    """

    def __init__(self, db_path: str = "backend/data/index_status.db"):
        """
        Initialize IndexStatusService.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path

        # Ensure data directory exists
        db_dir = Path(db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)

        # Initialize database schema
        self.init_db()

        logger.info(f"IndexStatusService initialized with database: {db_path}")

    def _get_connection(self) -> sqlite3.Connection:
        """
        Create a new database connection.

        Returns:
            SQLite connection with row factory enabled
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        return conn

    def init_db(self) -> None:
        """
        Initialize database schema.

        Creates index_status table if it doesn't exist.
        """
        conn = self._get_connection()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS index_status (
                    file_path TEXT PRIMARY KEY,
                    file_hash TEXT NOT NULL,
                    status TEXT NOT NULL,
                    indexed_at TEXT,
                    error_message TEXT,
                    file_size INTEGER NOT NULL,
                    last_modified TEXT NOT NULL
                )
            """)
            conn.commit()
            logger.info("Database schema initialized")
        except sqlite3.Error as e:
            logger.error(f"Failed to initialize database: {e}", exc_info=True)
            raise
        finally:
            conn.close()

    def get_status(self, file_path: str) -> Optional[IndexStatus]:
        """
        Retrieve index status for a single file.

        Args:
            file_path: Relative file path from upload directory

        Returns:
            IndexStatus if found, None otherwise
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM index_status WHERE file_path = ?", (file_path,)
            )
            row = cursor.fetchone()

            if row is None:
                return None

            return self._row_to_model(row)
        except sqlite3.Error as e:
            logger.error(f"Failed to get status for {file_path}: {e}", exc_info=True)
            raise
        finally:
            conn.close()

    def list_all_status(self) -> List[IndexStatus]:
        """
        Retrieve all index status records.

        Returns:
            List of all IndexStatus records
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM index_status ORDER BY last_modified DESC"
            )
            rows = cursor.fetchall()

            return [self._row_to_model(row) for row in rows]
        except sqlite3.Error as e:
            logger.error(f"Failed to list all status: {e}", exc_info=True)
            raise
        finally:
            conn.close()

    def upsert_status(self, status: IndexStatus) -> None:
        """
        Insert or update index status atomically.

        Uses INSERT OR REPLACE for atomic upsert operation.

        Args:
            status: IndexStatus to insert or update
        """
        conn = self._get_connection()
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO index_status
                (file_path, file_hash, status, indexed_at, error_message, file_size, last_modified)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    status.file_path,
                    status.file_hash,
                    status.status.value,
                    status.indexed_at.isoformat() if status.indexed_at else None,
                    status.error_message,
                    status.file_size,
                    status.last_modified.isoformat(),
                ),
            )
            conn.commit()
            logger.debug(
                f"Upserted status for {status.file_path}: {status.status.value}"
            )
        except sqlite3.Error as e:
            logger.error(
                f"Failed to upsert status for {status.file_path}: {e}", exc_info=True
            )
            raise
        finally:
            conn.close()

    def update_status_field(
        self, file_path: str, field: str, value: str | int | datetime | None
    ) -> None:
        """
        Update a single field for a file's status.

        Useful for atomic status transitions (e.g., pending -> processing).

        Args:
            file_path: Relative file path from upload directory
            field: Field name to update (status, error_message, indexed_at)
            value: New value for the field
        """
        # Validate field name to prevent SQL injection
        allowed_fields = {"status", "error_message", "indexed_at", "file_hash"}
        if field not in allowed_fields:
            raise ValueError(f"Invalid field name: {field}. Allowed: {allowed_fields}")

        # Convert value to appropriate format
        if isinstance(value, datetime):
            value = value.isoformat()
        elif isinstance(value, StatusEnum):
            value = value.value

        conn = self._get_connection()
        try:
            query = f"UPDATE index_status SET {field} = ? WHERE file_path = ?"
            conn.execute(query, (value, file_path))
            conn.commit()
            logger.debug(f"Updated {field} for {file_path}: {value}")
        except sqlite3.Error as e:
            logger.error(
                f"Failed to update {field} for {file_path}: {e}", exc_info=True
            )
            raise
        finally:
            conn.close()

    def delete_status(self, file_path: str) -> None:
        """
        Delete index status for a file.

        Args:
            file_path: Relative file path from upload directory
        """
        conn = self._get_connection()
        try:
            conn.execute("DELETE FROM index_status WHERE file_path = ?", (file_path,))
            conn.commit()
            logger.debug(f"Deleted status for {file_path}")
        except sqlite3.Error as e:
            logger.error(f"Failed to delete status for {file_path}: {e}", exc_info=True)
            raise
        finally:
            conn.close()

    def _row_to_model(self, row: sqlite3.Row) -> IndexStatus:
        """
        Convert SQLite row to IndexStatus model.

        Args:
            row: SQLite row object

        Returns:
            IndexStatus instance
        """
        return IndexStatus(
            file_path=row["file_path"],
            file_hash=row["file_hash"],
            status=StatusEnum(row["status"]),
            indexed_at=datetime.fromisoformat(row["indexed_at"])
            if row["indexed_at"]
            else None,
            error_message=row["error_message"],
            file_size=row["file_size"],
            last_modified=datetime.fromisoformat(row["last_modified"]),
        )
