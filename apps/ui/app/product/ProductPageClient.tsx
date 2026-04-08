'use client';

import React, { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { useRouter } from 'next/navigation';
import { MainLayout } from '@/components/templates/MainLayout';
import { Badge } from '@/components/atoms/Badge';
import { Button } from '@/components/atoms/Button';
import { Modal } from '@/components/molecules/Modal';
import { cn } from '@/components/utils';
import { useProduct } from '@/lib/hooks/useProducts';
import { useCategories } from '@/lib/hooks/useCategories';
import { mapApiProductToUiProduct } from '@/lib/utils/productMappers';
import { formatAgentResponse, type AgentMessageView } from '@/lib/utils/agentResponseCards';
import AgentMessageDisplay from '@/components/organisms/AgentMessageDisplay';
import { UseCaseTags } from '@/components/enrichment/UseCaseTags';
import { RelatedProductsRail } from '@/components/enrichment/RelatedProductsRail';
import { useRelatedProducts } from '@/lib/hooks/useRelatedProducts';
import agentApiClient from '@/lib/api/agentClient';
import { trackEcommerceEvent } from '@/lib/utils/telemetry';
import { FiArrowRight, FiShoppingCart, FiTruck, FiShield, FiRotateCcw } from 'react-icons/fi';

type FitVerdict = 'fits' | 'partial' | 'not_fit' | 'unknown';

type FitAssessment = {
  verdict: FitVerdict;
  confidence?: number;
  reasonsForFit: string[];
  reasonsAgainst: string[];
  recommendation: string;
};

type ProductContext = {
  name: string;
  description: string;
  features: string[];
  inStock: boolean;
};

const toRecord = (value: unknown): Record<string, unknown> | null => {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return null;
  }
  return value as Record<string, unknown>;
};

const toString = (value: unknown): string | undefined => {
  if (typeof value === 'string') {
    return value;
  }
  if (typeof value === 'number' || typeof value === 'boolean') {
    return String(value);
  }
  return undefined;
};

const toStringArray = (value: unknown): string[] => {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.map((entry) => toString(entry)).filter((entry): entry is string => Boolean(entry));
};

const parseVerdict = (value: unknown): FitVerdict => {
  const normalized = (toString(value) || '').trim().toLowerCase();
  if (['fits', 'fit', 'yes', 'works', 'good_fit'].includes(normalized)) {
    return 'fits';
  }
  if (['partial', 'maybe', 'partially_fits'].includes(normalized)) {
    return 'partial';
  }
  if (['not_fit', 'not fit', 'no', 'does_not_fit'].includes(normalized)) {
    return 'not_fit';
  }
  return 'unknown';
};

const deriveFitAssessment = (payload: unknown, fallbackText: string): FitAssessment => {
  const base = toRecord(payload) || {};
  const enrichment = toRecord((base as Record<string, unknown>).enriched_product) || {};
  const nestedFit = toRecord((base as Record<string, unknown>).fit_assessment) || {};

  const confidenceRaw =
    (base.confidence as number | string | undefined) ??
    (nestedFit.confidence as number | string | undefined) ??
    (enrichment.confidence as number | string | undefined);
  const confidenceNumber =
    typeof confidenceRaw === 'number'
      ? confidenceRaw
      : typeof confidenceRaw === 'string'
        ? Number(confidenceRaw)
        : undefined;

  const verdict = parseVerdict(
    base.fit_verdict || base.fit || nestedFit.fit_verdict || nestedFit.fit || enrichment.fit_verdict || enrichment.fit,
  );
  const reasonsForFit = toStringArray(
    base.reasons_for_fit || nestedFit.reasons_for_fit || enrichment.reasons_for_fit || base.reasons || enrichment.reasons,
  );
  const reasonsAgainst = toStringArray(
    base.reasons_against || nestedFit.reasons_against || enrichment.reasons_against || base.caveats || enrichment.caveats,
  );
  const recommendation =
    toString(base.recommendation || nestedFit.recommendation || enrichment.recommendation) ||
    toString(base.summary || nestedFit.summary || enrichment.summary) ||
    fallbackText;

  return {
    verdict,
    confidence: Number.isFinite(confidenceNumber as number) ? (confidenceNumber as number) : undefined,
    reasonsForFit,
    reasonsAgainst,
    recommendation,
  };
};

