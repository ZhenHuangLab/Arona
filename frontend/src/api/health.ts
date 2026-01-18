/**
 * Health Check API
 */

import apiClient from './client';
import type { HealthResponse, ReadyResponse } from '../types';

/**
 * Check backend health status
 */
export const checkHealth = async (): Promise<HealthResponse> => {
  const response = await apiClient.get<HealthResponse>('/health');
  return response.data;
};

/**
 * Check backend readiness
 */
export const checkReady = async (): Promise<ReadyResponse> => {
  const response = await apiClient.get<ReadyResponse>('/ready');
  return response.data;
};

// Named export for convenience
export const healthApi = {
  checkHealth,
  checkReady,
};
