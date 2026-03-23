'use client';

import React, { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { MainLayout } from '@/components/templates/MainLayout';
import { ShopLayout } from '@/components/templates/ShopLayout';
import { HeroSlider } from '@/components/organisms/HeroSlider';
import { useCategories } from '@/lib/hooks/useCategories';
import { useProducts } from '@/lib/hooks/useProducts';
import { getApiErrorMessage, getApiStatusCode } from '@/lib/api/errorPresentation';
import { mapApiProductsToUi } from '@/lib/utils/productMappers';
import { trackEcommerceEvent } from '@/lib/utils/telemetry';
import type { FilterGroup, Product as UiProduct } from '@/components/types';

type SortKey = 'popular' | 'price-low' | 'price-high' | 'rating' | 'name';

export function CategoryPageClient({ slug }: { slug: string }) {
  const [sortBy, setSortBy] = useState<SortKey>('popular');
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [activeFilters, setActiveFilters] = useState<Record<string, string[]>>({});

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
  const uiProducts = products as UiProduct[];

  const filterGroups = useMemo<FilterGroup[]>(() => {
    const groups: FilterGroup[] = [];

    if (slug === 'all') {
      groups.push({
        id: 'category',
        label: 'Category',
        type: 'checkbox',
        options: categories.map((category) => ({
          id: category.id,
          label: category.name,
          value: category.id,
          count: uiProducts.filter((product) => product.category === category.id).length,
        })),
      });
    }

    groups.push(
      {
        id: 'availability',
        label: 'Availability',
        type: 'checkbox',
        options: [
          {
            id: 'in-stock',
            label: 'In stock',
            value: 'in-stock',
            count: uiProducts.filter((product) => product.inStock).length,
          },
          {
            id: 'out-of-stock',
            label: 'Out of stock',
            value: 'out-of-stock',
            count: uiProducts.filter((product) => !product.inStock).length,
          },
        ],
      },
      {
        id: 'price',
        label: 'Price',
        type: 'checkbox',
        options: [
          {
            id: 'under-50',
            label: 'Under $50',
            value: 'under-50',
            count: uiProducts.filter((product) => product.price < 50).length,
          },
          {
            id: '50-150',
            label: '$50 - $150',
            value: '50-150',
            count: uiProducts.filter((product) => product.price >= 50 && product.price <= 150).length,
          },
          {
            id: 'over-150',
            label: 'Over $150',
            value: 'over-150',
            count: uiProducts.filter((product) => product.price > 150).length,
          },
        ],
      },
      {
        id: 'rating',
        label: 'Rating',
        type: 'checkbox',
        options: [
          {
            id: '4-plus',
            label: '4★ & up',
            value: '4-plus',
            count: uiProducts.filter((product) => (product.rating || 0) >= 4).length,
          },
          {
            id: '3-plus',
            label: '3★ & up',
            value: '3-plus',
            count: uiProducts.filter((product) => (product.rating || 0) >= 3).length,
          },
        ],
      },
    );

    return groups;
  }, [categories, slug, uiProducts]);

  const filteredAndSortedProducts = useMemo(() => {
    let filtered = [...uiProducts];

    const selectedCategories = activeFilters.category || [];
    if (selectedCategories.length > 0) {
      filtered = filtered.filter((product) => selectedCategories.includes(product.category));
    }

    const selectedAvailability = activeFilters.availability || [];
    if (selectedAvailability.length > 0) {
      filtered = filtered.filter((product) => {
        if (selectedAvailability.includes('in-stock') && product.inStock) {
          return true;
        }
        if (selectedAvailability.includes('out-of-stock') && !product.inStock) {
          return true;
        }
        return false;
      });
    }

    const selectedPrice = activeFilters.price || [];
    if (selectedPrice.length > 0) {
      filtered = filtered.filter((product) => {
        if (selectedPrice.includes('under-50') && product.price < 50) {
          return true;
        }
        if (selectedPrice.includes('50-150') && product.price >= 50 && product.price <= 150) {
          return true;
        }
        if (selectedPrice.includes('over-150') && product.price > 150) {
          return true;
        }
        return false;
      });
    }

    const selectedRating = activeFilters.rating || [];
    if (selectedRating.length > 0) {
      filtered = filtered.filter((product) => {
        const rating = product.rating || 0;
        if (selectedRating.includes('4-plus') && rating >= 4) {
          return true;
        }
        if (selectedRating.includes('3-plus') && rating >= 3) {
          return true;
        }
        return false;
      });
    }

    switch (sortBy) {
      case 'price-low':
        return filtered.sort((left, right) => left.price - right.price);
      case 'price-high':
        return filtered.sort((left, right) => right.price - left.price);
      case 'rating':
        return filtered.sort((left, right) => (right.rating || 0) - (left.rating || 0));
      case 'name':
        return filtered.sort((left, right) => left.title.localeCompare(right.title));
      default:
        return filtered;
    }
  }, [activeFilters, sortBy, uiProducts]);

  const handleFilterChange = (filterId: string, optionId: string, checked: boolean) => {
    setActiveFilters((previous) => {
      const current = previous[filterId] || [];
      const nextValues = checked
        ? Array.from(new Set([...current, optionId]))
        : current.filter((value) => value !== optionId);

      return {
        ...previous,
        [filterId]: nextValues,
      };
    });
  };

  useEffect(() => {
    trackEcommerceEvent('category_opened', {
      slug,
      source: 'category_page',
    });
  }, [slug]);

  useEffect(() => {
    setActiveFilters({});
    setFiltersOpen(false);
  }, [slug]);

  return (
    <MainLayout>
      <section className="mb-6">
        <HeroSlider />
      </section>

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
            {filteredAndSortedProducts.length} products
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={() => setFiltersOpen((current) => !current)}
            className="rounded-lg border border-[var(--hp-border)] bg-[var(--hp-surface-strong)] px-3 py-2 text-xs font-semibold uppercase tracking-wide text-[var(--hp-text)] lg:hidden"
            aria-label={filtersOpen ? 'Close filters' : 'Open filters'}
            aria-expanded={filtersOpen}
            aria-controls="catalog-filters"
          >
            {filtersOpen ? 'Close Filters' : 'Open Filters'}
          </button>
          <Link
            href="/search?agentChat=1"
            className="text-sm font-medium text-[var(--hp-primary)] hover:underline"
          >
            Open Product Agent Popup
          </Link>
        </div>
      </div>

      {isError ? (
        <div className="rounded-lg border border-red-300 p-4 text-red-700">
          <p>{productsErrorMessage}</p>
          {productsErrorStatus ? <p className="mt-2 text-xs">Backend status: {productsErrorStatus}</p> : null}
        </div>
      ) : (
        <div id="catalog-filters">
          <ShopLayout
            filterGroups={filterGroups}
            products={filteredAndSortedProducts}
            activeFilters={activeFilters}
            onFilterChange={handleFilterChange}
            onClearFilters={() => setActiveFilters({})}
            filtersOpen={filtersOpen}
            onToggleFilters={() => setFiltersOpen((current) => !current)}
            sortOptions={[
              { key: 'popular', value: 'popular', label: 'Most Popular' },
              { key: 'price-low', value: 'price-low', label: 'Price: Low to High' },
              { key: 'price-high', value: 'price-high', label: 'Price: High to Low' },
              { key: 'rating', value: 'rating', label: 'Highest Rated' },
              { key: 'name', value: 'name', label: 'Name (A-Z)' },
            ]}
            sortBy={sortBy}
            onSortChange={(value) => setSortBy(value as SortKey)}
            loading={isLoading}
          />
        </div>
      )}
    </MainLayout>
  );
}
