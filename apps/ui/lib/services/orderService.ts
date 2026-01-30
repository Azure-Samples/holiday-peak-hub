/**
 * Order Service
 * 
 * API functions for order operations
 */

import apiClient, { handleApiError } from '../api/client';
import API_ENDPOINTS from '../api/endpoints';
import type { Order, CreateOrderRequest } from '../types/api';

export const orderService = {
  /**
   * List user's orders
   */
  async list(): Promise<Order[]> {
    try {
      const response = await apiClient.get<Order[]>(API_ENDPOINTS.orders.list);
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  /**
   * Get single order by ID
   */
  async get(orderId: string): Promise<Order> {
    try {
      const response = await apiClient.get<Order>(API_ENDPOINTS.orders.get(orderId));
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  /**
   * Create new order from cart
   */
  async create(request: CreateOrderRequest): Promise<Order> {
    try {
      const response = await apiClient.post<Order>(
        API_ENDPOINTS.orders.create,
        request
      );
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  /**
   * Cancel an order
   */
  async cancel(orderId: string): Promise<{ message: string }> {
    try {
      const response = await apiClient.patch<{ message: string }>(
        API_ENDPOINTS.orders.cancel(orderId)
      );
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  },
};

export default orderService;
