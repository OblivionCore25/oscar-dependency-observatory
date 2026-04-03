import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import axios from 'axios';
import SnapshotsView from './SnapshotsView';

vi.mock('axios');

describe('SnapshotsView', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    vi.resetAllMocks();
  });

  const Wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );

  it('renders loading state and handles ecosystem switch', async () => {
    // Hang the promise to simulate loading
    vi.mocked(axios.get).mockImplementation(() => new Promise(() => {}));
    
    render(<SnapshotsView />, { wrapper: Wrapper });
    expect(screen.getByText('Temporal Snapshots')).toBeInTheDocument();

    const select = screen.getAllByRole('combobox')[0];
    fireEvent.change(select, { target: { value: 'pypi' } });
    expect((select as HTMLSelectElement).value).toBe('pypi');
  });

  it('renders empty snapshots list natively', async () => {
    vi.mocked(axios.get).mockResolvedValue({ data: [] });
    
    render(<SnapshotsView />, { wrapper: Wrapper });
    
    await waitFor(() => {
      expect(screen.getByText(/no snapshots found/i)).toBeInTheDocument();
    });
  });

  it('renders snapshots list and processes creation mutation pipeline', async () => {
    vi.mocked(axios.get).mockResolvedValue({
      data: [{ snapshot_id: 'snap-1', created_at: '2024-01-01T00:00:00Z', description: 'desc 1', ecosystem: 'npm' }]
    });

    vi.mocked(axios.post).mockResolvedValue({
      data: { snapshot_id: 'snap-2', created_at: '2024-01-02T00:00:00Z', description: 'New Test Snapshot' }
    });

    render(<SnapshotsView />, { wrapper: Wrapper });
    
    await waitFor(() => {
       expect(screen.getByText('snap-1')).toBeInTheDocument();
    });

    const input = screen.getByPlaceholderText(/e.g., Before React 19 upgrade/i);
    fireEvent.change(input, { target: { value: 'New Test Snapshot' } });
    
    const captureBtn = screen.getByRole('button', { name: /Capture State/i });
    fireEvent.click(captureBtn);

    await waitFor(() => {
      expect(axios.post).toHaveBeenCalledWith('http://localhost:8000/snapshots/npm', { description: 'New Test Snapshot' });
    });
    
    // Check that form was reset via onSuccess
    expect((input as HTMLInputElement).value).toBe('');
  });

  it('processes comparison mutation successfully', async () => {
    vi.mocked(axios.get).mockImplementation(async (url) => {
      if (url.includes('compare')) {
         return { data: { added_edges: 5, removed_edges: 2 } };
      }
      return {
        data: [
          { snapshot_id: 'snap-1', created_at: '2024-01-01T00:00:00Z', description: 'desc 1' },
          { snapshot_id: 'snap-2', created_at: '2024-01-02T00:00:00Z', description: 'desc 2' }
        ]
      };
    });

    render(<SnapshotsView />, { wrapper: Wrapper });

    await waitFor(() => {
       expect(screen.getByText('snap-1')).toBeInTheDocument();
    });

    const selects = screen.getAllByRole('combobox');
    
    fireEvent.change(selects[1], { target: { value: 'snap-1' } });
    fireEvent.change(selects[2], { target: { value: 'snap-2' } });

    const compareBtn = screen.getByRole('button', { name: /Compare Delta/i });
    fireEvent.click(compareBtn);

    await waitFor(() => {
      expect(axios.get).toHaveBeenCalledWith('http://localhost:8000/snapshots/npm/compare', {
        params: { snapshot_1: 'snap-1', snapshot_2: 'snap-2' }
      });
      expect(screen.getByText('+5')).toBeInTheDocument();
      expect(screen.getByText('-2')).toBeInTheDocument();
    });
  });
});
