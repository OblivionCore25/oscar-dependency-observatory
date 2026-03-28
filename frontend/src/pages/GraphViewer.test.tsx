import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import GraphViewer from './GraphViewer';
import * as hooks from '../hooks/useGraphQuery';

// Mock the canvas to avoid WebGL errors in testing
vi.mock('../components/GraphCanvas', () => ({
  default: () => <div data-testid="graph-canvas-mock">GraphCanvas Loaded</div>,
}));

vi.mock('../hooks/useGraphQuery', () => ({
  useGraphQuery: vi.fn(),
}));

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

describe('GraphViewer', () => {
  it('renders empty state when no params are provided', () => {
    mockSearchParams = new URLSearchParams('');
    vi.mocked(hooks.useGraphQuery).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: null,
    } as any);

    render(
      <MemoryRouter>
        <GraphViewer />
      </MemoryRouter>
    );

    expect(screen.getByText(/No Package Selected/i)).toBeInTheDocument();
    
    // Test navigation back to search
    fireEvent.click(screen.getByRole('button', { name: /Go to Search/i }));
    expect(mockNavigate).toHaveBeenCalledWith('/');
  });

  it('renders loading state when fetching graph', () => {
    mockSearchParams = new URLSearchParams('?ecosystem=npm&package=react&version=18.2.0');
    vi.mocked(hooks.useGraphQuery).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    } as any);

    render(
      <MemoryRouter>
        <GraphViewer />
      </MemoryRouter>
    );

    expect(screen.getByText(/Resolving Transitive Graph/i)).toBeInTheDocument();
  });

  it('renders error state when graph fetch fails', () => {
    mockSearchParams = new URLSearchParams('?ecosystem=npm&package=react&version=18.2.0');
    vi.mocked(hooks.useGraphQuery).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error('Graph Error'),
    } as any);

    render(
      <MemoryRouter>
        <GraphViewer />
      </MemoryRouter>
    );

    expect(screen.getByText(/Graph Resolution Failed/i)).toBeInTheDocument();
    expect(screen.getByText(/Graph Error/i)).toBeInTheDocument();

    // Test return to search on error exactly matches navigation
    const returnBtn = screen.getByRole('button', { name: /Return to Search/i });
    fireEvent.click(returnBtn);
    expect(mockNavigate).toHaveBeenCalledWith('/');
  });

  it('renders GraphCanvas and interacts with constraints sidebar', () => {
    mockSearchParams = new URLSearchParams('?ecosystem=npm&package=react&version=18.2.0');
    vi.mocked(hooks.useGraphQuery).mockReturnValue({
      data: {
        nodes: [{ id: '1' }],
        edges: [
          { source: 'A', target: 'B', constraint: '==1.0.0' },
          { source: 'B', target: 'C', constraint: 'unconstrained' },
        ],
      },
      isLoading: false,
      error: null,
    } as any);

    render(
      <MemoryRouter>
        <GraphViewer />
      </MemoryRouter>
    );

    expect(screen.getByTestId('graph-canvas-mock')).toBeInTheDocument();
    
    // Test opening sidebar
    const constraintsBtn = screen.getByRole('button', { name: /Edge Constraints/i });
    fireEvent.click(constraintsBtn);

    expect(screen.getByText(/==1.0.0/i)).toBeInTheDocument();
    expect(screen.getAllByText(/unconstrained/i).length).toBeGreaterThan(0);

    // Test secondary navigation events
    const methodGraphBtn = screen.getByRole('button', { name: /Method Call Graph/i });
    fireEvent.click(methodGraphBtn);
    expect(mockNavigate).toHaveBeenCalledWith('/methods/graph?project=react-18.2.0');

    const backBtn = screen.getByRole('button', { name: /Back to Search/i });
    fireEvent.click(backBtn);
    expect(mockNavigate).toHaveBeenCalledWith('/');

    // Test closing sidebar
    const closeBtn = screen.getByTitle('Close');
    fireEvent.click(closeBtn);
    expect(screen.queryByText(/==1.0.0/i)).not.toBeInTheDocument();
  });
});
