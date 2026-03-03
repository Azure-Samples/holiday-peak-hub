/**
 * Checkout Service
 * 
 * API functions for checkout operations
 */

import apiClient, { handleApiError } from '../api/client';
import API_ENDPOINTS from '../api/endpoints';
import type {
  CheckoutValidationResponse,
  CreatePaymentIntentRequest,
  PaymentIntentResponse,
} from '../types/api';

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

  /**
   * Create a Stripe PaymentIntent and return the client secret
   */
  async createPaymentIntent(
    data: CreatePaymentIntentRequest
  ): Promise<PaymentIntentResponse> {
    try {
      const response = await apiClient.post<PaymentIntentResponse>(
        API_ENDPOINTS.payments.intent,
        data
      );
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  },
};

export default checkoutService;
