/**
 * Query API
 */

import apiClient from './client';
import type {
  QueryRequest,
  QueryResponse,
  MultimodalQueryRequest,
  ConversationRequest,
  ConversationResponse,
} from '../types';

/**
 * Execute a standard RAG query
 */
export const executeQuery = async (request: QueryRequest): Promise<QueryResponse> => {
  const response = await apiClient.post<QueryResponse>('/api/query/', request);
  return response.data;
};

/**
 * Execute a multimodal query (with images, tables, equations)
 */
export const executeMultimodalQuery = async (
  request: MultimodalQueryRequest
): Promise<QueryResponse> => {
  const response = await apiClient.post<QueryResponse>('/api/query/multimodal', request);
  return response.data;
};

/**
 * Execute a conversational query with history
 */
export const executeConversationQuery = async (
  request: ConversationRequest
): Promise<ConversationResponse> => {
  const response = await apiClient.post<ConversationResponse>(
    '/api/query/conversation',
    request
  );
  return response.data;
};
