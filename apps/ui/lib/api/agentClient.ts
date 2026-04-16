/**
 * Agent API Client Configuration
 *
 * Axios client for communicating with agent APIs (APIM or direct service).
 */

import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios';

import { resolveAgentApiClientBaseUrl } from '@/app/api/_shared/base-url-resolver';
import { getCurrentPageSessionId } from '@/lib/hooks/usePageSession';

const AGENT_API_BASE_URL = resolveAgentApiClientBaseUrl().baseUrl || '';

if (!AGENT_API_BASE_URL && typeof window === 'undefined') {
  throw new Error(
    'Agent API base URL is not configured for server-side agent access. Set NEXT_PUBLIC_AGENT_API_URL or AGENT_API_URL.',
  );
}

export const agentApiClient: AxiosInstance = axios.create({
  baseURL: AGENT_API_BASE_URL,
  timeout: 60_000,
  headers: {
    'Content-Type': 'application/json',
  },
});

agentApiClient.interceptors.request.use(
  async (config: InternalAxiosRequestConfig) => {
    const token = typeof window !== 'undefined' ? sessionStorage.getItem('auth_token') : null;

    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    // Attach page-scoped Foundry session ID for thread reuse.
    // The backend uses this to resume the same Foundry conversation
    // while the user stays on the current page route.
    const pageSessionId = getCurrentPageSessionId();
    if (pageSessionId && config.headers) {
      config.headers['x-holiday-peak-session-id'] = pageSessionId;

      // Also inject session_id into POST body payloads so the backend
      // /invoke endpoint receives it in request_payload.
      if (config.method?.toLowerCase() === 'post' && config.data && typeof config.data === 'object') {
        config.data = { ...config.data, session_id: pageSessionId };
      }
    }

    return config;
  },
  (error) => Promise.reject(error)
);

agentApiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    if (error.response?.status === 401 && typeof window !== 'undefined') {
      sessionStorage.removeItem('auth_token');
    }
    return Promise.reject(error);
  }
);

export default agentApiClient;
