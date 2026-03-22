import { useQuery } from '@tanstack/react-query';
import { getTransitiveGraph } from '../services/api';

interface UseGraphQueryParams {
  ecosystem: string | null;
  packageName: string | null;
  version: string | null;
}

export function useGraphQuery({
  ecosystem,
  packageName,
  version,
}: UseGraphQueryParams) {
  return useQuery({
    queryKey: ['transitive-graph', ecosystem, packageName, version],
    queryFn: () => getTransitiveGraph(ecosystem!, packageName!, version!),
    enabled: !!ecosystem && !!packageName && !!version,
    staleTime: Infinity, // Graphs are mathematically immutable once published. Avoid aggressive refetching.
    retry: false,
  });
}
