'use client';

import React, { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { useRouter } from 'next/navigation';
import { MainLayout } from '@/components/templates/MainLayout';
import { Badge } from '@/components/atoms/Badge';
import { Button } from '@/components/atoms/Button';
import { Card } from '@/components/molecules/Card';
import { useProduct, useTriggerProductEnrichment } from '@/lib/hooks/useProducts';
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
  const [triggerEnrichmentStatus, setTriggerEnrichmentStatus] = useState<string | null>(null);
  const [triggerEnrichmentError, setTriggerEnrichmentError] = useState<string | null>(null);
  const triggerProductEnrichment = useTriggerProductEnrichment();

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

  const handleTriggerEnrichmentJob = async () => {
    if (!product?.id) {
      return;
    }

    setTriggerEnrichmentError(null);
    setTriggerEnrichmentStatus(null);

    try {
      const response = await triggerProductEnrichment.mutateAsync({
        productId: product.id,
        payload: {
          trigger_source: 'product_page',
        },
      });

      setTriggerEnrichmentStatus(`Queued at ${new Date(response.queued_at).toLocaleString()}`);
    } catch (triggerError: unknown) {
      const message =
        triggerError instanceof Error ? triggerError.message : 'Failed to trigger enrichment job.';
      setTriggerEnrichmentError(message);
    }
  };

  return (
    <MainLayout>
      {isLoading && (
        <div className="animate-pulse space-y-6">
          <div className="h-6 w-1/3 rounded bg-[var(--hp-surface-strong)]" />
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <div className="aspect-square rounded-2xl bg-[var(--hp-surface-strong)]" />
            <div className="space-y-4">
              <div className="h-8 w-3/4 rounded bg-[var(--hp-surface-strong)]" />
              <div className="h-6 w-1/4 rounded bg-[var(--hp-surface-strong)]" />
              <div className="h-24 w-full rounded bg-[var(--hp-surface-strong)]" />
            </div>
          </div>
        </div>
      )}

      {!isLoading && isError && (
        <Card className="border border-[var(--hp-primary)]/30 p-6">
          <p className="text-[var(--hp-primary)]">Product could not be loaded from the cloud backend.</p>
        </Card>
      )}

      {!isLoading && !isError && uiProduct && product && (
        <>
          <nav className="mb-6 flex items-center gap-2 text-sm text-[var(--hp-text-muted)]">
            <Link href="/" className="hover:text-[var(--hp-primary)]">Home</Link>
            <span>/</span>
            <Link
              href={`/category?slug=${encodeURIComponent(product.category_id)}`}
              className="hover:text-[var(--hp-primary)]"
            >
              {product.category_id}
            </Link>
            <span>/</span>
            <span className="text-[var(--hp-text)]">{product.name}</span>
          </nav>

          <section
            className="mb-12 grid grid-cols-1 gap-8 lg:grid-cols-[220px_1fr]"
            aria-label="Product detail and category navigation"
          >
            <aside className="h-fit rounded-2xl border border-[var(--hp-border)] bg-[var(--hp-surface)] p-4 lg:sticky lg:top-20">
              <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-[var(--hp-text-muted)]">Categories</p>
              <div className="space-y-2">
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
                      className={`w-full rounded-xl border px-3 py-2 text-left text-sm font-medium transition-colors ${
                        isActive
                          ? 'border-[var(--hp-primary)] bg-[var(--hp-surface-strong)] text-[var(--hp-primary)]'
                          : 'border-[var(--hp-border)] bg-[var(--hp-surface)] text-[var(--hp-text-muted)] hover:text-[var(--hp-text)]'
                      }`}
                    >
                      {category.name}
                    </button>
                  );
                })}
              </div>
            </aside>

            <div>
              <section className="grid grid-cols-1 gap-12 xl:grid-cols-2" aria-label="Product overview">
                <div className="aspect-square overflow-hidden rounded-2xl bg-[var(--hp-surface-strong)]">
                  <Image
                    src={uiProduct.thumbnail || '/images/products/p1.jpg'}
                    alt={product.name}
                    width={800}
                    height={800}
                    className="h-full w-full object-cover"
                  />
                </div>

                <div>
                  <div className="mb-4 flex items-center gap-3">
                    <Badge className="bg-[var(--hp-primary)] text-white">Agent Enriched</Badge>
                    {product.in_stock ? (
                      <Badge className="bg-[var(--hp-accent)]/20 text-[var(--hp-accent)]">In Stock</Badge>
                    ) : (
                      <Badge className="bg-[var(--hp-primary)]/20 text-[var(--hp-primary)]">Out of Stock</Badge>
                    )}
                  </div>

                  <h1 className="mb-2 text-3xl font-black text-[var(--hp-text)]">{product.name}</h1>
                  <p className="mb-6 text-[var(--hp-text-muted)]">{product.description}</p>

                  {uiProduct.enrichedDescription ? (
                    <Card className="mb-6 border border-[var(--hp-border)] bg-[var(--hp-surface)] p-4">
                      <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-[var(--hp-text-muted)]">
                        Enriched description
                      </p>
                      <p className="text-sm text-[var(--hp-text)]">{uiProduct.enrichedDescription}</p>
                    </Card>
                  ) : null}

                  <div className="mb-6 space-y-4">
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

                  <div className="mb-6 flex items-end gap-3">
                    <span className="text-4xl font-black text-[var(--hp-primary)]">${product.price.toFixed(2)}</span>
                    {typeof product.rating === 'number' && (
                      <span className="text-sm text-[var(--hp-text-muted)]">
                        ★ {product.rating.toFixed(1)}{product.review_count ? ` (${product.review_count})` : ''}
                      </span>
                    )}
                  </div>

                  <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
                    <Button
                      size="lg"
                      className="w-full sm:w-auto"
                      onClick={handleAddToCartClick}
                      disabled={!product.in_stock}
                    >
                      <FiShoppingCart className="mr-2 h-5 w-5" />
                      Add to Cart
                    </Button>

                    <Button
                      variant="outline"
                      size="lg"
                      className="w-full border-[var(--hp-primary)]/55 text-[var(--hp-primary)] hover:bg-[var(--hp-primary)]/10 sm:w-auto"
                      onClick={() => setShowFitPrompt((current) => !current)}
                    >
                      Does this fits my case?
                      <FiArrowRight className="ml-2 h-4 w-4" />
                    </Button>

                    <Button
                      variant="secondary"
                      size="lg"
                      className="w-full sm:w-auto"
                      onClick={() => {
                        void handleTriggerEnrichmentJob();
                      }}
                      loading={triggerProductEnrichment.isPending}
                    >
                      Trigger enrichment job
                    </Button>
                  </div>

                  {triggerEnrichmentStatus ? (
                    <p className="mt-2 text-sm text-[var(--hp-accent)]">{triggerEnrichmentStatus}</p>
                  ) : null}
                  {triggerEnrichmentError ? (
                    <p className="mt-2 text-sm text-[var(--hp-primary)]">{triggerEnrichmentError}</p>
                  ) : null}

                  {showFitPrompt ? (
                    <Card className="mt-4 border border-[var(--hp-border)] bg-[var(--hp-surface)] p-4 text-[var(--hp-text)]">
                      <label htmlFor="fit-use-case" className="mb-2 block text-sm font-semibold text-[var(--hp-text)]">
                        Describe your use case
                      </label>
                      <textarea
                        id="fit-use-case"
                        value={useCaseInput}
                        onChange={(event) => setUseCaseInput(event.target.value)}
                        placeholder="Example: I need this product for daily travel, outdoor use, and long battery life."
                        rows={4}
                        className="w-full rounded-xl border border-[var(--hp-border)] bg-[var(--hp-surface-strong)] px-3 py-2 text-sm text-[var(--hp-text)] placeholder:text-[var(--hp-text-muted)]"
                      />
                      <div className="mt-3 flex items-center gap-2">
                        <Button
                          size="sm"
                          onClick={handleRunFitEvaluation}
                          disabled={fitLoading || useCaseInput.trim().length === 0}
                        >
                          {fitLoading ? 'Evaluating...' : 'Evaluate fit'}
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-[var(--hp-text-muted)] hover:text-[var(--hp-text)]"
                          onClick={() => {
                            setShowFitPrompt(false);
                            setFitError(null);
                          }}
                        >
                          Close
                        </Button>
                      </div>
                    </Card>
                  ) : null}

                  {uiProduct.tags && uiProduct.tags.length > 0 && (
                    <div className="mt-6 flex flex-wrap gap-2">
                      {uiProduct.tags.map((tag) => (
                        <Badge key={tag} className="bg-[var(--hp-accent)]/20 text-[var(--hp-accent)]">
                          {tag}
                        </Badge>
                      ))}
                    </div>
                  )}

                  {fitError ? (
                    <Card className="mt-4 border border-[var(--hp-primary)]/30 p-4">
                      <p className="text-sm text-[var(--hp-primary)]">{fitError}</p>
                    </Card>
                  ) : null}

                  {fitAssessment && fitResponseView ? (
                    <Card className="mt-4 border border-[var(--hp-border)] p-4">
                      <div className="mb-3 flex items-center justify-between gap-3">
                        <h3 className="text-sm font-semibold text-[var(--hp-text)]">Use case evaluation</h3>
                        <Badge className={verdictBadgeClass(fitAssessment.verdict)}>
                          {fitAssessment.verdict === 'fits'
                            ? 'Fits'
                            : fitAssessment.verdict === 'partial'
                              ? 'Partially fits'
                              : fitAssessment.verdict === 'not_fit'
                                ? 'Does not fit'
                                : 'Needs review'}
                        </Badge>
                      </div>

                      <div className="mb-3 grid gap-2 text-sm sm:grid-cols-2">
                        <div className="rounded-lg border border-[var(--hp-border)] bg-[var(--hp-surface)] p-2">
                          <p className="text-xs font-semibold uppercase tracking-wide text-[var(--hp-text-muted)]">Confidence</p>
                          <p className="text-[var(--hp-text)]">
                            {typeof fitAssessment.confidence === 'number'
                              ? `${Math.round(fitAssessment.confidence * (fitAssessment.confidence <= 1 ? 100 : 1))}%`
                              : 'Not provided'}
                          </p>
                        </div>
                        <div className="rounded-lg border border-[var(--hp-border)] bg-[var(--hp-surface)] p-2">
                          <p className="text-xs font-semibold uppercase tracking-wide text-[var(--hp-text-muted)]">Recommendation</p>
                          <p className="text-[var(--hp-text)]">{fitAssessment.recommendation}</p>
                        </div>
                      </div>

                      {fitAssessment.reasonsForFit.length > 0 ? (
                        <div className="mb-3">
                          <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-[var(--hp-text-muted)]">Why it fits</p>
                          <ul className="space-y-1 text-sm text-[var(--hp-text)]">
                            {fitAssessment.reasonsForFit.slice(0, 4).map((reason, index) => (
                              <li key={`fit-reason-${index}`} className="rounded-md bg-[var(--hp-surface)] px-2 py-1">{reason}</li>
                            ))}
                          </ul>
                        </div>
                      ) : null}

                      {fitAssessment.reasonsAgainst.length > 0 ? (
                        <div className="mb-3">
                          <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-[var(--hp-text-muted)]">Possible constraints</p>
                          <ul className="space-y-1 text-sm text-[var(--hp-text)]">
                            {fitAssessment.reasonsAgainst.slice(0, 4).map((reason, index) => (
                              <li key={`fit-constraint-${index}`} className="rounded-md bg-[var(--hp-surface)] px-2 py-1">{reason}</li>
                            ))}
                          </ul>
                        </div>
                      ) : null}

                      <AgentMessageDisplay compact view={fitResponseView} />
                    </Card>
                  ) : null}
                </div>
              </section>
            </div>
          </section>

          <Card className="p-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <Feature icon={<FiTruck className="w-6 h-6" />} title="Fast Delivery" description="Delivery ETA from logistics agents." />
              <Feature icon={<FiRotateCcw className="w-6 h-6" />} title="Flexible Returns" description="Returns support assisted by agents." />
              <Feature icon={<FiShield className="w-6 h-6" />} title="Quality Insights" description="Product details enriched by specialist agents." />
            </div>
          </Card>
        </>
      )}
    </MainLayout>
  );
}

function Feature({ icon, title, description }: { icon: React.ReactNode; title: string; description: string }) {
  return (
    <div className="text-center">
      <div className="mb-2 flex justify-center text-[var(--hp-accent)]">{icon}</div>
      <h4 className="mb-1 text-sm font-semibold text-[var(--hp-text)]">{title}</h4>
      <p className="text-xs text-[var(--hp-text-muted)]">{description}</p>
    </div>
  );
}
