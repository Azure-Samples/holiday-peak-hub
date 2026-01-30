/**
 * React Query Hooks for Products
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { productService } from '../services/productService';
import type { Product } from '../types/api';

/**
 * Hook to fetch list of products
 */
export function useProducts(filters?: {
  search?: string;
  category?: string;
  limit?: number;
}) {
  return useQuery({
    queryKey: ['products', filters],
    queryFn: () => productService.list(filters),
  });
}

/**
 * Hook to fetch single product by ID
 */
export function useProduct(id: string) {
  return useQuery({
    queryKey: ['product', id],
    queryFn: () => productService.get(id),
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
