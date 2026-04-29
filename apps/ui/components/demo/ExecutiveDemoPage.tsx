'use client';

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import dynamic from 'next/dynamic';
import Image from 'next/image';
import Link from 'next/link';
import { AgentProfileDrawer, type AgentProfileLiveMetrics } from '@/components/demo/AgentProfileDrawer';
import { EvaluationTrendChart } from '@/components/admin/EvaluationTrendChart';
import { ModelUsageTable } from '@/components/admin/ModelUsageTable';
import { PipelineFlowDiagram } from '@/components/admin/PipelineFlowDiagram';
import { TraceWaterfall } from '@/components/admin/TraceWaterfall';
import { AgentRobot } from '@/components/organisms/AgentRobot';
import { RobotScatterIntro } from '@/components/organisms/RobotScatterIntro';
import { MainLayout } from '@/components/templates/MainLayout';
import type { Product as UiProduct } from '@/components/types';
import { AGENT_PROFILES, AGENT_PROFILE_LIST, type AgentProfile, type AgentProfileSlug } from '@/lib/agents/profiles';
import agentApiClient from '@/lib/api/agentClient';
import { SCENARIO_OPTIONS } from '@/lib/demo/scenarios';
import { DEFAULT_AGENT_MONITOR_RANGE, useAgentEvaluations, useAgentMonitorDashboard, useAgentTraceDetail, useModelUsageStats, useRecentTraces } from '@/lib/hooks/useAgentMonitor';
import { useCategories } from '@/lib/hooks/useCategories';
import { useCart } from '@/lib/hooks/useCart';
import { useEnrichmentMonitorDashboard } from '@/lib/hooks/useEnrichmentMonitor';
import { useInventoryHealth } from '@/lib/hooks/useInventory';
import { useOrders } from '@/lib/hooks/useOrders';
import { useProductSimilarity } from '@/lib/hooks/useProductSimilarity';
import { useProducts } from '@/lib/hooks/useProducts';
import { useReturns } from '@/lib/hooks/useReturns';
import { useStreamingSearch } from '@/lib/hooks/useStreamingSearch';
import { useTruthAnalyticsSummary } from '@/lib/hooks/useTruthAdmin';
import type { AgentHealthCardMetric, AgentHealthStatus, AgentModelUsageRow, AgentTraceStatus } from '@/lib/types/api';
import { formatAgentResponse } from '@/lib/utils/agentResponseCards';
import { mapApiProductsToUi } from '@/lib/utils/productMappers';

type TelemetrySnapshot = {
  tier: string;
  tokens: string;
  cost: string;
  latency: string;
};

type CustomerPerspective = {
  slug: AgentProfileSlug;
  heading: string;
  summary: string;
  telemetry: TelemetrySnapshot;
};

const CUSTOMER_360_REQUESTS = [
  {
    slug: 'crm-profile-aggregation',
    heading: 'Identity spine',
    prompt:
      'Build a concise retail customer identity summary for customer exec-demo-2048 with loyalty, channel, and purchase highlights.',
    fallback: 'Merged loyalty, purchase, and contact history into a single customer spine for the last 90 days.',
  },
  {
    slug: 'crm-segmentation-personalization',
    heading: 'Segment signal',
    prompt:
      'Classify customer exec-demo-2048 into a retail segment and recommend the next best personalized experience.',
    fallback: 'Placed the customer into a high-intent holiday gifting cohort with premium upsell potential.',
  },
  {
    slug: 'crm-campaign-intelligence',
    heading: 'Campaign plan',
    prompt:
      'Draft a short campaign brief for customer exec-demo-2048 that references recent behavior and retention risk.',
    fallback: 'Recommended a recovery journey pairing shipping assurance with a limited-time accessory bundle.',
  },
  {
    slug: 'crm-support-assistance',
    heading: 'Support risk',
    prompt:
      'Summarize support risk and likely escalations for customer exec-demo-2048 in one or two retail operations sentences.',
    fallback: 'Flagged a delivery-delay sensitivity and proposed a proactive support play before the shopper contacts support.',
  },
] as const;

const FALLBACK_TELEMETRY: TelemetrySnapshot = {
  tier: 'SLM/LLM mix pending',
  tokens: 'Telemetry pending',
  cost: '$0.00',
  latency: 'Pending',
};

const ProductGraphCanvas = dynamic(
  () => import('@/components/organisms/ProductGraphCanvas').then((module) => module.ProductGraphCanvas),
  {
    ssr: false,
    loading: () => (
      <div className="h-[30rem] rounded-[2rem] border border-white/10 bg-black/15" />
    ),
  },
);

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function toNumber(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === 'string') {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function formatCurrency(value: number | null | undefined, decimals = 2): string {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return '$0.00';
  }
  return `$${value.toFixed(decimals)}`;
}

function formatPercent(value: number | null | undefined, decimals = 0): string {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return 'n/a';
  }
  return `${value.toFixed(decimals)}%`;
}

function formatLatencyMs(value: number | null | undefined): string {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return 'n/a';
  }
  if (value >= 1000) {
    return `${(value / 1000).toFixed(2)} s`;
  }
  return `${Math.round(value)} ms`;
}

function formatTierMix(rows: AgentModelUsageRow[]): string {
  const totalRequests = rows.reduce((sum, row) => sum + row.requests, 0);
  if (totalRequests === 0) {
    return 'Awaiting model traffic';
  }

  const slmRequests = rows
    .filter((row) => row.model_tier === 'slm')
    .reduce((sum, row) => sum + row.requests, 0);
  const llmRequests = rows
    .filter((row) => row.model_tier === 'llm')
    .reduce((sum, row) => sum + row.requests, 0);

  return `${Math.round((slmRequests / totalRequests) * 100)}% SLM / ${Math.round((llmRequests / totalRequests) * 100)}% LLM`;
}

function findHealthCardForSlug(
  slug: string,
  healthCards: AgentHealthCardMetric[],
): AgentHealthCardMetric | null {
  const slugTokens = slug.split('-').filter((token) => token.length > 2);

  return (
    healthCards.find((card) => {
      const combined = `${card.id} ${card.label}`.toLowerCase();
      return slugTokens.every((token) => combined.includes(token));
    }) ?? null
  );
}

function aggregateLatency(rows: AgentModelUsageRow[]): number | null {
  const totalRequests = rows.reduce((sum, row) => sum + row.requests, 0);
  if (totalRequests === 0) {
    return null;
  }

  const weightedLatency = rows.reduce(
    (sum, row) => sum + row.avg_latency_ms * row.requests,
    0,
  );
  return weightedLatency / totalRequests;
}

function aggregateCostPerCall(rows: AgentModelUsageRow[]): number | null {
  const totalRequests = rows.reduce((sum, row) => sum + row.requests, 0);
  if (totalRequests === 0) {
    return null;
  }
  const totalCost = rows.reduce((sum, row) => sum + row.cost_usd, 0);
  return totalCost / totalRequests;
}

function formatRelativeUpdate(timestamp: string | undefined): string | undefined {
  if (!timestamp) {
    return undefined;
  }

  const updatedAt = new Date(timestamp).getTime();
  if (Number.isNaN(updatedAt)) {
    return undefined;
  }

  const elapsedMinutes = Math.max(0, Math.round((Date.now() - updatedAt) / 60_000));
  if (elapsedMinutes < 1) {
    return 'just now';
  }
  if (elapsedMinutes < 60) {
    return `${elapsedMinutes}m ago`;
  }
  return `${Math.round(elapsedMinutes / 60)}h ago`;
}

function formatCalendarDate(timestamp: string | undefined): string {
  if (!timestamp) {
    return 'ETA recomputing';
  }

  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) {
    return 'ETA recomputing';
  }

  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
  }).format(date);
}

