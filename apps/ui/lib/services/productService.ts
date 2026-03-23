/**
 * Product Service
 * 
 * API functions for product operations
 */

import apiClient, { handleApiError } from '../api/client';
import agentApiClient from '../api/agentClient';
import API_ENDPOINTS from '../api/endpoints';
import type {
  Product,
  ProductEnrichmentTriggerRequest,
  ProductEnrichmentTriggerResponse,
} from '../types/api';
import { parsePriceString, type AcpProduct } from '../utils/productMappers';

type AgentEnrichmentPayload = {
  title?: string;
  description?: string;
  enriched_description?: string;
  rating?: number;
  review_count?: number;
  reviewCount?: number;
  features?: string[];
  use_cases?: string[];
  complementary_products?: string[];
  substitute_products?: string[];
  media?: Array<{ url: string; type?: string }>;
  inventory?: Record<string, unknown>;
  related?: Array<Record<string, unknown>>;
};

export const productService = {
  mapAcpToProduct(product: AcpProduct): Product {
    const { amount } = parsePriceString(product.price);
    const availability = (product.availability || '').toLowerCase();

    return {
      id: product.item_id,
      name: product.title || product.item_id,
      description: product.description || '',
      price: amount,
      category_id: product.category_id || product.category || 'search',
      image_url: product.image_url || product.image,
      in_stock: availability !== 'out_of_stock',
    };
  },

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

  async listEnriched(params?: {
    search?: string;
    category?: string;
    limit?: number;
  }): Promise<Product[]> {
    const products = await this.list(params);
    const enrichedProducts = await Promise.all(
      products.map(async (product) => {
        try {
          return await this.get(product.id);
        } catch {
          return product;
        }
      })
    );
    return enrichedProducts;
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

  async getEnriched(id: string): Promise<Product> {
    let baseProduct: Product | null = null;
    let enrichment: AgentEnrichmentPayload | null = null;

    try {
      baseProduct = await this.get(id);
    } catch {
      baseProduct = null;
    }

    try {
      const response = await agentApiClient.post('/ecommerce-product-detail-enrichment/invoke', {
        sku: id,
      });
      const payload = response.data || {};
      enrichment = (payload.enriched_product || payload) as AgentEnrichmentPayload;
    } catch {
      enrichment = null;
    }

    if (!baseProduct && !enrichment) {
      throw new Error('Product not found');
    }

    return {
      id,
      name: baseProduct?.name || enrichment?.title || id,
      description: enrichment?.description || baseProduct?.description || '',
      enriched_description: enrichment?.enriched_description || baseProduct?.enriched_description,
      price: baseProduct?.price || 0,
      category_id: baseProduct?.category_id || 'catalog',
      image_url: baseProduct?.image_url,
      in_stock: baseProduct?.in_stock ?? true,
      rating: enrichment?.rating ?? baseProduct?.rating,
      review_count:
        enrichment?.review_count ?? enrichment?.reviewCount ?? baseProduct?.review_count,
      features: enrichment?.features ?? baseProduct?.features,
      use_cases: enrichment?.use_cases ?? baseProduct?.use_cases,
      complementary_products: enrichment?.complementary_products ?? baseProduct?.complementary_products,
      substitute_products: enrichment?.substitute_products ?? baseProduct?.substitute_products,
      media: enrichment?.media ?? baseProduct?.media,
      inventory: enrichment?.inventory ?? baseProduct?.inventory,
      related: enrichment?.related ?? baseProduct?.related,
    };
  },

  /**
   * Search products by name
   */
  async search(query: string, limit = 20): Promise<Product[]> {
    return this.list({ search: query, limit });
  },

  /**
   * Get products by category
   */
  async getByCategory(categoryId: string, limit = 50): Promise<Product[]> {
    return this.list({ category: categoryId, limit });
  },

  async triggerEnrichment(
    id: string,
    request?: ProductEnrichmentTriggerRequest,
  ): Promise<ProductEnrichmentTriggerResponse> {
    try {
      const response = await apiClient.post<ProductEnrichmentTriggerResponse>(
        API_ENDPOINTS.products.triggerEnrichment(id),
        request,
      );
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  },
};

export default productService;
