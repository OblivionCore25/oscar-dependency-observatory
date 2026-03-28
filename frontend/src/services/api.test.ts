import { describe, it, expect, vi } from 'vitest';
import { getPackageDetails, getTransitiveGraph, getTopRisk, getCoverage } from './api';
import axios from 'axios';

vi.mock('axios', () => {
  const mAxiosInstance = {
    get: vi.fn(),
  };
  return {
    default: {
      create: vi.fn(() => mAxiosInstance),
    },
  };
});

describe('API Service', () => {
  // We need to re-import the mocked instance internally
  const axiosInstance = axios.create();

  it('calls getPackageDetails', async () => {
    vi.mocked(axiosInstance.get).mockResolvedValueOnce({ data: { test: 1 } });
    const res = await getPackageDetails('npm', 'react', '18.2.0');
    expect(axiosInstance.get).toHaveBeenCalledWith('/packages/npm/react/18.2.0');
    expect(res).toEqual({ test: 1 });
  });

  it('calls getTransitiveGraph', async () => {
    vi.mocked(axiosInstance.get).mockResolvedValueOnce({ data: { nodes: [] } });
    const res = await getTransitiveGraph('pypi', 'requests', '2.31.0');
    expect(axiosInstance.get).toHaveBeenCalledWith('/dependencies/pypi/requests/2.31.0/transitive');
    expect(res).toEqual({ nodes: [] });
  });

  it('calls getTopRisk', async () => {
    vi.mocked(axiosInstance.get).mockResolvedValueOnce({ data: { items: [] } });
    const res = await getTopRisk('pypi', 10);
    expect(axiosInstance.get).toHaveBeenCalledWith('/analytics/top-risk', { params: { ecosystem: 'pypi', limit: 10 } });
    expect(res).toEqual({ items: [] });
  });

  it('calls getCoverage', async () => {
    vi.mocked(axiosInstance.get).mockResolvedValueOnce({ data: { count: 0 } });
    const res = await getCoverage('npm');
    expect(axiosInstance.get).toHaveBeenCalledWith('/analytics/coverage', { params: { ecosystem: 'npm' } });
    expect(res).toEqual({ count: 0 });
  });
});
