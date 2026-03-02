/**
 * API Client Configuration
 * 
 * Axios client with base URL, interceptors, and error handling
 * for communicating with the CRUD service backend.
 */

import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios';

const IS_TEST_ENV = process.env.NODE_ENV === 'test';
const SERVER_CRUD_API_BASE_URL = process.env.NEXT_PUBLIC_CRUD_API_URL;
const CRUD_API_BASE_URL = IS_TEST_ENV
  ? 'http://localhost:8000'
  : typeof window !== 'undefined'
    ? ''
    : SERVER_CRUD_API_BASE_URL;

if (!CRUD_API_BASE_URL && typeof window === 'undefined') {
  throw new Error('NEXT_PUBLIC_CRUD_API_URL must be set to the cloud CRUD gateway URL.');
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

/**
 * Handle API errors and convert to ApiError
 */
export const handleApiError = (error: unknown): ApiError => {
  if (axios.isAxiosError(error)) {
    const status = error.response?.status || 500;
    const message = error.response?.data?.detail || error.message;
    const details = error.response?.data;
    
    return new ApiError(status, message, details);
  }
  
  return new ApiError(500, 'An unexpected error occurred');
};

export default apiClient;
