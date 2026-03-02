import { useQuery } from '@tanstack/react-query';
import { categoryService } from '../services/categoryService';

export function useCategories(parentId?: string) {
  return useQuery({
    queryKey: ['categories', parentId || 'root'],
    queryFn: () => categoryService.list(parentId),
  });
}

export function useCategory(id?: string) {
  return useQuery({
    queryKey: ['category', id],
    queryFn: () => categoryService.get(id || ''),
    enabled: !!id,
  });
}