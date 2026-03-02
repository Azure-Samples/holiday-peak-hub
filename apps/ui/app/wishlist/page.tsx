'use client';

import Link from 'next/link';
import { MainLayout } from '@/components/templates/MainLayout';
import { Card } from '@/components/molecules/Card';
import { ProductGrid } from '@/components/organisms/ProductGrid';
import { useProducts } from '@/lib/hooks/useProducts';
import { mapApiProductsToUi } from '@/lib/utils/productMappers';

export default function WishlistPage() {
  const { data: products = [], isLoading } = useProducts({ limit: 8 });
  const items = mapApiProductsToUi(products);

  return (
    <MainLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Wishlist</h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">Suggested products from the live catalog.</p>
        </div>

        <Card className="p-4 text-sm text-gray-600 dark:text-gray-400">
          Persistent wishlist storage is not yet available in CRUD. This page shows curated products you can inspect and add to cart.
          <span className="ml-1">
            <Link href="/shop" className="text-ocean-500 dark:text-ocean-300 hover:underline">Open full catalog</Link>
          </span>
        </Card>

        <ProductGrid products={items} loading={isLoading} showSort={false} />
      </div>
    </MainLayout>
  );
}
