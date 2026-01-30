/**
 * User Service
 * 
 * API functions for user profile operations
 */

import apiClient, { handleApiError } from '../api/client';
import API_ENDPOINTS from '../api/endpoints';
import type { UserProfile, UpdateProfileRequest } from '../types/api';

export const userService = {
  /**
   * Get full user profile from database
   */
  async getProfile(): Promise<UserProfile> {
    try {
      const response = await apiClient.get<UserProfile>(API_ENDPOINTS.users.me);
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  /**
   * Update user profile
   */
  async updateProfile(request: UpdateProfileRequest): Promise<UserProfile> {
    try {
      const response = await apiClient.patch<UserProfile>(
        API_ENDPOINTS.users.update,
        request
      );
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  },
};

export default userService;
