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
}

export interface PackageDetailsResponse {
  id: string;
  ecosystem: string;
  name: string;
  version: string;
  metrics: PackageMetrics;
}

export interface TopRiskItem {
  id: string;
  ecosystem: string;
  name: string;
  version: string;
  fanIn: number;
  fanOut: number;
  bottleneckScore: number;
}

export interface TopRiskResponse {
  items: TopRiskItem[];
}
