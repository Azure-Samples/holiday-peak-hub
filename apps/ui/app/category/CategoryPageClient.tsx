'use client';

import React, { useMemo, useState } from 'react';
import Link from 'next/link';
import { MainLayout } from '@/components/templates/MainLayout';
import { ProductGrid } from '@/components/organisms/ProductGrid';
import { Badge } from '@/components/atoms/Badge';
import { Select } from '@/components/atoms/Select';
import { useCategories } from '@/lib/hooks/useCategories';
import { useProducts } from '@/lib/hooks/useProducts';
import { mapApiProductsToUi } from '@/lib/utils/productMappers';
import type { Product as UiProduct } from '@/components/types';

type SortKey = 'popular' | 'price-low' | 'price-high' | 'rating' | 'name';

export function CategoryPageClient({ slug }: { slug: string }) {
  const [sortBy, setSortBy] = useState<SortKey>('popular');

  const { data: categories = [] } = useCategories();
  const activeCategoryName =
    slug === 'all'
      ? 'All Products'
      : categories.find((category) => category.id === slug)?.name || slug;

  const {
    data: categoryProducts,
    isLoading,
    isError,
  } = useProducts({
    category: slug === 'all' ? undefined : slug,
    limit: 60,
  });

  const products = mapApiProductsToUi(categoryProducts || []);

  const sortedProducts = useMemo(() => {
    const copy = [...products];
    switch (sortBy) {
      case 'price-low':
        return copy.sort((left, right) => left.price - right.price);
      case 'price-high':
        return copy.sort((left, right) => right.price - left.price);
      case 'rating':
        return copy.sort((left, right) => (right.rating || 0) - (left.rating || 0));
      case 'name':
        return copy.sort((left, right) => left.name.localeCompare(right.name));
      default:
        return copy;
    }
  }, [products, sortBy]);

  const uiProducts = sortedProducts as UiProduct[];

  return (
    <MainLayout>
      <div className="mb-6 flex flex-wrap items-center gap-2">
        <Link
          href="/categories"
          className="text-sm text-ocean-500 dark:text-ocean-300 hover:underline"
        >
          Categories
        </Link>
        <span className="text-gray-400">/</span>
        <span className="text-sm text-gray-700 dark:text-gray-300">{activeCategoryName}</span>
      </div>

      <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">{activeCategoryName}</h1>
          <p className="text-gray-600 dark:text-gray-400 mt-2">
            {uiProducts.length} products
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Badge className="bg-ocean-500 text-white">Live Catalog</Badge>
          <Select
            name="category-sort"
            value={sortBy}
            onChange={(event) => setSortBy(event.target.value as SortKey)}
            options={[
              { value: 'popular', label: 'Most Popular' },
              { value: 'price-low', label: 'Price: Low to High' },
              { value: 'price-high', label: 'Price: High to Low' },
              { value: 'rating', label: 'Highest Rated' },
              { value: 'name', label: 'Name (A-Z)' },
            ]}
            size="sm"
            className="min-w-[220px]"
          />
        </div>
      </div>

      <div className="mb-8 flex flex-wrap gap-2">
        <Link
          href="/category?slug=all"
          className={`px-3 py-1 rounded-full text-sm border ${
            slug === 'all'
              ? 'bg-ocean-500 text-white border-ocean-500'
              : 'border-gray-300 dark:border-gray-700 text-gray-700 dark:text-gray-300'
          }`}
        >
          All
        </Link>
        {categories.map((category) => (
          <Link
            key={category.id}
            href={`/category?slug=${encodeURIComponent(category.id)}`}
            className={`px-3 py-1 rounded-full text-sm border ${
              category.id === slug
                ? 'bg-ocean-500 text-white border-ocean-500'
                : 'border-gray-300 dark:border-gray-700 text-gray-700 dark:text-gray-300'
            }`}
          >
            {category.name}
          </Link>
        ))}
      </div>

      {isError ? (
        <div className="rounded-lg border border-red-200 dark:border-red-900 p-4 text-red-600 dark:text-red-400">
          Products could not be loaded for this category.
        </div>
      ) : (
        <ProductGrid
          products={uiProducts}
          loading={isLoading}
          emptyMessage="No products were found for this category."
        />
      )}
    </MainLayout>
  );
}