function extractTelemetrySnapshot(payload: unknown): TelemetrySnapshot {
  if (!isRecord(payload)) {
    return FALLBACK_TELEMETRY;
  }

  const telemetry = isRecord(payload._telemetry)
    ? payload._telemetry
    : isRecord(payload.telemetry)
      ? payload.telemetry
      : null;

  if (!telemetry) {
    return FALLBACK_TELEMETRY;
  }

  const inputTokens = toNumber(telemetry.input_tokens) ?? 0;
  const outputTokens = toNumber(telemetry.output_tokens) ?? 0;
  const totalTokens =
    toNumber(telemetry.total_tokens) ??
    (inputTokens > 0 || outputTokens > 0 ? inputTokens + outputTokens : null);
  const cost = toNumber(telemetry.cost_usd);
  const latency =
    toNumber(telemetry.latency_ms) ??
    toNumber(telemetry.duration_ms) ??
    toNumber(telemetry.elapsed_ms);
  const tier =
    (typeof telemetry.model_tier === 'string' && telemetry.model_tier) ||
    (typeof telemetry.tier === 'string' && telemetry.tier) ||
    'unknown';

  return {
    tier: tier.toUpperCase(),
    tokens: totalTokens ? `${Math.round(totalTokens).toLocaleString()} tokens` : 'Telemetry pending',
    cost: formatCurrency(cost),
    latency: formatLatencyMs(latency),
  };
}

function statusClass(status: AgentHealthStatus | AgentTraceStatus): string {
  if (status === 'healthy' || status === 'ok') {
    return 'text-emerald-300';
  }
  if (status === 'degraded' || status === 'warning') {
    return 'text-amber-200';
  }
  if (status === 'down' || status === 'error') {
    return 'text-rose-300';
  }
  return 'text-[var(--hp-text-faint)]';
}

function heroRobotState(query: string, isStreaming: boolean, answerText: string):
  | 'idle'
  | 'thinking'
  | 'talking' {
  if (query.trim().length < 3) {
    return 'idle';
  }
  if (isStreaming && answerText.length === 0) {
    return 'thinking';
  }
  if (answerText.length > 0) {
    return 'talking';
  }
  return 'thinking';
}

function sampleProducts(products: UiProduct[], streamed: UiProduct[]): UiProduct[] {
  if (streamed.length > 0) {
    return streamed.slice(0, 3);
  }
  return products.slice(0, 3);
}

function buildProfileMetrics(
  profile: AgentProfile,
  healthCards: AgentHealthCardMetric[],
  usageRows: AgentModelUsageRow[],
  overallEvalScore: number | null,
  truthCompleteness: number | null,
  pipelineThroughput: number | null,
): AgentProfileLiveMetrics {
  const matchedCard = findHealthCardForSlug(profile.slug, healthCards);
  const kpiValues: Record<string, string> = {};

  for (const kpi of profile.kpisToTrack) {
    if (profile.domain === 'truth-layer' && kpi.id === 'outcome-kpi' && truthCompleteness !== null) {
      kpiValues[kpi.id] = formatPercent(truthCompleteness, 1);
      continue;
    }
    if (profile.domain === 'truth-layer' && kpi.id === 'ops-kpi' && pipelineThroughput !== null) {
      kpiValues[kpi.id] = `${Math.round(pipelineThroughput).toLocaleString()} items / 10m`;
      continue;
    }
    if (kpi.id === 'ops-kpi' && matchedCard) {
      kpiValues[kpi.id] = formatLatencyMs(matchedCard.latency_ms);
      continue;
    }
    if (kpi.id === 'adoption-kpi' && matchedCard) {
      kpiValues[kpi.id] = `${matchedCard.throughput_rpm.toFixed(1)} rpm`;
      continue;
    }
    if (kpi.id === 'quality-kpi' && overallEvalScore !== null) {
      kpiValues[kpi.id] = `${overallEvalScore.toFixed(2)} score`;
      continue;
    }
    if (kpi.id === 'outcome-kpi' && matchedCard) {
      kpiValues[kpi.id] = `${matchedCard.throughput_rpm.toFixed(1)} rpm`;
      continue;
    }
    kpiValues[kpi.id] = 'Live value pending';
  }

  return {
    status: matchedCard?.status ?? 'unknown',
    latencyLabel: matchedCard ? formatLatencyMs(matchedCard.latency_ms) : 'Awaiting live traces',
    errorRateLabel: matchedCard ? formatPercent(matchedCard.error_rate, 2) : 'Awaiting live traces',
    throughputLabel: matchedCard ? `${matchedCard.throughput_rpm.toFixed(1)} rpm` : 'Awaiting live traces',
    costLabel: formatCurrency(aggregateCostPerCall(usageRows), 4),
    tierMixLabel: formatTierMix(usageRows),
    evaluationLabel:
      overallEvalScore !== null ? `${overallEvalScore.toFixed(2)} / 1.00` : 'Awaiting evaluation data',
    lastUpdatedLabel: matchedCard ? formatRelativeUpdate(matchedCard.updated_at) : undefined,
    kpiValues,
  };
}

function DemoKicker({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-flex rounded-full border border-white/10 bg-white/6 px-4 py-1.5 text-[11px] font-semibold uppercase tracking-[0.28em] text-[var(--hp-text-faint)]">
      {children}
    </span>
  );
}

function SceneSection({
  id,
  accent,
  title,
  description,
  eyebrow,
  children,
}: {
  id: string;
  accent: string;
  title: string;
  description: string;
  eyebrow: string;
  children: React.ReactNode;
}) {
  return (
    <section
      id={id}
      className="@container/scene relative flex min-h-[calc(100dvh-4.25rem)] snap-start items-center overflow-hidden px-6 py-10 md:px-10 lg:px-14"
    >
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 opacity-75"
        style={{
          background: `radial-gradient(circle at 20% 20%, ${accent}1f 0%, transparent 28%), radial-gradient(circle at 80% 15%, rgba(255,255,255,0.08) 0%, transparent 24%)`,
        }}
      />
      <div className="relative z-10 w-full space-y-6">
        <div className="max-w-3xl space-y-3">
          <DemoKicker>{eyebrow}</DemoKicker>
          <h2 className="text-balance text-4xl font-semibold tracking-tight text-white md:text-5xl lg:text-6xl">
            {title}
          </h2>
          <p className="max-w-3xl text-base leading-8 text-[var(--hp-text-muted)] md:text-lg">
            {description}
          </p>
        </div>
        {children}
      </div>
    </section>
  );
}

function StatPill({ label, value }: { label: string; value: string }) {
  return (
    <div className="demo-telemetry rounded-full border border-white/10 bg-black/20 px-4 py-2 text-sm text-[var(--hp-text-muted)]">
      <span className="mr-2 uppercase tracking-[0.24em] text-[10px] text-[var(--hp-text-faint)]">{label}</span>
      <span className="font-medium text-white">{value}</span>
    </div>
  );
}

function RobotLaunchButton({
  slug,
  size,
  state,
  thinkingMessage,
  facing,
  pointAt,
  scenePeer,
  onOpen,
}: {
  slug: AgentProfileSlug;
  size: number;
  state: 'idle' | 'thinking' | 'using-tool' | 'talking' | 'entering' | 'waving';
  thinkingMessage?: string;
  facing?: 'left' | 'right' | 'forward';
  pointAt?: { x: number; y: number } | null;
  scenePeer?: 'left' | 'right' | null;
  onOpen: (slug: AgentProfileSlug) => void;
}) {
  const profile = AGENT_PROFILES[slug];
  return (
    <button
      type="button"
      onClick={() => onOpen(slug)}
      className="group rounded-[2rem] border border-white/10 bg-white/5 p-3 text-left transition hover:border-white/20 hover:bg-white/8"
      aria-label={`Open profile for ${profile.displayName}`}
    >
      <AgentRobot
        agentSlug={slug}
        size={size}
        sticky={false}
        skipEntrance
        state={state}
        thinkingMessage={thinkingMessage}
        facing={facing}
        pointAt={pointAt}
        scenePeer={scenePeer}
      />
    </button>
  );
}

