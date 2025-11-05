import { useMemo, useRef, useCallback, useState, useEffect } from 'react';
import { Network } from 'lucide-react';
import ForceGraph2D from 'react-force-graph-2d';
import { Card } from '@/components/ui/card';
import { EmptyState } from '../common/EmptyState';
import type { GraphNode, GraphEdge } from '@/types/graph';

interface GraphCanvasProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  width?: number;
  height?: number;
  /** Selected node ID for highlighting */
  selectedNodeId?: string | null;
  /** Callback when a node is clicked */
  onNodeSelect?: (nodeId: string | null) => void;
}

interface TooltipData {
  type: 'node' | 'link';
  x: number;
  y: number;
  content: {
    label: string;
    nodeType?: string;
    description?: string;
    metadata?: Record<string, unknown>;
    source?: string;
    target?: string;
    weight?: number;
  };
}

/**
 * GraphCanvas Component
 *
 * Interactive knowledge graph visualization using react-force-graph-2d.
 * Supports zoom, pan, node dragging, and tooltips.
 */
export function GraphCanvas({
  nodes,
  edges,
  width = 800,
  height = 600,
  selectedNodeId = null,
  onNodeSelect,
}: GraphCanvasProps) {
  // Ref to prevent unnecessary re-renders that cause graph to disappear
  const fgRef = useRef<any>(null);

  // Tooltip state
  const [tooltip, setTooltip] = useState<TooltipData | null>(null);

  // Track global mouse position for tooltips (using ref to avoid recreating callbacks)
  const mousePosRef = useRef({ x: 0, y: 0 });

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      mousePosRef.current = { x: e.clientX, y: e.clientY };
    };
    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  /**
   * Compute node degrees (number of connections) for identifying super nodes
   * Super nodes with many connections should always show labels
   */
  const nodeDegrees = useMemo(() => {
    const degrees = new Map<string, number>();

    // Initialize all nodes with degree 0
    nodes.forEach(node => degrees.set(node.id, 0));

    // Count connections for each node
    edges.forEach((edge) => {
      const sourceId = typeof edge.source === 'object' ? edge.source.id : edge.source;
      const targetId = typeof edge.target === 'object' ? edge.target.id : edge.target;

      degrees.set(sourceId, (degrees.get(sourceId) || 0) + 1);
      degrees.set(targetId, (degrees.get(targetId) || 0) + 1);
    });

    return degrees;
  }, [nodes, edges]);

  /**
   * Compute highlighted nodes and links based on selection
   * When a node is selected, highlight it and all connected nodes
   *
   * Note: ForceGraph2D mutates edge.source and edge.target from strings to objects
   * We need to handle both cases for robustness
   */
  const { highlightNodes, highlightLinks } = useMemo(() => {
    const hNodes = new Set<string>();
    const hLinks = new Set<string>();

    if (selectedNodeId) {
      // Add selected node
      hNodes.add(selectedNodeId);

      // Find all connected nodes and links
      // Handle both string and object cases for source/target
      edges.forEach((edge) => {
        const sourceId = typeof edge.source === 'object' ? edge.source.id : edge.source;
        const targetId = typeof edge.target === 'object' ? edge.target.id : edge.target;

        if (sourceId === selectedNodeId) {
          hNodes.add(targetId);
          hLinks.add(`${sourceId}-${targetId}`);
        }
        if (targetId === selectedNodeId) {
          hNodes.add(sourceId);
          hLinks.add(`${sourceId}-${targetId}`);
        }
      });
    }

    return { highlightNodes: hNodes, highlightLinks: hLinks };
  }, [selectedNodeId, edges]);

  /**
   * Store selection state in refs to prevent paintNode from recreating
   * This is CRITICAL: If paintNode function reference changes, ForceGraph2D
   * re-initializes and loses zoom/pan state, breaking interaction
   */
  const selectedNodeIdRef = useRef(selectedNodeId);
  const highlightNodesRef = useRef(highlightNodes);
  const highlightLinksRef = useRef(highlightLinks);
  const nodeDegreesRef = useRef(nodeDegrees);

  useEffect(() => {
    selectedNodeIdRef.current = selectedNodeId;
    highlightNodesRef.current = highlightNodes;
    highlightLinksRef.current = highlightLinks;
    nodeDegreesRef.current = nodeDegrees;
  }, [selectedNodeId, highlightNodes, highlightLinks, nodeDegrees]);

  /**
   * Transform GraphNode[] and GraphEdge[] to ForceGraph2D format
   *
   * ForceGraph2D expects:
   * - graphData: { nodes: [], links: [] }
   * - nodes: must have 'id' field (we have this)
   * - links: must have 'source' and 'target' fields (we have this)
   *
   * We add:
   * - name: mapped from label (for default tooltip)
   * - val: constant value for node size
   * - Keep all existing properties for custom tooltips
   */
  const graphData = useMemo(() => {
    return {
      nodes: nodes.map(node => ({
        ...node,
        name: node.label, // Map label to name for default tooltip
        val: 1, // Constant node size (can be customized later)
      })),
      links: edges, // Rename edges to links (ForceGraph2D expects 'links')
    };
  }, [nodes, edges]);

  /**
   * Node drag handlers to prevent graph disappearing
   * Use useCallback to maintain stable function references
   */
  const handleNodeDrag = useCallback((node: any) => {
    // Fix node position during drag
    node.fx = node.x;
    node.fy = node.y;
  }, []);

  const handleNodeDragEnd = useCallback((node: any) => {
    // Release node position after drag (allow force simulation to continue)
    node.fx = null;
    node.fy = null;
  }, []);

  /**
   * Node hover handler for rich tooltips
   * Shows node metadata including type, description, and custom metadata
   *
   * Note: react-force-graph-2d callback signature is (node, previousNode), not (node, event)
   * We use global mouse tracking (mousePosRef) for tooltip positioning
   */
  const handleNodeHover = useCallback((node: any | null, _previousNode: any) => {
    if (node) {
      setTooltip({
        type: 'node',
        x: mousePosRef.current.x,
        y: mousePosRef.current.y,
        content: {
          label: node.label || node.id,
          nodeType: node.type,
          description: node.description,
          metadata: node.metadata,
        },
      });
    } else {
      setTooltip(null);
    }
  }, []);

  /**
   * Link hover handler for edge tooltips
   * Shows relationship information including source, target, and weight
   *
   * Note: react-force-graph-2d callback signature is (link, previousLink), not (link, event)
   * We use global mouse tracking (mousePosRef) for tooltip positioning
   */
  const handleLinkHover = useCallback((link: any | null, _previousLink: any) => {
    if (link) {
      setTooltip({
        type: 'link',
        x: mousePosRef.current.x,
        y: mousePosRef.current.y,
        content: {
          label: link.label || 'related_to',
          source: typeof link.source === 'object' ? link.source.label : link.source,
          target: typeof link.target === 'object' ? link.target.label : link.target,
          weight: link.weight,
        },
      });
    } else {
      setTooltip(null);
    }
  }, []);

  /**
   * Node click handler for selection
   * Toggle selection: click selected node to deselect, click another to select it
   */
  const handleNodeClick = useCallback((node: any) => {
    if (onNodeSelect) {
      // Toggle: if clicking the same node, deselect; otherwise select the new node
      onNodeSelect(selectedNodeId === node.id ? null : node.id);
    }
  }, [selectedNodeId, onNodeSelect]);

  /**
   * Custom node rendering to highlight selected and connected nodes
   *
   * CRITICAL: This function has ZERO dependencies to prevent ForceGraph2D from
   * re-initializing on every state change. We use refs to access current state.
   *
   * Performance note: This function is called for every node on every frame.
   * Label rendering strategy:
   * 1. Always show labels for high-degree nodes (super nodes with many connections)
   * 2. Always show labels for selected/highlighted nodes
   * 3. Show all labels when zoomed in (globalScale > 1.2)
   */
  const paintNode = useCallback((node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
    // Guard: Skip rendering if node position is not yet initialized
    if (node.x === undefined || node.y === undefined) return;

    // Access current state via refs (prevents function recreation)
    const currentSelectedId = selectedNodeIdRef.current;
    const currentHighlightNodes = highlightNodesRef.current;
    const currentNodeDegrees = nodeDegreesRef.current;

    const isSelected = node.id === currentSelectedId;
    const isHighlighted = currentHighlightNodes.has(node.id);
    const isConnected = isHighlighted && !isSelected;

    // Determine node appearance based on selection state
    const nodeRadius = isSelected ? 8 : isConnected ? 6 : 5;
    const nodeOpacity = currentSelectedId && !isHighlighted ? 0.3 : 1.0;

    // Draw node circle
    ctx.beginPath();
    ctx.arc(node.x, node.y, nodeRadius, 0, 2 * Math.PI);
    ctx.fillStyle = isSelected
      ? '#8b5cf6' // Purple for selected
      : isConnected
      ? '#a78bfa' // Light purple for connected
      : node.color || '#6366f1'; // Default or auto-color
    ctx.globalAlpha = nodeOpacity;
    ctx.fill();
    ctx.globalAlpha = 1.0; // Reset alpha

    // Draw selection ring for selected node
    if (isSelected) {
      ctx.beginPath();
      ctx.arc(node.x, node.y, nodeRadius + 2, 0, 2 * Math.PI);
      ctx.strokeStyle = '#8b5cf6';
      ctx.lineWidth = 2;
      ctx.stroke();
    }

    // Determine if label should be shown
    const nodeDegree = currentNodeDegrees.get(node.id) || 0;
    const isHighDegreeNode = nodeDegree >= 5; // Super nodes with 5+ connections
    const shouldShowLabel =
      globalScale > 1.2 ||        // Zoomed in - show all labels
      isSelected ||               // Selected node - always show
      isHighlighted ||            // Highlighted node - always show
      isHighDegreeNode;           // Super node - always show

    // Draw label
    if (shouldShowLabel) {
      const label = node.label || node.id;
      // Larger font for selected nodes and super nodes
      const fontSize = (isSelected || isHighDegreeNode) ? 12 / globalScale : 10 / globalScale;
      ctx.font = `${isHighDegreeNode ? 'bold ' : ''}${fontSize}px sans-serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillStyle = isHighDegreeNode ? '#7c3aed' : '#1e293b'; // Purple for super nodes
      ctx.globalAlpha = nodeOpacity;

      // Truncate label based on zoom level and node importance
      const maxLength = globalScale > 1.5 ? 30 : (isSelected || isHighDegreeNode) ? 20 : 15;
      const displayLabel = label.length > maxLength ? label.slice(0, maxLength) + '...' : label;

      ctx.fillText(
        displayLabel,
        node.x,
        node.y - nodeRadius - 8
      );
      ctx.globalAlpha = 1.0; // Reset alpha
    }
  }, []); // ✅ ZERO dependencies - function reference never changes!

  /**
   * Custom link color based on selection
   * Uses refs to prevent function recreation
   */
  const getLinkColor = useCallback((link: any) => {
    const linkId = `${typeof link.source === 'object' ? link.source.id : link.source}-${typeof link.target === 'object' ? link.target.id : link.target}`;
    const currentSelectedId = selectedNodeIdRef.current;
    const currentHighlightLinks = highlightLinksRef.current;
    const isHighlighted = currentHighlightLinks.has(linkId);

    if (currentSelectedId && !isHighlighted) {
      return 'rgba(148, 163, 184, 0.2)'; // Dim non-highlighted links
    }
    return isHighlighted ? '#8b5cf6' : '#94a3b8'; // Purple for highlighted, gray for normal
  }, []); // ✅ ZERO dependencies

  // Show empty state when no nodes
  if (nodes.length === 0) {
    return (
      <Card className="p-8">
        <EmptyState
          icon={Network}
          title="No graph data"
          description="Upload and process documents to see the knowledge graph"
        />
      </Card>
    );
  }

  return (
    <Card className="p-4">
      <div className="flex items-center gap-2 mb-4">
        <Network className="h-5 w-5 text-muted-foreground" />
        <h3 className="text-sm font-semibold">
          Knowledge Graph ({nodes.length} nodes, {edges.length} edges)
        </h3>
      </div>
      <div className="border rounded-lg bg-background overflow-hidden relative">
        <ForceGraph2D
          ref={fgRef}
          graphData={graphData as any}
          width={width}
          height={height}
          nodeLabel={() => ''} // Disable default tooltip (we use custom)
          nodeAutoColorBy="type"
          nodeCanvasObject={paintNode}
          nodeCanvasObjectMode="replace" // Use constant string instead of arrow function
          linkLabel={() => ''} // Disable default tooltip (we use custom)
          linkColor={getLinkColor}
          linkWidth={useCallback((link: any) => {
            const linkId = `${typeof link.source === 'object' ? link.source.id : link.source}-${typeof link.target === 'object' ? link.target.id : link.target}`;
            return highlightLinksRef.current.has(linkId) ? 2.5 : 1.5;
          }, [])} // ✅ Use ref to prevent recreation
          linkDirectionalArrowLength={4}
          linkDirectionalArrowRelPos={0.8}
          linkDirectionalArrowColor={getLinkColor}
          enableZoomInteraction={true}
          enablePanInteraction={true}
          enableNodeDrag={true}
          onNodeDrag={handleNodeDrag}
          onNodeDragEnd={handleNodeDragEnd}
          onNodeHover={handleNodeHover}
          onLinkHover={handleLinkHover}
          onNodeClick={handleNodeClick}
          backgroundColor="#ffffff"
          // Performance optimizations for large graphs
          warmupTicks={100} // Pre-compute layout before rendering (improves initial performance)
          cooldownTicks={200} // Stop simulation after 200 frames to save CPU
          cooldownTime={15000} // Or stop after 15 seconds
          d3AlphaDecay={0.0228} // Default value (controls simulation decay rate)
          d3VelocityDecay={0.4} // Default value (controls node movement damping)
        />

        {/* Custom Tooltip */}
        {tooltip && (
          <div
            className="fixed z-50 pointer-events-none"
            style={{
              left: `${tooltip.x + 10}px`,
              top: `${tooltip.y + 10}px`,
            }}
          >
            <div className="bg-popover text-popover-foreground border rounded-lg shadow-lg p-3 max-w-xs">
              {tooltip.type === 'node' ? (
                // Node tooltip
                <div className="space-y-1">
                  <p className="font-semibold text-sm">{tooltip.content.label}</p>
                  {tooltip.content.nodeType && (
                    <p className="text-xs text-muted-foreground">
                      Type: <span className="font-medium">{tooltip.content.nodeType}</span>
                    </p>
                  )}
                  {tooltip.content.description && (
                    <p className="text-xs text-muted-foreground mt-1">
                      {tooltip.content.description}
                    </p>
                  )}
                  {tooltip.content.metadata && Object.keys(tooltip.content.metadata).length > 0 && (
                    <p className="text-xs text-muted-foreground mt-1">
                      {Object.keys(tooltip.content.metadata).length} metadata field(s)
                    </p>
                  )}
                </div>
              ) : (
                // Link tooltip
                <div className="space-y-1">
                  <p className="font-semibold text-sm">{tooltip.content.label}</p>
                  <p className="text-xs text-muted-foreground">
                    {tooltip.content.source} → {tooltip.content.target}
                  </p>
                  {tooltip.content.weight !== undefined && (
                    <p className="text-xs text-muted-foreground">
                      Weight: {tooltip.content.weight.toFixed(2)}
                    </p>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
      <p className="text-xs text-muted-foreground mt-2">
        Interactive graph: zoom (scroll), pan (drag), move nodes (drag nodes), hover for details, click to select
      </p>
      {selectedNodeId && (
        <p className="text-xs text-purple-600 mt-1">
          Selected: {nodes.find(n => n.id === selectedNodeId)?.label || selectedNodeId}
          {' '}(click again to deselect)
        </p>
      )}
    </Card>
  );
}

