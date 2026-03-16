/**
 * Semantic Search Service
 *
 * Uses agent API (APIM) when configured, falls back to CRUD search.
 */

import agentApiClient from '../api/agentClient';
import { resolveAgentApiClientBaseUrl } from '@/app/api/_shared/base-url-resolver';
import { productService } from './productService';
import {
  mapAcpProductsToUi,
  mapApiProductsToUi,
  type AcpProduct,
} from '../utils/productMappers';
import type { Product as UiProduct } from '../../components/types';

const AGENT_API_BASE_URL = resolveAgentApiClientBaseUrl().baseUrl || '';

export interface SemanticSearchRequest {
  query: string;
  limit?: number;
  filters?: {
    category?: string;
    priceRange?: { min: number; max: number };
  };
}

export interface SemanticSearchResponse {
  items: UiProduct[];
  source: 'agent' | 'crud';
}

export const semanticSearchService = {
  async search(request: SemanticSearchRequest): Promise<SemanticSearchResponse> {
    const trimmed = request.query.trim();
    if (!trimmed) {
      return { items: [], source: 'crud' };
    }

    if (AGENT_API_BASE_URL) {
      try {
        const response = await agentApiClient.post('/ecommerce-catalog-search/invoke', request);
        const payload = response.data || {};
        const results = (payload.results || payload.items || []) as AcpProduct[];
        return { items: mapAcpProductsToUi(results), source: 'agent' };
      } catch (error) {
        console.error('Semantic search failed:', error);
        // Fall back to CRUD search
      }
    }

    const fallback = await productService.search(trimmed, request.limit || 20);
    return { items: mapApiProductsToUi(fallback), source: 'crud' };
  },
};

export default semanticSearchService;
