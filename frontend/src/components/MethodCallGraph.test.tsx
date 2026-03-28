import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import MethodCallGraph from './MethodCallGraph';
import Graph from 'graphology';

let sigmaEvents: Record<string, Function> = {};
let shouldThrowGraphError = false;

// Mock react-sigma core hooks and components
vi.mock('@react-sigma/core', () => ({
  // Ensure children renders so GraphLoader executes
  SigmaContainer: ({ children }: any) => <div data-testid="sigma-container">{children}</div>,
  useLoadGraph: () => (graph: any) => {
    if (shouldThrowGraphError) throw new Error('Simulated Graphology Exception');
  },
  useRegisterEvents: () => (events: any) => {
    Object.assign(sigmaEvents, events);
  },
  useSigma: () => ({
    getCamera: () => ({ animatedReset: vi.fn() })
  }),
}));

describe('MethodCallGraph', () => {
  beforeEach(() => {
    sigmaEvents = {};
    shouldThrowGraphError = false;
    vi.spyOn(window, 'requestAnimationFrame').mockImplementation((cb) => { cb(1); return 1; });
  });

  const mockData = {
    root: '1',
    nodes: [
      { id: '1', name: 'main', blast_radius: 10, community_id: 1 },
      { id: '2', name: 'helper', blast_radius: 2, community_id: null },
      { id: '3', name: 'orphan', blast_radius: 0, community_id: 2 }
    ],
    edges: [
      { source_id: '1', target_id: '2', call_type: 'dynamic' },
      { source_id: '2', target_id: '1', call_type: 'static' }
    ]
  };

  it('processes call graph data, layouts nodes, and binds click handlers', () => {
    const mockOnNodeSelect = vi.fn();
    
    // Pass highlightedNodes to cover color filtering
    const { getByTestId, getByText } = render(
      <MethodCallGraph 
        data={mockData} 
        highlightedNodes={['1']} 
        onNodeSelect={mockOnNodeSelect} 
      />
    );

    expect(getByTestId('sigma-container')).toBeInTheDocument();
    expect(getByText(/Graph Legend/i)).toBeInTheDocument();

    // Trigger the node and stage click events
    sigmaEvents['clickNode']?.({ node: '1' });
    expect(mockOnNodeSelect).toHaveBeenCalledWith('1');

    sigmaEvents['clickStage']?.();
    expect(mockOnNodeSelect).toHaveBeenCalledWith(null);
  });

  it('renders error boundary when GraphLoader constructor throws', () => {
    shouldThrowGraphError = true;
    
    const { getByText } = render(<MethodCallGraph data={mockData} />);
    
    expect(getByText(/Graphology Render Crash/i)).toBeInTheDocument();
    expect(getByText(/Simulated Graphology Exception/i)).toBeInTheDocument();
  });
});
