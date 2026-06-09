/**
 * React hook for streaming semantic search via Server-Sent Events.
 *
 * Provides progressive rendering: products arrive first, then model-answer
 * text chunks stream in token-by-token.
 */

import { useCallback, useRef, useState } from 'react';
import {
  semanticSearchService,
  type SemanticSearchRequest,
  type SemanticSearchResponse,
  type StreamingSearchCallbacks,
} from '../services/semanticSearchService';

export interface StreamingSearchState {
  /** Deterministic product results (available early). */
  results: SemanticSearchResponse | null;
  /** Accumulated model answer text (grows as tokens arrive). */
  answerText: string;
  /** Whether the stream is currently in progress. */
  isStreaming: boolean;
  /** Error, if any. */
  error: unknown | null;
}

export function useStreamingSearch() {
  const [state, setState] = useState<StreamingSearchState>({
    results: null,
    answerText: '',
    isStreaming: false,
    error: null,
  });

  const abortRef = useRef<AbortController | null>(null);

  const search = useCallback((request: SemanticSearchRequest) => {
    // Cancel any in-flight stream
    abortRef.current?.abort();

    setState({ results: null, answerText: '', isStreaming: true, error: null });

    const callbacks: StreamingSearchCallbacks = {
      onResults: (response) => {
        setState((prev) => ({ ...prev, results: response }));
      },
      onToken: (text) => {
        setState((prev) => ({ ...prev, answerText: prev.answerText + text }));
      },
      onDone: () => {
        setState((prev) => ({ ...prev, isStreaming: false }));
      },
      onError: (error) => {
        setState((prev) => ({ ...prev, error, isStreaming: false }));
      },
    };

    abortRef.current = semanticSearchService.searchStream(request, callbacks);
  }, []);

  const cancel = useCallback(() => {
    abortRef.current?.abort();
    setState((prev) => ({ ...prev, isStreaming: false }));
  }, []);

  return { ...state, search, cancel };
}
