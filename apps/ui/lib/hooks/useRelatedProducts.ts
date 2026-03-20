import { useQuery } from '@tanstack/react-query';
import type { Product as UiProduct } from '@/components/types';
import { mapApiProductToUiProduct } from '../utils/productMappers';
import { productService } from '../services/productService';

export function useRelatedProducts(ids: string[]) {
  const normalizedIds = Array.from(new Set(ids.filter(Boolean)));

  return useQuery({
    queryKey: ['related-products', normalizedIds],
    enabled: normalizedIds.length > 0,
    staleTime: 5 * 60 * 1000,
    queryFn: async () => {
      const productById: Record<string, UiProduct> = {};
      const results = await Promise.allSettled(
        normalizedIds.map(async (id) => {
          const product = await productService.getEnriched(id);
          return { id, product: mapApiProductToUiProduct(product) };
        }),
      );

      for (const result of results) {
        if (result.status === 'fulfilled') {
          productById[result.value.id] = result.value.product;
        }
      }

      return productById;
    },
  });
}

export default useRelatedProducts;
