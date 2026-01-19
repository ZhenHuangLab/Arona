import { QueryClient } from '@tanstack/react-query';
import { APIException } from '@/types';

/**
 * React Query Client Configuration
 *
 * Default options:
 * - Disable refetch on window focus (avoid unnecessary API calls)
 * - Retry failed queries once (with extra retries for transient startup/proxy errors)
 * - Cache data for 5 minutes (staleTime)
 * - Keep unused data in cache for 10 minutes (gcTime)
 */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      refetchOnReconnect: true,
      retry: (failureCount, error) => {
        // When Docker Compose starts both services, the frontend may begin proxying requests
        // before the FastAPI app is ready (e.g. model downloads / warmup). Nginx will return 502
        // during that window, and without retries the UI can get "stuck" until manual refresh.
        if (error instanceof APIException) {
          const transientStatus = error.status === 0 || error.status === 502 || error.status === 503 || error.status === 504;
          if (transientStatus) return failureCount < 9; // ~1 minute with backoff (see retryDelay)
        }

        return failureCount < 1;
      },
      retryDelay: (attemptIndex, error) => {
        // Exponential backoff (max 10s). Longer when backend is starting/restarting.
        const baseDelayMs = error instanceof APIException && (error.status === 0 || error.status === 502 || error.status === 503 || error.status === 504) ? 1000 : 500;
        return Math.min(baseDelayMs * 2 ** attemptIndex, 10_000);
      },
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
