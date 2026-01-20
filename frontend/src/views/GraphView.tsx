import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Network, RefreshCw, Sliders } from 'lucide-react';
import { GraphCanvas, GraphControls } from '@/components/documents';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { useGraph } from '@/hooks/useGraph';
import { LoadingSpinner } from '@/components/common';
import { useTheme } from '@/components/theme';

/**
 * Graph View
 *
 * Knowledge graph visualization interface.
 *
 * Features:
 * - Interactive graph visualization
 * - Graph statistics display
 * - Refresh functionality
 * - Loading states
 * - User-adjustable node limit (defaults to midpoint of range)
 */
export const GraphView: React.FC = () => {
  // State for user-adjustable node limit - start with null to indicate "not yet initialized"
  const [nodeLimit, setNodeLimit] = useState<number | null>(null);
  const userHasAdjustedRef = useRef(false);
  const [controlsOpen, setControlsOpen] = useState(false);

  // State for graph controls
  const [layout, setLayout] = useState<'normal' | 'tight' | 'loose'>('normal');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedNodeTypes, setSelectedNodeTypes] = useState<string[]>([]);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  // Use actual nodeLimit or a temporary default for the query
  const effectiveNodeLimit = nodeLimit ?? 100;
  const {
    graphData,
    totalStats,
    isLoading,
    isFetchingGraph,
    isFetchingStats,
    error,
    refetch,
  } = useGraph(effectiveNodeLimit);
  const { actualTheme } = useTheme();

  // Responsive sizing for the graph canvas
  const graphContainerRef = useRef<HTMLDivElement | null>(null);
  const [graphSize, setGraphSize] = useState<{ width: number; height: number }>({
    width: 800,
    height: 600,
  });

  /**
   * Extract unique node types from graph data
   */
  const nodeTypes = useMemo(() => {
    if (!graphData?.nodes) return [];
    const types = new Set<string>();
    graphData.nodes.forEach(node => {
      if (node.type) types.add(node.type);
    });
    return Array.from(types).sort();
  }, [graphData]);

  // Calculate slider bounds based on totalStats (only trust totals when initialized=true)
  const totalNodes = totalStats.initialized ? totalStats.node_count : 0;

  const { nodeLimitMin, nodeLimitMax, nodeLimitStep } = useMemo(() => {
    const max = totalNodes > 0 ? Math.min(totalNodes, 5000) : 500;
    const min = totalNodes > 0 ? Math.min(10, max) : 10;
    const step = max <= 200 ? 1 : max <= 1000 ? 10 : 50;
    return { nodeLimitMin: min, nodeLimitMax: max, nodeLimitStep: step };
  }, [totalNodes]);

  // Mark when user manually adjusts
  const handleNodeLimitChange = useCallback((limit: number) => {
    userHasAdjustedRef.current = true;
    setNodeLimit(limit);
  }, []);

  // Initialize nodeLimit to midpoint when totalStats becomes available (only once, if user hasn't adjusted)
  useEffect(() => {
    // Skip if user has manually adjusted
    if (userHasAdjustedRef.current) return;
    // Skip if no valid total yet
    if (totalNodes <= 0) return;
    // Skip if already initialized
    if (nodeLimit !== null) return;

    // Calculate midpoint
    const midpoint = Math.round((nodeLimitMin + nodeLimitMax) / 2);
    setNodeLimit(midpoint);
  }, [totalNodes, nodeLimitMin, nodeLimitMax, nodeLimit]);

  // Keep nodeLimit within the dynamic slider range (when range changes)
  useEffect(() => {
    if (nodeLimit === null) return;
    if (nodeLimit < nodeLimitMin) setNodeLimit(nodeLimitMin);
    else if (nodeLimit > nodeLimitMax) setNodeLimit(nodeLimitMax);
  }, [nodeLimit, nodeLimitMin, nodeLimitMax]);

  /**
   * Initialize selected types when node types change
   */
  useEffect(() => {
    if (nodeTypes.length > 0 && selectedNodeTypes.length === 0) {
      setSelectedNodeTypes(nodeTypes);
    }
  }, [nodeTypes, selectedNodeTypes.length]);

  useEffect(() => {
    const el = graphContainerRef.current;
    if (!el) return;

    const ro = new ResizeObserver((entries) => {
      const rect = entries[0]?.contentRect;
      if (!rect) return;
      const nextWidth = Math.max(320, Math.floor(rect.width));
      const nextHeight = Math.max(360, Math.floor(rect.height));
      setGraphSize((prev) =>
        prev.width === nextWidth && prev.height === nextHeight
          ? prev
          : { width: nextWidth, height: nextHeight }
      );
    });

    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  /**
   * Filter graph data based on search query and selected node types
   */
  const filteredGraphData = useMemo(() => {
    if (!graphData) return null;

    // Filter nodes
    let filteredNodes = graphData.nodes;

    // Filter by node type
    if (selectedNodeTypes.length > 0 && selectedNodeTypes.length < nodeTypes.length) {
      filteredNodes = filteredNodes.filter(node =>
        node.type && selectedNodeTypes.includes(node.type)
      );
    }

    // Filter by search query
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filteredNodes = filteredNodes.filter(node =>
        node.label.toLowerCase().includes(query) ||
        node.id.toLowerCase().includes(query)
      );
    }

    // Filter edges to only include those between visible nodes
    // Note: ForceGraph2D mutates edge.source and edge.target from strings to objects
    // We need to handle both cases: initial (string) and post-processing (object)
    const visibleNodeIds = new Set(filteredNodes.map(n => n.id));
    const filteredEdges = graphData.edges.filter(edge => {
      const sourceId = typeof edge.source === 'object' ? edge.source.id : edge.source;
      const targetId = typeof edge.target === 'object' ? edge.target.id : edge.target;
      return visibleNodeIds.has(sourceId) && visibleNodeIds.has(targetId);
    });

    return {
      nodes: filteredNodes,
      edges: filteredEdges,
      stats: graphData.stats,
    };
  }, [graphData, selectedNodeTypes, searchQuery, nodeTypes.length]);

  // Counts for display: use filtered data counts
  const displayedNodeCount = filteredGraphData?.nodes?.length ?? 0;
  const displayedEdgeCount = filteredGraphData?.edges?.length ?? 0;
  const hasAnyNodes = (graphData?.nodes?.length ?? 0) > 0;
  const isRefreshing = isFetchingGraph || isFetchingStats;

  return (
    <div className="space-y-4">
      {/* Title row */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2 min-w-0">
          <Network className="h-5 w-5 text-muted-foreground" aria-hidden="true" />
          <h2 className="text-lg font-semibold truncate">Graph</h2>
          {displayedNodeCount > 0 || displayedEdgeCount > 0 ? (
            <div className="hidden sm:flex items-center gap-2">
              <Badge variant="secondary" className="text-xs">
                {String(displayedNodeCount)} nodes
              </Badge>
              <Badge variant="secondary" className="text-xs">
                {String(displayedEdgeCount)} edges
              </Badge>
            </div>
          ) : null}
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setControlsOpen(true)}
            className="gap-2"
            title="Graph controls"
          >
            <Sliders className="h-4 w-4" aria-hidden="true" />
            Controls
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            disabled={isRefreshing}
            className="gap-2"
            title="Refresh graph data"
          >
            <RefreshCw className={`h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`} aria-hidden="true" />
            Refresh
          </Button>
        </div>
      </div>

      {/* Advanced controls dialog (collapsed behind a single button) */}
      <Dialog open={controlsOpen} onOpenChange={setControlsOpen}>
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>Graph controls</DialogTitle>
            <DialogDescription>
              Search, layout, and filters for the knowledge graph.
            </DialogDescription>
          </DialogHeader>
          <GraphControls
            nodeLimit={nodeLimit ?? effectiveNodeLimit}
            nodeLimitMin={nodeLimitMin}
            nodeLimitMax={nodeLimitMax}
            nodeLimitStep={nodeLimitStep}
            totalNodes={totalNodes}
            nodeTypes={nodeTypes}
            selectedTypes={selectedNodeTypes}
            layout={layout}
            searchQuery={searchQuery}
            onTypeFilterChange={setSelectedNodeTypes}
            onLayoutChange={setLayout}
            onSearchChange={setSearchQuery}
            onNodeLimitChange={handleNodeLimitChange}
          />
        </DialogContent>
      </Dialog>

      {/* Graph Visualization */}
      {isLoading ? (
        <Card className="p-12">
          <LoadingSpinner size="lg" text="Loading graph data..." />
        </Card>
      ) : error ? (
        <Card className="p-12">
          <div className="text-center text-muted-foreground space-y-2">
            <Network className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p className="text-lg font-medium">Failed to load graph</p>
            <p className="text-sm">{String((error as Error)?.message || error)}</p>
            <div className="pt-2">
              <Button variant="outline" onClick={() => refetch()} className="gap-2">
                <RefreshCw className="h-4 w-4" aria-hidden="true" />
                Retry
              </Button>
            </div>
          </div>
        </Card>
      ) : filteredGraphData && filteredGraphData.nodes.length > 0 ? (
        <Card className="p-0 overflow-hidden">
          <div
            ref={graphContainerRef}
            className="w-full h-[60vh] min-h-[480px] flex items-center justify-center"
          >
            <GraphCanvas
              nodes={filteredGraphData.nodes}
              edges={filteredGraphData.edges}
              width={graphSize.width}
              height={graphSize.height}
              selectedNodeId={selectedNodeId}
              onNodeSelect={setSelectedNodeId}
              theme={actualTheme}
            />
          </div>
        </Card>
      ) : hasAnyNodes ? (
        <Card className="p-12">
          <div className="text-center text-muted-foreground">
            <Network className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p className="text-lg font-medium">No nodes match your filters</p>
            <p className="text-sm mt-2">Try adjusting your search or type filters</p>
          </div>
        </Card>
      ) : (
        <Card className="p-12">
          <div className="text-center text-muted-foreground">
            <Network className="h-12 w-12 mx-auto mb-4 opacity-50" />
            {totalStats.initialized && totalNodes > 0 ? (
              <>
                <p className="text-lg font-medium">Preparing graph…</p>
                <p className="text-sm mt-2">
                  Found {totalNodes} nodes in stats. Retrying data load automatically…
                </p>
              </>
            ) : (
              <>
                <p className="text-lg font-medium">No graph data yet</p>
                <p className="text-sm mt-2">
                  Upload and process documents to populate the knowledge graph.
                </p>
              </>
            )}
          </div>
        </Card>
      )}
    </div>
  );
};
