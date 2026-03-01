import apiClient, { handleApiError } from '../api/client';
import API_ENDPOINTS from '../api/endpoints';
import type { Return, SalesAnalytics, Shipment, Ticket } from '../types/api';

export const staffService = {
  async getAnalyticsSummary(): Promise<SalesAnalytics> {
    try {
      const response = await apiClient.get<SalesAnalytics>(API_ENDPOINTS.staff.analytics.summary);
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  async listTickets(): Promise<Ticket[]> {
    try {
      const response = await apiClient.get<Ticket[]>(API_ENDPOINTS.staff.tickets.list);
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  async listReturns(): Promise<Return[]> {
    try {
      const response = await apiClient.get<Return[]>(API_ENDPOINTS.staff.returns.list);
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  async listShipments(): Promise<Shipment[]> {
    try {
      const response = await apiClient.get<Shipment[]>(API_ENDPOINTS.staff.shipments.list);
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  },
};

export default staffService;
