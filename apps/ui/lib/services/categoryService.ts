import apiClient, { handleApiError } from '../api/client';
import API_ENDPOINTS from '../api/endpoints';
import type { Category } from '../types/api';
import { MOCK_CATEGORIES } from '../data/mockData';

const FALLBACK_CATEGORIES: Category[] = MOCK_CATEGORIES;

export const categoryService = {
  async list(parentId?: string): Promise<Category[]> {
    try {
      const url = parentId
        ? `${API_ENDPOINTS.categories.list}?parent_id=${encodeURIComponent(parentId)}`
        : API_ENDPOINTS.categories.list;
      const response = await apiClient.get<Category[]>(url);
      return response.data;
    } catch (error) {
      const status = (error as { response?: { status?: number } })?.response?.status;
      if (status === 401 || (status !== undefined && status >= 500)) {
        return FALLBACK_CATEGORIES;
      }
      throw handleApiError(error);
    }
  },

  async get(id: string): Promise<Category> {
    try {
      const response = await apiClient.get<Category>(API_ENDPOINTS.categories.get(id));
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  },
};

export default categoryService;