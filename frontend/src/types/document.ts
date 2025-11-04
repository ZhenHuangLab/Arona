/**
 * Document-related type definitions
 */

export interface DocumentFile {
  id: string;
  name: string;
  path: string;
  size: number;
  type?: string;
  status: 'pending' | 'uploading' | 'processing' | 'success' | 'error' | 'indexed' | 'uploaded';
  progress?: number;
  error?: string;
  uploadedAt?: Date;
  processedAt?: Date;
}

export interface UploadProgress {
  fileId: string;
  progress: number;
  loaded: number;
  total: number;
}

// Alias for DocumentCard component
export type DocumentInfo = DocumentFile;

export interface DocumentMetadata {
  title?: string;
  author?: string;
  createdAt?: string;
  modifiedAt?: string;
  pageCount?: number;
  wordCount?: number;
}

