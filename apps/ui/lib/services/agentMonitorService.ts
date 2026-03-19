import apiClient, { handleApiError } from '../api/client';
import API_ENDPOINTS from '../api/endpoints';
import type {
  AgentEvaluationsPayload,
  AgentMonitorDashboard,
  AgentMonitorTimeRange,
  AgentTraceDetail,
} from '../types/api';

function withTimeRange(path: string, timeRange: AgentMonitorTimeRange): string {
  const queryJoiner = path.includes('?') ? '&' : '?';
  return `${path}${queryJoiner}time_range=${encodeURIComponent(timeRange)}`;
}

export const agentMonitorService = {
  async getDashboard(timeRange: AgentMonitorTimeRange): Promise<AgentMonitorDashboard> {
    try {
      const response = await apiClient.get<AgentMonitorDashboard>(
        withTimeRange(API_ENDPOINTS.admin.agentActivity.dashboard, timeRange)
      );
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  async getTraceDetail(traceId: string, timeRange: AgentMonitorTimeRange): Promise<AgentTraceDetail> {
    try {
      const response = await apiClient.get<AgentTraceDetail>(
        withTimeRange(API_ENDPOINTS.admin.agentActivity.traceDetail(traceId), timeRange)
      );
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  async getEvaluations(timeRange: AgentMonitorTimeRange): Promise<AgentEvaluationsPayload> {
    try {
      const response = await apiClient.get<AgentEvaluationsPayload>(
        withTimeRange(API_ENDPOINTS.admin.agentActivity.evaluations, timeRange)
      );
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  async getHealthIndicator(): Promise<AgentMonitorDashboard> {
    try {
      const response = await apiClient.get<AgentMonitorDashboard>(
        withTimeRange(API_ENDPOINTS.admin.agentActivity.health, '15m')
      );
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  },
};

export default agentMonitorService;
