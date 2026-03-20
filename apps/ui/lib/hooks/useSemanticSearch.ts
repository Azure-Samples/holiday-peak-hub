/**
 * React Query hook for semantic search.
 */

import { useQuery } from '@tanstack/react-query';
import { semanticSearchService } from '../services/semanticSearchService';

export function useSemanticSearch(
  query: string,
  limit = 20,
  mode: 'auto' | 'keyword' | 'intelligent' = 'auto',
) {
  return useQuery({
    queryKey: ['semantic-search', query, limit, mode],
    queryFn: () => semanticSearchService.searchWithMode(query, mode, limit),
    enabled: query.trim().length > 0,
    staleTime: 60 * 1000,
  });
}
