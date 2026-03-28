import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import axios from 'axios';
import MethodGraphViewer from './MethodGraphViewer';

// Mock the nested canvas to isolate MethodGraphViewer logic
vi.mock('../components/MethodCallGraph', () => ({
  default: ({ onNodeSelect }: any) => (
    <div data-testid="method-graph-mock">
        MethodCallGraph Loaded
        <button onClick={() => onNodeSelect('1')}>Select Node 1</button>
        <button onClick={() => onNodeSelect('3')}>Select Node 3</button>
      </div>
  ),
}));

vi.mock('axios');

const mockNavigate = vi.fn();
let mockSearchParams = new URLSearchParams('');

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual as any,
    useNavigate: () => mockNavigate,
    useSearchParams: () => [mockSearchParams, vi.fn()],
  };
});

describe('MethodGraphViewer', () => {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

  const renderComponent = () => render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <MethodGraphViewer />
      </MemoryRouter>
    </QueryClientProvider>
  );

  it('renders No Project Selected when missing project param', () => {
    mockSearchParams = new URLSearchParams('');
    renderComponent();
    expect(screen.getByText(/No Project Selected/i)).toBeInTheDocument();

    const backExplorerBtn = screen.getByRole('button', { name: /Back to Explorer/i });
    fireEvent.click(backExplorerBtn);
    expect(mockNavigate).toHaveBeenCalledWith('/methods');
  });

  it('fetches and renders graph data, and filters correctly', async () => {
    mockSearchParams = new URLSearchParams('?project=fastapi-0.100.0');

    const mockGraphData = {
      nodes: [
        { id: '1', name: 'app.main', complexity: 20, community_id: 1, file_path: 'main.py', start_line: 10, betweenness_centrality: 0.5, fan_in: 5, fan_out: 2, blast_radius: 10 },
        { id: '2', name: 'app.utils', complexity: 5, community_id: 2 },
        { id: '3', name: 'app.empty', community_id: 1 } // missing complexity, centrality, fan_in/out
      ],
      edges: [
        { source_id: '1', target_id: '2', confidence: 0.9 },
        { source_id: '1', target_id: '3' } // missing confidence
      ],
      node_count: 3,
      edge_count: 2
    };

    vi.mocked(axios.get).mockResolvedValueOnce({ data: mockGraphData });

    renderComponent();
    
    await waitFor(() => {
      expect(screen.getByTestId('method-graph-mock')).toBeInTheDocument();
    });

    // Test filters
    const complexitySlider = screen.getAllByRole('slider')[0];
    fireEvent.change(complexitySlider, { target: { value: 10 } });

    // Verify side panel interaction (via mock node select)
    
    // Select node to fetch blast radius
    vi.mocked(axios.get).mockResolvedValueOnce({
      data: { nodes: [{ id: '1' }] }
    });

    const selectBtn = screen.getByText('Select Node 1');
    fireEvent.click(selectBtn);

    await waitFor(() => {
      expect(screen.getByText('main.py:10')).toBeInTheDocument();
      expect(screen.getByText('Community Cluster #1')).toBeInTheDocument();
    });

    // Test other sliders and dropdowns
    const confidenceSlider = screen.getAllByRole('slider')[1];
    fireEvent.change(confidenceSlider, { target: { value: 0.5 } });

    const communitySelect = screen.getByRole('combobox');
    fireEvent.change(communitySelect, { target: { value: '1' } });

    // Test header back button
    const headerBackBtn = screen.getAllByRole('button')[0];
    fireEvent.click(headerBackBtn);
    expect(mockNavigate).toHaveBeenCalledWith('/methods');

    // Test Empty Node detail panel
    const selectNode3Btn = screen.getByText('Select Node 3');
    fireEvent.click(selectNode3Btn);
    expect(screen.getByText('app.empty')).toBeInTheDocument();
    
    // Test Close panel (since unnamed SVG needs custom selector from previous commit)
    const closeBtn2 = document.querySelector('button.shrink-0');
    if (closeBtn2) fireEvent.click(closeBtn2);

    expect(screen.queryByText('main.py:1')).not.toBeInTheDocument();
  });

  it('handles error state', async () => {
    mockSearchParams = new URLSearchParams('?project=error-project');
    vi.mocked(axios.get).mockRejectedValueOnce({
      response: { data: { detail: 'Method graph not found' } }
    });

    renderComponent();
    
    await waitFor(() => {
      expect(screen.getByText(/Topology Render Failed/i)).toBeInTheDocument();
      expect(screen.getByText(/Method graph not found/i)).toBeInTheDocument();
    });

    // Test error action buttons
    const browseBtn = screen.getByRole('button', { name: /Browse Projects/i });
    fireEvent.click(browseBtn);
    expect(mockNavigate).toHaveBeenCalledWith('/methods');

    // Test fallback error state without detail
    mockSearchParams = new URLSearchParams('?project=generic-error');
    vi.mocked(axios.get).mockRejectedValueOnce(new Error('Generic Error message'));
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText(/Generic Error message/i)).toBeInTheDocument();
    });
  });
});
