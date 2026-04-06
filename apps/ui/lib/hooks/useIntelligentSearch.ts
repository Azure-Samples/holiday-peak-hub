import { useCallback, useEffect, useMemo, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useSemanticSearch } from './useSemanticSearch';
import { productService } from '../services/productService';
import type { SemanticSearchContext } from '../services/semanticSearchService';

export type IntelligentSearchPreference = 'auto' | 'keyword' | 'intelligent';
export type IntelligentSearchStage = 'baseline' | 'rerank';

export interface IntelligentSearchOptions {
  userId?: string;
  tenantId?: string;
  enableTwoStage?: boolean;
}

const DEFAULT_SEARCH_PREFERENCE: IntelligentSearchPreference = 'intelligent';
const SEARCH_MODE_STORAGE_KEY = 'hp.search.mode.preference';
const SEARCH_QUERY_HISTORY_STORAGE_PREFIX = 'hp.search.query.history';
const SEARCH_SESSION_STORAGE_PREFIX = 'hp.search.session';
const MAX_QUERY_HISTORY_ENTRIES = 8;

function isValidPreference(value: string | null): value is IntelligentSearchPreference {
  return value === 'auto' || value === 'keyword' || value === 'intelligent';
}

function readStoredPreference(): IntelligentSearchPreference {
  if (typeof window === 'undefined') {
    return DEFAULT_SEARCH_PREFERENCE;
  }

  try {
    const rawValue = window.localStorage.getItem(SEARCH_MODE_STORAGE_KEY);
    return isValidPreference(rawValue) ? rawValue : DEFAULT_SEARCH_PREFERENCE;
  } catch {
    return DEFAULT_SEARCH_PREFERENCE;
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

function resolveUserScopeKey(userId?: string): string {
  const trimmed = userId?.trim();
  return trimmed && trimmed.length > 0 ? trimmed : 'anonymous';
}

function buildQueryHistoryStorageKey(scope: string): string {
  return `${SEARCH_QUERY_HISTORY_STORAGE_PREFIX}.${scope}`;
}

function buildSessionStorageKey(scope: string): string {
  return `${SEARCH_SESSION_STORAGE_PREFIX}.${scope}`;
}

function generateSecureHex(byteLength: number): string {
  if (typeof crypto !== 'undefined' && typeof crypto.getRandomValues === 'function') {
    const randomBytes = new Uint8Array(byteLength);
    crypto.getRandomValues(randomBytes);
    return Array.from(randomBytes, (value) => value.toString(16).padStart(2, '0')).join('');
  }

  return Date.now().toString(16);
}

function generateSessionId(scope: string): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }

  return `${scope}-${Date.now()}-${generateSecureHex(4)}`;
}

function readQueryHistory(scope: string): string[] {
  if (typeof window === 'undefined') {
    return [];
  }

  try {
    const rawValue = window.localStorage.getItem(buildQueryHistoryStorageKey(scope));
    if (!rawValue) {
      return [];
    }

    const parsed = JSON.parse(rawValue);
    if (!Array.isArray(parsed)) {
      return [];
    }

    return parsed
      .filter((value): value is string => typeof value === 'string')
      .map((value) => value.trim())
      .filter((value) => value.length > 0)
      .slice(-MAX_QUERY_HISTORY_ENTRIES);
  } catch {
    return [];
  }
}

function writeQueryHistory(scope: string, history: string[]): void {
  if (typeof window === 'undefined') {
    return;
  }

  try {
    window.localStorage.setItem(buildQueryHistoryStorageKey(scope), JSON.stringify(history));
  } catch {
    // localStorage may be unavailable in restricted environments.
  }
}

function appendQueryHistory(scope: string, query: string): string[] {
  const normalizedQuery = query.trim();
  if (!normalizedQuery) {
    return readQueryHistory(scope);
  }

  const previousHistory = readQueryHistory(scope);
  const deduplicatedHistory = previousHistory.filter((entry) => entry !== normalizedQuery);
  const nextHistory = [...deduplicatedHistory, normalizedQuery].slice(-MAX_QUERY_HISTORY_ENTRIES);

  writeQueryHistory(scope, nextHistory);
  return nextHistory;
}

function readOrCreateSessionId(scope: string): string {
  if (typeof window === 'undefined') {
    return generateSessionId(scope);
  }

  const storageKey = buildSessionStorageKey(scope);

  try {
    const existing = window.sessionStorage.getItem(storageKey);
    if (existing && existing.trim().length > 0) {
      return existing;
    }

    const created = generateSessionId(scope);
    window.sessionStorage.setItem(storageKey, created);
    return created;
  } catch {
    return generateSessionId(scope);
  }
}

