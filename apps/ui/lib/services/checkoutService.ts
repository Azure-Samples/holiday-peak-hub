/**
 * Checkout Service
 * 
 * API functions for checkout operations
 */

import apiClient, { handleApiError } from '../api/client';
import API_ENDPOINTS from '../api/endpoints';
import type { CheckoutValidationResponse } from '../types/api';

export const checkoutService = {
  /**
   * Validate checkout before creating order
   */
  async validate(): Promise<CheckoutValidationResponse> {
    try {
      const response = await apiClient.post<CheckoutValidationResponse>(
        API_ENDPOINTS.checkout.validate
      );
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  },
};

export default checkoutService;
