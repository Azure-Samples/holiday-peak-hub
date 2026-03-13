/**
 * React Query Hooks for Checkout
 */

import { useMutation, useQuery } from '@tanstack/react-query';
import { checkoutService } from '../services/checkoutService';
import type {
  ConfirmPaymentIntentRequest,
  CreateOrderRequest,
  CreatePaymentIntentRequest,
} from '../types/api';

/**
 * Hook to validate checkout
 */
export function useCheckoutValidation() {
  return useQuery({
    queryKey: ['checkout', 'validation'],
    queryFn: () => checkoutService.validate(),
    // Don't automatically refetch
    staleTime: Infinity,
    gcTime: 0,
  });
}

/**
 * Hook to create order from cart for checkout
 */
export function useCreateCheckoutOrder() {
  return useMutation({
    mutationFn: (request: CreateOrderRequest) => checkoutService.createOrder(request),
  });
}

/**
 * Hook to create payment intent for checkout order
 */
export function useCreateCheckoutPaymentIntent() {
  return useMutation({
    mutationFn: (request: CreatePaymentIntentRequest) => checkoutService.createPaymentIntent(request),
  });
}

/**
 * Hook to reconcile confirmed payment intent and finalize order payment
 */
export function useConfirmCheckoutPaymentIntent() {
  return useMutation({
    mutationFn: (request: ConfirmPaymentIntentRequest) => checkoutService.confirmPaymentIntent(request),
  });
}
