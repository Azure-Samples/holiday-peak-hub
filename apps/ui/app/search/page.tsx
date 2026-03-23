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
import {
  SearchComparisonScorecard,
  type SearchComparisonItem,
} from '@/components/enrichment/SearchComparisonScorecard';
import { useIntelligentSearch } from '@/lib/hooks/useIntelligentSearch';
import { useRelatedProducts } from '@/lib/hooks/useRelatedProducts';
import { semanticSearchService } from '@/lib/services/semanticSearchService';

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
    failureKind: proxyFailure.failureKind,
    remediation: proxyFailure.remediation,
  };
}

function parseScore(value: unknown): number | undefined {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    return undefined;
  }

  return Number(value.toFixed(2));
}

function toScorecardItems(items: Array<Record<string, unknown>>): SearchComparisonItem[] {
  return items.map((item, index) => {
    const fallbackSku = `item-${index + 1}`;
    return {
      sku: String(item.sku ?? item.id ?? fallbackSku),
      score: parseScore(item.score ?? item.relevanceScore),
    };
  });
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
  const products = useMemo(() => data?.items ?? [], [data?.items]);
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
  const searchSource = data?.source;
  const fallbackReason = data?.fallback_reason;
  const isIntelligentFallback =
    data?.requested_mode === 'intelligent' && data?.source === 'crud';
  const showUnavailableAgentFallbackAlert =
    isIntelligentFallback && fallbackReason !== 'agent_mock';
  const [comparisonData, setComparisonData] = useState<{
    intelligent: SearchComparisonItem[];
    keyword: SearchComparisonItem[];
  } | null>(null);
  const [isComparisonLoading, setIsComparisonLoading] = useState(false);

  const proxyFailureLabelByKind: Record<'config' | 'network' | 'upstream', string> = {
    config: 'Catalog search proxy configuration is missing or invalid.',
    network: 'Catalog search backend is temporarily unreachable.',
    upstream: 'Catalog search backend returned a temporary gateway error.',
  };

  useEffect(() => {
    setQuery(initialQuery);
  }, [initialQuery]);

  useEffect(() => {
    const trimmedQuery = query.trim();
    if (!trimmedQuery) {
      setComparisonData(null);
      setIsComparisonLoading(false);
      return;
    }

    let isMounted = true;
    setIsComparisonLoading(true);

    const loadComparisonData = async () => {
      try {
        const [intelligentResult, keywordResult] = await Promise.allSettled([
          semanticSearchService.searchWithMode(trimmedQuery, 'intelligent', 8),
          semanticSearchService.searchWithMode(trimmedQuery, 'keyword', 8),
        ]);

        if (!isMounted) {
          return;
        }

        const intelligentFromComparison =
          intelligentResult.status === 'fulfilled'
            ? toScorecardItems(intelligentResult.value.items as unknown as Array<Record<string, unknown>>)
            : null;
        const keywordFromComparison =
          keywordResult.status === 'fulfilled'
            ? toScorecardItems(keywordResult.value.items as unknown as Array<Record<string, unknown>>)
            : null;

        const intelligent = intelligentFromComparison ?? [];
        const keyword = keywordFromComparison ?? [];

        if (intelligent.length > 0 || keyword.length > 0) {
          setComparisonData({ intelligent, keyword });
          return;
        }

        setComparisonData(null);
      } catch {
        if (isMounted) {
          setComparisonData(null);
        }
      } finally {
        if (isMounted) {
          setIsComparisonLoading(false);
        }
      }
    };

    void loadComparisonData();

    return () => {
      isMounted = false;
    };
  }, [query, products]);

  const handleSearch = (value: string) => {
    const trimmed = value.trim();
    setQuery(trimmed);
    if (trimmed) {
      router.push(`/search?q=${encodeURIComponent(trimmed)}`);
      return;
    }

    router.push('/search');
  };

  return (
    <MainLayout
      navigationProps={{
        onSearch: handleSearch,
      }}
    >
      <div className="mb-8 space-y-4">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Search</h1>
        <div className="flex flex-wrap items-center gap-2 rounded-xl border border-[var(--hp-border)] bg-[var(--hp-surface-strong)] p-3">
          <span className="text-xs font-semibold uppercase tracking-wide text-[var(--hp-text-muted)]">
            Demo flow
          </span>
          <Button size="sm" onClick={() => handleSearch('laptop')}>
            Run agent-friendly query
          </Button>
          <Link href="/search?agentChat=1" className="inline-flex">
            <Button size="sm" variant="secondary">
              Open popup comparison
            </Button>
          </Link>
        </div>
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
          {query ? <SearchModeIndicator source={searchSource ?? 'fallback'} /> : null}
          {resolvedMode === 'intelligent' && (
            <IntentClassificationDisplay
              intent={data?.intent?.intent}
              confidence={data?.intent?.confidence}
            />
          )}
        </div>
        {query && showUnavailableAgentFallbackAlert ? (
          <Alert
            variant="warning"
            title="Intelligent mode fell back to catalog"
            dismissible={false}
          >
            Results are from CRUD catalog search because the agent path was unavailable.
          </Alert>
        ) : null}
        <IntentPanel mode={resolvedMode} intent={data?.intent} subqueries={data?.subqueries} />
        {query && (
          <div aria-live="polite">
            {isComparisonLoading ? (
              <div className="rounded-xl border border-[var(--hp-border)] bg-[var(--hp-surface-strong)] p-3 text-sm text-[var(--hp-text-muted)]">
                Building intelligent-vs-keyword scorecard…
              </div>
            ) : comparisonData ? (
              <SearchComparisonScorecard
                intelligent={comparisonData.intelligent}
                keyword={comparisonData.keyword}
              />
            ) : null}
          </div>
        )}
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
            {resolvedMode === 'intelligent' ? 'Intelligent Search' : 'Keyword Search'} • Source:{' '}
            {searchSource === 'agent' ? 'Agent API' : 'CRUD Catalog'}
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
