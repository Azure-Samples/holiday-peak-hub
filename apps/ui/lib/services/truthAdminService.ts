import apiClient, { handleApiError } from '../api/client';
import API_ENDPOINTS from '../api/endpoints';
import type {
  CategorySchema,
  TenantConfig,
  TruthAnalyticsSummary,
  CompletenessBreakdown,
  PipelineThroughput,
} from '../types/api';

export const truthAdminService = {
  async listSchemas(): Promise<CategorySchema[]> {
    try {
      const response = await apiClient.get<CategorySchema[]>(API_ENDPOINTS.truth.schemas.list);
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  async getSchema(id: string): Promise<CategorySchema> {
    try {
      const response = await apiClient.get<CategorySchema>(API_ENDPOINTS.truth.schemas.get(id));
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  async createSchema(schema: Omit<CategorySchema, 'id' | 'created_at' | 'updated_at'>): Promise<CategorySchema> {
    try {
      const response = await apiClient.post<CategorySchema>(API_ENDPOINTS.truth.schemas.create, schema);
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  async updateSchema(id: string, schema: Partial<CategorySchema>): Promise<CategorySchema> {
    try {
      const response = await apiClient.put<CategorySchema>(API_ENDPOINTS.truth.schemas.update(id), schema);
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  async deleteSchema(id: string): Promise<void> {
    try {
      await apiClient.delete(API_ENDPOINTS.truth.schemas.delete(id));
    } catch (error) {
      throw handleApiError(error);
    }
  },

  async getConfig(): Promise<TenantConfig> {
    try {
      const response = await apiClient.get<TenantConfig>(API_ENDPOINTS.truth.config.get);
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  async updateConfig(config: Partial<TenantConfig>): Promise<TenantConfig> {
    try {
      const response = await apiClient.put<TenantConfig>(API_ENDPOINTS.truth.config.update, config);
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  async getAnalyticsSummary(): Promise<TruthAnalyticsSummary> {
    try {
      const response = await apiClient.get<TruthAnalyticsSummary>(API_ENDPOINTS.truth.analytics.summary);
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  async getCompletenessBreakdown(): Promise<CompletenessBreakdown[]> {
    try {
      const response = await apiClient.get<CompletenessBreakdown[]>(API_ENDPOINTS.truth.analytics.completeness);
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  async getPipelineThroughput(): Promise<PipelineThroughput[]> {
    try {
      const response = await apiClient.get<PipelineThroughput[]>(API_ENDPOINTS.truth.analytics.throughput);
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  },
};

export default truthAdminService;
