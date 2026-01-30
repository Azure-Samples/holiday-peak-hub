/**
 * Authentication Service
 * 
 * API functions for authentication operations
 */

import apiClient, { handleApiError } from '../api/client';
import API_ENDPOINTS from '../api/endpoints';
import type { User } from '../types/api';

export const authService = {
  /**
   * Get current user profile from token
   */
  async getCurrentUser(): Promise<User> {
    try {
      const response = await apiClient.get<User>(API_ENDPOINTS.auth.me);
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  /**
   * Logout user
   */
  async logout(): Promise<{ message: string }> {
    try {
      const response = await apiClient.post<{ message: string }>(
        API_ENDPOINTS.auth.logout
      );
      
      // Clear token from session storage
      if (typeof window !== 'undefined') {
        sessionStorage.removeItem('auth_token');
      }
      
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  /**
   * Set authentication token
   */
  setToken(token: string): void {
    if (typeof window !== 'undefined') {
      sessionStorage.setItem('auth_token', token);
    }
  },

  /**
   * Get authentication token
   */
  getToken(): string | null {
    if (typeof window !== 'undefined') {
      return sessionStorage.getItem('auth_token');
    }
    return null;
  },

  /**
   * Clear authentication token
   */
  clearToken(): void {
    if (typeof window !== 'undefined') {
      sessionStorage.removeItem('auth_token');
    }
  },
};

export default authService;
