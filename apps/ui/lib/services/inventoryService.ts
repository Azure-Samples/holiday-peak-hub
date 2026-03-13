/**
 * Inventory Service
 *
 * API functions for inventory health and reservation lifecycle operations.
 */

import apiClient, { handleApiError } from '../api/client';
import API_ENDPOINTS from '../api/endpoints';
import type {
  CreateReservationRequest,
  InventoryHealthResponse,
  InventoryReservation,
  ReservationActionRequest,
} from '../types/api';

export const inventoryService = {
  async getHealth(): Promise<InventoryHealthResponse> {
    try {
      const response = await apiClient.get<InventoryHealthResponse>(API_ENDPOINTS.inventory.health);
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  async createReservation(request: CreateReservationRequest): Promise<InventoryReservation> {
    try {
      const response = await apiClient.post<InventoryReservation>(
        API_ENDPOINTS.inventory.reservations.create,
        request
      );
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  async getReservation(reservationId: string): Promise<InventoryReservation> {
    try {
      const response = await apiClient.get<InventoryReservation>(
        API_ENDPOINTS.inventory.reservations.get(reservationId)
      );
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  async confirmReservation(
    reservationId: string,
    request: ReservationActionRequest
  ): Promise<InventoryReservation> {
    try {
      const response = await apiClient.post<InventoryReservation>(
        API_ENDPOINTS.inventory.reservations.confirm(reservationId),
        request
      );
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  async releaseReservation(
    reservationId: string,
    request: ReservationActionRequest
  ): Promise<InventoryReservation> {
    try {
      const response = await apiClient.post<InventoryReservation>(
        API_ENDPOINTS.inventory.reservations.release(reservationId),
        request
      );
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  },
};

export default inventoryService;
