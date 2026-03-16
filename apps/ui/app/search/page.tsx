'use client';

import React, { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { MainLayout } from '@/components/templates/MainLayout';
import { SearchInput } from '@/components/molecules/SearchInput';
import { ProductGrid } from '@/components/organisms/ProductGrid';
import { Badge } from '@/components/atoms/Badge';
import { Alert } from '@/components/molecules/Alert';
import { Button } from '@/components/atoms/Button';
import { useSemanticSearch } from '@/lib/hooks/useSemanticSearch';

type ProxyErrorShape = {
  status?: number;
  details?: {
    proxy?: {
      failureKind?: 'config' | 'network' | 'upstream';
      remediation?: string[];
    };
  };
};

function getProxyFailureError(error: unknown): ProxyErrorShape['details']['proxy'] | null {
  if (!error || typeof error !== 'object') {
    return null;
  }

  const proxyError = error as ProxyErrorShape;
  if (proxyError.status !== 502 || !proxyError.details?.proxy?.failureKind) {
    return null;
  }

  return proxyError.details.proxy;
}

export default function SearchPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialQuery = searchParams.get('q') ?? '';
  const [query, setQuery] = useState(initialQuery);

  const { data, isLoading, error, refetch, isFetching } = useSemanticSearch(query, 20);
  const products = data?.items ?? [];
  const sourceLabel =
    data?.source === 'agent'
      ? 'Catalog Search Agent'
      : 'Catalog Search fallback (agent unavailable)';
  const proxyFailure = getProxyFailureError(error);

  const proxyFailureLabelByKind: Record<'config' | 'network' | 'upstream', string> = {
    config: 'Catalog search proxy configuration is missing or invalid.',
    network: 'Catalog search backend is temporarily unreachable.',
    upstream: 'Catalog search backend returned a temporary gateway error.',
  };

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
        <div role="status" aria-live="polite" aria-atomic="true">
          <Badge className="bg-ocean-500 text-white">Search source: {sourceLabel}</Badge>
        </div>
      </div>

      <ProductGrid
        products={products}
        loading={isLoading}
        emptyMessage={query ? 'No products matched your search.' : 'Search for products above.'}
      />

      {proxyFailure && query && (
        <Alert
          variant="warning"
          title="Catalog search is temporarily unavailable"
          dismissible={false}
          className="mt-4"
        >
          <div className="space-y-3">
            <p>{proxyFailureLabelByKind[proxyFailure.failureKind]}</p>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => {
                void refetch();
              }}
              loading={isFetching}
            >
              Retry search
            </Button>
          </div>
        </Alert>
      )}
    </MainLayout>
  );
}
