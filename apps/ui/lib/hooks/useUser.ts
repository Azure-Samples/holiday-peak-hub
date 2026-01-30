/**
 * React Query Hooks for User Profile
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { userService } from '../services/userService';
import type { UpdateProfileRequest } from '../types/api';

/**
 * Hook to fetch user profile
 */
export function useUserProfile() {
  return useQuery({
    queryKey: ['user', 'profile'],
    queryFn: () => userService.getProfile(),
  });
}

/**
 * Hook to update user profile
 */
export function useUpdateProfile() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: UpdateProfileRequest) => userService.updateProfile(request),
    onSuccess: () => {
      // Invalidate user profile
      queryClient.invalidateQueries({ queryKey: ['user', 'profile'] });
    },
  });
}
