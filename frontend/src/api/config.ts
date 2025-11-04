/**
 * Configuration API
 */

import apiClient from './client';
import type { ConfigResponse, ConfigReloadRequest, ConfigReloadResponse } from '../types';

/**
 * Get current backend configuration
 */
export const getConfig = async (): Promise<ConfigResponse> => {
  const response = await apiClient.get<ConfigResponse>('/api/config/current');
  return response.data;
};

/**
 * Reload configuration from files
 */
export const reloadConfig = async (request?: ConfigReloadRequest): Promise<ConfigReloadResponse> => {
  const response = await apiClient.post<ConfigReloadResponse>('/api/config/reload', request || {});
  return response.data;
};

// Named export for convenience
export const configApi = {
  getConfig,
  reloadConfig,
};

