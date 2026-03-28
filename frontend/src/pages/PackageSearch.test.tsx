import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import PackageSearch from './PackageSearch';
import * as hooks from '../hooks/usePackageQuery';

// We do not need QueryClientProvider if we mock the hook directly!
vi.mock('../hooks/usePackageQuery', () => ({
  usePackageQuery: vi.fn(),
}));

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual as any,
    useNavigate: () => mockNavigate,
  };
});

const renderComponent = () => render(
  <MemoryRouter>
    <PackageSearch />
  </MemoryRouter>
);

describe('PackageSearch', () => {
  it('renders form and handles submission visually (without data)', () => {
    vi.mocked(hooks.usePackageQuery).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: null,
    } as any);

    renderComponent();

    const input = screen.getByPlaceholderText(/e.g. react or fastapi/i);
    const version = screen.getByPlaceholderText(/e.g. 18.2.0/i);
    const EcosystemSelect = screen.getByRole('combobox');
    
    // Type into inputs
    fireEvent.change(input, { target: { value: 'requests' } });
    fireEvent.change(version, { target: { value: '2.31.0' } });
    fireEvent.change(EcosystemSelect, { target: { value: 'pypi' } });

    // Submit form
    const button = screen.getByRole('button', { name: /Search/i });
    expect(button).not.toBeDisabled();
    fireEvent.click(button);
    // State updates internally.
  });

  it('shows loading state when isLoading is true', () => {
    vi.mocked(hooks.usePackageQuery).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    } as any);

    renderComponent();
    expect(screen.getByRole('button', { name: /Search/i })).toBeDisabled();
  });

  it('renders results when data is present and handles navigation', () => {
    vi.mocked(hooks.usePackageQuery).mockReturnValue({
      data: {
        ecosystem: 'pypi',
        name: 'requests',
        version: '2.31.0',
        metrics: {
          directDependencies: 10,
          fanOut: 100,
          fanIn: 500,
          bottleneckScore: 0,
          diamondCount: 5,
          pageRank: 0.1,
          closenessCentrality: 0.2,
        }
      },
      isLoading: false,
      error: null,
    } as any);

    renderComponent();

    expect(screen.getByText('Direct Dependencies')).toBeInTheDocument();
    
    // Test Graph Navigation
    const viewGraphBtn = screen.getByRole('button', { name: /View Graph/i });
    fireEvent.click(viewGraphBtn);
    expect(mockNavigate).toHaveBeenCalledWith('/graph?ecosystem=pypi&package=requests&version=2.31.0');

    // Test Method Navigation
    const methodBtn = screen.getByRole('button', { name: /Method Insights/i });
    fireEvent.click(methodBtn);
    expect(mockNavigate).toHaveBeenCalledWith('/methods');
  });

  it('renders error state', () => {
    vi.mocked(hooks.usePackageQuery).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: { response: { data: { detail: 'Backend Validation Failed' } } },
    } as any);

    render(
      <MemoryRouter>
        <PackageSearch />
      </MemoryRouter>
    );

    expect(screen.getByText(/Search Failed/i)).toBeInTheDocument();
  });
});
