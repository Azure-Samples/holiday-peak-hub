/**
 * React Query hook for semantic search.
 */

import { useQuery } from '@tanstack/react-query';
import { semanticSearchService } from '../services/semanticSearchService';

export function useSemanticSearch(query: string, limit = 20) {
  return useQuery({
    queryKey: ['semantic-search', query, limit],
    queryFn: () => semanticSearchService.search({ query, limit }),
    enabled: query.trim().length > 0,
    staleTime: 60 * 1000,
  });
}
