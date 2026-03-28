import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import axios from 'axios';
import HotspotDashboard from './HotspotDashboard';

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

describe('HotspotDashboard', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  const renderComponent = () => {
    const freshClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    return render(
      <QueryClientProvider client={freshClient}>
        <MemoryRouter>
          <HotspotDashboard />
        </MemoryRouter>
      </QueryClientProvider>
    );
  };

  it('renders No Project Selected when missing project param', () => {
    mockSearchParams = new URLSearchParams('');
    renderComponent();
    expect(screen.getByText(/No Project Selected/i)).toBeInTheDocument();
  });

  it('fetches and renders hotspots when project param is present', async () => {
    mockSearchParams = new URLSearchParams('?project=fastapi-0.100.0');
    const mockData = [
      {
        composite_risk: 1500, // triggers > 1000 branch
        metrics: { complexity: 20, blast_radius: 50, betweenness_centrality: 0.5 }, // triggers > 10 branch
        method: { id: 1, name: 'process_request', file_path: 'app/main.py', start_line: 10 }
      },
      {
        composite_risk: 500, // triggers < 1000 branch (Math.round)
        metrics: { complexity: 5, blast_radius: null, betweenness_centrality: null }, // triggers falsy fallbacks
        method: { id: 2, name: 'helper_func', file_path: 'app/utils.py', start_line: 5 }
      }
    ];

    vi.mocked(axios.get).mockResolvedValueOnce({ data: mockData });

    renderComponent();
    
    expect(screen.getByText(/Computing topological centrality/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('process_request')).toBeInTheDocument();
      expect(screen.getByText('helper_func')).toBeInTheDocument();
    });

    // Check formatting branches
    expect(screen.getByText('1.5k')).toBeInTheDocument(); // high composite
    expect(screen.getByText('500')).toBeInTheDocument(); // low composite

    expect(screen.getByText('20')).toBeInTheDocument(); // high complexity
    expect(screen.getByText('5')).toBeInTheDocument(); // low complexity
  });

  it('handles error state gracefully', async () => {
    mockSearchParams = new URLSearchParams('?project=error-project');
    vi.mocked(axios.get).mockRejectedValueOnce(new Error('Network Error'));

    renderComponent();
    
    await waitFor(() => {
      expect(screen.getByText(/Failed to compute hotspot limits/i)).toBeInTheDocument();
    });
  });
});
