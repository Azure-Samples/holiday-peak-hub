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
const MOCK_HOST_SUFFIX = 'example.com';

export type SearchResultType = 'deterministic' | 'model_answer' | 'degraded_fallback';
export type SearchDegradedReason = 'model_timeout' | 'model_error';

function usesMockHost(rawUrl: string): boolean {
  const candidate = rawUrl.trim();
  if (!candidate) {
    return false;
  }

  try {
    const parsed = new URL(candidate, 'https://placeholder.invalid');
    const hostname = parsed.hostname.toLowerCase();
    return hostname === MOCK_HOST_SUFFIX || hostname.endsWith(`.${MOCK_HOST_SUFFIX}`);
  } catch {
    return false;
  }
}

function parseSearchResultType(value: unknown): SearchResultType | undefined {
  if (
    value === 'deterministic'
    || value === 'model_answer'
    || value === 'degraded_fallback'
  ) {
    return value;
  }

  return undefined;
}

function parseSearchDegradedReason(value: unknown): SearchDegradedReason | undefined {
  if (value === 'model_timeout' || value === 'model_error') {
    return value;
  }

  return undefined;
}

function parseStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .filter((item): item is string => typeof item === 'string')
    .map((item) => item.trim())
    .filter((item) => item.length > 0);
}

export interface SemanticSearchRequest {
  query: string;
  limit?: number;
  mode?: 'keyword' | 'intelligent';
  user_id?: string;
  tenant_id?: string;
  session_id?: string;
  query_history?: string[];
  search_stage?: 'baseline' | 'rerank';
  baseline_candidate_skus?: string[];
  correlation_id?: string;
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
  requested_mode?: 'keyword' | 'intelligent';
  fallback_reason?: 'agent_unavailable' | 'agent_mock';
  trace_id?: string;
  intent?: SemanticSearchIntent | null;
  subqueries?: string[];
  answer_source?: string;
  result_type?: SearchResultType;
  degraded?: boolean;
  degraded_reason?: SearchDegradedReason;
  degraded_message?: string;
  fallback_keywords?: string[];
}

export type SemanticSearchContext = Pick<
  SemanticSearchRequest,
  | 'user_id'
  | 'tenant_id'
  | 'session_id'
  | 'query_history'
  | 'search_stage'
  | 'baseline_candidate_skus'
  | 'correlation_id'
>;

export type SearchModePreference = 'auto' | 'keyword' | 'intelligent';

export const semanticSearchService = {
  async searchWithMode(
    query: string,
    mode: SearchModePreference,
    limit = 20,
    context?: SemanticSearchContext,
  ): Promise<SemanticSearchResponse> {
    const requestedMode = mode === 'auto' ? undefined : mode;
    return this.search({ query, limit, mode: requestedMode, ...(context || {}) });
  },

  async search(request: SemanticSearchRequest): Promise<SemanticSearchResponse> {
    const trimmed = request.query.trim();
    const requestedMode = request.mode;
    if (!trimmed) {
      return {
        items: [],
        source: 'crud',
        mode: requestedMode === 'intelligent' ? 'intelligent' : 'keyword',
        requested_mode: requestedMode,
        result_type: 'deterministic',
        degraded: false,
      };
    }

    if (AGENT_API_BASE_URL) {
      try {
        const response = await agentApiClient.post('/ecommerce-catalog-search/invoke', request);
        const payload = response.data || {};
        const results = (payload.results || payload.items || []) as AcpProduct[];

        const appearsMockPayload = results.some((item) => {
          const title = String(item?.title || '').toLowerCase();
          const imageUrl = String(item?.image_url || '');
          const itemUrl = String((item as { url?: string })?.url || '');
          return (
            title.includes('mock')
            || usesMockHost(imageUrl)
            || usesMockHost(itemUrl)
          );
        });

        if (appearsMockPayload) {
          throw new Error('Agent returned mock payload');
        }

        const mode = payload.mode === 'intelligent' ? 'intelligent' : 'keyword';
        const fallbackKeywords = parseStringArray(payload.fallback_keywords);
        return {
          items: mapAcpProductsToUi(results),
          source: 'agent',
          mode,
          requested_mode: requestedMode,
          trace_id: typeof payload.trace_id === 'string' ? payload.trace_id : undefined,
          intent: (payload.intent as SemanticSearchIntent | undefined) || null,
          subqueries: Array.isArray(payload.subqueries)
            ? payload.subqueries.filter((value: unknown): value is string => typeof value === 'string')
            : [],
          answer_source: typeof payload.answer_source === 'string' ? payload.answer_source : undefined,
          result_type: parseSearchResultType(payload.result_type),
          degraded: payload.degraded === true,
          degraded_reason: parseSearchDegradedReason(payload.degraded_reason),
          degraded_message:
            typeof payload.degraded_message === 'string' ? payload.degraded_message : undefined,
          fallback_keywords: fallbackKeywords.length > 0 ? fallbackKeywords : undefined,
        };
      } catch (error) {
        console.error('Semantic search failed:', error);
        // Fall back to CRUD search
      }
    }

    const fallback = await productService.search(trimmed, request.limit || 20);
    return {
      items: mapApiProductsToUi(fallback),
      source: 'crud',
      mode: 'keyword',
      requested_mode: requestedMode,
      fallback_reason:
        requestedMode === 'intelligent'
          ? AGENT_API_BASE_URL
            ? 'agent_mock'
            : 'agent_unavailable'
          : undefined,
      result_type: 'deterministic',
      degraded: false,
    };
  },
};

export default semanticSearchService;