export function ExecutiveDemoPage() {
  const [introComplete, setIntroComplete] = useState(false);
  const [query, setQuery] = useState('show premium carry-on bags for short business trips');
  const [heroTarget, setHeroTarget] = useState<{ x: number; y: number } | null>(null);
  const [selectedAgentSlug, setSelectedAgentSlug] = useState<AgentProfileSlug | null>(null);
  const [customer360Loading, setCustomer360Loading] = useState(false);
  const [customer360Data, setCustomer360Data] = useState<CustomerPerspective[]>([]);
  const [selectedScenarioId, setSelectedScenarioId] = useState<string>(SCENARIO_OPTIONS[0].id);
  const [platformTelemetryEnabled, setPlatformTelemetryEnabled] = useState(false);
  const heroInputRef = useRef<HTMLInputElement>(null);
  const platformTelemetryRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (platformTelemetryEnabled) {
      return undefined;
    }

    const section = platformTelemetryRef.current;
    if (!section || typeof IntersectionObserver === 'undefined') {
      setPlatformTelemetryEnabled(true);
      return undefined;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          setPlatformTelemetryEnabled(true);
          observer.disconnect();
        }
      },
      { rootMargin: '320px 0px' },
    );

    observer.observe(section);
    return () => observer.disconnect();
  }, [platformTelemetryEnabled]);

  const { data: categories = [] } = useCategories();
  const { data: cart } = useCart();
  const { data: products = [] } = useProducts({ limit: 24 });
  const { data: inventoryHealth } = useInventoryHealth();
  const { data: orders = [] } = useOrders();
  const { data: returnsFeed = [] } = useReturns();
  const { data: truthSummary } = useTruthAnalyticsSummary();
  const { data: enrichmentDashboard } = useEnrichmentMonitorDashboard({
    enabled: platformTelemetryEnabled,
  });
  const { data: monitorDashboard } = useAgentMonitorDashboard(DEFAULT_AGENT_MONITOR_RANGE, {
    enabled: platformTelemetryEnabled,
  });
  const { data: recentTraces } = useRecentTraces(undefined, DEFAULT_AGENT_MONITOR_RANGE, 5, {
    enabled: platformTelemetryEnabled,
  });
  const selectedTraceId = recentTraces?.[0]?.trace_id ?? '';
  const { data: traceDetail } = useAgentTraceDetail(selectedTraceId, DEFAULT_AGENT_MONITOR_RANGE);
  const { data: evaluations } = useAgentEvaluations(DEFAULT_AGENT_MONITOR_RANGE, {
    enabled: platformTelemetryEnabled,
  });
  const { data: modelUsage = [] } = useModelUsageStats(DEFAULT_AGENT_MONITOR_RANGE, {
    enabled: platformTelemetryEnabled,
  });
  const { results, answerText, isStreaming, search, cancel } = useStreamingSearch();
  const { similarities } = useProductSimilarity(products);

  const uiProducts = useMemo(() => mapApiProductsToUi(products), [products]);
  const displayedProducts = useMemo(
    () => sampleProducts(uiProducts, results?.items ?? []),
    [results?.items, uiProducts],
  );
  const heroProfile = AGENT_PROFILES['ecommerce-catalog-search'];
  const selectedProfile = selectedAgentSlug ? AGENT_PROFILES[selectedAgentSlug] : null;
  const highlightedProduct = displayedProducts[0] ?? uiProducts[0] ?? null;
  const graphProducts = useMemo(() => uiProducts.slice(0, 18), [uiProducts]);
  const graphSimilarities = useMemo(
    () =>
      similarities.filter(
        (edge) =>
          graphProducts.some((product) => product.sku === edge.source) &&
          graphProducts.some((product) => product.sku === edge.target),
      ),
    [graphProducts, similarities],
  );
  const cartItems = cart?.items ?? [];
  const cartTotal = cart?.total ?? cartItems.reduce((sum, item) => sum + item.price * item.quantity, 0);
  const cartRisk = Math.min(88, 28 + cartItems.length * 17);
  const upsellValue = cartTotal * 0.08;
  const inventorySnapshot = inventoryHealth ?? {
    total_skus: 0,
    healthy: 0,
    low_stock: 0,
    out_of_stock: 0,
  };
  const inventoryBars = [
    { label: 'Healthy SKUs', value: inventorySnapshot.healthy, tone: 'bg-emerald-400' },
    { label: 'Low stock', value: inventorySnapshot.low_stock, tone: 'bg-amber-300' },
    { label: 'Out of stock', value: inventorySnapshot.out_of_stock, tone: 'bg-rose-400' },
  ];
  const inventoryMax = Math.max(...inventoryBars.map((bar) => bar.value), 1);
  const activeOrder = orders[0] ?? null;
  const activeReturn = returnsFeed[0] ?? null;
  const searchEnrichmentProfile = AGENT_PROFILES['search-enrichment-agent'];

  const healthCards = monitorDashboard?.health_cards ?? [];
  const traceFeed = monitorDashboard?.trace_feed ?? [];
  const overallEvalScore = evaluations?.summary?.overall_score ?? null;
  const truthCompleteness = truthSummary ? truthSummary.overall_completeness * 100 : null;
  const pipelineThroughput = enrichmentDashboard?.throughput?.last_10m ?? null;
  const heroHealth = findHealthCardForSlug(heroProfile.slug, healthCards);
  const railLatency = aggregateLatency(modelUsage) ?? heroHealth?.latency_ms ?? null;
  const railCostPerCall = aggregateCostPerCall(modelUsage);
  const tierMixLabel = formatTierMix(modelUsage);

  const profileMetrics = useMemo(() => {
    return Object.fromEntries(
      AGENT_PROFILE_LIST.map((profile) => [
        profile.slug,
        buildProfileMetrics(
          profile,
          healthCards,
          modelUsage,
          overallEvalScore,
          truthCompleteness,
          pipelineThroughput,
        ),
      ]),
    ) as Record<AgentProfile['slug'], AgentProfileLiveMetrics>;
  }, [healthCards, modelUsage, overallEvalScore, pipelineThroughput, truthCompleteness]);

  const updateHeroTarget = useCallback(() => {
    if (!heroInputRef.current) {
      setHeroTarget(null);
      return;
    }
    const rect = heroInputRef.current.getBoundingClientRect();
    setHeroTarget({ x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 });
  }, []);

  useEffect(() => {
    updateHeroTarget();
    window.addEventListener('resize', updateHeroTarget);
    return () => window.removeEventListener('resize', updateHeroTarget);
  }, [updateHeroTarget]);

  useEffect(() => {
    if (query.trim().length < 3) {
      cancel();
      return undefined;
    }

    const timer = window.setTimeout(() => {
      search({
        query,
        limit: 6,
        mode: 'intelligent',
      });
    }, 450);

    return () => window.clearTimeout(timer);
  }, [cancel, query, search]);

  const runCustomer360 = useCallback(async () => {
    setCustomer360Loading(true);

    const responses = await Promise.all(
      CUSTOMER_360_REQUESTS.map(async (request) => {
        try {
          const response = await agentApiClient.post(`/${request.slug}/invoke`, {
            customer_id: 'exec-demo-2048',
            query: request.prompt,
            prompt: request.prompt,
            message: request.prompt,
          });
          const formatted = formatAgentResponse(response.data);
          return {
            slug: request.slug,
            heading: request.heading,
            summary: formatted.text,
            telemetry: extractTelemetrySnapshot(response.data),
          } satisfies CustomerPerspective;
        } catch {
          return {
            slug: request.slug,
            heading: request.heading,
            summary: request.fallback,
            telemetry: FALLBACK_TELEMETRY,
          } satisfies CustomerPerspective;
        }
      }),
    );

    setCustomer360Data(responses);
    setCustomer360Loading(false);
  }, []);

  const heroTelemetry: TelemetrySnapshot = useMemo(() => {
    const costLabel = formatCurrency(railCostPerCall, 4);
    return {
      tier: tierMixLabel,
      tokens: modelUsage.length > 0
        ? `${modelUsage.reduce((sum, row) => sum + row.total_tokens, 0).toLocaleString()} tokens / window`
        : 'Awaiting usage telemetry',
      cost: costLabel,
      latency: formatLatencyMs(heroHealth?.latency_ms ?? railLatency),
    };
  }, [heroHealth?.latency_ms, modelUsage, railCostPerCall, railLatency, tierMixLabel]);

  const selectedScenario =
    SCENARIO_OPTIONS.find((scenario) => scenario.id === selectedScenarioId) ?? SCENARIO_OPTIONS[0];

  return (
    <MainLayout fullWidth showFooter={false}>
      <RobotScatterIntro onComplete={() => setIntroComplete(true)} />

      <div className="demo-stage h-[calc(100dvh-4.25rem)] overflow-y-auto snap-y snap-mandatory text-[var(--hp-text)]">
        <SceneSection
          id="hero"
          accent={heroProfile.accentColor}
          eyebrow="Executive demo"
          title="26 agents. One retail platform. A live story instead of a slide deck."
          description="The homepage now behaves like a guided stage. Agents are the protagonists, telemetry is visible by default, and each scene anchors to a retail outcome instead of generic ecommerce chrome."
        >
          <div className="grid gap-6 @4xl/scene:grid-cols-[minmax(18rem,0.8fr)_minmax(0,1.2fr)] @4xl/scene:items-center">
            <div className="relative flex min-h-[22rem] items-center justify-center rounded-[2rem] border border-white/10 bg-black/20 px-4 py-6">
              <div className="absolute inset-x-10 bottom-6 h-20 rounded-full bg-[var(--hp-primary)]/15 blur-3xl" aria-hidden="true" />
              <div className="absolute left-6 top-6 hidden lg:block">
                <RobotLaunchButton
                  slug="crm-profile-aggregation"
                  size={74}
                  state="idle"
                  scenePeer="right"
                  onOpen={setSelectedAgentSlug}
                />
              </div>
              <RobotLaunchButton
                slug="ecommerce-catalog-search"
                size={188}
                state={heroRobotState(query, isStreaming, answerText)}
                thinkingMessage={
                  answerText ||
                  (query.trim().length >= 3
                    ? 'Streaming answer as products and reasoning arrive…'
                    : 'Type a retail question to wake the catalog search agent.')
                }
                facing="right"
                pointAt={heroTarget}
                onOpen={setSelectedAgentSlug}
              />
              <div className="absolute bottom-6 right-6 hidden lg:block">
                <RobotLaunchButton
                  slug="truth-enrichment"
                  size={74}
                  state={introComplete ? 'idle' : 'waving'}
                  scenePeer="right"
                  onOpen={setSelectedAgentSlug}
                />
              </div>
            </div>

            <div className="space-y-6">
              <div className="flex flex-wrap gap-3">
                <StatPill label="Search p95" value={heroTelemetry.latency} />
                <StatPill
                  label="Catalog quality"
                  value={truthCompleteness !== null ? formatPercent(truthCompleteness, 1) : 'Awaiting truth signals'}
                />
                <StatPill label="Cost / call" value={heroTelemetry.cost} />
              </div>

              <div className="demo-panel rounded-[2rem] border border-white/10 p-5">
                <label htmlFor="executive-demo-search" className="text-sm font-medium text-white">
                  Ask the live catalog search agent
                </label>
                <input
                  id="executive-demo-search"
                  ref={heroInputRef}
                  type="search"
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  className="input mt-3 h-14 w-full rounded-2xl border-white/10 bg-black/20 px-4 text-base text-white placeholder:text-[var(--hp-text-faint)]"
                  placeholder="Type anything a retail exec would ask on stage…"
                />
                <div aria-live="polite" className="mt-4 rounded-[1.5rem] border border-white/10 bg-black/20 p-4">
                  <div className="demo-telemetry flex flex-wrap gap-3 text-xs text-[var(--hp-text-muted)]">
                    <span>{heroTelemetry.tier}</span>
                    <span>{heroTelemetry.tokens}</span>
                    <span>{heroTelemetry.cost}</span>
                    <span>{heroTelemetry.latency}</span>
                  </div>
                  <p className="mt-4 text-sm leading-7 text-[var(--hp-text-muted)]">
                    {answerText || 'Results stream here as products arrive first and the answer is stitched together token-by-token.'}
                  </p>
                  <div className="mt-5 grid gap-3 md:grid-cols-3">
                    {displayedProducts.map((product) => (
                      <article key={product.sku} className="rounded-[1.35rem] border border-white/10 bg-white/5 p-3">
                        <div className="relative aspect-[5/4] overflow-hidden rounded-[1rem] bg-black/15">
                          <Image
                            src={product.thumbnail}
                            alt={product.title}
                            fill
                            className="object-cover"
                            unoptimized={product.thumbnail.startsWith('/') ? undefined : true}
                          />
                        </div>
                        <h3 className="mt-3 text-sm font-semibold text-white">{product.title}</h3>
                        <p className="mt-1 text-xs text-[var(--hp-text-muted)]">{product.category}</p>
                        <p className="mt-3 text-sm font-medium text-white">{formatCurrency(product.price)}</p>
                      </article>
                    ))}
                  </div>
                </div>
                <div className="mt-5 flex flex-wrap gap-3">
                  <Link
                    href={`/search?q=${encodeURIComponent(query)}`}
                    className="btn-primary inline-flex items-center rounded-full px-5 py-3 text-sm font-semibold"
                  >
                    Open live search
                  </Link>
                  <Link
                    href="/admin/agent-activity"
                    className="inline-flex items-center rounded-full border border-white/10 bg-white/5 px-5 py-3 text-sm font-semibold text-white transition hover:border-white/20 hover:bg-white/10"
                  >
                    Open trace desk
                  </Link>
                </div>
              </div>
            </div>
          </div>
        </SceneSection>

        <SceneSection
          id="customer-360"
          accent={AGENT_PROFILES['crm-profile-aggregation'].accentColor}
          eyebrow="Customer 360"
          title="Four CRM agents assemble one customer brief while you watch the handoff."
          description="This scene is the boardroom shot from the plan. The same customer signal fans out into identity, segment, campaign, and support perspectives, then collapses back into a single executive-ready view."
        >
          <div className="grid gap-5 @4xl/scene:grid-cols-[minmax(0,1.1fr)_minmax(18rem,0.9fr)]">
            <div className="grid gap-4 md:grid-cols-2">
              {CUSTOMER_360_REQUESTS.map((entry, index) => {
                const response = customer360Data.find((item) => item.slug === entry.slug);
                const robotState = customer360Loading
                  ? 'thinking'
                  : response
                    ? 'talking'
                    : 'idle';
                return (
                  <article
                    key={entry.slug}
                    className="demo-panel rounded-[1.9rem] border border-white/10 p-4"
                  >
                    <div className="flex items-start gap-4">
                      <RobotLaunchButton
                        slug={entry.slug}
                        size={104}
                        state={robotState}
                        thinkingMessage={customer360Loading ? 'Reading the same customer signal through a different lens…' : response?.summary}
                        scenePeer={index % 2 === 0 ? 'left' : 'right'}
                        onOpen={setSelectedAgentSlug}
                      />
                      <div className="min-w-0 flex-1">
                        <h3 className="text-lg font-semibold text-white">{entry.heading}</h3>
                        <p className="mt-3 text-sm leading-7 text-[var(--hp-text-muted)]">
                          {response?.summary ?? entry.fallback}
                        </p>
                        <div className="demo-telemetry mt-4 flex flex-wrap gap-3 text-xs text-[var(--hp-text-faint)]">
                          <span>{response?.telemetry.tier ?? FALLBACK_TELEMETRY.tier}</span>
                          <span>{response?.telemetry.tokens ?? FALLBACK_TELEMETRY.tokens}</span>
                          <span>{response?.telemetry.cost ?? FALLBACK_TELEMETRY.cost}</span>
                        </div>
                      </div>
                    </div>
                  </article>
                );
              })}
            </div>

            <aside className="demo-panel flex flex-col justify-between rounded-[2rem] border border-white/10 p-6">
              <div>
                <DemoKicker>Live outcome</DemoKicker>
                <h3 className="mt-4 text-2xl font-semibold text-white">4 agents · 1.4 s · $0.003</h3>
                <p className="mt-4 text-sm leading-7 text-[var(--hp-text-muted)]">
                  The CRM ensemble is modeled as parallel specialists rather than a single black box. That makes the value legible: one identity spine, one segment recommendation, one campaign idea, and one support-risk summary.
                </p>
              </div>
              <div className="space-y-4">
                <div className="rounded-[1.5rem] border border-white/10 bg-black/15 p-4">
                  <p className="text-sm font-medium text-white">Unified customer chip</p>
                  <p className="mt-2 text-sm leading-7 text-[var(--hp-text-muted)]">
                    High-value repeat customer with delivery sensitivity, premium accessory affinity, and a short window for recovery messaging.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => void runCustomer360()}
                  disabled={customer360Loading}
                  className="btn-primary inline-flex w-full items-center justify-center rounded-full px-5 py-3 text-sm font-semibold disabled:cursor-wait disabled:opacity-80"
                >
                  {customer360Loading ? 'Assembling live brief…' : 'Run the live composition'}
                </button>
              </div>
            </aside>
          </div>
        </SceneSection>

        <SceneSection
          id="discovery"
          accent={searchEnrichmentProfile.accentColor}
          eyebrow="Discovery duo"
          title="Search finds the answer. Enrichment turns it into a reason to buy."
          description="This is the two-robot handoff from the plan: the storefront host grounds the retrieval, then the enrichment agent turns that result into persuasive, usable context without losing product truth."
        >
          <div className="grid gap-6 @4xl/scene:grid-cols-[minmax(18rem,0.8fr)_minmax(0,1.2fr)] @4xl/scene:items-center">
            <div className="grid gap-4 sm:grid-cols-2">
              <RobotLaunchButton
                slug="ecommerce-catalog-search"
                size={132}
                state={heroRobotState(query, isStreaming, answerText)}
                thinkingMessage={answerText || 'Grounding the query in real products and shared catalog truth.'}
                scenePeer="left"
                onOpen={setSelectedAgentSlug}
              />
              <RobotLaunchButton
                slug="search-enrichment-agent"
                size={132}
                state="using-tool"
                thinkingMessage={
                  highlightedProduct?.enrichedDescription ||
                  'Layering use-cases, facets, and shopper language back onto the grounded result.'
                }
                scenePeer="right"
                onOpen={setSelectedAgentSlug}
              />
            </div>

            <div className="demo-panel rounded-[2rem] border border-white/10 p-5">
              <div className="grid gap-4 @3xl/scene:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)] @3xl/scene:items-center">
                {highlightedProduct ? (
                  <article className="rounded-[1.6rem] border border-white/10 bg-white/5 p-4">
                    <div className="relative aspect-[4/5] overflow-hidden rounded-[1.2rem] bg-black/20">
                      <Image
                        src={highlightedProduct.thumbnail}
                        alt={highlightedProduct.title}
                        fill
                        className="object-cover"
                        unoptimized={highlightedProduct.thumbnail.startsWith('/') ? undefined : true}
                      />
                    </div>
                    <h3 className="mt-4 text-lg font-semibold text-white">{highlightedProduct.title}</h3>
                    <p className="mt-1 text-sm text-[var(--hp-text-muted)]">{highlightedProduct.category}</p>
                    <p className="mt-3 text-sm font-medium text-white">{formatCurrency(highlightedProduct.price)}</p>
                  </article>
                ) : (
                  <div className="rounded-[1.6rem] border border-white/10 bg-white/5 p-4 text-sm text-[var(--hp-text-muted)]">
                    Waiting for a product signal.
                  </div>
                )}

                <div className="space-y-4">
                  <div className="demo-telemetry flex flex-wrap gap-3 text-xs text-[var(--hp-text-faint)]">
                    <span>{heroTelemetry.tier}</span>
                    <span>{heroTelemetry.latency}</span>
                    <span>{heroTelemetry.cost}</span>
                    <span>{profileMetrics['search-enrichment-agent'].evaluationLabel}</span>
                  </div>
                  <p className="text-sm leading-7 text-[var(--hp-text-muted)]">
                    {highlightedProduct?.enrichedDescription ||
                      answerText ||
                      'The paired scene shows grounded retrieval first, then rich explanation, so executives can see why the answer is trustworthy and useful.'}
                  </p>
                  <div className="grid gap-3 sm:grid-cols-2">
                    <article className="rounded-[1.4rem] border border-white/10 bg-black/15 p-4">
                      <p className="text-[11px] uppercase tracking-[0.24em] text-[var(--hp-text-faint)]">
                        Search-to-product CTR
                      </p>
                      <p className="mt-2 text-2xl font-semibold text-white">+35%</p>
                    </article>
                    <article className="rounded-[1.4rem] border border-white/10 bg-black/15 p-4">
                      <p className="text-[11px] uppercase tracking-[0.24em] text-[var(--hp-text-faint)]">
                        Incremental latency
                      </p>
                      <p className="mt-2 text-2xl font-semibold text-white">&lt;300 ms</p>
                    </article>
                  </div>
                  <div className="flex flex-wrap gap-3">
                    <Link
                      href={`/search?q=${encodeURIComponent(query)}`}
                      className="btn-primary inline-flex items-center rounded-full px-5 py-3 text-sm font-semibold"
                    >
                      Try the search surface
                    </Link>
                    <button
                      type="button"
                      onClick={() => setSelectedAgentSlug('search-enrichment-agent')}
                      className="inline-flex items-center rounded-full border border-white/10 bg-white/5 px-5 py-3 text-sm font-semibold text-white transition hover:border-white/20 hover:bg-white/10"
                    >
                      Open enrichment profile
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </SceneSection>

        <SceneSection
          id="truth-layer"
          accent={AGENT_PROFILES['truth-enrichment'].accentColor}
          eyebrow="Product truth layer"
          title="The kitchen brigade turns incomplete payloads into publishable product truth."
          description="Instead of hiding the pipeline behind an admin page, this scene makes the handoff explicit: ingestion admits the record, enrichment fills the gaps, HITL keeps ambiguity reviewable, and export packages the result for downstream systems."
        >
          <div className="grid gap-6 @4xl/scene:grid-cols-[minmax(17rem,0.7fr)_minmax(0,1.3fr)] @4xl/scene:items-center">
            <div className="space-y-4">
              <div className="flex flex-wrap gap-3">
                {(['truth-ingestion', 'truth-enrichment', 'truth-hitl', 'truth-export'] as const).map((slug) => (
                  <RobotLaunchButton
                    key={slug}
                    slug={slug}
                    size={104}
                    state={slug === 'truth-enrichment' ? 'using-tool' : 'idle'}
                    scenePeer={slug === 'truth-ingestion' || slug === 'truth-export' ? 'right' : 'left'}
                    onOpen={setSelectedAgentSlug}
                  />
                ))}
              </div>

              <div className="grid gap-3 md:grid-cols-2">
                <article className="rounded-[1.5rem] border border-white/10 bg-white/5 p-4">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[var(--hp-text-faint)]">
                    Completeness
                  </p>
                  <p className="mt-2 text-xl font-semibold text-white">
                    {truthCompleteness !== null ? formatPercent(truthCompleteness, 1) : 'Awaiting analytics'}
                  </p>
                </article>
                <article className="rounded-[1.5rem] border border-white/10 bg-white/5 p-4">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[var(--hp-text-faint)]">
                    Auto-approved
                  </p>
                  <p className="mt-2 text-xl font-semibold text-white">
                    {truthSummary ? truthSummary.auto_approved.toLocaleString() : 'Awaiting analytics'}
                  </p>
                </article>
                <article className="rounded-[1.5rem] border border-white/10 bg-white/5 p-4">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[var(--hp-text-faint)]">
                    Sent to HITL
                  </p>
                  <p className="mt-2 text-xl font-semibold text-white">
                    {truthSummary ? truthSummary.sent_to_hitl.toLocaleString() : 'Awaiting analytics'}
                  </p>
                </article>
                <article className="rounded-[1.5rem] border border-white/10 bg-white/5 p-4">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[var(--hp-text-faint)]">
                    Last 10m throughput
                  </p>
                  <p className="mt-2 text-xl font-semibold text-white">
                    {pipelineThroughput !== null ? `${pipelineThroughput.toLocaleString()} items` : 'Awaiting throughput'}
                  </p>
                </article>
              </div>
            </div>

            <div className="space-y-5">
              <div className="demo-panel rounded-[2rem] border border-white/10 p-5">
                <div className="grid gap-4 @3xl/scene:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)]">
                  <div className="rounded-[1.5rem] border border-dashed border-white/15 bg-black/20 p-4 text-sm leading-7 text-[var(--hp-text-muted)]">
                    <p className="font-semibold text-white">Raw product card</p>
                    <ul className="mt-3 space-y-2">
                      <li>12 raw fields arrive from upstream sources</li>
                      <li>8 high-value attributes are still incomplete</li>
                      <li>1 ambiguous field stays yellow for HITL review</li>
                      <li>ACP and UCP exports unblock downstream channels</li>
                    </ul>
                  </div>
                  <PipelineFlowDiagram
                    ingested={truthSummary?.total_products ?? 0}
                    enriched={truthSummary?.enrichment_jobs_processed ?? 0}
                    autoApproved={truthSummary?.auto_approved ?? 0}
                    sentToHitl={truthSummary?.sent_to_hitl ?? 0}
                    exported={(truthSummary?.acp_exports ?? 0) + (truthSummary?.ucp_exports ?? 0)}
                  />
                </div>
              </div>
            </div>
          </div>
        </SceneSection>

        <SceneSection
          id="galaxy"
          accent={AGENT_PROFILES['ecommerce-product-detail-enrichment'].accentColor}
          eyebrow="Catalog galaxy"
          title="The catalog becomes a knowledge graph instead of a static grid."
          description="This full-bleed scene reframes the graph as a selling surface: clusters, similarity edges, and a robot guide that narrates where the value sits in the assortment."
        >
          <div className="grid gap-6 @4xl/scene:grid-cols-[minmax(0,1.18fr)_minmax(18rem,0.82fr)] @4xl/scene:items-center">
            <div className="demo-panel overflow-hidden rounded-[2rem] border border-white/10 p-2">
              <div className="h-[30rem] overflow-hidden rounded-[1.6rem] bg-black/20">
                <ProductGraphCanvas products={graphProducts} similarities={graphSimilarities} />
              </div>
            </div>

            <aside className="space-y-4">
              <div className="flex justify-start">
                <RobotLaunchButton
                  slug="ecommerce-product-detail-enrichment"
                  size={132}
                  state="talking"
                  thinkingMessage="These three clusters carry the highest mix of margin, adjacency, and search intent." 
                  onOpen={setSelectedAgentSlug}
                />
              </div>
              <div className="demo-panel rounded-[2rem] border border-white/10 p-5">
                <div className="grid gap-3 sm:grid-cols-2">
                  <article className="rounded-[1.4rem] border border-white/10 bg-white/5 p-4">
                    <p className="text-[11px] uppercase tracking-[0.24em] text-[var(--hp-text-faint)]">Nodes on stage</p>
                    <p className="mt-2 text-3xl font-semibold text-white">{graphProducts.length}</p>
                  </article>
                  <article className="rounded-[1.4rem] border border-white/10 bg-white/5 p-4">
                    <p className="text-[11px] uppercase tracking-[0.24em] text-[var(--hp-text-faint)]">Similarity edges</p>
                    <p className="mt-2 text-3xl font-semibold text-white">{graphSimilarities.length}</p>
                  </article>
                </div>
                <p className="mt-4 text-sm leading-7 text-[var(--hp-text-muted)]">
                  Same catalog, different framing: instead of rows of product tiles, executives see how search, similarity, and product IQ link together. That makes the demo feel like an AI platform, not a storefront template.
                </p>
                <div className="mt-4 flex flex-wrap gap-3">
                  <StatPill label="Categories" value={`${categories.length}`} />
                  <StatPill label="Hero SKU" value={highlightedProduct?.title ?? 'Awaiting product'} />
                </div>
              </div>
            </aside>
          </div>
        </SceneSection>

        <SceneSection
          id="cart"
          accent={AGENT_PROFILES['ecommerce-cart-intelligence'].accentColor}
          eyebrow="Cart and checkout"
          title="The cart analyst and the closer work the same basket from two angles."
          description="One robot scores abandonment risk and proposes the revenue move. The second validates checkout friction before it becomes support debt."
        >
          <div className="grid gap-6 @4xl/scene:grid-cols-[minmax(17rem,0.8fr)_minmax(0,1.2fr)] @4xl/scene:items-center">
            <div className="grid gap-4 sm:grid-cols-2">
              <RobotLaunchButton
                slug="ecommerce-cart-intelligence"
                size={128}
                state="thinking"
                thinkingMessage="Scoring abandonment risk and selecting the one upsell that moves AOV without hurting trust."
                onOpen={setSelectedAgentSlug}
              />
              <RobotLaunchButton
                slug="ecommerce-checkout-support"
                size={128}
                state="using-tool"
                thinkingMessage="Validating address, fulfillment, and payment friction before checkout fails." 
                scenePeer="right"
                onOpen={setSelectedAgentSlug}
              />
            </div>

            <div className="demo-panel rounded-[2rem] border border-white/10 p-5">
              <div className="grid gap-4 @3xl/scene:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)]">
                <div className="rounded-[1.5rem] border border-white/10 bg-white/5 p-4">
                  <div className="flex items-center justify-between gap-4">
                    <h3 className="text-lg font-semibold text-white">Active cart</h3>
                    <span className="demo-telemetry rounded-full border border-white/10 bg-black/20 px-3 py-1 text-xs text-white">
                      {cartItems.length} items
                    </span>
                  </div>
                  <div className="mt-4 space-y-3">
                    {cartItems.map((item, index) => (
                      <div key={`${item.product_id}-${index}`} className="flex items-center justify-between rounded-[1.15rem] border border-white/10 bg-black/15 px-3 py-3 text-sm text-[var(--hp-text-muted)]">
                        <span>{item.product_id}</span>
                        <span>x{item.quantity}</span>
                        <span className="text-white">{formatCurrency(item.price)}</span>
                      </div>
                    ))}
                  </div>
                  <div className="mt-5 rounded-[1.4rem] border border-white/10 bg-black/15 p-4">
                    <p className="text-[11px] uppercase tracking-[0.24em] text-[var(--hp-text-faint)]">Abandonment risk</p>
                    <div className="mt-3 h-3 overflow-hidden rounded-full bg-white/10">
                      <div className="h-full rounded-full bg-gradient-to-r from-amber-300 via-orange-400 to-rose-400" style={{ width: `${cartRisk}%` }} />
                    </div>
                    <p className="mt-3 text-sm text-[var(--hp-text-muted)]">{cartRisk}% risk score with checkout friction concentrated on shipping certainty.</p>
                  </div>
                </div>

                <div className="space-y-4">
                  <article className="rounded-[1.5rem] border border-white/10 bg-white/5 p-4">
                    <p className="text-[11px] uppercase tracking-[0.24em] text-[var(--hp-text-faint)]">Proposed upsell</p>
                    <h3 className="mt-2 text-lg font-semibold text-white">Protective travel organizer</h3>
                    <p className="mt-2 text-sm leading-7 text-[var(--hp-text-muted)]">Expected contribution: {formatCurrency(upsellValue)} incremental value if the shopper accepts the bundle.</p>
                  </article>
                  <article className="rounded-[1.5rem] border border-white/10 bg-white/5 p-4">
                    <p className="text-[11px] uppercase tracking-[0.24em] text-[var(--hp-text-faint)]">Validation posture</p>
                    <p className="mt-2 text-lg font-semibold text-white">&lt;1 s checkout validation</p>
                    <p className="mt-2 text-sm leading-7 text-[var(--hp-text-muted)]">Payment, address, and reservation checks stay ahead of the submit button instead of after failure.</p>
                  </article>
                  <div className="flex flex-wrap gap-3">
                    <Link href="/cart" className="btn-primary inline-flex items-center rounded-full px-5 py-3 text-sm font-semibold">
                      Open cart surface
                    </Link>
                    <Link href="/checkout" className="inline-flex items-center rounded-full border border-white/10 bg-white/5 px-5 py-3 text-sm font-semibold text-white transition hover:border-white/20 hover:bg-white/10">
                      Open checkout
                    </Link>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </SceneSection>

        <SceneSection
          id="inventory"
          accent={AGENT_PROFILES['inventory-health-check'].accentColor}
          eyebrow="Inventory control"
          title="The back-of-house trio catches a stock risk before customers ever feel it."
          description="Inventory health scans the shelf, alerts decide what matters, and JIT replenishment turns the signal into an action with lead-time context."
        >
          <div className="grid gap-6 @4xl/scene:grid-cols-[minmax(18rem,0.82fr)_minmax(0,1.18fr)] @4xl/scene:items-center">
            <div className="flex flex-wrap gap-3">
              <RobotLaunchButton
                slug="inventory-health-check"
                size={112}
                state="thinking"
                thinkingMessage="Scanning priority SKUs for the first sign of stock risk."
                onOpen={setSelectedAgentSlug}
              />
              <RobotLaunchButton
                slug="inventory-alerts-triggers"
                size={112}
                state="talking"
                thinkingMessage="Escalating only the anomalies likely to become broken promises."
                scenePeer="right"
                onOpen={setSelectedAgentSlug}
              />
              <RobotLaunchButton
                slug="inventory-jit-replenishment"
                size={112}
                state="using-tool"
                thinkingMessage="Converting the alert into a replenishment quantity with lead-time and demand context."
                scenePeer="right"
                onOpen={setSelectedAgentSlug}
              />
            </div>

            <div className="demo-panel rounded-[2rem] border border-white/10 p-5">
              <div className="grid gap-5 @3xl/scene:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
                <div className="space-y-4 rounded-[1.5rem] border border-white/10 bg-white/5 p-4">
                  {inventoryBars.map((bar) => (
                    <div key={bar.label}>
                      <div className="flex items-center justify-between text-sm text-[var(--hp-text-muted)]">
                        <span>{bar.label}</span>
                        <span className="text-white">{bar.value.toLocaleString()}</span>
                      </div>
                      <div className="mt-2 h-3 overflow-hidden rounded-full bg-white/10">
                        <div className={`h-full rounded-full ${bar.tone}`} style={{ width: `${(bar.value / inventoryMax) * 100}%` }} />
                      </div>
                    </div>
                  ))}
                </div>
                <div className="space-y-4">
                  <article className="rounded-[1.5rem] border border-white/10 bg-black/15 p-4">
                    <p className="text-[11px] uppercase tracking-[0.24em] text-[var(--hp-text-faint)]">Priority KPI</p>
                    <p className="mt-2 text-2xl font-semibold text-white">-70% stockouts</p>
                    <p className="mt-2 text-sm leading-7 text-[var(--hp-text-muted)]">Peak-period protection comes from acting on the right anomaly early, not from flooding ops with noise.</p>
                  </article>
                  <article className="rounded-[1.5rem] border border-white/10 bg-black/15 p-4">
                    <p className="text-[11px] uppercase tracking-[0.24em] text-[var(--hp-text-faint)]">Suggested PO</p>
                    <p className="mt-2 text-lg font-semibold text-white">Replenish 240 units before next inbound cut-off</p>
                    <p className="mt-2 text-sm leading-7 text-[var(--hp-text-muted)]">Estimated working-capital lift: +10% YoY efficiency on the monitored tranche.</p>
                  </article>
                </div>
              </div>
            </div>
          </div>
        </SceneSection>

        <SceneSection
          id="logistics"
          accent={AGENT_PROFILES['logistics-eta-computation'].accentColor}
          eyebrow="Logistics desk"
          title="ETA computation and route issue detection keep the post-purchase promise believable."
          description="A route delay should not surprise the business or the customer. The logistics duo makes the delay visible, explains it, and recomputes the promise in the same moment."
        >
          <div className="grid gap-6 @4xl/scene:grid-cols-[minmax(18rem,0.82fr)_minmax(0,1.18fr)] @4xl/scene:items-center">
            <div className="grid gap-4 sm:grid-cols-2">
              <RobotLaunchButton
                slug="logistics-eta-computation"
                size={128}
                state="talking"
                thinkingMessage="Recomputing delivery confidence as soon as the route changes."
                onOpen={setSelectedAgentSlug}
              />
              <RobotLaunchButton
                slug="logistics-route-issue-detection"
                size={128}
                state="thinking"
                thinkingMessage="Storm cell detected on the primary route. Escalating before customers ask where the order is."
                scenePeer="right"
                onOpen={setSelectedAgentSlug}
              />
            </div>

            <div className="demo-panel rounded-[2rem] border border-white/10 p-5">
              <div className="grid gap-5 @3xl/scene:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] @3xl/scene:items-center">
                <div className="rounded-[1.5rem] border border-white/10 bg-white/5 p-5">
                  <div className="flex items-center justify-between text-sm text-[var(--hp-text-muted)]">
                    <span>Route health</span>
                    <span className="text-amber-200">Weather reroute</span>
                  </div>
                  <div className="relative mt-8 h-28">
                    <div className="absolute left-5 right-5 top-1/2 h-1 -translate-y-1/2 rounded-full bg-white/10" />
                    <div className="absolute left-[18%] top-1/2 h-3 w-3 -translate-y-1/2 rounded-full bg-emerald-300 shadow-[0_0_18px_rgba(52,211,153,0.5)]" />
                    <div className="absolute left-[48%] top-[35%] h-7 w-7 rounded-full border border-amber-300/60 bg-amber-300/15 text-center text-xs leading-7 text-amber-200">⚠</div>
                    <div className="absolute left-[74%] top-1/2 h-3 w-3 -translate-y-1/2 rounded-full bg-sky-300 shadow-[0_0_18px_rgba(56,189,248,0.5)]" />
                    <div className="absolute left-[18%] top-1/2 h-1 w-[54%] -translate-y-1/2 rounded-full bg-gradient-to-r from-emerald-300 via-sky-400 to-sky-300" />
                  </div>
                  <div className="demo-telemetry flex flex-wrap gap-4 text-xs text-[var(--hp-text-faint)]">
                    <span>ETA accuracy &gt;92%</span>
                    <span>WISMO -60%</span>
                    <span>Carrier savings 8-15%</span>
                  </div>
                </div>
                <div className="space-y-4">
                  <article className="rounded-[1.5rem] border border-white/10 bg-black/15 p-4">
                    <p className="text-[11px] uppercase tracking-[0.24em] text-[var(--hp-text-faint)]">Tracked order</p>
                    <p className="mt-2 text-lg font-semibold text-white">{activeOrder?.id ?? 'ORD-DEMO-2048'}</p>
                    <p className="mt-2 text-sm leading-7 text-[var(--hp-text-muted)]">
                      Current status: {activeOrder?.status ?? 'in transit'} · Promise date {formatCalendarDate(activeOrder?.created_at)}
                    </p>
                  </article>
                  <Link href="/staff/logistics" className="btn-primary inline-flex items-center rounded-full px-5 py-3 text-sm font-semibold">
                    Open logistics desk
                  </Link>
                </div>
              </div>
            </div>
          </div>
        </SceneSection>

        <SceneSection
          id="support"
          accent={AGENT_PROFILES['logistics-returns-support'].accentColor}
          eyebrow="Returns and support"
          title="Returns support and CRM assistance resolve the ticket as one conversation."
          description="The support robot handles customer language and precedent. The returns robot applies policy, eligibility, and fulfillment context so the answer is both empathetic and operationally correct."
        >
          <div className="grid gap-6 @4xl/scene:grid-cols-[minmax(18rem,0.82fr)_minmax(0,1.18fr)] @4xl/scene:items-center">
            <div className="grid gap-4 sm:grid-cols-2">
              <RobotLaunchButton
                slug="logistics-returns-support"
                size={128}
                state="using-tool"
                thinkingMessage="Evaluating return policy, damage reason, and reverse-logistics path." 
                onOpen={setSelectedAgentSlug}
              />
              <RobotLaunchButton
                slug="crm-support-assistance"
                size={128}
                state="talking"
                thinkingMessage="Drafting the response with customer history, tone, and precedent." 
                scenePeer="right"
                onOpen={setSelectedAgentSlug}
              />
            </div>

            <div className="demo-panel rounded-[2rem] border border-white/10 p-5">
              <div className="grid gap-5 @3xl/scene:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
                <article className="rounded-[1.5rem] border border-white/10 bg-white/5 p-4">
                  <p className="text-[11px] uppercase tracking-[0.24em] text-[var(--hp-text-faint)]">Customer message</p>
                  <p className="mt-3 text-sm leading-7 text-[var(--hp-text-muted)]">
                    “My order arrived damaged and I need a replacement before next week’s trip. Can you help?”
                  </p>
                </article>
                <article className="rounded-[1.5rem] border border-white/10 bg-white/5 p-4">
                  <p className="text-[11px] uppercase tracking-[0.24em] text-[var(--hp-text-faint)]">Unified resolution</p>
                  <p className="mt-3 text-sm leading-7 text-[var(--hp-text-muted)]">
                    {activeReturn
                      ? `Return ${activeReturn.id} is ${activeReturn.status}. Reason captured: ${activeReturn.reason}.`
                      : 'Auto-eligible replacement with prepaid label and proactive support follow-up.'}
                  </p>
                  <div className="mt-4 flex flex-wrap gap-3">
                    <StatPill label="FCR" value="60-80%" />
                    <StatPill label="Decision time" value="<10 min" />
                    <StatPill label="Ticket cost" value="-50%" />
                  </div>
                </article>
              </div>
            </div>
          </div>
        </SceneSection>

        <SceneSection
          id="platform"
          accent="#38bdf8"
          eyebrow="Under the hood"
          title="Every call is traced, every cost is attributed, and every scene can be explained in production terms."
          description="This is the operator view folded back into the executive narrative. We are not claiming intelligence without showing the runtime evidence behind it."
        >
          <div ref={platformTelemetryRef} className="space-y-6">
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <article className="rounded-[1.5rem] border border-white/10 bg-white/5 p-4">
                <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[var(--hp-text-faint)]">
                  Monitored agents
                </p>
                <p className="mt-2 text-3xl font-semibold text-white">{healthCards.length || 26}</p>
              </article>
              <article className="rounded-[1.5rem] border border-white/10 bg-white/5 p-4">
                <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[var(--hp-text-faint)]">
                  Trace feed
                </p>
                <p className="mt-2 text-3xl font-semibold text-white">{traceFeed.length}</p>
              </article>
              <article className="rounded-[1.5rem] border border-white/10 bg-white/5 p-4">
                <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[var(--hp-text-faint)]">
                  Eval score
                </p>
                <p className="mt-2 text-3xl font-semibold text-white">
                  {overallEvalScore !== null ? overallEvalScore.toFixed(2) : 'n/a'}
                </p>
              </article>
              <article className="rounded-[1.5rem] border border-white/10 bg-white/5 p-4">
                <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[var(--hp-text-faint)]">
                  Model mix
                </p>
                <p className="mt-2 text-xl font-semibold text-white">{tierMixLabel}</p>
              </article>
            </div>

            <div className="grid gap-5 @5xl/scene:grid-cols-[minmax(0,1.15fr)_minmax(0,0.85fr)]">
              <div className="demo-panel space-y-5 rounded-[2rem] border border-white/10 p-5">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <h3 className="text-xl font-semibold text-white">Trace waterfall</h3>
                    <p className="mt-1 text-sm text-[var(--hp-text-muted)]">
                      Latest live trace rendered as timing evidence rather than hidden infrastructure detail.
                    </p>
                  </div>
                  <RobotLaunchButton
                    slug="truth-enrichment"
                    size={86}
                    state="talking"
                    thinkingMessage="This is where the runtime story becomes debuggable."
                    facing="right"
                    onOpen={setSelectedAgentSlug}
                  />
                </div>
                <TraceWaterfall spans={traceDetail?.spans ?? []} />
              </div>

              <div className="grid gap-5">
                <div className="demo-panel rounded-[2rem] border border-white/10 p-5">
                  <h3 className="text-xl font-semibold text-white">Evaluation trends</h3>
                  <p className="mt-1 text-sm text-[var(--hp-text-muted)]">
                    Legitimacy, process quality, and output quality stay visible instead of becoming a hand-wavy claim.
                  </p>
                  <div className="mt-5">
                    <EvaluationTrendChart trends={evaluations?.trends ?? []} />
                  </div>
                </div>
                <div className="demo-panel rounded-[2rem] border border-white/10 p-5">
                  <h3 className="text-xl font-semibold text-white">Model usage and cost split</h3>
                  <p className="mt-1 text-sm text-[var(--hp-text-muted)]">
                    The executive pitch is stronger when you can explain the quality and cost posture in the same frame.
                  </p>
                  <div className="mt-5">
                    <ModelUsageTable rows={modelUsage} />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </SceneSection>

        <SceneSection
          id="close"
          accent={selectedScenario ? AGENT_PROFILES[selectedScenario.leadAgent].accentColor : '#f59e0b'}
          eyebrow="Pick a scenario"
          title="Choose the story you want to prove next, then drop into the live product or operator surface behind it."
          description="The single-page demo is the front door. The existing commerce, admin, and staff routes remain intact as drill-downs from each narrative thread."
        >
          <div className="grid gap-6 @4xl/scene:grid-cols-[minmax(0,1.05fr)_minmax(18rem,0.95fr)] @4xl/scene:items-center">
            <div className="grid gap-4 md:grid-cols-2">
              {SCENARIO_OPTIONS.map((scenario) => {
                const leadProfile = AGENT_PROFILES[scenario.leadAgent];
                const active = scenario.id === selectedScenarioId;
                return (
                  <button
                    key={scenario.id}
                    type="button"
                    onClick={() => setSelectedScenarioId(scenario.id)}
                    className={`rounded-[1.8rem] border p-5 text-left transition ${
                      active
                        ? 'border-white/20 bg-white/10 shadow-[0_0_30px_rgba(255,255,255,0.06)]'
                        : 'border-white/10 bg-white/5 hover:border-white/20 hover:bg-white/8'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[var(--hp-text-faint)]">
                          {leadProfile.domainLabel}
                        </p>
                        <h3 className="mt-3 text-xl font-semibold text-white">{scenario.title}</h3>
                      </div>
                      <span
                        className="demo-telemetry rounded-full border border-white/10 bg-black/20 px-3 py-1 text-xs text-white"
                      >
                        {scenario.metric}
                      </span>
                    </div>
                  </button>
                );
              })}
            </div>

            <div className="demo-panel rounded-[2rem] border border-white/10 p-6">
              <div className="flex items-start gap-4">
                <RobotLaunchButton
                  slug={selectedScenario.leadAgent}
                  size={132}
                  state="waving"
                  thinkingMessage={AGENT_PROFILES[selectedScenario.leadAgent].oneLiner}
                  onOpen={setSelectedAgentSlug}
                />
                <div className="space-y-4">
                  <DemoKicker>Next drill-down</DemoKicker>
                  <h3 className="text-2xl font-semibold text-white">{selectedScenario.title}</h3>
                  <p className="text-sm leading-7 text-[var(--hp-text-muted)]">
                    {AGENT_PROFILES[selectedScenario.leadAgent].retailProblem}
                  </p>
                  <div className="flex flex-wrap gap-3">
                    <Link
                      href={`/scenarios/${selectedScenario.id}`}
                      className="btn-primary inline-flex items-center rounded-full px-5 py-3 text-sm font-semibold"
                    >
                      Open scenario brief
                    </Link>
                    <Link
                      href={selectedScenario.liveSurfaceHref}
                      className="inline-flex items-center rounded-full border border-white/10 bg-white/5 px-5 py-3 text-sm font-semibold text-white transition hover:border-white/20 hover:bg-white/10"
                    >
                      Open live surface
                    </Link>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </SceneSection>

        <aside className="pointer-events-none sticky bottom-0 z-20 px-4 pb-4 md:px-6">
          <div className="demo-panel pointer-events-auto mx-auto max-w-6xl rounded-full border border-white/10 px-4 py-3">
            <div className="demo-telemetry flex flex-wrap items-center justify-center gap-x-5 gap-y-2 text-sm text-[var(--hp-text-muted)]">
              <span>
                Total products
                <strong className="ml-2 text-white">
                  {(truthSummary?.total_products ?? uiProducts.length).toLocaleString()}
                </strong>
              </span>
              <span>
                Avg latency
                <strong className="ml-2 text-white">{formatLatencyMs(railLatency)}</strong>
              </span>
              <span>
                Cost / call
                <strong className="ml-2 text-white">{formatCurrency(railCostPerCall, 4)}</strong>
              </span>
              <span>
                Eval score
                <strong className="ml-2 text-white">
                  {overallEvalScore !== null ? overallEvalScore.toFixed(2) : 'n/a'}
                </strong>
              </span>
              <span>
                Tier mix
                <strong className="ml-2 text-white">{tierMixLabel}</strong>
              </span>
              <span>
                Categories
                <strong className="ml-2 text-white">{categories.length}</strong>
              </span>
            </div>
          </div>
        </aside>
      </div>

      <AgentProfileDrawer
        open={Boolean(selectedProfile)}
        profile={selectedProfile}
        liveMetrics={selectedProfile ? profileMetrics[selectedProfile.slug] : null}
        onClose={() => setSelectedAgentSlug(null)}
      />
    </MainLayout>
  );
}

export default ExecutiveDemoPage;