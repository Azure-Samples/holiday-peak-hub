'use client';

import React from 'react';
import { Button } from '@/components/atoms/Button';
import { MainLayout } from '@/components/templates/MainLayout';
import { ProductGraphCanvas } from '@/components/organisms/ProductGraphCanvas';
import { useCategories } from '@/lib/hooks/useCategories';
import { useProducts } from '@/lib/hooks/useProducts';
import { mapApiProductsToUi } from '@/lib/utils/productMappers';

export default function HomePage() {
  useCategories();
  const {
    data: products = [],
    isLoading,
    isError,
    refetch,
    isFetching,
  } = useProducts({ limit: 100 });

  const featuredProducts = mapApiProductsToUi(products);
  const hasProducts = featuredProducts.length > 0;

  return (
    <MainLayout fullWidth>
      <section className="h-[calc(100dvh-3.5rem)]">
        {isLoading && (
          <div className="flex h-full items-center justify-center">
            <p className="text-gray-600 dark:text-gray-400">Loading products...</p>
          </div>
        )}

        {!isLoading && isError && (
          <div className="flex h-full items-center justify-center px-6">
            <div role="alert" className="text-center space-y-4">
              <p className="text-red-600 dark:text-red-400">
                Products are temporarily unavailable.
              </p>
              <Button
                variant="secondary"
                size="sm"
                loading={isFetching}
                onClick={() => {
                  void refetch();
                }}
              >
                Retry products
              </Button>
            </div>
          </div>
        )}

        {!isLoading && !isError && !hasProducts && (
          <div className="flex h-full items-center justify-center">
            <p className="text-gray-600 dark:text-gray-400">No products available right now.</p>
          </div>
        )}

        {!isLoading && !isError && hasProducts && (
          <ProductGraphCanvas
            products={featuredProducts}
            ariaLabel="Homepage draggable product graph"
          />
        )}
      </section>
    </MainLayout>
  );
}