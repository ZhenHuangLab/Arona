import { useQuery } from '@tanstack/react-query';
import { getIndexStatus } from '@/api/documents';
import type { IndexStatusListResponse } from '@/types/index-status';

/**
 * useIndexStatus Hook
 * 
 * Custom hook for fetching document index status with React Query.
 * 
 * Features:
 * - Fetch index status for all documents
 * - Automatic polling every 10 seconds
 * - Loading and error states
 * - Manual refetch capability
 * 
 * Usage:
 * ```tsx
 * const { data, isLoading, error, refetch } = useIndexStatus();
 * 
 * if (data) {
 *   const status = data.find(s => s.file_path === documentPath);
 * }
 * ```
 */
export function useIndexStatus() {
  const {
    data,
    isLoading,
    error,
    refetch,
  } = useQuery<IndexStatusListResponse>({
    queryKey: ['documents', 'index-status'],
    queryFn: getIndexStatus,
    staleTime: 5 * 1000, // 5 seconds - status changes frequently
    refetchInterval: 10 * 1000, // Poll every 10 seconds
    refetchOnWindowFocus: true, // Refetch when user returns to tab
  });

  return {
    indexStatuses: data || [],
    isLoading,
    error,
    refetch,
  };
}

