import { useQuery } from '@tanstack/react-query';
import { getGraphData, getGraphStats } from '@/api/graph';
import type { GraphDataResponse } from '@/types/api';

/**
 * useGraph Hook
 *
 * Custom hook for knowledge graph operations with React Query.
 *
 * Features:
 * - Fetch graph data for visualization
 * - Fetch graph statistics
 * - Loading states
 * - Error handling
 * - Automatic refetching
 * - User-adjustable node limit
 */
export function useGraph(limit: number = 100) {
  const retryDelay = (attemptIndex: number) => Math.min(1000 * 2 ** attemptIndex, 15_000);

  const toNumber = (value: unknown): number | undefined => {
    if (typeof value === 'number' && Number.isFinite(value)) return value;
    if (typeof value === 'string' && value.trim()) {
      const parsed = Number(value);
      if (Number.isFinite(parsed)) return parsed;
    }
    return undefined;
  };

  // Query: Graph data
  const {
    data: graphData,
    isLoading: isLoadingGraph,
    error: graphError,
    refetch: refetchGraph,
  } = useQuery<GraphDataResponse>({
    queryKey: ['graph', 'data', limit],
    queryFn: () => getGraphData(limit, false),
    staleTime: 60 * 1000, // 1 minute
    retry: 10,
    retryDelay,
  });

  // Query: Graph stats
  const {
    data: statsData,
    isLoading: isLoadingStats,
  } = useQuery({
    queryKey: ['graph', 'stats'],
    queryFn: getGraphStats,
    staleTime: 60 * 1000, // 1 minute
    retry: 10,
    retryDelay,
  });

  // Extract stats from response and normalize field names.
  // Prefer /graph/stats totals (total_entities/total_relations) when available.
  // Fall back to /graph/data stats (total_nodes/total_edges) or array lengths.
  const stats: { node_count: number; edge_count: number } = {
    node_count:
      toNumber(statsData?.total_entities) ??
      toNumber(graphData?.stats?.total_nodes) ??
      graphData?.nodes?.length ??
      0,
    edge_count:
      toNumber(statsData?.total_relations) ??
      toNumber(graphData?.stats?.total_edges) ??
      graphData?.edges?.length ??
      0,
  };

  return {
    graphData,
    stats,
    isLoading: isLoadingGraph || isLoadingStats,
    error: graphError,
    refetch: refetchGraph,
  };
}
