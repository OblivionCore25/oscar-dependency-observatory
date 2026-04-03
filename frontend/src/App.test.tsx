import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import App from './App';

// Mock Sigma since it relies on WebGL and heavy canvas features
vi.mock('@react-sigma/core', () => ({
  SigmaContainer: ({ children }: any) => <div data-testid="sigma-container">{children}</div>,
  useSigma: () => ({ getGraph: vi.fn(), getBBox: vi.fn(), getCamera: vi.fn() }),
  useRegisterEvents: () => vi.fn(),
  useSetSettings: () => vi.fn(),
}));
vi.mock('graphology', () => {
  return {
    default: class Graph {
      addNode() {}
      addEdge() {}
      nodes() { return [] }
      edges() { return [] }
      clear() {}
      forEachNode() {}
      hasNode() { return false; }
    }
  };
});
vi.mock('@react-sigma/layout-forceatlas2', () => ({
  useWorkerLayoutForceAtlas2: () => ({ start: vi.fn(), stop: vi.fn(), stopAsync: vi.fn(), isRunning: false }),
}));

// Mock API layer
vi.mock('./services/api', () => ({
  getPackageDetails: vi.fn().mockResolvedValue({}),
  getTransitiveGraph: vi.fn().mockResolvedValue({ nodes: [], edges: [] }),
  getTopRisk: vi.fn().mockResolvedValue({ items: [] }),
  getCoverage: vi.fn().mockResolvedValue({ count: 0, coveragePct: 0, ingestedPackages: 100, estimatedTotal: 500000, ecosystem: 'npm' }),
  getProjectAnalysis: vi.fn().mockResolvedValue({ meta: {}, methods: [], calls: [], metrics: [], classes: [], modules: [], imports: [], inheritance: [] }),
  getProjectGraph: vi.fn().mockResolvedValue({ nodes: [], edges: [] }),
}));

const queryClient = new QueryClient();

describe('App Routing Built-in Smoke Test', () => {
  it('navigates through all major routes without crashing', async () => {
    // App contains BrowserRouter internally
    render(
      <QueryClientProvider client={queryClient}>
        <App />
      </QueryClientProvider>
    );

    // Initial route is / (PackageSearch)
    await waitFor(() => {
      // Look for unique text on the home page
      expect(screen.getByText(/Find and explore dependencies for any package/i)).toBeInTheDocument();
    });

    // Navigate to Graph Viewer
    const graphLink = screen.getAllByText(/Graph Viewer/i)[0]; // The link in sidebar
    fireEvent.click(graphLink);
    
    await waitFor(() => {
      expect(screen.getByText(/No Package Selected/i)).toBeInTheDocument();
    });

    // Navigate to Top Risk
    const topRiskLink = screen.getAllByText(/Top Risk/i)[0];
    fireEvent.click(topRiskLink);
    
    await waitFor(() => {
      expect(screen.getByText(/Top Risk Dependencies/i)).toBeInTheDocument();
    });

    // Navigate to Snapshots
    const snapshotsLink = screen.getAllByText(/Snapshots/i)[0];
    fireEvent.click(snapshotsLink);
    
    await waitFor(() => {
      expect(screen.getByText(/Temporal Snapshots/i)).toBeInTheDocument();
    });

    // Navigate to Method Observatory
    const methodLink = screen.getAllByText(/Method Observatory/i)[0];
    fireEvent.click(methodLink);
    
    await waitFor(() => {
      expect(screen.getByText(/Method Explorer/i)).toBeInTheDocument();
    });
  });
});
