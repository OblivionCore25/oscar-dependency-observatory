import { useQuery } from '@tanstack/react-query';
import { getTopRisk } from '../services/api';
import type { TopRiskResponse } from '../types/api';

interface UseAnalyticsQueryOptions {
  ecosystem: string;
  limit: number;
}

export const useAnalyticsQuery = ({ ecosystem, limit }: UseAnalyticsQueryOptions) => {
  return useQuery<TopRiskResponse, Error>({
    queryKey: ['topRisk', ecosystem, limit],
    queryFn: () => getTopRisk(ecosystem, limit),
    // Keeping data relatively fresh but avoiding spam
    staleTime: 5 * 60 * 1000, 
  });
};
