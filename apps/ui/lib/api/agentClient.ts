/**
 * Agent API Client Configuration
 *
 * Axios client for communicating with agent APIs (APIM or direct service).
 */

import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios';

const IS_TEST_ENV = process.env.NODE_ENV === 'test';
const SERVER_CRUD_API_BASE_URL = process.env.NEXT_PUBLIC_CRUD_API_URL || '';
const AGENT_API_BASE_URL = IS_TEST_ENV
  ? `${SERVER_CRUD_API_BASE_URL.replace(/\/$/, '')}/agents`
  : typeof window !== 'undefined'
    ? '/agent-api'
    : process.env.NEXT_PUBLIC_AGENT_API_URL || `${SERVER_CRUD_API_BASE_URL.replace(/\/$/, '')}/agents`;

if (!AGENT_API_BASE_URL && typeof window === 'undefined') {
  throw new Error('NEXT_PUBLIC_AGENT_API_URL or NEXT_PUBLIC_CRUD_API_URL must be set to a cloud backend URL.');
}

export const agentApiClient: AxiosInstance = axios.create({
  baseURL: AGENT_API_BASE_URL,
  timeout: 5000,
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
