import React, { useState, useMemo } from 'react';
import { Network, RefreshCw, Settings2 } from 'lucide-react';
import { GraphCanvas, GraphControls } from '@/components/documents';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useGraph } from '@/hooks/useGraph';
import { LoadingSpinner } from '@/components/common';

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
 * - User-adjustable node limit
 */
export const GraphView: React.FC = () => {
  // State for user-adjustable node limit
  const [nodeLimit, setNodeLimit] = useState<number>(100);
  const [showSettings, setShowSettings] = useState<boolean>(false);

  // State for graph controls
  const [layout, setLayout] = useState<'normal' | 'tight' | 'loose'>('normal');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedNodeTypes, setSelectedNodeTypes] = useState<string[]>([]);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  const { graphData, stats, isLoading, refetch } = useGraph(nodeLimit);

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

  /**
   * Initialize selected types when node types change
   */
  useMemo(() => {
    if (nodeTypes.length > 0 && selectedNodeTypes.length === 0) {
      setSelectedNodeTypes(nodeTypes);
    }
  }, [nodeTypes, selectedNodeTypes.length]);

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

    // Debug logging (can be removed after verification)
    console.log('[GraphView] Filtering results:', {
      totalNodes: graphData.nodes.length,
      filteredNodes: filteredNodes.length,
      totalEdges: graphData.edges.length,
      filteredEdges: filteredEdges.length,
      sampleEdge: graphData.edges[0],
      edgeSourceType: typeof graphData.edges[0]?.source,
      edgeTargetType: typeof graphData.edges[0]?.target,
    });

    return {
      nodes: filteredNodes,
      edges: filteredEdges,
      stats: graphData.stats,
    };
  }, [graphData, selectedNodeTypes, searchQuery, nodeTypes.length]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <Card className="p-6 bg-gradient-to-r from-purple-50 to-pink-50 border-purple-200">
        <div className="flex items-start justify-between">
          <div className="flex items-start gap-4">
            <div className="p-3 bg-purple-600 rounded-lg">
              <Network className="h-6 w-6 text-white" />
            </div>
            <div className="flex-1">
              <h2 className="text-xl font-bold text-gray-900 mb-2">
                Knowledge Graph
              </h2>
              <p className="text-gray-600 mb-4">
                Visualize relationships between entities extracted from your documents.
              </p>
              {stats && (
                <div className="flex items-center gap-3">
                  <Badge variant="secondary" className="text-sm">
                    {String(stats.node_count || 0)} Nodes
                  </Badge>
                  <Badge variant="secondary" className="text-sm">
                    {String(stats.edge_count || 0)} Edges
                  </Badge>
                </div>
              )}
            </div>
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowSettings(!showSettings)}
            >
              <Settings2 className="h-4 w-4 mr-2" />
              Settings
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => refetch()}
              disabled={isLoading}
            >
              <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
          </div>
        </div>
      </Card>

      {/* Settings Panel */}
      {showSettings && (
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4">Graph Settings</h3>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Node Limit: {nodeLimit}
              </label>
              <input
                type="range"
                min="10"
                max="2000"
                step="10"
                value={nodeLimit}
                onChange={(e) => setNodeLimit(Number(e.target.value))}
                className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
              />
              <div className="flex justify-between text-xs text-gray-500 mt-1">
                <span>10</span>
                <span>2000</span>
              </div>
              {nodeLimit > 500 && (
                <p className="text-xs text-amber-600 mt-2">
                  ⚠️ High node counts may impact performance
                </p>
              )}
            </div>
          </div>
        </Card>
      )}

      {/* Graph Controls */}
      {!isLoading && graphData && graphData.nodes.length > 0 && (
        <GraphControls
          nodeTypes={nodeTypes}
          selectedTypes={selectedNodeTypes}
          layout={layout}
          searchQuery={searchQuery}
          onTypeFilterChange={setSelectedNodeTypes}
          onLayoutChange={setLayout}
          onSearchChange={setSearchQuery}
        />
      )}

      {/* Graph Visualization */}
      {isLoading ? (
        <Card className="p-12">
          <LoadingSpinner size="lg" text="Loading graph data..." />
        </Card>
      ) : filteredGraphData && filteredGraphData.nodes.length > 0 ? (
        <GraphCanvas
          nodes={filteredGraphData.nodes}
          edges={filteredGraphData.edges}
          width={800}
          height={600}
          selectedNodeId={selectedNodeId}
          onNodeSelect={setSelectedNodeId}
        />
      ) : (
        <Card className="p-12">
          <div className="text-center text-muted-foreground">
            <Network className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p className="text-lg font-medium">No nodes match your filters</p>
            <p className="text-sm mt-2">Try adjusting your search or type filters</p>
          </div>
        </Card>
      )}

      {/* Graph Info */}
      {filteredGraphData && filteredGraphData.nodes.length > 0 && (
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-3">Graph Information</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
            <div>
              <p className="text-gray-600">Visible Nodes</p>
              <p className="text-2xl font-bold text-gray-900">
                {filteredGraphData.nodes.length}
              </p>
              {graphData && filteredGraphData.nodes.length < graphData.nodes.length && (
                <p className="text-xs text-muted-foreground mt-1">
                  of {graphData.nodes.length} total
                </p>
              )}
            </div>
            <div>
              <p className="text-gray-600">Visible Edges</p>
              <p className="text-2xl font-bold text-gray-900">
                {filteredGraphData.edges.length}
              </p>
              {graphData && filteredGraphData.edges.length < graphData.edges.length && (
                <p className="text-xs text-muted-foreground mt-1">
                  of {graphData.edges.length} total
                </p>
              )}
            </div>
            <div>
              <p className="text-gray-600">Avg. Connections</p>
              <p className="text-2xl font-bold text-gray-900">
                {filteredGraphData.nodes.length > 0
                  ? (filteredGraphData.edges.length / filteredGraphData.nodes.length).toFixed(1)
                  : '0'}
              </p>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
};
