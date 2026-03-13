import apiClient, { handleApiError } from '../api/client';
import API_ENDPOINTS from '../api/endpoints';
import type {
  CreateTicketRequest,
  EscalateTicketRequest,
  Refund,
  ResolveTicketRequest,
  Return,
  ReturnTransitionRequest,
  SalesAnalytics,
  Shipment,
  Ticket,
  UpdateTicketRequest,
} from '../types/api';

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

  async createTicket(request: CreateTicketRequest): Promise<Ticket> {
    try {
      const response = await apiClient.post<Ticket>(API_ENDPOINTS.staff.tickets.create, request);
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  async updateTicket(ticketId: string, request: UpdateTicketRequest): Promise<Ticket> {
    try {
      const response = await apiClient.patch<Ticket>(API_ENDPOINTS.staff.tickets.update(ticketId), request);
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  async resolveTicket(ticketId: string, request: ResolveTicketRequest): Promise<Ticket> {
    try {
      const response = await apiClient.post<Ticket>(API_ENDPOINTS.staff.tickets.resolve(ticketId), request);
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  async escalateTicket(ticketId: string, request: EscalateTicketRequest): Promise<Ticket> {
    try {
      const response = await apiClient.post<Ticket>(API_ENDPOINTS.staff.tickets.escalate(ticketId), request);
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

  async getReturn(returnId: string): Promise<Return> {
    try {
      const response = await apiClient.get<Return>(API_ENDPOINTS.staff.returns.get(returnId));
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  async approveReturn(returnId: string, request: ReturnTransitionRequest): Promise<Return> {
    try {
      const response = await apiClient.post<Return>(API_ENDPOINTS.staff.returns.approve(returnId), request);
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  async rejectReturn(returnId: string, request: ReturnTransitionRequest): Promise<Return> {
    try {
      const response = await apiClient.post<Return>(API_ENDPOINTS.staff.returns.reject(returnId), request);
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  async receiveReturn(returnId: string, request: ReturnTransitionRequest): Promise<Return> {
    try {
      const response = await apiClient.post<Return>(API_ENDPOINTS.staff.returns.receive(returnId), request);
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  async restockReturn(returnId: string, request: ReturnTransitionRequest): Promise<Return> {
    try {
      const response = await apiClient.post<Return>(API_ENDPOINTS.staff.returns.restock(returnId), request);
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  async refundReturn(returnId: string, request: ReturnTransitionRequest): Promise<Return> {
    try {
      const response = await apiClient.post<Return>(API_ENDPOINTS.staff.returns.refund(returnId), request);
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  async getReturnRefundProgress(returnId: string): Promise<Refund> {
    try {
      const response = await apiClient.get<Refund>(API_ENDPOINTS.staff.returns.refundProgress(returnId));
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
