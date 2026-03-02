'use client';

import React, { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { MainLayout } from '@/components/templates/MainLayout';
import { SearchInput } from '@/components/molecules/SearchInput';
import { ProductGrid } from '@/components/organisms/ProductGrid';
import { Badge } from '@/components/atoms/Badge';
import { useProductSearch } from '@/lib/hooks/useProducts';
import { mapApiProductsToUi } from '@/lib/utils/productMappers';

export default function SearchPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialQuery = searchParams.get('q') ?? '';
  const [query, setQuery] = useState(initialQuery);

  const { data, isLoading } = useProductSearch(query, 20);
  const products = mapApiProductsToUi(data || []);

  useEffect(() => {
    setQuery(initialQuery);
  }, [initialQuery]);

  const handleSearch = (value: string) => {
    const trimmed = value.trim();
    setQuery(trimmed);
    if (trimmed) {
      router.push(`/search?q=${encodeURIComponent(trimmed)}`);
    }
  };

  return (
    <MainLayout
      navigationProps={{
        onSearch: handleSearch,
      }}
    >
      <div className="mb-8 space-y-4">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Search</h1>
        <SearchInput
          placeholder="Search products..."
          value={query}
          onChange={setQuery}
          onSearch={handleSearch}
          size="lg"
        />
        <div>
          <Badge className="bg-ocean-500 text-white">Source: Catalog Search</Badge>
        </div>
      </div>

      <ProductGrid
        products={products}
        loading={isLoading}
        emptyMessage={query ? 'No products matched your search.' : 'Search for products above.'}
      />
    </MainLayout>
  );
}
