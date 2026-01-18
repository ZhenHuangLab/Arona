/**
 * Knowledge Graph API
 */

import apiClient from './client';
import type { GraphDataResponse } from '../types';

/**
 * Get knowledge graph data for visualization
 */
export const getGraphData = async (
  limit: number = 100,
  includeMetadata: boolean = false
): Promise<GraphDataResponse> => {
  const response = await apiClient.get<GraphDataResponse>('/api/graph/data', {
    params: {
      limit,
      include_metadata: includeMetadata,
    },
  });
  return response.data;
};

/**
 * Get graph statistics
 */
export const getGraphStats = async (): Promise<Record<string, unknown>> => {
  const response = await apiClient.get<Record<string, unknown>>('/api/graph/stats');
  return response.data;
};
