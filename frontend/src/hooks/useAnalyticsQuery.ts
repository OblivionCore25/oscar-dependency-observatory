import { useQuery } from '@tanstack/react-query';
import { getTopRisk, getCoverage } from '../services/api';
import type { TopRiskResponse, CoverageResponse } from '../types/api';

interface UseAnalyticsQueryOptions {
  ecosystem: string;
  limit: number;
}

export const useAnalyticsQuery = ({ ecosystem, limit }: UseAnalyticsQueryOptions) => {
  return useQuery<TopRiskResponse, Error>({
    queryKey: ['topRisk', ecosystem, limit],
    queryFn: () => getTopRisk(ecosystem, limit),
    staleTime: 5 * 60 * 1000,
  });
};

export const useCoverageQuery = (ecosystem: string) => {
  return useQuery<CoverageResponse, Error>({
    queryKey: ['coverage', ecosystem],
    queryFn: () => getCoverage(ecosystem),
    staleTime: 10 * 60 * 1000,
  });
};
