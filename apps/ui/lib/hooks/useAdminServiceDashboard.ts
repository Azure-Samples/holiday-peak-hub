import { useQuery } from '@tanstack/react-query';
import { adminServiceDashboardService } from '../services/adminServiceDashboardService';
import type { AdminServiceDomain, AgentMonitorTimeRange } from '../types/api';

export const DEFAULT_ADMIN_SERVICE_RANGE: AgentMonitorTimeRange = '1h';

export const ADMIN_SERVICE_RANGE_OPTIONS: Array<{
  value: AgentMonitorTimeRange;
  label: string;
}> = [
  { value: '15m', label: 'Last 15 minutes' },
  { value: '1h', label: 'Last 1 hour' },
  { value: '6h', label: 'Last 6 hours' },
  { value: '24h', label: 'Last 24 hours' },
  { value: '7d', label: 'Last 7 days' },
];

export function useAdminServiceDashboard(
  domain: AdminServiceDomain,
  service: string,
  timeRange: AgentMonitorTimeRange,
) {
  return useQuery({
    queryKey: ['admin', 'service-dashboard', domain, service, timeRange],
    queryFn: () => adminServiceDashboardService.getDashboard(domain, service, timeRange),
    enabled: Boolean(domain) && Boolean(service),
    refetchInterval: 15_000,
  });
}
