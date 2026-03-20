'use client';

import React, { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { MainLayout } from '@/components/templates/MainLayout';
import { SearchInput } from '@/components/molecules/SearchInput';
import { Alert } from '@/components/molecules/Alert';
import { Button } from '@/components/atoms/Button';
import { SearchModeToggle } from '@/components/enrichment/SearchModeToggle';
import { SearchModeIndicator } from '@/components/enrichment/SearchModeIndicator';
import { IntentClassificationDisplay } from '@/components/enrichment/IntentClassificationDisplay';
import { IntentPanel } from '@/components/enrichment/IntentPanel';
import { SearchResultCard } from '@/components/enrichment/SearchResultCard';
import { useIntelligentSearch } from '@/lib/hooks/useIntelligentSearch';
import { useRelatedProducts } from '@/lib/hooks/useRelatedProducts';

type ProxyErrorShape = {
  status?: number;
  details?: {
    proxy?: {
      failureKind?: 'config' | 'network' | 'upstream';
      remediation?: string[];
    };
  };
};

type ProxyFailureShape = {
  failureKind: 'config' | 'network' | 'upstream';
  remediation?: string[];
};

function getProxyFailureError(error: unknown): ProxyFailureShape | null {
  if (!error || typeof error !== 'object') {
    return null;
  }

  const proxyError = error as ProxyErrorShape;
  const proxyFailure = proxyError.details?.proxy;

  if (proxyError.status !== 502 || !proxyFailure?.failureKind) {
    return null;
  }

  return {
    failureKind: proxyError.details.proxy.failureKind,
    remediation: proxyError.details.proxy.remediation,
  };
}

export default function SearchPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialQuery = searchParams.get('q') ?? '';
  const [query, setQuery] = useState(initialQuery);

  const {
    data,
    isLoading,
    error,
    refetch,
    isFetching,
    preference,
    setPreference,
    resolvedMode,
  } = useIntelligentSearch(query, 20);
  const products = data?.items ?? [];
  const relatedProductIds = useMemo(() => {
    const ids = new Set<string>();
    for (const product of products) {
      for (const relatedId of product.complementaryProducts || []) {
        ids.add(relatedId);
      }
      for (const relatedId of product.substituteProducts || []) {
        ids.add(relatedId);
      }
    }
    return Array.from(ids);
  }, [products]);
  const { data: relatedProductMap = {} } = useRelatedProducts(relatedProductIds);
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
        <Link
          href={data?.trace_id ? `/admin/agent-activity/${data.trace_id}` : '/admin/agent-activity'}
          className="inline-flex text-sm text-blue-600 hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:text-blue-400"
        >
          {data?.trace_id ? 'View search trace' : 'View Agent Activity'}
        </Link>
        <SearchInput
          placeholder="Search products..."
          value={query}
          onChange={setQuery}
          onSearch={handleSearch}
          size="lg"
        />
        <SearchModeToggle
          preference={preference}
          resolvedMode={resolvedMode}
          onChange={setPreference}
        />
        <div className="space-y-2" aria-label="Search mode and intent classification">
          <SearchModeIndicator source={resolvedMode === 'intelligent' ? 'agent' : 'fallback'} />
          {resolvedMode === 'intelligent' && (
            <IntentClassificationDisplay
              intent={data?.intent?.intent}
              confidence={data?.intent?.confidence}
            />
          )}
        </div>
        <IntentPanel mode={resolvedMode} intent={data?.intent} subqueries={data?.subqueries} />
      </div>

      {query ? (
        <div className="mb-4">
          <span
            className={`inline-flex rounded-full px-3 py-1 text-sm font-semibold ${
              resolvedMode === 'intelligent'
                ? 'bg-gradient-to-r from-[var(--hp-primary)] to-[var(--hp-accent)] text-white'
                : 'bg-[var(--hp-surface-strong)] text-[var(--hp-text-muted)]'
            }`}
          >
            {resolvedMode === 'intelligent' ? 'Intelligent Search' : 'Keyword Search'}
          </span>
        </div>
      ) : null}

      {isLoading ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 6 }).map((_, index) => (
            <div key={`search-skeleton-${index}`} className="h-80 animate-pulse rounded-2xl bg-[var(--hp-surface-strong)]" />
          ))}
        </div>
      ) : products.length === 0 ? (
        <p className="py-10 text-center text-lg text-[var(--hp-text-muted)]">
          {query ? 'No products matched your search.' : 'Search for products above.'}
        </p>
      ) : (
        <section className="space-y-4" aria-label="Search results">
          {products.map((product) => (
            <SearchResultCard key={product.sku} product={product} relatedProductMap={relatedProductMap} />
          ))}
        </section>
      )}

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
