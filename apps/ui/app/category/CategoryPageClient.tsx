'use client';

import React, { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { MainLayout } from '@/components/templates/MainLayout';
import { ProductGrid } from '@/components/organisms/ProductGrid';
import { CanvasShelf } from '@/components/organisms/CanvasShelf';
import { useCategories } from '@/lib/hooks/useCategories';
import { useProducts } from '@/lib/hooks/useProducts';
import { getApiErrorMessage, getApiStatusCode } from '@/lib/api/errorPresentation';
import { mapApiProductsToUi } from '@/lib/utils/productMappers';
import { trackEcommerceEvent } from '@/lib/utils/telemetry';
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
    error,
  } = useProducts({
    category: slug === 'all' ? undefined : slug,
    limit: 60,
  });

  const productsErrorStatus = getApiStatusCode(error);
  const productsErrorMessage = getApiErrorMessage(
    error,
    'Products could not be loaded for this category.',
  );

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
        return copy.sort((left, right) => left.title.localeCompare(right.title));
      default:
        return copy;
    }
  }, [products, sortBy]);

  const uiProducts = sortedProducts as UiProduct[];
  const categoryShelfItems = [
    {
      id: 'all',
      title: 'All Products',
      subtitle: 'Browse the complete live catalog',
      meta: slug === 'all' ? 'Active' : 'Category',
      href: '/category?slug=all',
    },
    ...categories.map((category) => ({
      id: category.id,
      title: category.name,
      subtitle: category.description || 'Explore this category',
      meta: category.id === slug ? 'Active' : 'Category',
      href: `/category?slug=${encodeURIComponent(category.id)}`,
    })),
  ];
  const productShelfItems = uiProducts.slice(0, 12).map((product) => ({
    id: product.sku,
    title: product.title,
    subtitle: product.description,
    meta: product.inStock ? 'In stock' : 'Low availability',
    href: `/product?id=${encodeURIComponent(product.sku)}`,
  }));

  useEffect(() => {
    trackEcommerceEvent('category_opened', {
      slug,
      source: 'category_page',
    });
  }, [slug]);

  return (
    <MainLayout>
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <Link
          href="/"
          className="text-sm text-[var(--hp-primary)] hover:underline"
        >
          Home
        </Link>
        <span className="text-[var(--hp-text-muted)]">/</span>
        <span className="text-sm text-[var(--hp-text-muted)]">{activeCategoryName}</span>
      </div>

      <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-[var(--hp-text-muted)]">Category</p>
          <h1 className="mt-1 text-3xl font-black text-[var(--hp-text)]">{activeCategoryName}</h1>
          <p className="mt-1 text-sm text-[var(--hp-text-muted)]">
            {uiProducts.length} products
          </p>
        </div>
        <Link
          href="/agents/product-enrichment-chat"
          className="text-sm font-medium text-[var(--hp-primary)] hover:underline"
        >
          Open Product Enrichment Chat
        </Link>
      </div>

      <div className="mb-5">
        <CanvasShelf
          title="Category Navigator"
          items={categoryShelfItems}
          ariaLabel="Category navigator shelf with drag and keyboard navigation"
        />
      </div>

      {isError ? (
        <div className="rounded-lg border border-red-300 p-4 text-red-700">
          <p>{productsErrorMessage}</p>
          {productsErrorStatus ? <p className="mt-2 text-xs">Backend status: {productsErrorStatus}</p> : null}
        </div>
      ) : (
        <>
          {productShelfItems.length > 0 && (
            <div className="mb-5">
              <CanvasShelf
                title="Product Flow"
                items={productShelfItems}
                ariaLabel="Product shelf with drag and keyboard navigation"
              />
            </div>
          )}
          <ProductGrid
            products={uiProducts}
            sortOptions={[
              { key: 'popular', value: 'popular', label: 'Most Popular' },
              { key: 'price-low', value: 'price-low', label: 'Price: Low to High' },
              { key: 'price-high', value: 'price-high', label: 'Price: High to Low' },
              { key: 'rating', value: 'rating', label: 'Highest Rated' },
              { key: 'name', value: 'name', label: 'Name (A-Z)' },
            ]}
            currentSort={sortBy}
            onSortChange={(value) => setSortBy(value as SortKey)}
            loading={isLoading}
            emptyMessage="No products were found for this category."
          />
        </>
      )}
    </MainLayout>
  );
}
