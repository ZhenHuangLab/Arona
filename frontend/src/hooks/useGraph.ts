import { useCallback, useEffect, useRef } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
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
 * - Auto-retry when stats show data but graph is empty
 */
export function useGraph(limit: number = 100) {
  const queryClient = useQueryClient();
  const retryDelay = (attemptIndex: number) => Math.min(1000 * 2 ** attemptIndex, 15_000);

  const toNumber = (value: unknown): number | undefined => {
    if (typeof value === 'number' && Number.isFinite(value)) return value;
    if (typeof value === 'string' && value.trim()) {
      const parsed = Number(value);
      if (Number.isFinite(parsed)) return parsed;
    }
    return undefined;
  };

  // Query: Graph stats (used for total counts and slider max)
  const {
    data: statsData,
    isLoading: isLoadingStats,
    isFetching: isFetchingStats,
    refetch: refetchStats,
  } = useQuery({
    queryKey: ['graph', 'stats'],
    queryFn: getGraphStats,
    staleTime: 60 * 1000, // 1 minute
    refetchOnMount: 'always',
    retry: 10,
    retryDelay,
  });

  // Query: Graph data
  const {
    data: graphData,
    isLoading: isLoadingGraph,
    isFetching: isFetchingGraph,
    error: graphError,
    refetch: refetchGraph,
  } = useQuery<GraphDataResponse>({
    queryKey: ['graph', 'data', limit],
    queryFn: () => getGraphData(limit, false),
    staleTime: 60 * 1000, // 1 minute
    refetchOnMount: 'always',
    retry: 10,
    retryDelay,
  });

  // Total stats from /graph/stats endpoint (for slider max and total display)
  const fallbackNodeCount =
    toNumber(graphData?.stats?.total_nodes) ??
    graphData?.nodes?.length ??
    0;
  const fallbackEdgeCount =
    toNumber(graphData?.stats?.total_edges) ??
    graphData?.edges?.length ??
    0;

  const totalEntities = toNumber(statsData?.total_entities);
  const totalRelations = toNumber(statsData?.total_relations);

  const totalStats = {
    node_count:
      totalEntities === undefined
        ? fallbackNodeCount
        : (totalEntities === 0 && fallbackNodeCount > 0 ? fallbackNodeCount : totalEntities),
    edge_count:
      totalRelations === undefined
        ? fallbackEdgeCount
        : (totalRelations === 0 && fallbackEdgeCount > 0 ? fallbackEdgeCount : totalRelations),
    initialized: statsData?.initialized === true,
  };

  // Loaded stats: actual loaded data counts (for badges showing current rendered count)
  const loadedStats = {
    node_count: graphData?.nodes?.length ?? 0,
    edge_count: graphData?.edges?.length ?? 0,
  };

  // Refetch both stats and graph data
  const refetch = useCallback(async () => {
    // Invalidate and refetch both queries
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['graph', 'stats'] }),
      queryClient.invalidateQueries({ queryKey: ['graph', 'data', limit] }),
    ]);
    await Promise.all([refetchStats(), refetchGraph()]);
  }, [queryClient, limit, refetchStats, refetchGraph]);

  // Auto-retry: when stats show initialized=true and total_entities>0 but graphData.nodes is empty
  const autoRetryRef = useRef(false);
  const autoRetryCountRef = useRef(0);
  const maxAutoRetries = 5;

  useEffect(() => {
    const shouldAutoRetry =
      totalStats.initialized &&
      totalStats.node_count > 0 &&
      !isLoadingGraph &&
      !graphError &&
      loadedStats.node_count === 0 &&
      autoRetryCountRef.current < maxAutoRetries;

    if (shouldAutoRetry && !autoRetryRef.current) {
      autoRetryRef.current = true;
      autoRetryCountRef.current += 1;
      const timer = setTimeout(() => {
        refetchGraph();
        autoRetryRef.current = false;
      }, 1500); // Wait 1.5s before retry

      return () => clearTimeout(timer);
    }

    // Reset retry count when we successfully get data
    if (loadedStats.node_count > 0) {
      autoRetryCountRef.current = 0;
    }
  }, [totalStats.initialized, totalStats.node_count, isLoadingGraph, graphError, loadedStats.node_count, refetchGraph]);

  // Auto-refresh stats once if we have graph data but totals look stale/empty.
  // This fixes cases where /graph/stats was cached as 0 and doesn't refetch until manual refresh.
  const didAutoRefreshStatsRef = useRef(false);
  useEffect(() => {
    if (didAutoRefreshStatsRef.current) return;
    if (isLoadingStats) return;
    if (loadedStats.node_count <= 0) return;

    // If stats are missing, uninitialized, or show 0 while data exists, refresh once.
    const statsLooksEmpty =
      statsData?.initialized !== true ||
      (toNumber(statsData?.total_entities) ?? 0) === 0;

    if (statsLooksEmpty) {
      didAutoRefreshStatsRef.current = true;
      refetchStats();
    }
  }, [isLoadingStats, loadedStats.node_count, statsData, refetchStats]);

  return {
    graphData,
    /** Total stats from backend (for slider max, overall totals) */
    totalStats,
    /** Loaded/rendered stats (for badges showing current displayed count) */
    loadedStats,
    /** Combined stats for backward compatibility - prefer totalStats or loadedStats */
    stats: totalStats,
    isLoadingGraph,
    isLoadingStats,
    isFetchingGraph,
    isFetchingStats,
    isLoading: isLoadingGraph || isLoadingStats,
    error: graphError,
    /** Refetch both stats and graph data */
    refetch,
    /** Refetch only graph data */
    refetchGraph,
    /** Refetch only stats */
    refetchStats,
  };
}
