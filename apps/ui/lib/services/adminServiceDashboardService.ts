import apiClient, { handleApiError } from '../api/client';
import API_ENDPOINTS from '../api/endpoints';
import type { AdminServiceDashboard, AgentMonitorTimeRange, AdminServiceDomain } from '../types/api';

function withTimeRange(path: string, timeRange: AgentMonitorTimeRange): string {
  const queryJoiner = path.includes('?') ? '&' : '?';
  return `${path}${queryJoiner}time_range=${encodeURIComponent(timeRange)}`;
}

export const adminServiceDashboardService = {
  async getDashboard(
    domain: AdminServiceDomain,
    service: string,
    timeRange: AgentMonitorTimeRange,
  ): Promise<AdminServiceDashboard> {
    try {
      const response = await apiClient.get<AdminServiceDashboard>(
        withTimeRange(API_ENDPOINTS.admin.serviceDashboard(domain, service), timeRange),
      );
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  },
};

export default adminServiceDashboardService;
