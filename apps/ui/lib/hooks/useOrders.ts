/**
 * React Query Hooks for Orders
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { orderService } from '../services/orderService';
import type { CreateOrderRequest } from '../types/api';

/**
 * Hook to fetch user's orders
 */
export function useOrders() {
  return useQuery({
    queryKey: ['orders'],
    queryFn: () => orderService.list(),
  });
}

/**
 * Hook to fetch single order
 */
export function useOrder(orderId: string) {
  return useQuery({
    queryKey: ['order', orderId],
    queryFn: () => orderService.get(orderId),
    enabled: !!orderId,
  });
}

/**
 * Hook to create new order
 */
export function useCreateOrder() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: CreateOrderRequest) => orderService.create(request),
    onSuccess: () => {
      // Invalidate orders and cart
      queryClient.invalidateQueries({ queryKey: ['orders'] });
      queryClient.invalidateQueries({ queryKey: ['cart'] });
    },
  });
}

/**
 * Hook to cancel order
 */
export function useCancelOrder() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (orderId: string) => orderService.cancel(orderId),
    onSuccess: (_, orderId) => {
      // Invalidate specific order and orders list
      queryClient.invalidateQueries({ queryKey: ['order', orderId] });
      queryClient.invalidateQueries({ queryKey: ['orders'] });
    },
  });
}
