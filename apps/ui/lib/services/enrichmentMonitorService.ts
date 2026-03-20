import apiClient, { handleApiError } from '../api/client';
import API_ENDPOINTS from '../api/endpoints';
import type {
  EnrichmentDecisionRequest,
  EnrichmentEntityDetail,
  EnrichmentMonitorDashboard,
} from '../types/api';

export const enrichmentMonitorService = {
  async getDashboard(): Promise<EnrichmentMonitorDashboard> {
    try {
      const response = await apiClient.get<EnrichmentMonitorDashboard>(
        API_ENDPOINTS.admin.enrichmentMonitor.dashboard
      );
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  async getEntityDetail(entityId: string): Promise<EnrichmentEntityDetail> {
    try {
      const response = await apiClient.get<EnrichmentEntityDetail>(
        API_ENDPOINTS.admin.enrichmentMonitor.detail(entityId)
      );
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  async submitDecision(entityId: string, request: EnrichmentDecisionRequest): Promise<void> {
    try {
      await apiClient.post(API_ENDPOINTS.admin.enrichmentMonitor.decision(entityId), request);
    } catch (error) {
      throw handleApiError(error);
    }
  },

  async getEnrichmentPipelineStats(): Promise<
    Pick<EnrichmentMonitorDashboard, 'status_cards' | 'throughput'>
  > {
    const dashboard = await this.getDashboard();
    return {
      status_cards: dashboard.status_cards,
      throughput: dashboard.throughput,
    };
  },

  async getActiveEnrichmentJobs(): Promise<EnrichmentMonitorDashboard['active_jobs']> {
    const dashboard = await this.getDashboard();
    return dashboard.active_jobs;
  },

  async getEnrichmentDetail(entityId: string): Promise<EnrichmentEntityDetail> {
    return this.getEntityDetail(entityId);
  },
};

export default enrichmentMonitorService;
