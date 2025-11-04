/**
 * Document Management API
 */

import apiClient, { createFormDataClient } from './client';
import type {
  DocumentUploadResponse,
  DocumentProcessRequest,
  DocumentProcessResponse,
  BatchProcessRequest,
  BatchProcessResponse,
  DocumentListResponse,
  DocumentDetailsResponse,
  DocumentDeleteResponse,
} from '../types';
import type { IndexStatusListResponse } from '../types/index-status';

/**
 * Upload a document file
 */
export const uploadDocument = async (
  file: File,
  onProgress?: (progress: number) => void
): Promise<DocumentUploadResponse> => {
  const formData = new FormData();
  formData.append('file', file);

  const client = createFormDataClient();
  const response = await client.post<DocumentUploadResponse>(
    '/api/documents/upload',
    formData,
    {
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(progress);
        }
      },
    }
  );

  return response.data;
};

/**
 * Process an uploaded document
 */
export const processDocument = async (
  request: DocumentProcessRequest
): Promise<DocumentProcessResponse> => {
  const response = await apiClient.post<DocumentProcessResponse>(
    '/api/documents/process',
    request
  );
  return response.data;
};

/**
 * Upload and process a document in one step
 */
export const uploadAndProcessDocument = async (
  file: File,
  parseMethod: string = 'auto',
  onProgress?: (progress: number) => void
): Promise<DocumentProcessResponse> => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('parse_method', parseMethod);

  const client = createFormDataClient();
  const response = await client.post<DocumentProcessResponse>(
    '/api/documents/upload-and-process',
    formData,
    {
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(progress);
        }
      },
    }
  );

  return response.data;
};

/**
 * Batch process documents from a folder
 */
export const batchProcessDocuments = async (
  request: BatchProcessRequest
): Promise<BatchProcessResponse> => {
  const response = await apiClient.post<BatchProcessResponse>(
    '/api/documents/batch-process',
    request
  );
  return response.data;
};

/**
 * List processed documents
 */
export const listDocuments = async (): Promise<DocumentListResponse> => {
  const response = await apiClient.get<DocumentListResponse>('/api/documents/list');
  return response.data;
};

/**
 * Get detailed metadata for all documents
 */
export const getDocumentDetails = async (): Promise<DocumentDetailsResponse> => {
  try {
    const response = await apiClient.get<DocumentDetailsResponse>('/api/documents/details');
    return response.data;
  } catch (error) {
    console.error('Failed to get document details:', error);
    throw error;
  }
};

/**
 * Delete a document (soft delete - moves to trash)
 */
export const deleteDocument = async (filename: string): Promise<DocumentDeleteResponse> => {
  try {
    const response = await apiClient.delete<DocumentDeleteResponse>(
      `/api/documents/delete/${encodeURIComponent(filename)}`
    );
    return response.data;
  } catch (error) {
    console.error('Failed to delete document:', error);
    throw error;
  }
};

/**
 * Get index status for all documents
 * Returns indexing status (pending/processing/indexed/failed) for each document
 */
export const getIndexStatus = async (): Promise<IndexStatusListResponse> => {
  try {
    const response = await apiClient.get<IndexStatusListResponse>('/api/documents/index-status');
    return response.data;
  } catch (error) {
    console.error('Failed to get index status:', error);
    throw error;
  }
};

