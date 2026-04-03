import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import axios from 'axios';
import CommunityView from './CommunityView';

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

describe('CommunityView', () => {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

  const renderComponent = () => render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <CommunityView />
      </MemoryRouter>
    </QueryClientProvider>
  );

  it('renders No Project Selected when missing project param', () => {
    mockSearchParams = new URLSearchParams('');
    renderComponent();
    expect(screen.getByText(/No Project Selected/i)).toBeInTheDocument();
  });

  it('fetches and renders communities when project is present', async () => {
    mockSearchParams = new URLSearchParams('?project=fastapi-0.100.0');
    
    vi.mocked(axios.get).mockResolvedValueOnce({ 
      data: {
        "1": [
          { method: { id: 1, name: 'auth_handler', file_path: 'app/auth.py', start_line: 10 } },
          { method: { id: 2, name: 'verify_token', file_path: 'app/auth.py', start_line: 20 } }
        ],
        "2": [
          { method: { id: 3, name: 'db_query', file_path: 'app/db.py', start_line: 15 } }
        ]
      }
    });

    renderComponent();
    
    expect(screen.getByText(/Resolving algorithmic community constraints/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('Community #1')).toBeInTheDocument();
      expect(screen.getByText('auth_handler')).toBeInTheDocument();
      expect(screen.getByText('Community #2')).toBeInTheDocument();
      expect(screen.getByText('db_query')).toBeInTheDocument();
    });
  });

  it('handles error state gracefully', async () => {
    mockSearchParams = new URLSearchParams('?project=error-project');
    vi.mocked(axios.get).mockRejectedValueOnce(new Error('Network Error'));

    renderComponent();
    
    await waitFor(() => {
      expect(screen.getByText(/Failed to compute Louvain graphs/i)).toBeInTheDocument();
    });
  });
});