export function useIntelligentSearch(query: string, limit = 20, options: IntelligentSearchOptions = {}) {
  const queryClient = useQueryClient();
  const [preference, setPreference] = useState<IntelligentSearchPreference>(() => readStoredPreference());
  const [debouncedQuery, setDebouncedQuery] = useState(query);
  const scopeKey = useMemo(() => resolveUserScopeKey(options.userId), [options.userId]);
  const [sessionId, setSessionId] = useState(() => readOrCreateSessionId(scopeKey));
  const [queryHistory, setQueryHistory] = useState<string[]>(() => readQueryHistory(scopeKey));
  const shouldUseTwoStage = options.enableTwoStage ?? true;

  useEffect(() => {
    const debounceId = window.setTimeout(() => {
      setDebouncedQuery(query);
    }, 300);

    return () => {
      window.clearTimeout(debounceId);
    };
  }, [query]);

  useEffect(() => {
    setSessionId(readOrCreateSessionId(scopeKey));
    setQueryHistory(readQueryHistory(scopeKey));
  }, [scopeKey]);

  useEffect(() => {
    const trimmed = debouncedQuery.trim();
    if (!trimmed) {
      return;
    }

    setQueryHistory(appendQueryHistory(scopeKey, trimmed));
  }, [debouncedQuery, scopeKey]);

  const trimmedDebouncedQuery = debouncedQuery.trim();
  const hasQuery = trimmedDebouncedQuery.length > 0;

  const baselineContext = useMemo<SemanticSearchContext>(
    () => ({
      user_id: options.userId,
      tenant_id: options.tenantId,
      session_id: sessionId,
      query_history: queryHistory,
      search_stage: 'baseline',
      correlation_id: hasQuery ? `${sessionId}:baseline:${trimmedDebouncedQuery}` : undefined,
    }),
    [options.userId, options.tenantId, sessionId, queryHistory, hasQuery, trimmedDebouncedQuery],
  );

  const baselineMode: IntelligentSearchPreference = useMemo(() => {
    if (preference === 'auto') {
      return shouldUseTwoStage ? 'keyword' : 'intelligent';
    }

    return preference;
  }, [preference, shouldUseTwoStage]);
  const baselineQuery = useSemanticSearch(
    debouncedQuery,
    limit,
    baselineMode,
    baselineContext,
    hasQuery,
  );
  const baselineData = baselineQuery.data;

  const baselineCandidateSkus = useMemo(
    () => (baselineData?.items || []).map((item) => item.sku),
    [baselineData?.items],
  );

  const shouldAttemptRerank = preference === 'auto';
  const rerankEnabled = Boolean(
    shouldUseTwoStage
      && hasQuery
      && shouldAttemptRerank
      && baselineCandidateSkus.length > 0,
  );

  const rerankContext = useMemo<SemanticSearchContext>(
    () => ({
      user_id: options.userId,
      tenant_id: options.tenantId,
      session_id: sessionId,
      query_history: queryHistory,
      search_stage: 'rerank',
      baseline_candidate_skus: baselineCandidateSkus,
      correlation_id: hasQuery ? `${sessionId}:rerank:${trimmedDebouncedQuery}` : undefined,
    }),
    [
      options.userId,
      options.tenantId,
      sessionId,
      queryHistory,
      baselineCandidateSkus,
      hasQuery,
      trimmedDebouncedQuery,
    ],
  );

  const rerankQuery = useSemanticSearch(
    debouncedQuery,
    limit,
    'intelligent',
    rerankContext,
    rerankEnabled,
  );
  const rerankedData = shouldUseTwoStage ? rerankQuery.data : undefined;

  const isReranking = rerankEnabled && !rerankedData && (rerankQuery.isLoading || rerankQuery.isFetching);

  const searchStage = useMemo<IntelligentSearchStage>(
    () => (shouldUseTwoStage && shouldAttemptRerank && rerankedData ? 'rerank' : 'baseline'),
    [shouldUseTwoStage, shouldAttemptRerank, rerankedData],
  );

  const displayedData = searchStage === 'rerank' ? rerankedData : baselineData;

  const relatedProductIds = useMemo(() => {
    const ids = new Set<string>();
    for (const item of displayedData?.items || []) {
      for (const relatedId of item.complementaryProducts || []) {
        ids.add(relatedId);
      }
      for (const relatedId of item.substituteProducts || []) {
        ids.add(relatedId);
      }
    }
    return Array.from(ids);
  }, [displayedData?.items]);

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
    if (displayedData?.mode === 'intelligent') {
      return 'intelligent';
    }

    return 'keyword';
  }, [displayedData?.mode]);

  const refetch = useCallback(async () => {
    await baselineQuery.refetch();

    if (rerankEnabled) {
      await rerankQuery.refetch();
    }
  }, [baselineQuery, rerankEnabled, rerankQuery]);

  const updatePreference = useCallback((nextPreference: IntelligentSearchPreference) => {
    setPreference(nextPreference);
    writeStoredPreference(nextPreference);
  }, []);

  return {
    ...baselineQuery,
    data: displayedData,
    error: baselineQuery.error,
    isLoading: baselineQuery.isLoading,
    isFetching: baselineQuery.isFetching || isReranking,
    refetch,
    preference,
    setPreference: updatePreference,
    resolvedMode,
    debouncedQuery,
    baselineData,
    rerankedData,
    isReranking,
    searchStage,
    sessionId,
  };
}

export default useIntelligentSearch;
