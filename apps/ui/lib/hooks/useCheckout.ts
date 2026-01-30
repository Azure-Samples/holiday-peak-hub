/**
 * React Query Hooks for Checkout
 */

import { useQuery } from '@tanstack/react-query';
import { checkoutService } from '../services/checkoutService';

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
