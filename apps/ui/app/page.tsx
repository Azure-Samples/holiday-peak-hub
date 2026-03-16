'use client';

import React from 'react';
import { MainLayout } from '@/components/templates/MainLayout';
import { ProductGraphCanvas } from '@/components/organisms/ProductGraphCanvas';
import { useCategories } from '@/lib/hooks/useCategories';
import { useProducts } from '@/lib/hooks/useProducts';
import { mapApiProductsToUi } from '@/lib/utils/productMappers';

export default function HomePage() {
  useCategories();
  const { data: products = [] } = useProducts({ limit: 100 });

  const featuredProducts = mapApiProductsToUi(products);

  return (
    <MainLayout fullWidth>
      <section className="h-[calc(100dvh-3.5rem)]">
        <ProductGraphCanvas
          products={featuredProducts}
          ariaLabel="Homepage draggable product graph"
        />
      </section>
    </MainLayout>
  );
}