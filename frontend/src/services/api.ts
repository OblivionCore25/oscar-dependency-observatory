import axios from 'axios';
import type { PackageDetailsResponse, TransitiveGraphResponse, TopRiskResponse } from '../types/api';

// Uses the Vite proxy (/api -> http://127.0.0.1:8000)
const apiClient = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

export const getPackageDetails = async (
  ecosystem: string,
  packageName: string,
  version: string
): Promise<PackageDetailsResponse> => {
  const response = await apiClient.get<PackageDetailsResponse>(
    `/packages/${ecosystem}/${encodeURIComponent(packageName)}/${encodeURIComponent(version)}`
  );
  return response.data;
};

export const getTransitiveGraph = async (
  ecosystem: string,
  packageName: string,
  version: string
): Promise<TransitiveGraphResponse> => {
  const response = await apiClient.get<TransitiveGraphResponse>(
    `/dependencies/${ecosystem}/${encodeURIComponent(packageName)}/${encodeURIComponent(version)}/transitive`
  );
  return response.data;
};

export const getTopRisk = async (ecosystem: string = 'npm', limit: number = 50): Promise<TopRiskResponse> => {
  const response = await apiClient.get<TopRiskResponse>(`/analytics/top-risk`, {
    params: { ecosystem, limit }
  });
  return response.data;
};
