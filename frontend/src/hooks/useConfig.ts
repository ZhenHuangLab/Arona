import { useQuery } from '@tanstack/react-query';
import { getConfig } from '@/api/config';
import type { ConfigResponse } from '@/types/api';

/**
 * useConfig Hook
 *
 * Custom hook for fetching backend configuration with React Query.
 *
 * Features:
 * - Fetch current backend configuration
 * - 5-minute cache (staleTime)
 * - Loading and error states
 * - Automatic refetching on reconnect
 *
 * Usage:
 * ```tsx
 * const { config, isLoading, error, refetch } = useConfig();
 *
 * if (config) {
 *   console.log(config.storage.upload_dir);
 * }
 * ```
 */
export function useConfig() {
  const {
    data: config,
    isLoading,
    error,
    refetch,
  } = useQuery<ConfigResponse>({
    queryKey: ['config', 'current'],
    queryFn: getConfig,
    staleTime: 5 * 60 * 1000, // 5 minutes - config rarely changes
    gcTime: 10 * 60 * 1000, // 10 minutes - keep in cache
    refetchOnWindowFocus: false, // Don't refetch on window focus
    refetchOnReconnect: true, // Refetch on reconnect
  });

  return {
    config,
    isLoading,
    error,
    refetch,
  };
}
