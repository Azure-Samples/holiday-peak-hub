'use client';

import React, { useMemo, useState } from 'react';
import Link from 'next/link';
import { MainLayout } from '@/components/templates/MainLayout';
import { ProductGrid } from '@/components/organisms/ProductGrid';
import { Badge } from '@/components/atoms/Badge';
import { Select } from '@/components/atoms/Select';
import { useCategories } from '@/lib/hooks/useCategories';
import { useProducts } from '@/lib/hooks/useProducts';
import { getApiErrorMessage, getApiStatusCode } from '@/lib/api/errorPresentation';
import { mapApiProductsToUi } from '@/lib/utils/productMappers';
import type { Product as UiProduct } from '@/components/types';
import { FiList, FiMessageSquare } from 'react-icons/fi';

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

  return (
    <MainLayout>
      <div className="mb-5 flex flex-wrap items-center gap-2">
        <Link
          href="/"
          className="text-sm text-[var(--hp-primary)] hover:underline"
        >
          Home
        </Link>
        <span className="text-[var(--hp-text-muted)]">/</span>
        <span className="text-sm text-[var(--hp-text-muted)]">{activeCategoryName}</span>
      </div>

      <section className="showcase-shell mb-6 p-4 sm:p-5">
        <div className="grid gap-3 md:grid-cols-2">
          <article className="rounded-2xl border border-[var(--hp-border)] bg-[var(--hp-surface-strong)]/70 p-3">
            <div className="mb-1 inline-flex items-center text-xs font-semibold uppercase tracking-wide text-[var(--hp-accent)]">
              <FiList className="mr-1 h-4 w-4" />
              Catalog Layer
            </div>
            <p className="text-sm text-[var(--hp-text-muted)]">Use filters and sort below to inspect raw catalog data in this category.</p>
          </article>
          <article className="rounded-2xl border border-[var(--hp-border)] bg-[var(--hp-surface-strong)]/70 p-3">
            <div className="mb-1 inline-flex items-center text-xs font-semibold uppercase tracking-wide text-[var(--hp-primary)]">
              <FiMessageSquare className="mr-1 h-4 w-4" />
              Agent Layer
            </div>
            <p className="text-sm text-[var(--hp-text-muted)]">
              Need interpretation? Open
              {' '}
              <Link href="/agents/product-enrichment-chat" className="font-semibold text-[var(--hp-primary)] underline-offset-2 hover:underline">
                Product Enrichment Chat
              </Link>
              .
            </p>
          </article>
        </div>
      </section>

      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-black text-[var(--hp-text)]">{activeCategoryName}</h1>
          <p className="mt-2 text-[var(--hp-text-muted)]">
            {uiProducts.length} products
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Badge className="bg-[var(--hp-surface-strong)] text-[var(--hp-primary)]">Live Catalog</Badge>
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

      <nav className="mb-6 flex flex-wrap gap-2" aria-label="Category filters">
        <Link
          href="/category?slug=all"
          className={`px-3 py-1 rounded-full text-sm border ${
            slug === 'all'
              ? 'bg-[var(--hp-primary)] text-white border-[var(--hp-primary)]'
              : 'border-[var(--hp-border)] text-[var(--hp-text)]'
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
                ? 'bg-[var(--hp-primary)] text-white border-[var(--hp-primary)]'
                : 'border-[var(--hp-border)] text-[var(--hp-text)]'
            }`}
          >
            {category.name}
          </Link>
        ))}
      </nav>

      {isError ? (
        <div className="rounded-lg border border-red-300 p-4 text-red-700">
          <p>{productsErrorMessage}</p>
          {productsErrorStatus ? <p className="mt-2 text-xs">Backend status: {productsErrorStatus}</p> : null}
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
