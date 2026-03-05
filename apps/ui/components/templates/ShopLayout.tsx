/**
 * ShopLayout Template
 * E-commerce shop page with filters and product grid
 */

import React from 'react';
import { cn } from '../utils';
import { FilterPanel } from '../organisms/FilterPanel';
import { ProductGrid } from '../organisms/ProductGrid';
import type {
  FilterGroup,
  Product,
  SortOption,
  BaseComponentProps,
} from '../types';

export interface ShopLayoutProps extends BaseComponentProps {
  /** Filter groups */
  filterGroups: FilterGroup[];
  /** Products to display */
  products: Product[];
  /** Active filter values */
  activeFilters?: Record<string, string[]>;
  /** Clear all filters handler */
  onClearFilters?: () => void;
  /** Grid layout (grid or list) */
  layout?: 'grid' | 'list';
  /** Layout change handler */
  onLayoutChange?: (layout: 'grid' | 'list') => void;
  /** Sort option */
  sortBy?: string;
  /** Sort change handler */
  onSortChange?: (value: string) => void;
  /** Sort options */
  sortOptions?: SortOption[];
  /** Add to cart handler */
  onAddToCart?: (product: Product) => void;
  /** Add to wishlist handler */
  onAddToWishlist?: (product: Product) => void;
  /** Product click handler */
  onProductClick?: (product: Product) => void;
  /** Filter change handler */
  onFilterChange?: (filterId: string, optionId: string, checked: boolean) => void;
  /** Loading state */
  loading?: boolean;
  /** Whether filters are open on mobile */
  filtersOpen?: boolean;
  /** Toggle filters on mobile */
  onToggleFilters?: () => void;
}

export const ShopLayout: React.FC<ShopLayoutProps> = ({
  filterGroups,
  products,
  activeFilters,
  onFilterChange,
  onClearFilters,
  layout = 'grid',
  onLayoutChange,
  sortBy,
  onSortChange,
  sortOptions,
  onAddToCart,
  onAddToWishlist,
  loading = false,
  filtersOpen = false,
  onToggleFilters,
  className,
  testId,
  ariaLabel,
}) => {
  return (
    <div
      data-testid={testId}
      aria-label={ariaLabel || 'Shop layout'}
      className={cn('w-full', className)}
    >
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
        {/* Filters Sidebar - Desktop */}
        <aside className="hidden lg:block lg:col-span-1">
          <div className="sticky top-20">
            <FilterPanel
              filterGroups={filterGroups}
              selectedFilters={activeFilters}
              onFilterChange={onFilterChange}
              onClearAll={onClearFilters}
            />
          </div>
        </aside>

        {/* Mobile Filter Overlay */}
        {filtersOpen && (
          <div className="lg:hidden fixed inset-0 z-50 bg-black/50" onClick={onToggleFilters}>
            <div
              className="fixed inset-y-0 left-0 w-80 bg-white dark:bg-gray-800 overflow-y-auto p-4"
              onClick={(e) => e.stopPropagation()}
            >
              <FilterPanel
                filterGroups={filterGroups}
                selectedFilters={activeFilters}
                onFilterChange={onFilterChange}
                onClearAll={onClearFilters}
              />
            </div>
          </div>
        )}

        {/* Product Grid */}
        <div className="lg:col-span-3">
          <ProductGrid
            products={products}
            defaultView={layout}
            onViewChange={onLayoutChange}
            currentSort={sortBy}
            onSortChange={onSortChange}
            sortOptions={sortOptions}
            onAddToCart={onAddToCart}
            onWishlist={onAddToWishlist}
            loading={loading}
          />
        </div>
      </div>
    </div>
  );
};

ShopLayout.displayName = 'ShopLayout';
