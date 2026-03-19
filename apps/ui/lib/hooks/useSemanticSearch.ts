/**
 * React Query hook for semantic search.
 */

import { useQuery } from '@tanstack/react-query';
import { semanticSearchService } from '../services/semanticSearchService';

export function useSemanticSearch(query: string, limit = 20, mode?: 'keyword' | 'intelligent') {
  return useQuery({
    queryKey: ['semantic-search', query, limit, mode],
    queryFn: () => semanticSearchService.search({ query, limit, mode }),
    enabled: query.trim().length > 0,
    staleTime: 60 * 1000,
  });
}
