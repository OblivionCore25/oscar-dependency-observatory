import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { BrowserRouter } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import MethodExplorer from './MethodExplorer';

vi.mock('axios');

vi.mock('@tanstack/react-query', async () => {
  const actual = await vi.importActual('@tanstack/react-query');
  return {
    ...actual as any,
    useQuery: vi.fn(),
    useMutation: vi.fn(),
    useQueryClient: vi.fn(),
  };
});

describe('MethodExplorer', () => {
  const mockInvalidateQueries = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useQueryClient).mockReturnValue({
      invalidateQueries: mockInvalidateQueries,
    } as any);
  });

  const Wrapper = ({ children }: { children: React.ReactNode }) => (
    <BrowserRouter>
      {children}
    </BrowserRouter>
  );

  it('renders loading state for projects', () => {
    vi.mocked(useQuery).mockReturnValue({ data: undefined, isLoading: true, error: null } as any);
    vi.mocked(useMutation).mockReturnValue({ mutate: vi.fn(), isPending: false, isError: false } as any);

    render(<MethodExplorer />, { wrapper: Wrapper });
    expect(screen.getByText(/loading analyzed projects/i)).toBeInTheDocument();
  });

  it('renders error state for projects', () => {
    vi.mocked(useQuery).mockReturnValue({ data: undefined, isLoading: false, error: { message: 'Network error' } } as any);
    vi.mocked(useMutation).mockReturnValue({ mutate: vi.fn(), isPending: false, isError: false } as any);

    render(<MethodExplorer />, { wrapper: Wrapper });
    expect(screen.getByText(/failed to load projects/i)).toBeInTheDocument();
  });

  it('renders empty list state', () => {
    vi.mocked(useQuery).mockReturnValue({ data: [], isLoading: false, error: null } as any);
    vi.mocked(useMutation).mockReturnValue({ mutate: vi.fn(), isPending: false, isError: false } as any);

    render(<MethodExplorer />, { wrapper: Wrapper });
    expect(screen.getByText(/no projects found/i)).toBeInTheDocument();
  });

  it('renders project list and filters properly', () => {
    vi.mocked(useQuery).mockReturnValue({ data: ['requests_2.31.0', 'boto3_1.0.0'], isLoading: false, error: null } as any);
    vi.mocked(useMutation).mockReturnValue({ mutate: vi.fn(), isPending: false, isError: false } as any);

    render(<MethodExplorer />, { wrapper: Wrapper });
    
    expect(screen.getByText('requests_2.31.0')).toBeInTheDocument();
    expect(screen.getByText('boto3_1.0.0')).toBeInTheDocument();
    
    // Test search filter
    const searchInput = screen.getByPlaceholderText(/search projects by name/i);
    fireEvent.change(searchInput, { target: { value: 'boto' } });
    
    expect(screen.queryByText('requests_2.31.0')).not.toBeInTheDocument();
    expect(screen.getByText('boto3_1.0.0')).toBeInTheDocument();
  });

  it('handles analyze submission synchronously and runs its coverage lines', async () => {
    vi.mocked(useQuery).mockReturnValue({ data: [], isLoading: false, error: null } as any);

    // Mock the mutation to intercept its config and run it synchronously to guarantee execution coverage
    let capturedOptions: any;
    vi.mocked(useMutation).mockImplementation((opts: any) => {
      capturedOptions = opts;
      return {
        mutate: () => {
          // Immediately execute the mutation function and trigger onSuccess to render UI
          opts.mutationFn().then(opts.onSuccess);
        },
        isPending: false,
        isError: false,
      } as any;
    });

    vi.mocked(axios.post).mockResolvedValue({
      data: { project_slug: 'pytest-7.0.0', meta: { method_count: 500, file_count: 40 } }
    });

    render(<MethodExplorer />, { wrapper: Wrapper });
    
    const pkgInput = screen.getByLabelText(/pypi package name/i);
    const verInput = screen.getByLabelText(/version/i);
    
    fireEvent.change(pkgInput, { target: { value: 'pytest' } });
    fireEvent.change(verInput, { target: { value: '7.0.0' } });

    const analyzeBtn = screen.getByRole('button', { name: /Download & Analyze/i });
    fireEvent.click(analyzeBtn);

    // Because it's a promise, we waitFor the state updates
    await waitFor(() => {
      expect(screen.getByText(/pytest-7.0.0/i)).toBeInTheDocument();
      expect(screen.getByText(/analyzed — 500 methods across 40 files/i)).toBeInTheDocument();
    });

    expect(mockInvalidateQueries).toHaveBeenCalled();
  });

  it('handles analyze submission error', async () => {
    vi.mocked(useQuery).mockReturnValue({ data: [], isLoading: false, error: null } as any);
    
    vi.mocked(useMutation).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
      isError: true,
      error: { response: { data: { detail: 'Package too large' } } }
    } as any);

    render(<MethodExplorer />, { wrapper: Wrapper });
    
    // UI immediately displays error if useMutation sets it
    expect(screen.getByText(/Package too large/i)).toBeInTheDocument();
  });
});
