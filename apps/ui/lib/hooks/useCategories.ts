import { useQuery } from '@tanstack/react-query';
import { ApiError } from '../api/client';
import { categoryService } from '../services/categoryService';

const CATALOG_QUERY_STALE_TIME_MS = 5 * 60 * 1000;

function shouldRetryCatalogReadQuery(failureCount: number, error: unknown): boolean {
  if (!(error instanceof ApiError)) {
    return false;
  }

  return failureCount < 1 && error.status >= 500 && error.status < 600;
}

export function useCategories(parentId?: string) {
  return useQuery({
    queryKey: ['categories', parentId || 'root'],
    queryFn: () => categoryService.list(parentId),
    retry: shouldRetryCatalogReadQuery,
    retryOnMount: false,
    refetchOnReconnect: false,
    staleTime: CATALOG_QUERY_STALE_TIME_MS,
  });
}

export function useCategory(id?: string) {
  return useQuery({
    queryKey: ['category', id],
    queryFn: () => categoryService.get(id || ''),
    enabled: !!id,
  });
}