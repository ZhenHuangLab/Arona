/**
 * Knowledge graph type definitions
 */

import type { GraphNode as APIGraphNode, GraphEdge as APIGraphEdge } from './api';

// Re-export API types
export type { APIGraphNode as GraphNode, APIGraphEdge as GraphEdge };

export interface GraphStats {
  total_nodes: number;
  total_edges: number;
  avg_degree?: number;
  [key: string]: unknown;
}

export interface GraphVisualizationConfig {
  width: number;
  height: number;
  nodeRadius: number;
  linkDistance: number;
  chargeStrength: number;
}
