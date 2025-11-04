import { QueryClient } from '@tanstack/react-query';

/**
 * React Query Client Configuration
 * 
 * Default options:
 * - Disable refetch on window focus (avoid unnecessary API calls)
 * - Retry failed queries once
 * - Cache data for 5 minutes (staleTime)
 * - Keep unused data in cache for 10 minutes (gcTime)
 */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      refetchOnReconnect: true,
      retry: 1,
      staleTime: 5 * 60 * 1000, // 5 minutes
      gcTime: 10 * 60 * 1000, // 10 minutes (formerly cacheTime)
    },
    mutations: {
      retry: 0,
    },
  },
});

/**
 * Query Keys
 * 
 * Centralized query key definitions for type safety and consistency
 */
export const queryKeys = {
  health: ['health'] as const,
  config: {
    current: ['config', 'current'] as const,
  },
  documents: {
    all: ['documents'] as const,
    list: () => [...queryKeys.documents.all, 'list'] as const,
  },
  graph: {
    all: ['graph'] as const,
    data: (limit?: number) => [...queryKeys.graph.all, 'data', limit] as const,
    stats: () => [...queryKeys.graph.all, 'stats'] as const,
  },
} as const;

