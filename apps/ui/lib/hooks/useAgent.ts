/**
 * Generic typed hooks for agent service communication.
 *
 * Provides useAgentQuery (GET) and useAgentMutation (POST) backed by
 * @tanstack/react-query and the shared agentApiClient.
 */

import { useQuery, useMutation, type UseQueryResult, type UseMutationResult } from '@tanstack/react-query';
import { AxiosError } from 'axios';

import { agentApiClient } from '@/lib/api/agentClient';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface AgentError {
  status: number;
  message: string;
  service: string;
  endpoint: string;
}

export interface AgentQueryOptions<TResponse> {
  /** Agent service name (e.g., 'ecommerce-catalog-search') */
  service: string;
  /** Endpoint path (e.g., '/search', '/recommendations') */
  endpoint: string;
  /** Optional query parameters */
  params?: Record<string, string | number | boolean | undefined>;
  /** TanStack Query options overrides */
  enabled?: boolean;
  staleTime?: number;
  refetchInterval?: number | false;
  /** Transform response data */
  select?: (data: TResponse) => TResponse;
}

export interface AgentMutationOptions<TRequest, TResponse> {
  /** Agent service name */
  service: string;
  /** Endpoint path */
  endpoint: string;
  /** Callbacks */
  onSuccess?: (data: TResponse) => void;
  onError?: (error: AgentError) => void;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function buildUrl(service: string, endpoint: string): string {
  if (endpoint.startsWith('/agents/')) {
    return endpoint;
  }
  return `/${service}${endpoint}`;
}

function buildQueryKey(
  service: string,
  endpoint: string,
  params?: Record<string, string | number | boolean | undefined>,
): unknown[] {
  const key: unknown[] = ['agent', service, endpoint];
  if (params) {
    const sorted = Object.entries(params)
      .filter(([, v]) => v !== undefined)
      .sort(([a], [b]) => a.localeCompare(b));
    for (const [k, v] of sorted) {
      key.push(k, v);
    }
  }
  return key;
}

function toAgentError(error: unknown, service: string, endpoint: string): AgentError {
  if (error instanceof AxiosError) {
    return {
      status: error.response?.status ?? 0,
      message:
        (error.response?.data as { detail?: string } | undefined)?.detail ??
        error.message,
      service,
      endpoint,
    };
  }
  return {
    status: 0,
    message: error instanceof Error ? error.message : 'Unknown error',
    service,
    endpoint,
  };
}

// ---------------------------------------------------------------------------
// Hooks
// ---------------------------------------------------------------------------

export function useAgentQuery<TResponse>(
  options: AgentQueryOptions<TResponse>,
): UseQueryResult<TResponse, AgentError> {
  const { service, endpoint, params, enabled, staleTime, refetchInterval, select } = options;
  const url = buildUrl(service, endpoint);

  return useQuery<TResponse, AgentError>({
    queryKey: buildQueryKey(service, endpoint, params),
    queryFn: async () => {
      try {
        const response = await agentApiClient.get<TResponse>(url, {
          params: params as Record<string, string>,
        });
        return response.data;
      } catch (error) {
        throw toAgentError(error, service, endpoint);
      }
    },
    enabled,
    staleTime,
    refetchInterval,
    select,
  });
}

export function useAgentMutation<TRequest, TResponse>(
  options: AgentMutationOptions<TRequest, TResponse>,
): UseMutationResult<TResponse, AgentError, TRequest> {
  const { service, endpoint, onSuccess, onError } = options;
  const url = buildUrl(service, endpoint);

  return useMutation<TResponse, AgentError, TRequest>({
    mutationFn: async (payload: TRequest) => {
      try {
        const response = await agentApiClient.post<TResponse>(url, payload);
        return response.data;
      } catch (error) {
        throw toAgentError(error, service, endpoint);
      }
    },
    onSuccess,
    onError,
  });
}
