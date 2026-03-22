import { useQuery } from '@tanstack/react-query';
import { getPackageDetails } from '../services/api';

interface UsePackageQueryParams {
  ecosystem: string;
  packageName: string;
  version: string;
  enabled?: boolean;
}

export function usePackageQuery({
  ecosystem,
  packageName,
  version,
  enabled = true,
}: UsePackageQueryParams) {
  return useQuery({
    queryKey: ['package', ecosystem, packageName, version],
    queryFn: () => getPackageDetails(ecosystem, packageName, version),
    enabled: enabled && !!ecosystem && !!packageName && !!version,
    retry: false, // Don't retry dynamically on 404/500s because they reflect direct explicit user inputs
  });
}
