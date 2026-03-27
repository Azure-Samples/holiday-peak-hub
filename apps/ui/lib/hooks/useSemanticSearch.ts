/**
 * React Query hook for semantic search.
 */

import { useQuery } from '@tanstack/react-query';
import {
  semanticSearchService,
  type SemanticSearchContext,
} from '../services/semanticSearchService';

export function useSemanticSearch(
  query: string,
  limit = 20,
  mode: 'auto' | 'keyword' | 'intelligent' = 'auto',
  context?: SemanticSearchContext,
  enabled?: boolean,
) {
  const historyMarker = context?.query_history?.join('|') || '';
  const stageMarker = context?.search_stage || 'default';
  const sessionMarker = context?.session_id || 'anonymous';

  return useQuery({
    queryKey: ['semantic-search', query, limit, mode, stageMarker, sessionMarker, historyMarker],
    queryFn: () => semanticSearchService.searchWithMode(query, mode, limit, context),
    enabled: enabled ?? query.trim().length > 0,
    staleTime: 60 * 1000,
  });
}
