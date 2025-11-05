/**
 * Configuration Type Definitions
 * 
 * TypeScript interfaces for indexing configuration and trigger responses.
 * Matches backend Pydantic models from backend/models/config.py and backend/models/index_status.py
 */

/**
 * Indexing Configuration
 * 
 * Configuration for automatic background indexing.
 * Returned by GET /api/config/indexing
 * Used in PUT /api/config/indexing (all fields optional for partial updates)
 */
export interface IndexingConfig {
  /**
   * Whether automatic background indexing is enabled
   */
  auto_indexing_enabled: boolean;
  
  /**
   * Seconds between background scans for new files
   * Validation: Must be >= 1
   * Note: Backend uses SECONDS, not minutes!
   */
  indexing_scan_interval: number;
  
  /**
   * Maximum number of files to process per iteration
   * Validation: Must be >= 1
   */
  indexing_max_files_per_batch: number;
}

/**
 * Indexing Configuration Update Request
 * 
 * Request body for PUT /api/config/indexing
 * All fields are optional to support partial updates
 */
export interface IndexingConfigUpdate {
  auto_indexing_enabled?: boolean;
  indexing_scan_interval?: number;
  indexing_max_files_per_batch?: number;
}

/**
 * Trigger Index Response
 *
 * Response from POST /api/documents/trigger-index
 * Provides summary of scan and processing operation
 */
export interface TriggerIndexResponse {
  /**
   * Total number of files found in upload directory
   */
  files_scanned: number;

  /**
   * Number of files with status=pending (awaiting processing)
   */
  files_pending: number;

  /**
   * Number of files currently being processed
   */
  files_processing: number;

  /**
   * Human-readable summary of the operation
   */
  message: string;
}

/**
 * Reindex Request
 *
 * Request for POST /api/documents/reindex
 * Allows manual re-indexing of specific files or all files
 */
export interface ReindexRequest {
  /**
   * List of file paths to re-index
   * If undefined or null, re-index all files
   */
  file_paths?: string[] | null;

  /**
   * If true, re-index even if status is already 'indexed'
   * If false, only re-index 'failed' files
   */
  force?: boolean;
}

/**
 * Reindex Response
 *
 * Response from POST /api/documents/reindex
 * Provides summary of re-indexing operation
 */
export interface ReindexResponse {
  /**
   * Number of files marked for re-indexing (status changed to pending)
   */
  files_marked_for_reindex: number;

  /**
   * Number of files skipped (not found or already pending/processing)
   */
  files_skipped: number;

  /**
   * Human-readable summary of the operation
   */
  message: string;
}

