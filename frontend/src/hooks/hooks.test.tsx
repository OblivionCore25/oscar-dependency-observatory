import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi } from 'vitest';
import { useAnalyticsQuery, useCoverageQuery } from './useAnalyticsQuery';
import { useGraphQuery } from './useGraphQuery';
import { usePackageQuery } from './usePackageQuery';
import * as api from '../services/api';

vi.mock('../services/api', () => ({
  getPackageDetails: vi.fn().mockResolvedValue({}),
  getTransitiveGraph: vi.fn().mockResolvedValue({}),
  getTopRisk: vi.fn().mockResolvedValue({}),
  getCoverage: vi.fn().mockResolvedValue({}),
}));

const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
const wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
);

describe('Hooks', () => {
  it('useAnalyticsQuery', async () => {
    const { result } = renderHook(() => useAnalyticsQuery({ ecosystem: 'npm', limit: 10 }), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(api.getTopRisk).toHaveBeenCalledWith('npm', 10);
  });

  it('useCoverageQuery', async () => {
    const { result } = renderHook(() => useCoverageQuery('pypi'), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(api.getCoverage).toHaveBeenCalledWith('pypi');
  });

  it('useGraphQuery', async () => {
    const { result } = renderHook(() => useGraphQuery({ ecosystem: 'npm', packageName: 'react', version: '1.0' }), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(api.getTransitiveGraph).toHaveBeenCalledWith('npm', 'react', '1.0');
  });

  it('usePackageQuery', async () => {
    const { result } = renderHook(() => usePackageQuery({ ecosystem: 'npm', packageName: 'react', version: '1.0' }), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(api.getPackageDetails).toHaveBeenCalledWith('npm', 'react', '1.0');
  });
});
