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
  });

  // Query: Graph stats
  const {
    data: statsData,
    isLoading: isLoadingStats,
  } = useQuery({
    queryKey: ['graph', 'stats'],
    queryFn: getGraphStats,
    staleTime: 60 * 1000, // 1 minute
  });

  // Extract stats from response and normalize field names
  // Backend returns: total_nodes, total_edges
  // Frontend expects: node_count, edge_count
  const rawStats = graphData?.stats || statsData;
  const stats = {
    node_count: rawStats?.total_nodes ?? graphData?.nodes?.length ?? 0,
    edge_count: rawStats?.total_edges ?? graphData?.edges?.length ?? 0,
  };

  return {
    graphData,
    stats,
    isLoading: isLoadingGraph || isLoadingStats,
    error: graphError,
    refetch: refetchGraph,
  };
}
