import apiClient, { handleApiError } from '../api/client';
import API_ENDPOINTS from '../api/endpoints';
import type { CreateReturnRequest, Refund, Return } from '../types/api';

export const returnsService = {
  async list(): Promise<Return[]> {
    try {
      const response = await apiClient.get<Return[]>(API_ENDPOINTS.returns.list);
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  async create(request: CreateReturnRequest): Promise<Return> {
    try {
      const response = await apiClient.post<Return>(API_ENDPOINTS.returns.create, request);
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  async get(returnId: string): Promise<Return> {
    try {
      const response = await apiClient.get<Return>(API_ENDPOINTS.returns.get(returnId));
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  async getRefundProgress(returnId: string): Promise<Refund> {
    try {
      const response = await apiClient.get<Refund>(API_ENDPOINTS.returns.refund(returnId));
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  },
};

export default returnsService;
