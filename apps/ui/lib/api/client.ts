/**
 * API Client Configuration
 * 
 * Axios client with base URL, interceptors, and error handling
 * for communicating with the CRUD service backend.
 */

import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios';

const IS_TEST_ENV = process.env.NODE_ENV === 'test';
const SERVER_BASE_URL_ENV_KEYS = [
  'NEXT_PUBLIC_CRUD_API_URL',
  'NEXT_PUBLIC_API_URL',
  'NEXT_PUBLIC_API_BASE_URL',
  'CRUD_API_URL',
] as const;

type ServerApiBaseUrlResolution = {
  baseUrl: string | null;
  sourceKey: (typeof SERVER_BASE_URL_ENV_KEYS)[number] | null;
};

function normalizeServerApiBaseUrl(candidate: string | undefined): string | null {
  if (!candidate) {
    return null;
  }

  const trimmed = candidate.trim();
  if (!trimmed) {
    return null;
  }

  return trimmed.replace(/\/+$/, '');
}

// Strategy pattern: resolve first configured API base URL alias in documented priority order.
export function resolveServerCrudApiBaseUrl(env: NodeJS.ProcessEnv = process.env): ServerApiBaseUrlResolution {
  for (const key of SERVER_BASE_URL_ENV_KEYS) {
    const resolved = normalizeServerApiBaseUrl(env[key]);
    if (resolved) {
      return {
        baseUrl: resolved,
        sourceKey: key,
      };
    }
  }

  return {
    baseUrl: null,
    sourceKey: null,
  };
}

const SERVER_CRUD_API_BASE_URL = resolveServerCrudApiBaseUrl().baseUrl;
const CRUD_API_BASE_URL = IS_TEST_ENV
  ? 'http://localhost:8000'
  : typeof window !== 'undefined'
    ? ''
    : SERVER_CRUD_API_BASE_URL;

if (!CRUD_API_BASE_URL && typeof window === 'undefined') {
  throw new Error(
    'CRUD API base URL is not configured. Set one of NEXT_PUBLIC_CRUD_API_URL, NEXT_PUBLIC_API_URL, NEXT_PUBLIC_API_BASE_URL, or CRUD_API_URL.',
  );
}

/**
 * Create axios instance with default configuration
 */
export const apiClient: AxiosInstance = axios.create({
  baseURL: CRUD_API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Request interceptor - attach auth token
 */
apiClient.interceptors.request.use(
  async (config: InternalAxiosRequestConfig) => {
    // Get token from session storage (will be set by AuthContext)
    const token = typeof window !== 'undefined' ? sessionStorage.getItem('auth_token') : null;
    
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

/**
 * Response interceptor - handle errors globally
 */
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    // Handle 401 Unauthorized
    if (error.response?.status === 401 && typeof window !== 'undefined') {
      sessionStorage.removeItem('auth_token');
    }

    // Handle 403 Forbidden
    if (error.response?.status === 403) {
      console.error('Access denied:', error.response.data);
    }

    // Handle 429 Too Many Requests
    if (error.response?.status === 429) {
      console.warn('Rate limit exceeded. Please try again later.');
    }

    return Promise.reject(error);
  }
);

/**
 * API Error class for consistent error handling
 */
export class ApiError extends Error {
  constructor(
    public status: number,
    public message: string,
    public details?: any
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

function extractErrorMessage(details: unknown): string | null {
  const extractString = (value: unknown, depth = 0): string | null => {
    if (depth > 4 || value === null || value === undefined) {
      return null;
    }

    if (typeof value === 'string') {
      const normalized = value.trim();
      return normalized.length > 0 ? normalized : null;
    }

    if (Array.isArray(value)) {
      for (const entry of value) {
        const extracted = extractString(entry, depth + 1);
        if (extracted) {
          return extracted;
        }
      }
      return null;
    }

    if (typeof value === 'object') {
      const record = value as Record<string, unknown>;
      const preferredKeys = ['detail', 'error', 'message', 'title', 'msg'];

      for (const key of preferredKeys) {
        const extracted = extractString(record[key], depth + 1);
        if (extracted) {
          return extracted;
        }
      }
    }

    return null;
  };

  return extractString(details);
}

/**
 * Handle API errors and convert to ApiError
 */
export const handleApiError = (error: unknown): ApiError => {
  if (axios.isAxiosError(error)) {
    const status = error.response?.status || 500;
    const details = error.response?.data;
    const message = extractErrorMessage(details) || error.message || 'Request failed';
    
    return new ApiError(status, message, details);
  }
  
  return new ApiError(500, 'An unexpected error occurred');
};

export default apiClient;
