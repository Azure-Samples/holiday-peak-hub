import apiClient, { handleApiError } from '../api/client';
import API_ENDPOINTS from '../api/endpoints';
import type {
  AgentEvaluationsPayload,
  AgentHealthCardMetric,
  AgentMonitorDashboard,
  AgentModelUsageRow,
  AgentMonitorTimeRange,
  AgentTraceSummary,
  AgentTraceDetail,
} from '../types/api';

function withTimeRange(path: string, timeRange: AgentMonitorTimeRange): string {
  const queryJoiner = path.includes('?') ? '&' : '?';
  return `${path}${queryJoiner}time_range=${encodeURIComponent(timeRange)}`;
}

export const agentMonitorService = {
  async getAgentHealth(timeRange: AgentMonitorTimeRange): Promise<AgentHealthCardMetric[]> {
    const dashboard = await this.getDashboard(timeRange);
    return dashboard.health_cards;
  },

  async getRecentTraces(
    agentName: string | undefined,
    limit: number,
    timeRange: AgentMonitorTimeRange
  ): Promise<AgentTraceSummary[]> {
    const dashboard = await this.getDashboard(timeRange);
    const normalizedAgentName = agentName?.trim().toLowerCase();
    const filtered = normalizedAgentName
      ? dashboard.trace_feed.filter((trace) => trace.agent_name.toLowerCase() === normalizedAgentName)
      : dashboard.trace_feed;

    return filtered.slice(0, Math.max(limit, 0));
  },

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

  async getModelUsageStats(timeRange: AgentMonitorTimeRange): Promise<AgentModelUsageRow[]> {
    const dashboard = await this.getDashboard(timeRange);
    return dashboard.model_usage;
  },

  async getLatestEvaluations(timeRange: AgentMonitorTimeRange): Promise<AgentEvaluationsPayload> {
    return this.getEvaluations(timeRange);
  },
};

export default agentMonitorService;
