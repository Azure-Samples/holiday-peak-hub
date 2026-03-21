'use client';

import React from 'react';
import dynamic from 'next/dynamic';
import { MainLayout } from '@/components/templates/MainLayout';
import { useCategories } from '@/lib/hooks/useCategories';
import { useProducts } from '@/lib/hooks/useProducts';
import { mapApiProductsToUi } from '@/lib/utils/productMappers';

const ProductGraphCanvas = dynamic(
  () => import('@/components/organisms/ProductGraphCanvas').then((module) => module.ProductGraphCanvas),
  {
    ssr: false,
    loading: () => <div className="h-[calc(100dvh-3.5rem)] animate-pulse bg-[var(--hp-surface-strong)]" />,
  },
);

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