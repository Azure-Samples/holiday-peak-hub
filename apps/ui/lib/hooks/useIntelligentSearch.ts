import { useCallback, useEffect, useMemo, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useSemanticSearch } from './useSemanticSearch';
import { productService } from '../services/productService';

export type IntelligentSearchPreference = 'auto' | 'keyword' | 'intelligent';

const SEARCH_MODE_STORAGE_KEY = 'hp.search.mode.preference';

function isValidPreference(value: string | null): value is IntelligentSearchPreference {
  return value === 'auto' || value === 'keyword' || value === 'intelligent';
}

function readStoredPreference(): IntelligentSearchPreference {
  if (typeof window === 'undefined') {
    return 'auto';
  }

  try {
    const rawValue = window.localStorage.getItem(SEARCH_MODE_STORAGE_KEY);
    return isValidPreference(rawValue) ? rawValue : 'auto';
  } catch {
    return 'auto';
  }
}

function writeStoredPreference(value: IntelligentSearchPreference): void {
  if (typeof window === 'undefined') {
    return;
  }

  try {
    window.localStorage.setItem(SEARCH_MODE_STORAGE_KEY, value);
  } catch {
    // localStorage may be unavailable in restricted environments.
  }
}

export function useIntelligentSearch(query: string, limit = 20) {
  const queryClient = useQueryClient();
  const [preference, setPreference] = useState<IntelligentSearchPreference>('auto');
  const [debouncedQuery, setDebouncedQuery] = useState(query);

  useEffect(() => {
    const debounceId = window.setTimeout(() => {
      setDebouncedQuery(query);
    }, 300);

    return () => {
      window.clearTimeout(debounceId);
    };
  }, [query]);

  useEffect(() => {
    setPreference(readStoredPreference());
  }, []);

  const queryResult = useSemanticSearch(debouncedQuery, limit, preference);

  const relatedProductIds = useMemo(() => {
    const ids = new Set<string>();
    for (const item of queryResult.data?.items || []) {
      for (const relatedId of item.complementaryProducts || []) {
        ids.add(relatedId);
      }
      for (const relatedId of item.substituteProducts || []) {
        ids.add(relatedId);
      }
    }
    return Array.from(ids);
  }, [queryResult.data?.items]);

  useEffect(() => {
    for (const relatedId of relatedProductIds) {
      void queryClient.prefetchQuery({
        queryKey: ['related-product-preview', relatedId],
        queryFn: () => productService.getEnriched(relatedId),
        staleTime: 5 * 60 * 1000,
      });
    }
  }, [queryClient, relatedProductIds]);

  const resolvedMode = useMemo<'keyword' | 'intelligent'>(() => {
    if (queryResult.data?.mode === 'intelligent') {
      return 'intelligent';
    }

    if (preference === 'intelligent') {
      return 'intelligent';
    }

    return 'keyword';
  }, [queryResult.data?.mode, preference]);

  const updatePreference = useCallback((nextPreference: IntelligentSearchPreference) => {
    setPreference(nextPreference);
    writeStoredPreference(nextPreference);
  }, []);

  return {
    ...queryResult,
    preference,
    setPreference: updatePreference,
    resolvedMode,
    debouncedQuery,
  };
}

export default useIntelligentSearch;
