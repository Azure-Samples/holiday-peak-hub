'use client';

import React, { useState } from 'react';
import { ShopLayout } from '@/components/templates/ShopLayout';
import { Card } from '@/components/molecules/Card';
import { Button } from '@/components/atoms/Button';
import { Badge } from '@/components/atoms/Badge';
import { Select } from '@/components/atoms/Select';
import { Checkbox } from '@/components/atoms/Checkbox';
import Link from 'next/link';
import { FiGrid, FiList, FiFilter } from 'react-icons/fi';

export default function CategoryPage({ params }: { params: { slug: string } }) {
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [sortBy, setSortBy] = useState('popular');

  // Mock products - will be replaced with actual API call
  const products = Array.from({ length: 12 }, (_, i) => ({
    id: i + 1,
    title: `Product ${i + 1}`,
    price: '$' + ((i + 1) * 29.99).toFixed(2),
    originalPrice: i % 3 === 0 ? '$' + ((i + 1) * 39.99).toFixed(2) : null,
    rating: 4 + (i % 2) * 0.5,
    reviews: 100 + i * 50,
    inStock: i % 5 !== 0,
  }));

  const filters = (
    <div className="bg-white dark:bg-gray-800 rounded-xl p-6 space-y-6 shadow-md border border-gray-200 dark:border-gray-700">
      <div>
        <h3 className="font-semibold text-gray-900 dark:text-white mb-4">Filters</h3>
        <Button
          variant="outline"
          className="w-full border-ocean-500 text-ocean-500 hover:bg-ocean-50 dark:border-ocean-300 dark:text-ocean-300"
        >
          <FiFilter className="mr-2" />
          Clear All
        </Button>
      </div>

      <div>
        <h4 className="font-medium text-gray-900 dark:text-white mb-3">Price Range</h4>
        <div className="space-y-2">
          <Checkbox label="Under $50" />
          <Checkbox label="$50 - $100" />
          <Checkbox label="$100 - $200" />
          <Checkbox label="$200+" />
        </div>
      </div>

      <div>
        <h4 className="font-medium text-gray-900 dark:text-white mb-3">Rating</h4>
        <div className="space-y-2">
          <Checkbox label="★★★★★ 5 Stars" />
          <Checkbox label="★★★★☆ 4+ Stars" />
          <Checkbox label="★★★☆☆ 3+ Stars" />
        </div>
      </div>

      <div>
        <h4 className="font-medium text-gray-900 dark:text-white mb-3">Availability</h4>
        <div className="space-y-2">
          <Checkbox label="In Stock" defaultChecked />
          <Checkbox label="On Sale" />
        </div>
      </div>

      <div>
        <h4 className="font-medium text-gray-900 dark:text-white mb-3">Brand</h4>
        <div className="space-y-2">
          <Checkbox label="Nike" />
          <Checkbox label="Adidas" />
          <Checkbox label="Apple" />
          <Checkbox label="Samsung" />
        </div>
      </div>
    </div>
  );

  return (
    <ShopLayout filters={filters}>
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
          {params.slug.charAt(0).toUpperCase() + params.slug.slice(1)} Products
        </h1>
        <p className="text-gray-600 dark:text-gray-400">
          Showing {products.length} results
        </p>
      </div>

      {/* Toolbar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-600 dark:text-gray-400">Sort by:</span>
          <Select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            options={[
              { value: 'popular', label: 'Most Popular' },
              { value: 'newest', label: 'Newest' },
              { value: 'price-low', label: 'Price: Low to High' },
              { value: 'price-high', label: 'Price: High to Low' },
              { value: 'rating', label: 'Highest Rated' },
            ]}
          />
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setViewMode('grid')}
            className={`p-2 rounded-lg ${
              viewMode === 'grid'
                ? 'bg-ocean-500 text-white'
                : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300'
            }`}
          >
            <FiGrid className="w-5 h-5" />
          </button>
          <button
            onClick={() => setViewMode('list')}
            className={`p-2 rounded-lg ${
              viewMode === 'list'
                ? 'bg-ocean-500 text-white'
                : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300'
            }`}
          >
            <FiList className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Products Grid/List */}
      <div
        className={
          viewMode === 'grid'
            ? 'grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6'
            : 'space-y-4'
        }
      >
        {products.map((product) => (
          <ProductCard key={product.id} product={product} viewMode={viewMode} />
        ))}
      </div>

      {/* Pagination */}
      <div className="mt-12 flex justify-center">
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm">Previous</Button>
          {[1, 2, 3, 4].map((page) => (
            <Button
              key={page}
              variant={page === 1 ? 'primary' : 'outline'}
              size="sm"
              className={page === 1 ? 'bg-ocean-500' : ''}
            >
              {page}
            </Button>
          ))}
          <Button variant="outline" size="sm">Next</Button>
        </div>
      </div>
    </ShopLayout>
  );
}

