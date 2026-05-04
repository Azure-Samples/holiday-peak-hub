/**
 * React Query Hooks for Products
 */

import { useMutation, useQuery } from '@tanstack/react-query';
import { ApiError } from '../api/client';
import { productService } from '../services/productService';
import type { ProductEnrichmentTriggerRequest } from '../types/api';

const CATALOG_QUERY_STALE_TIME_MS = 5 * 60 * 1000;

function shouldRetryCatalogReadQuery(failureCount: number, error: unknown): boolean {
  if (!(error instanceof ApiError)) {
    return false;
  }

  return failureCount < 1 && error.status >= 500 && error.status < 600;
}

/**
 * Hook to fetch list of products
 */
export function useProducts(filters?: {
  search?: string;
  category?: string;
  limit?: number;
  enrich?: boolean;
}, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: ['products', filters],
    queryFn: () =>
      filters?.enrich
        ? productService.listEnriched(filters)
        : productService.list(filters),
    enabled: options?.enabled ?? true,
    retry: shouldRetryCatalogReadQuery,
    retryOnMount: false,
    refetchOnReconnect: false,
    staleTime: CATALOG_QUERY_STALE_TIME_MS,
  });
}

/**
 * Hook to fetch single product by ID
 */
export function useProduct(id: string) {
  return useQuery({
    queryKey: ['product', id],
    queryFn: () => productService.getEnriched(id),
    enabled: !!id,
  });
}

/**
 * Hook to search products
 */
export function useProductSearch(query: string, limit = 20) {
  return useQuery({
    queryKey: ['products', 'search', query, limit],
    queryFn: () => productService.search(query, limit),
    enabled: query.length > 0,
  });
}

/**
 * Hook to fetch products by category
 */
export function useProductsByCategory(categoryId: string, limit = 50) {
  return useQuery({
    queryKey: ['products', 'category', categoryId, limit],
    queryFn: () => productService.getByCategory(categoryId, limit),
    enabled: !!categoryId,
  });
}

export function useTriggerProductEnrichment() {
  return useMutation({
    mutationFn: ({
      productId,
      payload,
    }: {
      productId: string;
      payload?: ProductEnrichmentTriggerRequest;
    }) => productService.triggerEnrichment(productId, payload),
  });
}
