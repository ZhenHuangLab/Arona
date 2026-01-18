/**
 * useIndexingConfig Hooks
 *
 * Custom hooks for indexing configuration operations with React Query.
 * Handles fetching, updating configuration, and triggering manual index scans.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getIndexingConfig, updateIndexingConfig, triggerIndex, reindexDocuments } from '@/api/config';
import { toast } from '@/lib/toast';
import type { IndexingConfig, IndexingConfigUpdate, TriggerIndexResponse, ReindexRequest, ReindexResponse } from '@/types/config';

/**
 * useIndexingConfig Hook
 *
 * Fetches current indexing configuration from backend.
 *
 * Features:
 * - Fetch indexing configuration
 * - 1-minute cache (staleTime)
 * - Loading and error states
 * - Manual refetch capability
 *
 * Usage:
 * ```tsx
 * const { config, isLoading, error, refetch } = useIndexingConfig();
 *
 * if (config) {
 *   console.log(config.auto_indexing_enabled);
 * }
 * ```
 */
export function useIndexingConfig() {
  const {
    data: config,
    isLoading,
    error,
    refetch,
  } = useQuery<IndexingConfig>({
    queryKey: ['config', 'indexing'],
    queryFn: getIndexingConfig,
    staleTime: 60 * 1000, // 1 minute - config changes infrequently
    gcTime: 5 * 60 * 1000, // 5 minutes - keep in cache
    refetchOnWindowFocus: false, // Don't refetch on window focus
  });

  return {
    config,
    isLoading,
    error,
    refetch,
  };
}

/**
 * useUpdateIndexingConfig Hook
 *
 * Mutation for updating indexing configuration.
 *
 * Features:
 * - Update configuration with partial updates
 * - Automatic cache invalidation
 * - Success/error toast notifications
 * - Loading state management
 *
 * Usage:
 * ```tsx
 * const { updateConfig, isUpdating } = useUpdateIndexingConfig();
 *
 * const handleSubmit = (data) => {
 *   updateConfig(data);
 * };
 * ```
 */
export function useUpdateIndexingConfig() {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: async (config: IndexingConfigUpdate) => {
      return updateIndexingConfig(config);
    },
    onSuccess: () => {
      toast.success(
        'Configuration Updated',
        'Indexing configuration has been updated successfully'
      );
      // Invalidate indexing config to refetch
      queryClient.invalidateQueries({ queryKey: ['config', 'indexing'] });
    },
    onError: (error: Error) => {
      const message = error instanceof Error ? error.message : 'Update failed';
      toast.error('Update Failed', `Failed to update configuration: ${message}`);
    },
  });

  return {
    updateConfig: mutation.mutate,
    isUpdating: mutation.isPending,
    error: mutation.error,
  };
}

/**
 * useTriggerIndex Hook
 *
 * Mutation for manually triggering index scan and processing.
 *
 * Features:
 * - Trigger immediate index scan
 * - Show scan results in toast
 * - Automatic cache invalidation for index status
 * - Loading state management
 *
 * Usage:
 * ```tsx
 * const { triggerScan, isTriggering } = useTriggerIndex();
 *
 * const handleRefresh = () => {
 *   triggerScan();
 * };
 * ```
 */
export function useTriggerIndex() {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: async () => {
      return triggerIndex();
    },
    onSuccess: (data: TriggerIndexResponse) => {
      // Show detailed toast with scan results
      toast.success(
        'Index Scan Complete',
        `${data.message} (${data.files_scanned} files scanned, ${data.files_pending} pending)`
      );
      // Invalidate index status to refetch updated statuses
      queryClient.invalidateQueries({ queryKey: ['documents', 'index-status'] });
      // Also invalidate documents list as processing may have completed
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    },
    onError: (error: Error) => {
      const message = error instanceof Error ? error.message : 'Trigger failed';
      toast.error('Index Trigger Failed', `Failed to trigger index scan: ${message}`);
    },
  });

  return {
    triggerScan: mutation.mutate,
    isTriggering: mutation.isPending,
    error: mutation.error,
  };
}

/**
 * useReindexDocuments Hook
 *
 * Mutation for manually triggering re-indexing of documents.
 *
 * Features:
 * - Re-index specific files or all files
 * - Force re-indexing of already indexed files
 * - Show re-indexing results in toast
 * - Automatic cache invalidation for index status
 * - Loading state management
 *
 * Usage:
 * ```tsx
 * const { reindex, isReindexing } = useReindexDocuments();
 *
 * // Re-index all failed files
 * const handleReindexFailed = () => {
 *   reindex({ force: false });
 * };
 *
 * // Force re-index all files
 * const handleReindexAll = () => {
 *   reindex({ force: true });
 * };
 *
 * // Re-index specific files
 * const handleReindexSpecific = () => {
 *   reindex({ file_paths: ['doc1.pdf', 'doc2.pdf'], force: true });
 * };
 * ```
 */
export function useReindexDocuments() {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: async (request: ReindexRequest) => {
      return reindexDocuments(request);
    },
    onSuccess: (data: ReindexResponse) => {
      // Show detailed toast with re-indexing results
      toast.success(
        'Re-index Complete',
        `${data.message}`
      );
      // Invalidate index status to refetch updated statuses
      queryClient.invalidateQueries({ queryKey: ['documents', 'index-status'] });
      // Also invalidate documents list as processing may have completed
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    },
    onError: (error: Error) => {
      const message = error instanceof Error ? error.message : 'Re-index failed';
      toast.error('Re-index Failed', `Failed to re-index documents: ${message}`);
    },
  });

  return {
    reindex: mutation.mutate,
    isReindexing: mutation.isPending,
    error: mutation.error,
  };
}