function ProductCard({ product, viewMode }: { product: any; viewMode: 'grid' | 'list' }) {
  if (viewMode === 'list') {
    return (
      <Link href={`/product/${product.id}`}>
        <Card className="hover:shadow-lg transition-all p-4">
          <div className="flex gap-4">
            <div className="w-32 h-32 flex-shrink-0 bg-gradient-to-br from-gray-100 to-gray-200 dark:from-gray-800 dark:to-gray-700 rounded-lg" />
            <div className="flex-1">
              <h3 className="font-semibold text-lg text-gray-900 dark:text-white mb-2">
                {product.title}
              </h3>
              <div className="flex items-center mb-2">
                <div className="flex text-yellow-400">
                  {'★'.repeat(Math.floor(product.rating))}{'☆'.repeat(5 - Math.floor(product.rating))}
                </div>
                <span className="text-sm text-gray-500 dark:text-gray-400 ml-2">
                  ({product.reviews} reviews)
                </span>
              </div>
              <div className="flex items-center gap-3 mb-3">
                <span className="text-2xl font-bold text-ocean-500 dark:text-ocean-300">
                  {product.price}
                </span>
                {product.originalPrice && (
                  <>
                    <span className="text-gray-500 dark:text-gray-400 line-through">
                      {product.originalPrice}
                    </span>
                    <Badge className="bg-lime-500 text-white">Sale</Badge>
                  </>
                )}
              </div>
              {product.inStock ? (
                <Badge className="bg-lime-100 text-lime-700 dark:bg-lime-900 dark:text-lime-300">
                  In Stock
                </Badge>
              ) : (
                <Badge className="bg-gray-200 text-gray-700 dark:bg-gray-700 dark:text-gray-300">
                  Out of Stock
                </Badge>
              )}
            </div>
          </div>
        </Card>
      </Link>
    );
  }

  return (
    <Link href={`/product/${product.id}`}>
      <Card className="group hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1">
        <div className="aspect-square overflow-hidden rounded-t-lg relative">
          <div className="w-full h-full bg-gradient-to-br from-gray-100 to-gray-200 dark:from-gray-800 dark:to-gray-700" />
          {product.originalPrice && (
            <Badge className="absolute top-2 right-2 bg-lime-500 text-white">
              Sale
            </Badge>
          )}
        </div>
        <div className="p-4">
          <h3 className="font-semibold text-gray-900 dark:text-white mb-2 line-clamp-2">
            {product.title}
          </h3>
          <div className="flex items-center mb-2">
            <div className="flex text-yellow-400 text-sm">
              {'★'.repeat(Math.floor(product.rating))}{'☆'.repeat(5 - Math.floor(product.rating))}
            </div>
            <span className="text-xs text-gray-500 dark:text-gray-400 ml-2">
              ({product.reviews})
            </span>
          </div>
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xl font-bold text-ocean-500 dark:text-ocean-300">
              {product.price}
            </span>
            {product.originalPrice && (
              <span className="text-sm text-gray-500 dark:text-gray-400 line-through">
                {product.originalPrice}
              </span>
            )}
          </div>
          {product.inStock ? (
            <Badge className="bg-lime-100 text-lime-700 dark:bg-lime-900 dark:text-lime-300 text-xs">
              In Stock
            </Badge>
          ) : (
            <Badge className="bg-gray-200 text-gray-700 dark:bg-gray-700 dark:text-gray-300 text-xs">
              Out of Stock
            </Badge>
          )}
        </div>
      </Card>
    </Link>
  );
}