const tokenizeUseCase = (text: string): string[] => {
  return text
    .toLowerCase()
    .split(/[^a-z0-9]+/)
    .filter((token) => token.length > 2);
};

const buildLocalFitAssessment = (useCase: string, productContext: ProductContext): FitAssessment => {
  const useCaseTokens = tokenizeUseCase(useCase);
  const corpus = [productContext.name, productContext.description, ...productContext.features].join(' ').toLowerCase();

  const matched = useCaseTokens.filter((token) => corpus.includes(token));
  const missing = useCaseTokens.filter((token) => !corpus.includes(token));

  const baseScore = useCaseTokens.length > 0 ? matched.length / useCaseTokens.length : 0.4;
  const confidence = Math.max(0.15, Math.min(0.95, baseScore + (productContext.inStock ? 0.12 : -0.08)));

  const verdict: FitVerdict = confidence >= 0.65 ? 'fits' : confidence >= 0.45 ? 'partial' : 'not_fit';

  const reasonsForFit = [
    ...matched.slice(0, 3).map((token) => `Matches use-case signal: ${token}`),
    ...(productContext.inStock ? ['Currently in stock.'] : []),
  ];

  const reasonsAgainst = [
    ...missing.slice(0, 3).map((token) => `No direct evidence for: ${token}`),
    ...(!productContext.inStock ? ['Stock signal is weak for immediate purchase.'] : []),
  ];

  const recommendation =
    verdict === 'fits'
      ? 'This product appears to fit your stated use case.'
      : verdict === 'partial'
        ? 'This product may fit partially; review constraints before buying.'
        : 'This product does not look ideal for your stated use case.';

  return {
    verdict,
    confidence: Number(confidence.toFixed(2)),
    reasonsForFit,
    reasonsAgainst,
    recommendation,
  };
};

const isGenericAssessment = (assessment: FitAssessment): boolean => {
  const recommendation = assessment.recommendation.toLowerCase();
  const hasReasons = assessment.reasonsForFit.length > 0 || assessment.reasonsAgainst.length > 0;

  if (assessment.verdict === 'unknown') {
    return true;
  }

  if (!hasReasons && (recommendation.includes('acp-supplied') || recommendation.includes('rich,'))) {
    return true;
  }

  return false;
};

const verdictBadgeClass = (verdict: FitVerdict): string => {
  if (verdict === 'fits') {
    return 'bg-[var(--hp-accent)]/20 text-[var(--hp-accent)]';
  }
  if (verdict === 'partial') {
    return 'bg-[var(--hp-focus)]/20 text-[var(--hp-focus)]';
  }
  if (verdict === 'not_fit') {
    return 'bg-[var(--hp-primary)]/20 text-[var(--hp-primary)]';
  }
  return 'bg-[var(--hp-surface-strong)] text-[var(--hp-text-muted)]';
};

