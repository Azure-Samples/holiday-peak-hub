/**
 * ProductGrid Organism Component
 * Product listing with grid/list view toggle and sorting
 * Migrated from e-commerce/products.tsx
 */

import React, { useState } from 'react';
import { FiGrid, FiMenu } from 'react-icons/fi';
import { cn } from '../utils';
import { Select } from '../atoms/Select';
import { Button } from '../atoms/Button';
import { ProductCard } from '../molecules/ProductCard';
import { Skeleton } from '../atoms/Skeleton';
import type { Product, SortOption, BaseComponentProps } from '../types';

export interface ProductGridProps extends BaseComponentProps {
  /** Products to display */
  products: Product[];
  /** Sort options */
  sortOptions?: SortOption[];
  /** Current sort key */
  currentSort?: string;
  /** Sort change handler */
  onSortChange?: (sortKey: string) => void;
  /** Default view mode */
  defaultView?: 'grid' | 'list';
  /** View change handler */
  onViewChange?: (view: 'grid' | 'list') => void;
  /** Whether to show view toggle */
  showViewToggle?: boolean;
  /** Whether to show sort dropdown */
  showSort?: boolean;
  /** Loading state */
  loading?: boolean;
  /** Number of columns in grid view */
  gridColumns?: 2 | 3 | 4;
  /** @deprecated Use gridColumns instead */
  columns?: 2 | 3 | 4;
  /** Add to cart handler */
  onAddToCart?: (product: Product) => void;
  /** Wishlist handler */
  onWishlist?: (product: Product) => void;
  /** Empty state message */
  emptyMessage?: string;
}

export const ProductGrid: React.FC<ProductGridProps> = ({
  products = [],
  sortOptions = [
    { key: 'relevance', label: 'Most Relevant', value: 'relevance' },
    { key: 'price-asc', label: 'Price: Low to High', value: 'price-asc' },
    { key: 'price-desc', label: 'Price: High to Low', value: 'price-desc' },
    { key: 'rating', label: 'Highest Rated', value: 'rating' },
    { key: 'newest', label: 'Newest', value: 'newest' },
  ],
  currentSort = 'relevance',
  onSortChange,
  defaultView = 'grid',
  onViewChange,
  showViewToggle = true,
  showSort = true,
  loading = false,
  gridColumns = 4,
  columns,
  onAddToCart,
  onWishlist,
  emptyMessage = 'No products found',
  className,
  testId,
  ariaLabel,
}) => {
  const [view, setView] = useState<'grid' | 'list'>(defaultView);
  const resolvedGridColumns = columns ?? gridColumns;

  const handleViewChange = (newView: 'grid' | 'list') => {
    setView(newView);
    onViewChange?.(newView);
  };

  const handleSortChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    onSortChange?.(e.target.value);
  };

  const gridColsClass = {
    2: 'md:grid-cols-2',
    3: 'md:grid-cols-2 lg:grid-cols-3',
    4: 'md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4',
  };

  return (
    <div
      data-testid={testId}
      aria-label={ariaLabel || 'Product listing'}
      className={cn('showcase-shell w-full p-3 sm:p-4', className)}
    >
      <div className="mb-4 grid grid-cols-2 gap-2 lg:hidden" role="region" aria-label="Catalog controls">
        <div className="col-span-1">
          <div className="flex flex-col items-start space-y-2">
            <div className="font-semibold text-[var(--hp-text)]">
              {products.length} products
            </div>

            {showViewToggle && (
              <div className="flex items-center space-x-1">
                <Button
                  variant="ghost"
                  size="sm"
                  iconOnly
                  onClick={() => handleViewChange('grid')}
                  ariaLabel="Grid view"
                  className={cn(
                    'border border-[var(--hp-border)]',
                    view === 'grid' && 'bg-[var(--hp-surface-strong)]'
                  )}
                >
                  <FiGrid className="w-5 h-5" />
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  iconOnly
                  onClick={() => handleViewChange('list')}
                  ariaLabel="List view"
                  className={cn(
                    'border border-[var(--hp-border)]',
                    view === 'list' && 'bg-[var(--hp-surface-strong)]'
                  )}
                >
                  <FiMenu className="w-5 h-5" />
                </Button>
              </div>
            )}
          </div>
        </div>

        {showSort && (
          <div className="col-span-1 place-self-end">
            <Select
              name="sort-mobile"
              value={currentSort}
              onChange={handleSortChange}
              options={sortOptions.map((opt) => ({
                value: opt.key,
                label: opt.label,
              }))}
              size="sm"
            />
          </div>
        )}
      </div>

      <div className="hidden mb-4 lg:flex lg:items-center lg:justify-between">
        <div className="flex items-center gap-4">
          <div className="font-semibold text-[var(--hp-text)]">
            {products.length} products
          </div>

          {showViewToggle && (
            <div className="flex items-center space-x-1">
              <Button
                variant="ghost"
                size="sm"
                iconOnly
                onClick={() => handleViewChange('grid')}
                ariaLabel="Grid view"
                className={cn(
                  'border border-[var(--hp-border)]',
                  view === 'grid' && 'bg-[var(--hp-surface-strong)]'
                )}
              >
                <FiGrid className="w-5 h-5" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                iconOnly
                onClick={() => handleViewChange('list')}
                ariaLabel="List view"
                className={cn(
                  'border border-[var(--hp-border)]',
                  view === 'list' && 'bg-[var(--hp-surface-strong)]'
                )}
              >
                <FiMenu className="w-5 h-5" />
              </Button>
            </div>
          )}
        </div>

        {showSort && (
          <div className="flex items-center gap-2">
            <label className="text-sm font-medium text-[var(--hp-text-muted)] whitespace-nowrap">
              Sort by
            </label>
            <Select
              name="sort-desktop"
              value={currentSort}
              onChange={handleSortChange}
              options={sortOptions.map((opt) => ({
                value: opt.key,
                label: opt.label,
              }))}
              size="sm"
              className="w-48"
            />
          </div>
        )}
      </div>

      {loading ? (
        <div
          className={cn(
            view === 'grid'
              ? `grid grid-cols-1 gap-4 ${gridColsClass[resolvedGridColumns]}`
              : 'space-y-4'
          )}
        >
          {Array.from({ length: 8 }).map((_, i) => (
            <Skeleton key={i} height={view === 'grid' ? 400 : 150} />
          ))}
        </div>
      ) : products.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12">
          <p className="text-lg text-[var(--hp-text-muted)]">
            {emptyMessage}
          </p>
        </div>
      ) : (
        <div
          className={cn(
            view === 'grid'
              ? `grid grid-cols-1 gap-4 ${gridColsClass[resolvedGridColumns]}`
              : 'space-y-4'
          )}
          role="list"
          aria-label="Catalog products"
        >
          {products.map((product) => (
            <ProductCard
              key={product.sku}
              product={product}
              layout={view}
              onAddToCart={onAddToCart}
              onWishlist={onWishlist}
            />
          ))}
        </div>
      )}
    </div>
  );
};

ProductGrid.displayName = 'ProductGrid';
