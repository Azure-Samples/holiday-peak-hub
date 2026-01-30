/**
 * Cart Service
 * 
 * API functions for cart operations
 */

import apiClient, { handleApiError } from '../api/client';
import API_ENDPOINTS from '../api/endpoints';
import type { Cart, AddToCartRequest } from '../types/api';

export const cartService = {
  /**
   * Get current user's cart
   */
  async get(): Promise<Cart> {
    try {
      const response = await apiClient.get<Cart>(API_ENDPOINTS.cart.get);
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  /**
   * Add item to cart
   */
  async addItem(request: AddToCartRequest): Promise<{ message: string }> {
    try {
      const response = await apiClient.post<{ message: string }>(
        API_ENDPOINTS.cart.addItem,
        request
      );
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  /**
   * Remove item from cart
   */
  async removeItem(productId: string): Promise<{ message: string }> {
    try {
      const response = await apiClient.delete<{ message: string }>(
        API_ENDPOINTS.cart.removeItem(productId)
      );
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  /**
   * Clear entire cart
   */
  async clear(): Promise<{ message: string }> {
    try {
      const response = await apiClient.delete<{ message: string }>(
        API_ENDPOINTS.cart.clear
      );
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  },
};

export default cartService;
