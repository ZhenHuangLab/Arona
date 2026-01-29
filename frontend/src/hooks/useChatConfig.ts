/**
 * useChatConfig Hooks
 *
 * Custom hooks for chat configuration operations with React Query.
 * Handles fetching and updating chat settings.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getChatConfig, updateChatConfig } from '@/api/config';
import { toast } from '@/lib/toast';
import type { ChatConfig, ChatConfigUpdate } from '@/types/config';

/**
 * useChatConfig Hook
 *
 * Fetches current chat configuration from backend.
 *
 * Features:
 * - Fetch chat configuration
 * - 1-minute cache (staleTime)
 * - Loading and error states
 * - Manual refetch capability
 *
 * Usage:
 * ```tsx
 * const { config, isLoading, error, refetch } = useChatConfig();
 *
 * if (config) {
 *   console.log(config.auto_attach_retrieved_images);
 * }
 * ```
 */
export function useChatConfig() {
  const {
    data: config,
    isLoading,
    error,
    refetch,
  } = useQuery<ChatConfig>({
    queryKey: ['config', 'chat'],
    queryFn: getChatConfig,
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
 * useUpdateChatConfig Hook
 *
 * Mutation for updating chat configuration.
 *
 * Features:
 * - Update configuration with partial updates
 * - Automatic cache invalidation
 * - Success/error toast notifications
 * - Loading state management
 *
 * Usage:
 * ```tsx
 * const { updateConfig, isUpdating } = useUpdateChatConfig();
 *
 * const handleSubmit = (data) => {
 *   updateConfig(data);
 * };
 * ```
 */
export function useUpdateChatConfig() {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: async (config: ChatConfigUpdate) => {
      return updateChatConfig(config);
    },
    onSuccess: () => {
      toast.success(
        'Configuration Updated',
        'Chat configuration has been updated successfully'
      );
      // Invalidate chat config to refetch
      queryClient.invalidateQueries({ queryKey: ['config', 'chat'] });
      // Also invalidate current config which includes chat settings
      queryClient.invalidateQueries({ queryKey: ['config'] });
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