export function ProductPageClient({ productId }: { productId: string }) {
  const router = useRouter();
  const { data: product, isLoading, isError } = useProduct(productId);
  const { data: categories = [] } = useCategories();

  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [showFitPrompt, setShowFitPrompt] = useState(false);
  const [useCaseInput, setUseCaseInput] = useState('');
  const [fitLoading, setFitLoading] = useState(false);
  const [fitError, setFitError] = useState<string | null>(null);
  const [fitResponseView, setFitResponseView] = useState<AgentMessageView | null>(null);
  const [fitAssessment, setFitAssessment] = useState<FitAssessment | null>(null);
  const uiProduct = useMemo(() => (product ? mapApiProductToUiProduct(product) : null), [product]);
  const relatedProductIds = useMemo(() => {
    if (!uiProduct) {
      return [];
    }

    return Array.from(
      new Set([...(uiProduct.complementaryProducts || []), ...(uiProduct.substituteProducts || [])]),
    );
  }, [uiProduct]);
  const { data: relatedProductMap = {} } = useRelatedProducts(relatedProductIds);

  useEffect(() => {
    if (!product?.category_id) {
      return;
    }
    setSelectedCategory(product.category_id);
  }, [product?.category_id]);

  const categoryList = useMemo(() => {
    if (categories.length > 0) {
      return categories;
    }
    if (!product?.category_id) {
      return [];
    }
    return [
      {
        id: product.category_id,
        name: product.category_id,
        description: 'Current product category',
      },
    ];
  }, [categories, product?.category_id]);

  useEffect(() => {
    if (!product) {
      return;
    }

    trackEcommerceEvent('product_opened', {
      sku: product.id,
      source: 'product_page',
    });
  }, [product]);

  const handleAddToCartClick = () => {
    if (!product) {
      return;
    }

    trackEcommerceEvent('add_to_cart_clicked', {
      sku: product.id,
      source: 'product_page',
      in_stock: product.in_stock,
    });
  };

  const handleRunFitEvaluation = async () => {
    if (!product || !useCaseInput.trim()) {
      return;
    }

    setFitLoading(true);
    setFitError(null);

    try {
      const response = await agentApiClient.post('/ecommerce-product-detail-enrichment/invoke', {
        sku: product.id,
        use_case: useCaseInput.trim(),
        message: `Evaluate if this product fits my use case: ${useCaseInput.trim()}`,
      });

      const remoteView = formatAgentResponse(response.data);
      const remoteAssessment = deriveFitAssessment(response.data, remoteView.text);

      if (isGenericAssessment(remoteAssessment)) {
        const localAssessment = buildLocalFitAssessment(useCaseInput, {
          name: product.name,
          description: product.description,
          features: product.features || [],
          inStock: product.in_stock,
        });

        setFitAssessment(localAssessment);
        setFitResponseView(
          formatAgentResponse({
            summary: localAssessment.recommendation,
            fit_verdict: localAssessment.verdict,
            confidence: localAssessment.confidence,
            reasons_for_fit: localAssessment.reasonsForFit,
            reasons_against: localAssessment.reasonsAgainst,
            recommendation: localAssessment.recommendation,
          }),
        );
      } else {
        setFitAssessment(remoteAssessment);
        setFitResponseView(remoteView);
      }
    } catch (error: unknown) {
      const detail =
        typeof error === 'object' &&
        error !== null &&
        'message' in error &&
        typeof (error as { message?: unknown }).message === 'string'
          ? (error as { message: string }).message
          : 'The product enrichment agent could not evaluate this use case right now.';
      setFitError(detail);
    } finally {
      setFitLoading(false);
    }
  };

  return (
    <MainLayout>
      {isLoading && (
        <div className="animate-pulse space-y-6 px-4 md:px-8 lg:px-12 max-w-7xl mx-auto">
          <div className="h-4 w-48 rounded bg-gray-200 dark:bg-gray-800" />
          <div className="grid grid-cols-1 gap-10 lg:grid-cols-[280px_1fr]">
            <div className="hidden lg:block space-y-3">
              {Array.from({ length: 8 }).map((_, i) => (
                <div key={i} className="h-10 rounded-xl bg-gray-100 dark:bg-gray-800" />
              ))}
            </div>
            <div className="grid grid-cols-1 gap-10 xl:grid-cols-2">
              <div className="aspect-square rounded-2xl bg-gray-100 dark:bg-gray-800 relative overflow-hidden">
                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/60 to-transparent dark:via-white/5 -translate-x-full animate-[shimmer_2s_ease-in-out_infinite]" />
              </div>
              <div className="space-y-4">
                <div className="flex gap-2">
                  <div className="h-6 w-24 rounded-full bg-gray-200 dark:bg-gray-800" />
                  <div className="h-6 w-16 rounded-full bg-gray-200 dark:bg-gray-800" />
                </div>
                <div className="h-8 w-3/4 rounded bg-gray-200 dark:bg-gray-800" />
                <div className="h-4 w-full rounded bg-gray-100 dark:bg-gray-800" />
                <div className="h-4 w-2/3 rounded bg-gray-100 dark:bg-gray-800" />
                <div className="h-10 w-32 rounded-full bg-gray-200 dark:bg-gray-800 mt-6" />
              </div>
            </div>
          </div>
        </div>
      )}

      {!isLoading && isError && (
        <div className="mx-auto max-w-md text-center py-20 px-4">
          <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-red-50 dark:bg-red-900/20">
            <FiShield className="h-8 w-8 text-red-500" />
          </div>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">Product unavailable</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400">We couldn&apos;t load this product from the backend. Please try again later.</p>
        </div>
      )}

      {!isLoading && !isError && uiProduct && product && (
        <div className="px-4 md:px-8 lg:px-12 max-w-7xl mx-auto">
          {/* Breadcrumb */}
          <nav className="mb-6 flex items-center gap-2 text-xs text-gray-400 dark:text-gray-500 font-medium">
            <Link href="/" className="hover:text-gray-900 dark:hover:text-white transition-colors">Home</Link>
            <span>/</span>
            <Link
              href={`/category?slug=${encodeURIComponent(product.category_id)}`}
              className="hover:text-gray-900 dark:hover:text-white transition-colors"
            >
              {product.category_id}
            </Link>
            <span>/</span>
            <span className="text-gray-700 dark:text-gray-300 truncate max-w-[200px]">{product.name}</span>
          </nav>

          <section className="grid grid-cols-1 gap-10 lg:grid-cols-[240px_1fr]" aria-label="Product detail">
            {/* ── Category Sidebar ── */}
            <aside className="hidden lg:block">
              <div className="sticky top-24 rounded-2xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900 p-4 shadow-sm">
                <p className="mb-3 text-[10px] font-semibold uppercase tracking-widest text-gray-400">Categories</p>
                <nav className="space-y-0.5">
                  {categoryList.map((category) => {
                    const isActive = category.id === selectedCategory;
                    return (
                      <button
                        key={category.id}
                        type="button"
                        onClick={() => {
                          setSelectedCategory(category.id);
                          router.push(`/category?slug=${encodeURIComponent(category.id)}`);
                        }}
                        className={cn(
                          'w-full rounded-lg px-3 py-2 text-left text-sm transition-all duration-200',
                          isActive
                            ? 'bg-gray-900 dark:bg-white text-white dark:text-gray-900 font-semibold shadow-sm'
                            : 'text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-white'
                        )}
                      >
                        {category.name}
                      </button>
                    );
                  })}
                </nav>
              </div>
            </aside>

            {/* ── Main Content ── */}
            <div className="min-w-0">
              <section className="grid grid-cols-1 gap-10 xl:grid-cols-2 items-start" aria-label="Product overview">
                {/* ── Image ── */}
                <div className="group relative aspect-square w-full overflow-hidden rounded-2xl bg-gray-50 dark:bg-gray-800/50 border border-gray-100 dark:border-gray-800">
                  {/* Animated shimmer skeleton behind the image */}
                  <div className="absolute inset-0 bg-gradient-to-br from-gray-100 via-gray-50 to-gray-100 dark:from-gray-800 dark:via-gray-900 dark:to-gray-800">
                    <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/40 to-transparent dark:via-white/5 -translate-x-full animate-[shimmer_3s_ease-in-out_infinite]" />
                    {/* Decorative SVG pattern on placeholder */}
                    <svg className="absolute inset-0 w-full h-full opacity-[0.03] dark:opacity-[0.06]" xmlns="http://www.w3.org/2000/svg">
                      <defs>
                        <pattern id="grid" width="32" height="32" patternUnits="userSpaceOnUse">
                          <path d="M 32 0 L 0 0 0 32" fill="none" stroke="currentColor" strokeWidth="0.5"/>
                        </pattern>
                      </defs>
                      <rect width="100%" height="100%" fill="url(#grid)" />
                    </svg>
                    <div className="absolute inset-0 flex items-center justify-center">
                      <div className="text-gray-300 dark:text-gray-600">
                        <svg className="w-16 h-16 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="m2.25 15.75 5.159-5.159a2.25 2.25 0 0 1 3.182 0l5.159 5.159m-1.5-1.5 1.409-1.409a2.25 2.25 0 0 1 3.182 0l2.909 2.909M3.75 21h16.5A2.25 2.25 0 0 0 22.5 18.75V5.25A2.25 2.25 0 0 0 20.25 3H3.75A2.25 2.25 0 0 0 1.5 5.25v13.5A2.25 2.25 0 0 0 3.75 21Z" />
                        </svg>
                      </div>
                    </div>
                  </div>
                  <Image
                    src={uiProduct.thumbnail || '/images/products/p1.jpg'}
                    alt={product.name}
                    width={800}
                    height={800}
                    className="relative z-10 h-full w-full object-cover object-center transition-transform duration-700 ease-out group-hover:scale-[1.03]"
                  />
                  {/* Floating image tags */}
                  {uiProduct.tags && uiProduct.tags.length > 0 && (
                    <div className="absolute top-4 left-4 z-20 flex flex-wrap gap-1.5">
                       {uiProduct.tags.slice(0, 2).map((tag) => (
                         <span key={tag} className="rounded-full bg-white/90 dark:bg-black/60 backdrop-blur-sm px-2.5 py-0.5 text-[10px] font-semibold text-gray-800 dark:text-white shadow-sm">
                           {tag}
                         </span>
                       ))}
                    </div>
                  )}
                </div>

                {/* ── Product Info ── */}
                <div className="flex flex-col py-1">
                  {/* Status Badges */}
                  <div className="mb-4 flex flex-wrap items-center gap-2">
                    <Badge size="sm" className="bg-gray-900 dark:bg-white text-white dark:text-gray-900 border-none text-[10px] px-2.5 py-1">
                      Agent Enriched
                    </Badge>
                    {product.in_stock ? (
                      <Badge size="sm" className="bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800 text-[10px] px-2.5 py-1">
                        In Stock
                      </Badge>
                    ) : (
                      <Badge size="sm" className="bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 border border-red-200 dark:border-red-800 text-[10px] px-2.5 py-1">
                        Out of Stock
                      </Badge>
                    )}
                  </div>

                  {/* Title */}
                  <h1 className="mb-2 text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white leading-tight tracking-tight">{product.name}</h1>
                  <p className="mb-6 text-sm text-gray-500 dark:text-gray-400 leading-relaxed max-w-lg">{product.description}</p>

                  {/* Price + Rating */}
                  <div className="mb-6 flex items-baseline gap-3">
                    <span className="text-3xl font-bold text-gray-900 dark:text-white tabular-nums">${product.price.toFixed(2)}</span>
                    {typeof product.rating === 'number' && (
                      <span className="flex items-center gap-1 text-sm text-gray-400">
                        <span className="text-amber-500">★</span>
                        <span className="font-medium text-gray-600 dark:text-gray-300">{product.rating.toFixed(1)}</span>
                        <span>({product.review_count || 0})</span>
                      </span>
                    )}
                  </div>

                  {/* Enriched insight card */}
                  {uiProduct.enrichedDescription && (
                    <div className="mb-6 rounded-xl border border-gray-100 dark:border-gray-800 bg-gray-50/50 dark:bg-gray-800/30 p-4">
                      <p className="mb-1 flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-widest text-gray-400">
                        <span className="h-1.5 w-1.5 rounded-full bg-blue-500 animate-pulse" /> AI Insight
                      </p>
                      <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">{uiProduct.enrichedDescription}</p>
                    </div>
                  )}

                  {/* ── Action Buttons ── */}
                  <div className="mb-8 flex flex-wrap items-center gap-3">
                    <Button
                      size="md"
                      className="rounded-full bg-gray-900 dark:bg-white text-white dark:text-gray-900 hover:bg-gray-700 dark:hover:bg-gray-100 shadow-sm"
                      onClick={handleAddToCartClick}
                      disabled={!product.in_stock}
                      iconLeft={<FiShoppingCart className="h-4 w-4" />}
                    >
                      Add to cart
                    </Button>

                    <Button
                      variant="ghost"
                      size="md"
                      className="rounded-full border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800"
                      onClick={() => setShowFitPrompt(true)}
                    >
                      Does this fit?
                      <FiArrowRight className="ml-1.5 h-3.5 w-3.5 transition-transform duration-200 group-hover:translate-x-0.5" />
                    </Button>
                  </div>

                  {/* Use cases & Related */}
                  <div className="space-y-5">
                    <UseCaseTags useCases={uiProduct.useCases} />
                    <RelatedProductsRail
                      title="Complements"
                      items={uiProduct.complementaryProducts}
                      productMap={relatedProductMap}
                    />
                    <RelatedProductsRail
                      title="Alternatives"
                      items={uiProduct.substituteProducts}
                      productMap={relatedProductMap}
                    />
                  </div>

                  {/* ── Fit Evaluation Modal ── */}
                  <Modal
                    isOpen={showFitPrompt}
                    onClose={() => {
                      setShowFitPrompt(false);
                      setFitError(null);
                    }}
                    title="Does this product fit your needs?"
                    size="lg"
                  >
                    <div className="space-y-4">
                      <label htmlFor="fit-use-case" className="block text-sm font-semibold text-gray-900 dark:text-white">
                        Describe your use case
                      </label>
                      <textarea
                        id="fit-use-case"
                        value={useCaseInput}
                        onChange={(event) => setUseCaseInput(event.target.value)}
                        placeholder="e.g. 'I need running tights for cold winter mornings...'"
                        rows={3}
                        className="w-full rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 px-4 py-3 text-sm text-gray-900 dark:text-white placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-gray-900 dark:focus:ring-white focus:border-transparent transition-shadow duration-200 resize-none"
                      />

                      <div className="flex items-center gap-3">
                        <Button
                          size="sm"
                          className="rounded-full bg-gray-900 dark:bg-white text-white dark:text-gray-900 hover:bg-gray-700 dark:hover:bg-gray-100"
                          onClick={handleRunFitEvaluation}
                          disabled={fitLoading || useCaseInput.trim().length === 0}
                        >
                          {fitLoading ? 'Analyzing…' : 'Analyze fit'}
                        </Button>
                        <button
                          type="button"
                          className="text-xs font-medium text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors"
                          onClick={() => {
                            setShowFitPrompt(false);
                            setFitError(null);
                          }}
                        >
                          Cancel
                        </button>
                      </div>

                      {fitError && (
                        <div className="rounded-xl border border-red-200 dark:border-red-900 bg-red-50 dark:bg-red-900/10 px-4 py-3">
                          <p className="text-xs font-medium text-red-600 dark:text-red-400">{fitError}</p>
                        </div>
                      )}

                      {fitAssessment && fitResponseView && (
                        <div className="space-y-4 pt-4 border-t border-gray-100 dark:border-gray-800">
                          <div className="flex flex-wrap items-center justify-between gap-3">
                            <h3 className="text-sm font-bold text-gray-900 dark:text-white">AI Fit Evaluation</h3>
                            <Badge size="sm" className={`${verdictBadgeClass(fitAssessment.verdict)} text-xs px-2.5 py-1 font-semibold rounded-full`}>
                              {fitAssessment.verdict === 'fits'
                                ? '✓ Fits'
                                : fitAssessment.verdict === 'partial'
                                  ? '~ Partial'
                                  : fitAssessment.verdict === 'not_fit'
                                    ? '✕ No fit'
                                    : 'Review'}
                            </Badge>
                          </div>

                          <div className="grid gap-3 sm:grid-cols-2">
                            <div className="rounded-xl border border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-800/50 p-3">
                              <p className="mb-0.5 text-[10px] font-semibold uppercase tracking-widest text-gray-400">Confidence</p>
                              <p className="text-xl font-bold text-gray-900 dark:text-white tabular-nums">
                                {typeof fitAssessment.confidence === 'number'
                                  ? `${Math.round(fitAssessment.confidence * (fitAssessment.confidence <= 1 ? 100 : 1))}%`
                                  : 'N/A'}
                              </p>
                            </div>
                            <div className="rounded-xl border border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-800/50 p-3">
                              <p className="mb-0.5 text-[10px] font-semibold uppercase tracking-widest text-gray-400">Summary</p>
                              <p className="text-xs text-gray-700 dark:text-gray-300 leading-relaxed">{fitAssessment.recommendation}</p>
                            </div>
                          </div>

                          {fitAssessment.reasonsForFit.length > 0 && (
                            <div>
                              <p className="mb-2 text-[10px] font-semibold uppercase tracking-widest text-emerald-600">Positive signals</p>
                              <ul className="grid gap-1.5">
                                {fitAssessment.reasonsForFit.slice(0, 4).map((reason, index) => (
                                  <li key={`fit-reason-${index}`} className="flex items-start gap-2 rounded-lg bg-emerald-50 dark:bg-emerald-900/10 border border-emerald-100 dark:border-emerald-900/30 px-3 py-2 text-xs text-gray-700 dark:text-gray-300">
                                    <span className="text-emerald-500 mt-px shrink-0">✦</span> {reason}
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}

                          {fitAssessment.reasonsAgainst.length > 0 && (
                            <div>
                              <p className="mb-2 text-[10px] font-semibold uppercase tracking-widest text-amber-600">Considerations</p>
                              <ul className="grid gap-1.5">
                                {fitAssessment.reasonsAgainst.slice(0, 4).map((reason, index) => (
                                  <li key={`fit-constraint-${index}`} className="flex items-start gap-2 rounded-lg bg-amber-50 dark:bg-amber-900/10 border border-amber-100 dark:border-amber-900/30 px-3 py-2 text-xs text-gray-700 dark:text-gray-300">
                                    <span className="text-amber-500 mt-px shrink-0">✧</span> {reason}
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}

                          <div className="pt-4 border-t border-gray-100 dark:border-gray-800">
                            <AgentMessageDisplay compact view={fitResponseView} />
                          </div>
                        </div>
                      )}
                    </div>
                  </Modal>
                </div>
              </section>
            </div>
          </section>

          {/* ── Feature Strip ── */}
          <div className="mt-12 mb-8 rounded-2xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900 p-6 shadow-sm">
            <div className="grid grid-cols-1 divide-y sm:divide-y-0 sm:divide-x divide-gray-100 dark:divide-gray-800 sm:grid-cols-3">
              <Feature icon={<FiTruck className="w-5 h-5" />} title="Fast delivery" description="AI-optimized carrier routing for best ETA." />
              <Feature icon={<FiRotateCcw className="w-5 h-5" />} title="Easy returns" description="Instant agent-assisted processing." />
              <Feature icon={<FiShield className="w-5 h-5" />} title="Verified quality" description="Specs validated by AI specialists." />
            </div>
          </div>
        </div>
      )}
    </MainLayout>
  );
}

function Feature({ icon, title, description }: { icon: React.ReactNode; title: string; description: string }) {
  return (
    <div className="flex items-start gap-3 px-4 sm:px-6 py-4 sm:py-0">
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gray-50 dark:bg-gray-800 text-gray-600 dark:text-gray-400">
        {icon}
      </div>
      <div>
        <h4 className="text-sm font-semibold text-gray-900 dark:text-white">{title}</h4>
        <p className="text-xs text-gray-500 dark:text-gray-400 leading-relaxed mt-0.5">{description}</p>
      </div>
    </div>
  );
}
