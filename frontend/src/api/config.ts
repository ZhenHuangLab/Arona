/**
 * Configuration API
 */

import apiClient from './client';
import type { ConfigResponse, ConfigReloadRequest, ConfigReloadResponse, ModelsUpdateRequest, ModelsUpdateResponse } from '../types';
import type { IndexingConfig, IndexingConfigUpdate, TriggerIndexResponse, ReindexRequest, ReindexResponse, ChatConfig, ChatConfigUpdate } from '../types/config';

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

/**
 * Update model configuration (persist to env file) and optionally apply immediately.
 */
export const updateModelsConfig = async (request: ModelsUpdateRequest): Promise<ModelsUpdateResponse> => {
  const response = await apiClient.put<ModelsUpdateResponse>('/api/config/models', request);
  return response.data;
};

/**
 * Get current indexing configuration
 *
 * Fetches background indexing settings including:
 * - auto_indexing_enabled: Whether background indexing is active
 * - indexing_scan_interval: Seconds between scans for new files
 * - indexing_max_files_per_batch: Max files processed per iteration
 */
export const getIndexingConfig = async (): Promise<IndexingConfig> => {
  const response = await apiClient.get<IndexingConfig>('/api/config/indexing');
  return response.data;
};

/**
 * Update indexing configuration
 *
 * Updates background indexing settings at runtime.
 * Supports partial updates - only specified fields will be changed.
 * Changes take effect immediately for the background indexer.
 *
 * Note: Changes are runtime-only and will be lost on server restart.
 *
 * @param config - Partial configuration update (all fields optional)
 * @returns Updated configuration
 */
export const updateIndexingConfig = async (config: IndexingConfigUpdate): Promise<IndexingConfig> => {
  const response = await apiClient.put<IndexingConfig>('/api/config/indexing', config);
  return response.data;
};

/**
 * Manually trigger index scan and processing
 *
 * Scans the upload directory for new/modified files, updates their status,
 * and triggers background processing for pending files.
 *
 * @returns Summary of scan results and processing status
 */
export const triggerIndex = async (): Promise<TriggerIndexResponse> => {
  const response = await apiClient.post<TriggerIndexResponse>('/api/documents/trigger-index');
  return response.data;
};

/**
 * Manually trigger re-indexing for specific files or all files
 *
 * This allows users to force re-indexing of documents that are already
 * indexed or failed. It changes the status of selected files to 'pending'
 * so they will be processed again by the background indexer.
 *
 * Use cases:
 * - Re-index failed documents after fixing configuration issues
 * - Force re-indexing of all documents after upgrading the RAG system
 * - Re-index specific documents that need to be updated in the knowledge graph
 *
 * @param request - ReindexRequest with optional file_paths list and force flag
 * @returns Summary of re-indexing operation
 */
export const reindexDocuments = async (request: ReindexRequest): Promise<ReindexResponse> => {
  const response = await apiClient.post<ReindexResponse>('/api/documents/reindex', request);
  return response.data;
};

/**
 * Get current chat configuration
 *
 * Fetches chat settings including:
 * - auto_attach_retrieved_images: Whether to auto-attach images from retrieval
 * - max_retrieved_images: Maximum number of images to attach
 */
export const getChatConfig = async (): Promise<ChatConfig> => {
  const response = await apiClient.get<ChatConfig>('/api/config/chat');
  return response.data;
};

/**
 * Update chat configuration
 *
 * Updates chat settings at runtime and persists to env file.
 * Supports partial updates - only specified fields will be changed.
 *
 * @param config - Partial configuration update (all fields optional)
 * @returns Updated configuration
 */
export const updateChatConfig = async (config: ChatConfigUpdate): Promise<ChatConfig> => {
  const response = await apiClient.put<ChatConfig>('/api/config/chat', config);
  return response.data;
};

// Named export for convenience
export const configApi = {
  getConfig,
  reloadConfig,
  updateModelsConfig,
  getIndexingConfig,
  updateIndexingConfig,
  triggerIndex,
  reindexDocuments,
  getChatConfig,
  updateChatConfig,
};
