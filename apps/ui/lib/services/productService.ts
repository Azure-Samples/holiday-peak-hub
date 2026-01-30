/**
 * Product Service
 * 
 * API functions for product operations
 */

import apiClient, { handleApiError } from '../api/client';
import API_ENDPOINTS from '../api/endpoints';
import type { Product } from '../types/api';

export const productService = {
  /**
   * List all products with optional filters
   */
  async list(params?: {
    search?: string;
    category?: string;
    limit?: number;
  }): Promise<Product[]> {
    try {
      const queryParams = new URLSearchParams();
      if (params?.search) queryParams.append('search', params.search);
      if (params?.category) queryParams.append('category', params.category);
      if (params?.limit) queryParams.append('limit', params.limit.toString());

      const url = `${API_ENDPOINTS.products.list}${queryParams.toString() ? '?' + queryParams.toString() : ''}`;
      const response = await apiClient.get<Product[]>(url);
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  /**
   * Get single product by ID
   */
  async get(id: string): Promise<Product> {
    try {
      const response = await apiClient.get<Product>(API_ENDPOINTS.products.get(id));
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  /**
   * Search products by name
   */
  async search(query: string, limit = 20): Promise<Product[]> {
    try {
      const url = `${API_ENDPOINTS.products.list}?search=${encodeURIComponent(query)}&limit=${limit}`;
      const response = await apiClient.get<Product[]>(url);
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  /**
   * Get products by category
   */
  async getByCategory(categoryId: string, limit = 50): Promise<Product[]> {
    try {
      const url = `${API_ENDPOINTS.products.list}?category=${categoryId}&limit=${limit}`;
      const response = await apiClient.get<Product[]>(url);
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  },
};

export default productService;
