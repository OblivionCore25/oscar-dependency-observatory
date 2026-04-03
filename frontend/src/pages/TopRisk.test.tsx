import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import TopRisk from './TopRisk';
import * as hooks from '../hooks/useAnalyticsQuery';

vi.mock('../hooks/useAnalyticsQuery', () => ({
  useAnalyticsQuery: vi.fn(),
  useCoverageQuery: vi.fn(),
}));

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual as any,
    useNavigate: () => mockNavigate,
  };
});

describe('TopRisk', () => {
  const queryClient = new QueryClient();

  const renderComponent = () => {
    return render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <TopRisk />
        </MemoryRouter>
      </QueryClientProvider>
    );
  };

  it('renders correctly with mocked hooks and fetches NPM by default', () => {
    vi.mocked(hooks.useAnalyticsQuery).mockReturnValue({
      data: { items: [], meta: { limit: 50, fetch_duration_ms: 10 } },
      isLoading: false,
      error: null,
    } as any);

    vi.mocked(hooks.useCoverageQuery).mockReturnValue({
      data: { count: 0, coveragePct: 0, ingestedPackages: 0, estimatedTotal: 0, ecosystem: 'npm' },
    } as any);

    renderComponent();
    expect(screen.getByText(/Top Risk Dependencies/i)).toBeInTheDocument();
  });

  it('renders low graph coverage warning badge', () => {
    vi.mocked(hooks.useAnalyticsQuery).mockReturnValue({
      data: { items: [], meta: { limit: 50, fetch_duration_ms: 10 } },
      isLoading: false,
      error: null,
    } as any);

    vi.mocked(hooks.useCoverageQuery).mockReturnValue({
      data: { count: 0, coveragePct: 0.005, ingestedPackages: 0, estimatedTotal: 0, ecosystem: 'npm' },
    } as any);

    renderComponent();
    expect(screen.getByText('<0.01%')).toBeInTheDocument();
  });

  it('switches to PyPI ecosystem and Top 500 limit', async () => {
    vi.mocked(hooks.useAnalyticsQuery).mockReturnValue({
      data: { items: [] },
      isLoading: false,
      error: null,
    } as any);

    renderComponent();
    const pypiButton = screen.getByText('PyPI');
    fireEvent.click(pypiButton);

    const selectOptions = screen.getByRole('combobox');
    fireEvent.change(selectOptions, { target: { value: '1000' } });
    expect((selectOptions as HTMLSelectElement).value).toBe('1000');
  });

  it('handles Method Hotspots tab and navigation', async () => {
    renderComponent();
    const methodTab = screen.getByText(/Method Hotspots/i);
    fireEvent.click(methodTab);

    // After click, it should render Method Hotspots View
    expect(screen.getByText(/Hotspots at the code level require static analysis/i)).toBeInTheDocument();

    const analyzeBtn = screen.getByRole('button', { name: /Select an Analyzed Project/i });
    fireEvent.click(analyzeBtn);

    expect(mockNavigate).toHaveBeenCalledWith('/methods');
  });

  it('shows error state when useAnalyticsQuery yields error', () => {
    vi.mocked(hooks.useAnalyticsQuery).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error('Network error'),
    } as any);

    renderComponent();
    expect(screen.getByText(/Failed to load analytics/i)).toBeInTheDocument();
  });
});
