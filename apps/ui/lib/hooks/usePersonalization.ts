import { useMutation } from '@tanstack/react-query';
import personalizationService from '../services/personalizationService';

const IDENTIFIER_PATTERN = /^[A-Za-z0-9._-]+$/;
const MIN_QUANTITY = 1;
const MAX_QUANTITY = 100;
const MIN_MAX_ITEMS = 1;
const MAX_MAX_ITEMS = 10;

export type PersonalizationMutationRequest = {
  customerId: string;
  sku: string;
  quantity?: number;
  maxItems?: number;
};

export function useBrandShoppingFlow() {
  return useMutation({
    mutationFn: async (request: PersonalizationMutationRequest) => {
      const customerId = request.customerId.trim();
      const sku = request.sku.trim();
      const quantity = request.quantity ?? MIN_QUANTITY;
      const maxItems = request.maxItems ?? 4;

      if (!customerId || !IDENTIFIER_PATTERN.test(customerId)) {
        throw new Error('Customer ID is required and may only contain letters, numbers, dot, underscore, or hyphen.');
      }

      if (!sku || !IDENTIFIER_PATTERN.test(sku)) {
        throw new Error('SKU is required and may only contain letters, numbers, dot, underscore, or hyphen.');
      }

      if (!Number.isInteger(quantity) || quantity < MIN_QUANTITY || quantity > MAX_QUANTITY) {
        throw new Error('Quantity must be an integer between 1 and 100.');
      }

      if (!Number.isInteger(maxItems) || maxItems < MIN_MAX_ITEMS || maxItems > MAX_MAX_ITEMS) {
        throw new Error('Max items must be an integer between 1 and 10.');
      }

      return personalizationService.runFlow({
        customerId,
        sku,
        quantity,
        maxItems,
      });
    },
  });
}
