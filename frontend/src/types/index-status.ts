/**
 * Index Status Type Definitions
 *
 * Types for document indexing status tracking.
 * Matches backend IndexStatusResponse model.
 */

/**
 * Index status enum
 * Represents the current state of document indexing
 */
export type IndexStatusEnum = 'pending' | 'processing' | 'indexed' | 'failed';

/**
 * Index status for a single document
 * Returned by GET /api/documents/index-status
 */
export interface IndexStatus {
  file_path: string;
  file_hash: string;
  status: IndexStatusEnum;
  indexed_at: string | null; // ISO 8601 datetime string
  error_message: string | null;
  file_size: number;
  last_modified: string; // ISO 8601 datetime string
}

/**
 * Response from GET /api/documents/index-status
 */
export type IndexStatusListResponse = IndexStatus[];
