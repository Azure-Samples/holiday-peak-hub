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
  mode?: 'keyword' | 'intelligent';
  filters?: {
    category?: string;
    priceRange?: { min: number; max: number };
  };
}

export interface SemanticSearchIntent {
  intent?: string;
  confidence?: number;
  entities?: Record<string, unknown>;
  reasoning?: string;
}

export interface SemanticSearchResponse {
  items: UiProduct[];
  source: 'agent' | 'crud';
  mode: 'keyword' | 'intelligent';
  intent?: SemanticSearchIntent | null;
  subqueries?: string[];
}

export type SearchModePreference = 'auto' | 'keyword' | 'intelligent';

export const semanticSearchService = {
  async searchWithMode(
    query: string,
    mode: SearchModePreference,
    limit = 20,
  ): Promise<SemanticSearchResponse> {
    const requestedMode = mode === 'auto' ? undefined : mode;
    return this.search({ query, limit, mode: requestedMode });
  },

  async search(request: SemanticSearchRequest): Promise<SemanticSearchResponse> {
    const trimmed = request.query.trim();
    if (!trimmed) {
      return { items: [], source: 'crud', mode: request.mode || 'keyword' };
    }

    if (AGENT_API_BASE_URL) {
      try {
        const response = await agentApiClient.post('/ecommerce-catalog-search/invoke', request);
        const payload = response.data || {};
        const results = (payload.results || payload.items || []) as AcpProduct[];
        const mode = payload.mode === 'intelligent' ? 'intelligent' : 'keyword';
        return {
          items: mapAcpProductsToUi(results),
          source: 'agent',
          mode,
          intent: (payload.intent as SemanticSearchIntent | undefined) || null,
          subqueries: Array.isArray(payload.subqueries)
            ? payload.subqueries.filter((value: unknown): value is string => typeof value === 'string')
            : [],
        };
      } catch (error) {
        console.error('Semantic search failed:', error);
        // Fall back to CRUD search
      }
    }

    const fallback = await productService.search(trimmed, request.limit || 20);
    return { items: mapApiProductsToUi(fallback), source: 'crud', mode: 'keyword' };
  },
};

export default semanticSearchService;
