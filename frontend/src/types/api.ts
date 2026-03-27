/**
 * Shared API Response specifications matching backend Pydantic models exactly.
 */

export interface DependencyItem {
  name: string;
  constraint: string;
}

export interface DirectDependenciesResponse {
  package: string;
  version: string;
  ecosystem: string;
  dependencies: DependencyItem[];
}

export interface GraphNode {
  id: string;
  label: string;
  ecosystem: string;
  package: string;
  version: string;
}

export interface GraphEdge {
  source: string;
  target: string;
  constraint: string | null;
}

export interface TransitiveGraphResponse {
  root: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface PackageMetrics {
  directDependencies: number;
  transitiveDependencies: number;
  fanIn: number;
  fanOut: number;
  bottleneckScore: number;
  diamondCount: number;
  pageRank: number;
  closenessCentrality: number;
}

export interface PackageDetailsResponse {
  id: string;
  ecosystem: string;
  name: string;
  version: string;
  metrics: PackageMetrics;
}

// Analytics -----------------------------------------------------------------

export interface TopRiskItem {
  id: string;
  ecosystem: string;
  name: string;
  version: string;
  fanIn: number;
  fanOut: number;
  versionFanOut: number;
  bottleneckScore: number;
  bottleneckPercentile: number;
  pageRank: number;
  closenessCentrality: number;
}

export interface TopRiskResponse {
  items: TopRiskItem[];
  totalPackages: number;
}

export interface CoverageResponse {
  ecosystem: string;
  ingestedPackages: number;
  estimatedTotal: number;
  coveragePct: number;
}

// Snapshots -----------------------------------------------------------------

export interface Snapshot {
  snapshot_id: string;
  created_at: string;
  ecosystem: string;
  description: string | null;
}

export interface SnapshotComparisonResponse {
  snapshot_1_id: string;
  snapshot_2_id: string;
  ecosystem: string;
  added_edges: number;
  removed_edges: number;
}

