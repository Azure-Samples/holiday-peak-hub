/**
 * API Client Configuration
 * 
 * Axios client with base URL, interceptors, and error handling
 * for communicating with the CRUD service backend.
 */

import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios';
import {
  resolveCrudApiBaseUrl,
  resolveCrudApiClientBaseUrl,
} from '@/app/api/_shared/base-url-resolver';

export const resolveServerCrudApiBaseUrl = resolveCrudApiBaseUrl;

const CRUD_API_BASE_URL = resolveCrudApiClientBaseUrl().baseUrl || '';

const DEV_MOCK_AUTH_HEADER_PREFIX = 'X-Dev-Auth-';
const DEV_MOCK_AUTH_ENABLED =
  process.env.NODE_ENV !== 'production' && process.env.NEXT_PUBLIC_DEV_AUTH_MOCK === 'true';
const MOCK_AUTH_USER_STORAGE_KEY = 'mock_auth_user';

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

type MockAuthUser = {
  user_id?: string;
  email?: string;
  name?: string;
  roles?: string[];
};

function readMockAuthUserFromStorage(): MockAuthUser | null {
  if (!DEV_MOCK_AUTH_ENABLED || typeof window === 'undefined') {
    return null;
  }

  const raw = localStorage.getItem(MOCK_AUTH_USER_STORAGE_KEY);
  if (!raw) {
    return null;
  }

  try {
    return JSON.parse(raw) as MockAuthUser;
  } catch {
    return null;
  }
}

function appendDevMockAuthHeaders(config: InternalAxiosRequestConfig): void {
  if (!config.headers) {
    return;
  }

  const mockUser = readMockAuthUserFromStorage();
  const roles = Array.isArray(mockUser?.roles) ? mockUser?.roles : [];

  if (!mockUser || roles.length === 0) {
    return;
  }

  config.headers[`${DEV_MOCK_AUTH_HEADER_PREFIX}Mock`] = 'true';
  config.headers[`${DEV_MOCK_AUTH_HEADER_PREFIX}Roles`] = roles.join(',');

  if (typeof mockUser.user_id === 'string' && mockUser.user_id.trim().length > 0) {
    config.headers[`${DEV_MOCK_AUTH_HEADER_PREFIX}User-Id`] = mockUser.user_id;
  }

  if (typeof mockUser.email === 'string' && mockUser.email.trim().length > 0) {
    config.headers[`${DEV_MOCK_AUTH_HEADER_PREFIX}Email`] = mockUser.email;
  }

  if (typeof mockUser.name === 'string' && mockUser.name.trim().length > 0) {
    config.headers[`${DEV_MOCK_AUTH_HEADER_PREFIX}Name`] = mockUser.name;
  }
}

/**
 * Request interceptor - attach auth token
 */
apiClient.interceptors.request.use(
  async (config: InternalAxiosRequestConfig) => {
    // Get token from session storage (will be set by AuthContext)
    const token = typeof window !== 'undefined' ? sessionStorage.getItem('auth_token') : null;
    
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    } else {
      appendDevMockAuthHeaders(config);
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
    public details?: unknown
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
