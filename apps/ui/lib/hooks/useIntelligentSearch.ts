import { useCallback, useEffect, useMemo, useState } from 'react';
import { useSemanticSearch } from './useSemanticSearch';

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
  const [preference, setPreference] = useState<IntelligentSearchPreference>('auto');

  useEffect(() => {
    setPreference(readStoredPreference());
  }, []);

  const requestedMode = preference === 'auto' ? undefined : preference;
  const queryResult = useSemanticSearch(query, limit, requestedMode);

  const resolvedMode = useMemo<'keyword' | 'intelligent'>(() => {
    if (queryResult.data?.mode === 'intelligent') {
      return 'intelligent';
    }

    if (requestedMode === 'intelligent') {
      return 'intelligent';
    }

    return 'keyword';
  }, [queryResult.data?.mode, requestedMode]);

  const updatePreference = useCallback((nextPreference: IntelligentSearchPreference) => {
    setPreference(nextPreference);
    writeStoredPreference(nextPreference);
  }, []);

  return {
    ...queryResult,
    preference,
    setPreference: updatePreference,
    resolvedMode,
    requestedMode,
  };
}

export default useIntelligentSearch;
