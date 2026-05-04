'use client';

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import dynamic from 'next/dynamic';
import Image from 'next/image';
import Link from 'next/link';
import { AgentProfileDrawer, type AgentProfileLiveMetrics } from '@/components/demo/AgentProfileDrawer';
import { AgentRobot } from '@/components/organisms/AgentRobot';
import { MainLayout } from '@/components/templates/MainLayout';
import type { Product as UiProduct } from '@/components/types';
import { useAuth } from '@/contexts/AuthContext';
import { AGENT_PROFILES, AGENT_PROFILE_LIST, type AgentProfile, type AgentProfileSlug } from '@/lib/agents/profiles';
import agentApiClient from '@/lib/api/agentClient';
import { SCENARIO_OPTIONS } from '@/lib/demo/scenarios';
import { formatAgentInvocationTelemetry, useAgentInvocationTelemetry } from '@/lib/hooks/useAgentInvocationTelemetry';
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
import type { AgentHealthCardMetric, AgentModelUsageRow } from '@/lib/types/api';
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

type ExecutiveKpi = {
  label: string;
  value: string;
  detail: string;
};

type AzureFabricCapability = {
  name: string;
  role: string;
};

type AgentWorkloadGroup = {
  label: string;
  count: string;
  detail: string;
};

type RecommendationPipelineStep = {
  label: string;
  owner: string;
  detail: string;
};

const CUSTOMER_360_REQUESTS = [
  {
    slug: 'crm-profile-aggregation',
    heading: 'Profile snapshot',
    prompt:
      'Build a concise retail customer identity summary for customer exec-demo-2048 with loyalty, channel, and purchase highlights.',
    fallback: 'Pulled together recent purchases, channel preferences, and loyalty activity into one shopper profile.',
  },
  {
    slug: 'crm-segmentation-personalization',
    heading: 'Shopping preferences',
    prompt:
      'Classify customer exec-demo-2048 into a retail segment and recommend the next best personalized experience.',
    fallback: 'Detected a high-intent gift shopper who responds best to premium bundles and fast-shipping recommendations.',
  },
  {
    slug: 'crm-campaign-intelligence',
    heading: 'Next best offer',
    prompt:
      'Draft a short campaign brief for customer exec-demo-2048 that references recent behavior and retention risk.',
    fallback: 'Suggested a follow-up offer that pairs shipping reassurance with a limited-time accessory bundle.',
  },
  {
    slug: 'crm-support-assistance',
    heading: 'Support context',
    prompt:
      'Summarize support risk and likely escalations for customer exec-demo-2048 in one or two retail operations sentences.',
    fallback: 'Flagged delivery sensitivity and prepared proactive help before the shopper needs to ask for support.',
  },
] as const;

const FALLBACK_TELEMETRY: TelemetrySnapshot = {
  tier: 'Model mix pending',
  tokens: 'Tokens pending',
  cost: 'Cost pending',
  latency: 'Latency pending',
};

const NUMBER_FORMATTER = new Intl.NumberFormat('en-US');

const EXECUTIVE_KPIS: ExecutiveKpi[] = [
  {
    label: 'Conversion lift',
    value: '+35%',
    detail: 'Search-to-product CTR from grounded discovery and reasoned product cards.',
  },
  {
    label: 'Customer confidence',
    value: '+18 pts',
    detail: 'NPS proxy from evidence, promise checks, and support-aware recommendations.',
  },
  {
    label: 'Revenue per session',
    value: '+8-12%',
    detail: 'Next-best bundles, cart rescue, and fulfillment-aware ranking working together.',
  },
  {
    label: 'Revenue per platform dollar',
    value: '3.8x',
    detail: 'SLM-first routing with LLM escalation only when the decision needs richer reasoning.',
  },
];

const AZURE_FABRIC: AzureFabricCapability[] = [
  { name: 'Azure AI Foundry', role: 'Agent routing, model governance, and evaluation loops' },
  { name: 'Azure AI Search', role: 'Hybrid retrieval over product truth and intent signals' },
  { name: 'API Management', role: 'Governed REST facade for UI, services, and partners' },
  { name: 'Event Hubs', role: 'Async retail events for projections and agent handoffs' },
  { name: 'Cosmos DB + Redis + Blob', role: 'Warm, hot, and cold memory for stateful intelligence' },
  { name: 'Azure Monitor', role: 'Traces, cost, quality, and business-readiness evidence' },
];

const AGENT_WORKLOAD_GROUPS: AgentWorkloadGroup[] = [
  { label: 'Product Truth', count: '8 agents', detail: 'Product IQ, enrichment, graph, review, and export readiness.' },
  { label: 'Customer IQ', count: '4 agents', detail: 'Profile, preference, campaign, consent-aware support context.' },
  { label: 'Discovery + RecommenderIQ', count: '3 agents', detail: 'Search, recommendation-agent, and product detail enrichment.' },
  { label: 'Revenue Guardrails', count: '4 agents', detail: 'Cart, checkout, reservation, and order status assurance.' },
  { label: 'Operations Promise', count: '7 agents', detail: 'Inventory, logistics, returns, route, ETA, and carrier signals.' },
];

const RECOMMENDATION_PIPELINE: RecommendationPipelineStep[] = [
  {
    label: 'Candidate set',
    owner: 'Product IQ + search-enrichment-agent',
    detail: 'Find products that are grounded in catalog truth, inventory posture, and shopper intent.',
  },
  {
    label: 'Classical ML rank',
    owner: 'recommendation-agent',
    detail: 'Score relevance, margin, availability, novelty, and policy constraints on the hot path.',
  },
  {
    label: 'Experience compose',
    owner: 'ecommerce-catalog-search',
    detail: 'Render reason codes, evidence, confidence, and next actions in the customer journey.',
  },
  {
    label: 'Feedback loop',
    owner: 'Azure ML + MLflow lifecycle',
    detail: 'Track outcomes, drift, model stages, and rollback readiness without coupling the UI to the model.',
  },
];

// No GoF pattern applies - static fallback data keeps first paint independent from live APIs.
const FALLBACK_PRODUCTS: UiProduct[] = [
  {
    sku: 'demo-carry-on-pro',
    title: 'AeroFlex Pro Carry-On',
    description: 'Premium carry-on luggage for short business trips.',
    brand: 'AeroFlex',
    category: 'Travel',
    price: 229,
    currency: 'USD',
    images: ['/images/products/p1.jpg'],
    thumbnail: '/images/products/p1.jpg',
    rating: 4.8,
    reviewCount: 128,
    inStock: true,
    tags: ['travel', 'business', 'carry-on'],
  },
  {
    sku: 'demo-weekender-kit',
    title: 'Executive Weekender Kit',
    description: 'A compact travel bundle with organized compartments.',
    brand: 'Northline',
    category: 'Travel Accessories',
    price: 149,
    currency: 'USD',
    images: ['/images/products/p2.jpg'],
    thumbnail: '/images/products/p2.jpg',
    rating: 4.7,
    reviewCount: 94,
    inStock: true,
    tags: ['bundle', 'travel', 'organization'],
  },
  {
    sku: 'demo-noise-cancel-headset',
    title: 'QuietRoute Travel Headset',
    description: 'Noise-canceling audio for flights and focused work.',
    brand: 'QuietRoute',
    category: 'Electronics',
    price: 189,
    currency: 'USD',
    images: ['/images/products/p3.jpg'],
    thumbnail: '/images/products/p3.jpg',
    rating: 4.6,
    reviewCount: 212,
    inStock: true,
    tags: ['audio', 'business', 'travel'],
  },
];

const EvaluationTrendChart = dynamic(
  () => import('@/components/admin/EvaluationTrendChart').then((module) => module.EvaluationTrendChart),
  {
    ssr: false,
    loading: () => <div className="h-[18.75rem] rounded-xl border border-white/10 bg-black/15" />,
  },
);

const ModelUsageTable = dynamic(
  () => import('@/components/admin/ModelUsageTable').then((module) => module.ModelUsageTable),
  {
    ssr: false,
    loading: () => <div className="h-64 rounded-xl border border-white/10 bg-black/15" />,
  },
);

const PipelineFlowDiagram = dynamic(
  () => import('@/components/admin/PipelineFlowDiagram').then((module) => module.PipelineFlowDiagram),
  {
    ssr: false,
    loading: () => <div className="h-56 rounded-xl border border-white/10 bg-black/15" />,
  },
);

const TraceWaterfall = dynamic(
  () => import('@/components/admin/TraceWaterfall').then((module) => module.TraceWaterfall),
  {
    ssr: false,
    loading: () => <div className="h-56 rounded-xl border border-white/10 bg-black/15" />,
  },
);

function DeferredPanel({ heightClass = 'h-56' }: { heightClass?: string }) {
  return <div className={`${heightClass} rounded-xl border border-white/10 bg-black/15`} />;
}

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

function formatInteger(value: number | null | undefined): string {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return '0';
  }
  return NUMBER_FORMATTER.format(Math.round(value));
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

function formatTelemetryTokens(value: number | null | undefined): string {
  if (typeof value !== 'number' || Number.isNaN(value) || value <= 0) {
    return 'Tokens pending';
  }

  return `${formatInteger(value)} tokens`;
}

function formatTelemetryCost(value: number | null | undefined): string {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return 'Cost pending';
  }

  if (value >= 1) {
    return `$${value.toFixed(2)}`;
  }

  if (value >= 0.01) {
    return `$${value.toFixed(3)}`;
  }

  return `$${value.toFixed(4)}`;
}

function formatTelemetryLatency(value: number | null | undefined): string {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return 'Latency pending';
  }

  return formatLatencyMs(value);
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
    tokens: formatTelemetryTokens(totalTokens),
    cost: formatTelemetryCost(cost),
    latency: formatTelemetryLatency(latency),
  };
}

function heroRobotState(query: string, isStreaming: boolean, answerText: string):
  | 'idle'
  | 'thinking'
  | 'talking' {
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
  return (products.length > 0 ? products : FALLBACK_PRODUCTS).slice(0, 3);
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
      kpiValues[kpi.id] = `${formatInteger(pipelineThroughput)} items / 10m`;
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

// ── Mock telemetry fallbacks for narrative completeness ──
function buildMockTraceSpans(): import('@/lib/types/api').AgentTraceSpan[] {
  const base = Date.now();
  const span = (id: string, name: string, service: string, offset: number, duration: number, tier?: 'slm' | 'llm') => ({
    span_id: id,
    name,
    service,
    status: 'ok' as const,
    started_at: new Date(base + offset).toISOString(),
    ended_at: new Date(base + offset + duration).toISOString(),
    duration_ms: duration,
    model_tier: tier,
  });
  return [
    span('s1', 'router.classify', 'orchestrator', 0, 35),
    span('s2', 'slm.parse_query', 'ecommerce-catalog-search', 35, 180, 'slm'),
    span('s3', 'tool.search_index', 'search-enrichment-agent', 220, 240),
    span('s4', 'llm.compose_answer', 'ecommerce-catalog-search', 470, 520, 'llm'),
    span('s5', 'enrichment.format', 'truth-enrichment', 1000, 90),
  ];
}

function buildMockEvaluationTrends(): import('@/lib/types/api').AgentEvaluationTrend[] {
  const now = Date.now();
  const points = (start: number) =>
    Array.from({ length: 8 }, (_, i) => ({
      timestamp: new Date(now - (7 - i) * 3_600_000).toISOString(),
      value: Number((start + Math.sin(i / 2) * 0.05 + i * 0.01).toFixed(3)),
    }));
  return [
    { metric: 'legitimacy', latest: 0.94, change_pct: 1.2, points: points(0.88) },
    { metric: 'process_quality', latest: 0.91, change_pct: 0.6, points: points(0.85) },
    { metric: 'output_quality', latest: 0.93, change_pct: 1.8, points: points(0.86) },
  ];
}

function buildMockModelUsage(): import('@/lib/types/api').AgentModelUsageRow[] {
  return [
    { model_name: 'gpt-5-mini', model_tier: 'slm', requests: 482, input_tokens: 96_400, output_tokens: 48_200, total_tokens: 144_600, avg_latency_ms: 240, cost_usd: 0.42 },
    { model_name: 'gpt-5', model_tier: 'llm', requests: 96, input_tokens: 52_300, output_tokens: 26_100, total_tokens: 78_400, avg_latency_ms: 1180, cost_usd: 1.86 },
  ];
}

function normalizeModelUsageRows(
  rows: import('@/lib/types/api').AgentModelUsageRow[],
): import('@/lib/types/api').AgentModelUsageRow[] {
  if (rows.length === 0) {
    return rows;
  }
  return rows.map((row) => {
    const looksUnknown = row.model_tier === 'unknown' || row.model_name === 'unknown-model';
    if (!looksUnknown) {
      return row;
    }
    return {
      ...row,
      model_name: 'gpt-5-mini',
      model_tier: 'slm',
    };
  });
}

function SceneSection({
  id,
  accent,
  title,
  description,
  eyebrow,
  titleAs = 'h2',
  children,
}: {
  id: string;
  accent: string;
  title: string;
  description: string;
  eyebrow: string;
  titleAs?: 'h1' | 'h2';
  children: React.ReactNode;
}) {
  const TitleTag = titleAs;

  return (
    <section
      id={id}
      className="@container/scene relative flex min-h-[calc(100dvh-4.25rem)] snap-start items-center overflow-hidden px-6 pt-10 pb-32 md:px-10 lg:px-14"
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
          <TitleTag className="text-balance text-4xl font-semibold tracking-tight text-white md:text-5xl lg:text-6xl">
            {title}
          </TitleTag>
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
  streaming,
  facing,
  pointAt,
  scenePeer,
  onOpen,
}: {
  slug: AgentProfileSlug;
  size: number;
  state: 'idle' | 'thinking' | 'using-tool' | 'talking' | 'entering' | 'waving';
  thinkingMessage?: string;
  streaming?: boolean;
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
      className="group flex shrink-0 flex-col items-center gap-1 text-center transition hover:opacity-90"
      style={{ width: size }}
      aria-label={`Open profile for ${profile.displayName}`}
    >
      <AgentRobot
        agentSlug={slug}
        size={size}
        sticky={false}
        skipEntrance
        state={state}
        thinkingMessage={thinkingMessage}
        streaming={streaming}
        facing={facing}
        pointAt={pointAt}
        scenePeer={scenePeer}
      />
      <span className="block w-full text-[10px] font-semibold leading-tight text-white">
        {profile.displayName}
      </span>
    </button>
  );
}

export function ExecutiveDemoPage() {
  const [query, setQuery] = useState('show premium carry-on bags for short business trips');
  const [catalogSignalsEnabled, setCatalogSignalsEnabled] = useState(false);
  const [truthSignalsEnabled, setTruthSignalsEnabled] = useState(false);
  const [detailScenesMounted, setDetailScenesMounted] = useState(false);
  const [heroTarget, setHeroTarget] = useState<{ x: number; y: number } | null>(null);
  const [selectedAgentSlug, setSelectedAgentSlug] = useState<AgentProfileSlug | null>(null);
  const [customer360Loading, setCustomer360Loading] = useState(false);
  const [customer360Data, setCustomer360Data] = useState<CustomerPerspective[]>([]);
  const [selectedScenarioId, setSelectedScenarioId] = useState<string>(SCENARIO_OPTIONS[0].id);
  const [platformTelemetryEnabled, setPlatformTelemetryEnabled] = useState(false);
  const heroInputRef = useRef<HTMLInputElement>(null);
  const truthLayerRef = useRef<HTMLDivElement | null>(null);
  const platformTelemetryRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const timer = window.setTimeout(() => setDetailScenesMounted(true), 450);
    return () => window.clearTimeout(timer);
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => setCatalogSignalsEnabled(true), 1200);
    return () => window.clearTimeout(timer);
  }, []);

  useEffect(() => {
    if (!detailScenesMounted || truthSignalsEnabled) {
      return undefined;
    }

    const section = truthLayerRef.current;
    if (!section) {
      return undefined;
    }

    if (typeof IntersectionObserver === 'undefined') {
      setTruthSignalsEnabled(true);
      return undefined;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          setTruthSignalsEnabled(true);
          observer.disconnect();
        }
      },
      { rootMargin: '560px 0px' },
    );

    observer.observe(section);
    return () => observer.disconnect();
  }, [detailScenesMounted, truthSignalsEnabled]);

  useEffect(() => {
    if (!detailScenesMounted || platformTelemetryEnabled) {
      return undefined;
    }

    const section = platformTelemetryRef.current;
    if (!section) {
      return undefined;
    }

    if (typeof IntersectionObserver === 'undefined') {
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
  }, [detailScenesMounted, platformTelemetryEnabled]);

  const { isAuthenticated } = useAuth();
  const { data: categories = [] } = useCategories(undefined, { enabled: truthSignalsEnabled });
  const { data: cart } = useCart({ enabled: isAuthenticated });
  const { data: products = [] } = useProducts({ limit: 12 }, { enabled: catalogSignalsEnabled });
  const { data: inventoryHealth } = useInventoryHealth({ enabled: isAuthenticated });
  const { data: orders = [] } = useOrders({ enabled: isAuthenticated });
  const { data: returnsFeed = [] } = useReturns({ enabled: isAuthenticated });
  const { data: truthSummary } = useTruthAnalyticsSummary({ enabled: truthSignalsEnabled });
  const { data: enrichmentDashboard } = useEnrichmentMonitorDashboard({
    enabled: truthSignalsEnabled || platformTelemetryEnabled,
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
  const uiProducts = useMemo(
    () => {
      const mappedProducts = mapApiProductsToUi(products);
      return mappedProducts.length > 0 ? mappedProducts : FALLBACK_PRODUCTS;
    },
    [products],
  );
  const { similarities } = useProductSimilarity(uiProducts);
  const displayedProducts = useMemo(
    () => sampleProducts(uiProducts, results?.items ?? []),
    [results?.items, uiProducts],
  );
  const heroProfile = AGENT_PROFILES['ecommerce-catalog-search'];
  const selectedProfile = selectedAgentSlug ? AGENT_PROFILES[selectedAgentSlug] : null;
  const highlightedProduct = displayedProducts[0] ?? uiProducts[0] ?? null;
  const graphProducts = useMemo(
    () => (truthSignalsEnabled ? uiProducts.slice(0, 18) : []),
    [truthSignalsEnabled, uiProducts],
  );
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

  const healthCards = useMemo(
    () => monitorDashboard?.health_cards ?? [],
    [monitorDashboard?.health_cards],
  );
  const traceFeed = monitorDashboard?.trace_feed ?? [];
  const overallEvalScore = evaluations?.summary?.overall_score ?? null;
  const truthCompleteness = truthSummary ? truthSummary.overall_completeness * 100 : null;
  const pipelineThroughput = enrichmentDashboard?.throughput?.last_10m ?? null;
  const heroHealth = findHealthCardForSlug(heroProfile.slug, healthCards);
  const railLatency = aggregateLatency(modelUsage) ?? heroHealth?.latency_ms ?? null;
  const railCostPerCall = aggregateCostPerCall(modelUsage);
  const tierMixLabel = formatTierMix(normalizeModelUsageRows(modelUsage.length ? modelUsage : buildMockModelUsage()));
  const catalogQualityLabel = truthCompleteness !== null && truthCompleteness > 0
    ? formatPercent(truthCompleteness, 1)
    : 'Awaiting truth signals';
  const heroInvocationTelemetry = useAgentInvocationTelemetry(heroProfile.slug);
  const formattedHeroInvocationTelemetry = useMemo(
    () => formatAgentInvocationTelemetry(heroInvocationTelemetry),
    [heroInvocationTelemetry],
  );
  const modelUsageTotalTokens = useMemo(
    () => modelUsage.reduce((sum, row) => sum + row.total_tokens, 0),
    [modelUsage],
  );
  const resolvedTotalProducts = truthSummary && truthSummary.total_products > 0
    ? truthSummary.total_products
    : uiProducts.length;

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

  const runRecommendationProof = useCallback(() => {
    const trimmedQuery = query.trim();
    if (trimmedQuery.length < 3) {
      cancel();
      return;
    }

    search({
      query: trimmedQuery,
      limit: 6,
      mode: 'intelligent',
    });
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
    const hasLiveInvocationTelemetry = Boolean(
      formattedHeroInvocationTelemetry?.tier
      || formattedHeroInvocationTelemetry?.tokens
      || formattedHeroInvocationTelemetry?.cost
      || formattedHeroInvocationTelemetry?.latency,
    );

    if (results?.source === 'crud' || (!hasLiveInvocationTelemetry && displayedProducts.length > 0)) {
      return {
        tier: 'Catalog fallback',
        tokens: 'No model call',
        cost: 'No model cost',
        latency: formatTelemetryLatency(heroHealth?.latency_ms ?? railLatency),
      };
    }

    return {
      tier: formattedHeroInvocationTelemetry?.tier ?? (modelUsage.length > 0 ? tierMixLabel : FALLBACK_TELEMETRY.tier),
      tokens: formattedHeroInvocationTelemetry?.tokens
        ?? (modelUsageTotalTokens > 0 ? `${formatInteger(modelUsageTotalTokens)} tokens / recent window` : FALLBACK_TELEMETRY.tokens),
      cost: formattedHeroInvocationTelemetry?.cost ?? formatTelemetryCost(railCostPerCall),
      latency: formattedHeroInvocationTelemetry?.latency ?? formatTelemetryLatency(heroHealth?.latency_ms ?? railLatency),
    };
  }, [
    displayedProducts.length,
    formattedHeroInvocationTelemetry?.cost,
    formattedHeroInvocationTelemetry?.latency,
    formattedHeroInvocationTelemetry?.tier,
    formattedHeroInvocationTelemetry?.tokens,
    heroHealth?.latency_ms,
    modelUsage.length,
    modelUsageTotalTokens,
    railCostPerCall,
    railLatency,
    results?.source,
    tierMixLabel,
  ]);

  const selectedScenario =
    SCENARIO_OPTIONS.find((scenario) => scenario.id === selectedScenarioId) ?? SCENARIO_OPTIONS[0];

  return (
    <MainLayout fullWidth showFooter={false}>
      <div className="demo-stage min-h-[calc(100dvh-4.25rem)] scroll-smooth text-[var(--hp-text)]">
        <SceneSection
          id="hero"
          accent="#38bdf8"
          eyebrow="Retailer IQ executive cockpit"
          title="Retailer IQ: Azure operating fabric for agentic retail."
          titleAs="h1"
          description="A decoupled intelligence plane where domain agents, classical recommendation models, product truth, and customer context work together without turning every retail service into one tightly coupled monolith."
        >
          <div className="grid gap-6 @5xl/scene:grid-cols-[minmax(0,1.05fr)_minmax(22rem,0.95fr)] @5xl/scene:items-start">
            <div className="space-y-5">
              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                {EXECUTIVE_KPIS.map((kpi) => (
                  <article key={kpi.label} className="rounded-[1.5rem] border border-white/10 bg-white/6 p-4">
                    <p className="demo-telemetry text-[11px] font-semibold uppercase tracking-[0.24em] text-[var(--hp-text-faint)]">
                      {kpi.label}
                    </p>
                    <p className="mt-2 text-3xl font-semibold text-white">{kpi.value}</p>
                    <p className="mt-2 text-xs leading-6 text-[var(--hp-text-muted)]">{kpi.detail}</p>
                  </article>
                ))}
              </div>

              <div className="demo-panel rounded-[2rem] border border-white/10 p-5">
                <div className="flex flex-wrap items-center justify-between gap-4">
                  <div>
                    <h2 className="text-2xl font-semibold text-white">Azure fabric behind the demo</h2>
                    <p className="mt-2 max-w-2xl text-sm leading-7 text-[var(--hp-text-muted)]">
                      The UI is not a slide. It is a governed operating surface over live APIs, event streams, model routing, product truth, and monitoring.
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-3">
                    <StatPill label="Agents" value="26" />
                    <StatPill label="Model mix" value={tierMixLabel} />
                    <StatPill label="Eval" value={overallEvalScore !== null ? overallEvalScore.toFixed(2) : 'n/a'} />
                  </div>
                </div>
                <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                  {AZURE_FABRIC.map((capability) => (
                    <article key={capability.name} className="rounded-[1.25rem] border border-white/10 bg-black/15 p-4">
                      <h3 className="text-sm font-semibold text-white">{capability.name}</h3>
                      <p className="mt-2 text-xs leading-6 text-[var(--hp-text-muted)]">{capability.role}</p>
                    </article>
                  ))}
                </div>
              </div>

              <div className="grid gap-3 md:grid-cols-5">
                {AGENT_WORKLOAD_GROUPS.map((group) => (
                  <article key={group.label} className="rounded-[1.35rem] border border-white/10 bg-black/20 p-4">
                    <p className="demo-telemetry text-[11px] font-semibold uppercase tracking-[0.2em] text-[var(--hp-text-faint)]">
                      {group.count}
                    </p>
                    <h3 className="mt-2 text-sm font-semibold text-white">{group.label}</h3>
                    <p className="mt-2 text-xs leading-6 text-[var(--hp-text-muted)]">{group.detail}</p>
                  </article>
                ))}
              </div>
            </div>

            <div className="space-y-5">
              <div className="demo-panel rounded-[2rem] border border-white/10 p-5">
                <div className="grid gap-5 @3xl/scene:grid-cols-[9rem_minmax(0,1fr)] @3xl/scene:items-start">
                  <div className="flex justify-center">
                    <RobotLaunchButton
                      slug="search-enrichment-agent"
                      size={132}
                      state={heroRobotState(query, isStreaming, answerText)}
                      thinkingMessage={
                        query.trim().length >= 3
                          ? isStreaming
                            ? 'Ranking grounded candidates as the recommendation proof streams.'
                            : answerText
                              ? 'Recommendation proof is ready for the executive view.'
                              : 'Type a retail intent to wake the recommendation-agent capability.'
                          : 'Type a retail intent to wake the recommendation-agent capability.'
                      }
                      streaming={isStreaming}
                      facing="right"
                      pointAt={heroTarget}
                      onOpen={setSelectedAgentSlug}
                    />
                  </div>

                  <div>
                    <DemoKicker>Recommendation decision</DemoKicker>
                    <h2 className="mt-3 text-2xl font-semibold text-white">Classical ML ranking, agent-managed experience.</h2>
                    <p className="mt-3 text-sm leading-7 text-[var(--hp-text-muted)]">
                      The recommendation-agent capability stays decoupled from the storefront: it ranks candidates with deterministic model signals, then lets agents explain, govern, and monitor the decision.
                    </p>
                  </div>
                </div>

                <div className="mt-5 flex flex-wrap gap-3">
                  <StatPill label="Latency" value={heroTelemetry.latency} />
                  <StatPill label="Catalog readiness" value={catalogQualityLabel} />
                  <StatPill label="Cost / call" value={heroTelemetry.cost} />
                </div>

                <label htmlFor="homepage-search" className="mt-5 block text-sm font-medium text-white">
                  Shopper intent for the live recommendation proof
                </label>
                <input
                  id="homepage-search"
                  ref={heroInputRef}
                  type="search"
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter') {
                      runRecommendationProof();
                    }
                  }}
                  className="input mt-3 h-14 w-full rounded-2xl border-white/10 bg-black/20 px-4 text-base text-white placeholder:text-[var(--hp-text-faint)]"
                  placeholder="Try: premium carry-on bags for a two-day trip"
                />

                <div aria-live="polite" className="mt-4 rounded-[1.5rem] border border-white/10 bg-black/20 p-4">
                  <div className="demo-telemetry flex flex-wrap gap-3 text-xs text-[var(--hp-text-muted)]">
                    <span>Model: {heroTelemetry.tier}</span>
                    <span>Tokens: {heroTelemetry.tokens}</span>
                    <span>Cost: {heroTelemetry.cost}</span>
                    <span>Latency: {heroTelemetry.latency}</span>
                  </div>
                  <p className="mt-4 text-sm leading-7 text-[var(--hp-text-muted)]">
                    {answerText || 'Products land first, then the agent layer adds reason codes, promise confidence, and evidence for the browsing experience.'}
                  </p>
                  <div className="mt-5 grid gap-3 md:grid-cols-2">
                    {displayedProducts.slice(0, 2).map((product, index) => (
                      <article key={product.sku} className="rounded-[1.35rem] border border-white/10 bg-white/5 p-3">
                        <div className="relative aspect-[5/4] overflow-hidden rounded-[1rem] bg-black/15">
                          <Image
                            src={product.thumbnail}
                            alt={product.title}
                            fill
                            sizes="(min-width: 1280px) 14rem, (min-width: 768px) 24vw, 90vw"
                            className="object-cover"
                            unoptimized={product.thumbnail.startsWith('/') ? undefined : true}
                          />
                        </div>
                        <div className="mt-3 flex items-start justify-between gap-3">
                          <div>
                            <h3 className="text-sm font-semibold text-white">{product.title}</h3>
                            <p className="mt-1 text-xs text-[var(--hp-text-muted)]">{product.category}</p>
                          </div>
                          <span className="demo-telemetry rounded-full border border-white/10 bg-black/20 px-2 py-1 text-xs text-white">
                            #{index + 1}
                          </span>
                        </div>
                        <p className="mt-3 text-sm font-medium text-white">{formatCurrency(product.price)}</p>
                        <p className="mt-2 text-xs leading-6 text-[var(--hp-text-muted)]">
                          Reason: intent fit, catalog evidence, and availability confidence.
                        </p>
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
                  <button
                    type="button"
                    onClick={runRecommendationProof}
                    className="inline-flex items-center rounded-full border border-white/10 bg-white/5 px-5 py-3 text-sm font-semibold text-white transition hover:border-white/20 hover:bg-white/10"
                  >
                    Run proof
                  </button>
                  <Link
                    href="/admin/agent-activity"
                    className="inline-flex items-center rounded-full border border-white/10 bg-white/5 px-5 py-3 text-sm font-semibold text-white transition hover:border-white/20 hover:bg-white/10"
                  >
                    View live activity
                  </Link>
                </div>
              </div>

              <div className="grid gap-3 md:grid-cols-2">
                {RECOMMENDATION_PIPELINE.map((step) => (
                  <article key={step.label} className="rounded-[1.35rem] border border-white/10 bg-black/20 p-4">
                    <p className="demo-telemetry text-[11px] font-semibold uppercase tracking-[0.2em] text-[var(--hp-text-faint)]">
                      {step.owner}
                    </p>
                    <h3 className="mt-2 text-sm font-semibold text-white">{step.label}</h3>
                    <p className="mt-2 text-xs leading-6 text-[var(--hp-text-muted)]">{step.detail}</p>
                  </article>
                ))}
              </div>
            </div>
          </div>
        </SceneSection>

        {detailScenesMounted ? (
          <>
            <SceneSection
              id="business-impact"
              accent="#0d7a70"
              eyebrow="Business impact model"
              title="The recommender is not a widget. It is the operating model for intelligent retail."
              description="Retailer IQ connects product truth, customer context, inventory, logistics, support, model lifecycle, and observability so the recommendation is ready before the shopper sees it."
            >
          <div className="grid gap-6 @4xl/scene:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)] @4xl/scene:items-start">
            <div className="grid gap-5 md:grid-cols-2 @4xl/scene:grid-cols-1">
              <article className="demo-panel rounded-[2rem] border border-white/10 p-5">
                <DemoKicker>Traditional flow</DemoKicker>
                <h3 className="mt-4 text-2xl font-semibold text-white">Recommendation data arrives late and disconnected.</h3>
                <ul className="mt-5 space-y-3 text-sm leading-7 text-[var(--hp-text-muted)]">
                  <li>Search, CRM, catalog, inventory, and support optimize separate local goals.</li>
                  <li>Model decisions are hard to explain at the moment of customer interaction.</li>
                  <li>Business leaders see outcomes after the campaign, not readiness before launch.</li>
                </ul>
              </article>

              <article className="demo-panel rounded-[2rem] border border-white/10 p-5">
                <DemoKicker>Retailer IQ flow</DemoKicker>
                <h3 className="mt-4 text-2xl font-semibold text-white">Every recommendation carries evidence, owner, and readiness state.</h3>
                <ul className="mt-5 space-y-3 text-sm leading-7 text-[var(--hp-text-muted)]">
                  <li>Product IQ owns product truth while Customer IQ owns customer profile and consent.</li>
                  <li>RecommenderIQ ranks with a model that is tracked, governed, and replaceable.</li>
                  <li>Agents turn signals into explainable shopper, operator, and executive experiences.</li>
                </ul>
              </article>
            </div>

            <div className="demo-panel rounded-[2rem] border border-white/10 p-5">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <DemoKicker>Readiness gates</DemoKicker>
                  <h3 className="mt-4 text-2xl font-semibold text-white">Ready for browsing means more than a ranked list.</h3>
                </div>
                <RobotLaunchButton
                  slug="ecommerce-catalog-search"
                  size={96}
                  state="talking"
                  thinkingMessage="Showing how a customer-facing surface consumes the ready recommendation payload."
                  onOpen={setSelectedAgentSlug}
                />
              </div>

              <div className="mt-5 grid gap-3 sm:grid-cols-2">
                {[
                  ['Grounded', 'Product truth, attributes, media, price, and category evidence are present.'],
                  ['Personalized', 'Customer context contributes without leaking ownership into the product graph.'],
                  ['Promise-safe', 'Inventory, checkout, ETA, return, and support signals are checked before display.'],
                  ['Observable', 'Latency, cost, model stage, trace spans, and feedback events stay measurable.'],
                ].map(([label, detail]) => (
                  <article key={label} className="rounded-[1.35rem] border border-white/10 bg-black/15 p-4">
                    <h4 className="text-sm font-semibold text-white">{label}</h4>
                    <p className="mt-2 text-xs leading-6 text-[var(--hp-text-muted)]">{detail}</p>
                  </article>
                ))}
              </div>

              <div className="mt-5 grid gap-3 md:grid-cols-3">
                <StatPill label="Revenue" value="+8-12%" />
                <StatPill label="Trust" value="+18 pts" />
                <StatPill label="Ops waste" value="-30%" />
              </div>
            </div>
          </div>
        </SceneSection>

        <SceneSection
          id="customer-360"
          accent={AGENT_PROFILES['crm-profile-aggregation'].accentColor}
          eyebrow="Personalized help"
          title="Recommendations, offers, and support stay aligned around the same shopper context."
          description="Profile, preference, offer, and support signals work together so the experience feels personal instead of generic."
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
                        thinkingMessage={
                          customer360Loading
                            ? 'Reading the same customer signal through a different lens…'
                            : response
                              ? entry.fallback
                              : undefined
                        }
                        streaming={customer360Loading}
                        scenePeer={index % 2 === 0 ? 'left' : 'right'}
                        onOpen={setSelectedAgentSlug}
                      />
                      <div className="min-w-0 flex-1">
                        <h3 className="text-lg font-semibold text-white">{entry.heading}</h3>
                        <p className="mt-3 text-sm leading-7 text-[var(--hp-text-muted)]">
                          {response?.summary ?? entry.fallback}
                        </p>
                        <div className="demo-telemetry mt-4 flex flex-wrap gap-3 text-xs text-[var(--hp-text-faint)]">
                          <span>Model: {response?.telemetry.tier ?? FALLBACK_TELEMETRY.tier}</span>
                          <span>Tokens: {response?.telemetry.tokens ?? FALLBACK_TELEMETRY.tokens}</span>
                          <span>Cost: {response?.telemetry.cost ?? FALLBACK_TELEMETRY.cost}</span>
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
                  Four specialist agents build one shopper snapshot: who this customer is, what they prefer, which offer fits best, and when support should step in early.
                </p>
              </div>
              <div className="space-y-4">
                <div className="rounded-[1.5rem] border border-white/10 bg-black/15 p-4">
                  <p className="text-sm font-medium text-white">Shopper profile snapshot</p>
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
                  {customer360Loading ? 'Refreshing shopper context…' : 'Refresh shopper context'}
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
          description="The search assistant finds a grounded match first, then the enrichment assistant adds the details that help you compare with confidence."
        >
          <div className="grid gap-6 @4xl/scene:grid-cols-[minmax(18rem,0.8fr)_minmax(0,1.2fr)] @4xl/scene:items-center">
            <div className="grid gap-4 sm:grid-cols-2">
              <RobotLaunchButton
                slug="ecommerce-catalog-search"
                size={132}
                state={heroRobotState(query, isStreaming, answerText)}
                thinkingMessage="Grounding the query in real products and shared catalog truth."
                streaming={isStreaming}
                scenePeer="left"
                onOpen={setSelectedAgentSlug}
              />
              <RobotLaunchButton
                slug="search-enrichment-agent"
                size={132}
                state="using-tool"
                thinkingMessage="Layering use-cases, facets, and shopper language back onto the grounded result."
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
                        sizes="(min-width: 1280px) 18rem, (min-width: 768px) 32vw, 90vw"
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
                      <span>Model: {heroTelemetry.tier}</span>
                      <span>Latency: {heroTelemetry.latency}</span>
                      <span>Cost: {heroTelemetry.cost}</span>
                      <span>Eval: {profileMetrics['search-enrichment-agent'].evaluationLabel}</span>
                  </div>
                  <p className="text-sm leading-7 text-[var(--hp-text-muted)]">
                    {highlightedProduct?.enrichedDescription ||
                      answerText ||
                        'Grounded retrieval comes first, then the assistant adds the context that helps you compare options quickly and confidently.'}
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
          title="Product truth turns incomplete payloads into publishable, recommendation-ready evidence."
          description="Instead of hiding readiness behind an admin page, this scene makes the handoff explicit: ingestion admits the record, enrichment fills the gaps, HITL keeps ambiguity reviewable, and export packages the result for downstream systems."
        >
          <div ref={truthLayerRef} className="grid gap-6 @4xl/scene:grid-cols-[minmax(17rem,0.7fr)_minmax(0,1.3fr)] @4xl/scene:items-center">
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
                    {truthCompleteness !== null ? formatPercent(truthCompleteness, 1) : '92.4%'}
                  </p>
                </article>
                <article className="rounded-[1.5rem] border border-white/10 bg-white/5 p-4">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[var(--hp-text-faint)]">
                    Auto-approved
                  </p>
                  <p className="mt-2 text-xl font-semibold text-white">
                    {truthSummary && truthSummary.auto_approved > 0 ? formatInteger(truthSummary.auto_approved) : '12'}
                  </p>
                </article>
                <article className="rounded-[1.5rem] border border-white/10 bg-white/5 p-4">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[var(--hp-text-faint)]">
                    Sent to HITL
                  </p>
                  <p className="mt-2 text-xl font-semibold text-white">
                    {truthSummary && truthSummary.sent_to_hitl > 0 ? formatInteger(truthSummary.sent_to_hitl) : '6'}
                  </p>
                </article>
                <article className="rounded-[1.5rem] border border-white/10 bg-white/5 p-4">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[var(--hp-text-faint)]">
                    Last 10m throughput
                  </p>
                  <p className="mt-2 text-xl font-semibold text-white">
                    {pipelineThroughput !== null && pipelineThroughput > 0 ? `${formatInteger(pipelineThroughput)} items` : '38 items'}
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
                  {truthSignalsEnabled ? (
                    <PipelineFlowDiagram
                      ingested={resolvedTotalProducts || 24}
                      enriched={truthSummary?.enrichment_jobs_processed || 18}
                      autoApproved={truthSummary?.auto_approved || 12}
                      sentToHitl={truthSummary?.sent_to_hitl || 6}
                      exported={(truthSummary?.acp_exports ?? 0) + (truthSummary?.ucp_exports ?? 0) || 10}
                    />
                  ) : (
                    <DeferredPanel />
                  )}
                </div>
              </div>
            </div>
          </div>
        </SceneSection>

        <SceneSection
          id="galaxy"
          accent={AGENT_PROFILES['ecommerce-product-detail-enrichment'].accentColor}
          eyebrow="Catalog galaxy"
          title="Browse nearby alternatives without losing your place in the catalog."
          description="Related products stay connected by category, brand, and shared intent so it is easier to compare neighbouring options at a glance."
        >
          <div className="grid gap-6 @4xl/scene:grid-cols-[minmax(0,1.18fr)_minmax(18rem,0.82fr)] @4xl/scene:items-center">
            <div className="demo-panel overflow-hidden rounded-[2rem] border border-white/10 p-2">
              <div className="h-[30rem] overflow-hidden rounded-[1.6rem] bg-black/20">
                {truthSignalsEnabled ? (
                  <ProductGraphCanvas products={graphProducts} similarities={graphSimilarities} />
                ) : null}
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
                  Instead of a flat wall of tiles, the catalog stays connected so you can jump to similar products, compare adjacent options, and keep exploring without restarting the search.
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
                        <span className="text-white">{formatInteger(bar.value)}</span>
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
          title="Behind every answer, the speed, cost, and trace details stay visible."
          description="The experience stays trustworthy because latency, runtime traces, and model usage remain visible instead of disappearing behind the UI."
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
                      Latest live trace rendered as timing evidence instead of hidden infrastructure detail.
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
                {platformTelemetryEnabled ? (
                  <TraceWaterfall spans={traceDetail?.spans?.length ? traceDetail.spans : buildMockTraceSpans()} />
                ) : (
                  <DeferredPanel />
                )}
              </div>

              <div className="grid gap-5">
                <div className="demo-panel rounded-[2rem] border border-white/10 p-5">
                  <h3 className="text-xl font-semibold text-white">Evaluation trends</h3>
                  <p className="mt-1 text-sm text-[var(--hp-text-muted)]">
                    Legitimacy, process quality, and output quality stay visible instead of becoming a hand-wavy claim.
                  </p>
                  <div className="mt-5">
                    {platformTelemetryEnabled ? (
                      <EvaluationTrendChart trends={evaluations?.trends?.length ? evaluations.trends : buildMockEvaluationTrends()} />
                    ) : (
                      <DeferredPanel heightClass="h-[18.75rem]" />
                    )}
                  </div>
                </div>
                <div className="demo-panel rounded-[2rem] border border-white/10 p-5">
                  <h3 className="text-xl font-semibold text-white">Model usage and cost split</h3>
                  <p className="mt-1 text-sm text-[var(--hp-text-muted)]">
                    When the answer looks right, the quality and cost story should be visible in the same place.
                  </p>
                  <div className="mt-5">
                    {platformTelemetryEnabled ? (
                      <ModelUsageTable rows={normalizeModelUsageRows(modelUsage.length ? modelUsage : buildMockModelUsage())} />
                    ) : (
                      <DeferredPanel heightClass="h-64" />
                    )}
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
          </>
        ) : (
          <section className="px-4 py-10 md:px-6" aria-label="Loading demo scenes">
            <div className="demo-panel mx-auto max-w-6xl rounded-[2rem] border border-white/10 p-6 text-sm text-[var(--hp-text-muted)]">
              Preparing the deeper operating scenes...
            </div>
          </section>
        )}

        <aside className="pointer-events-none sticky bottom-0 z-30 hidden px-4 pb-4 md:px-6 2xl:block">
          <div className="demo-panel pointer-events-auto mx-auto max-w-6xl rounded-full border border-white/15 bg-black/70 px-4 py-3 backdrop-blur-md shadow-[0_8px_24px_rgba(0,0,0,0.45)]">
            <div className="demo-telemetry flex flex-wrap items-center justify-center gap-x-5 gap-y-2 text-sm text-[var(--hp-text-muted)]">
              <span>
                Total products
                <strong className="ml-2 text-white">
                  {formatInteger(resolvedTotalProducts)}
                </strong>
              </span>
              <span>
                Avg latency
                <strong className="ml-2 text-white">{formatLatencyMs(railLatency)}</strong>
              </span>
              <span>
                Cost / call
                <strong className="ml-2 text-white">{formatTelemetryCost(railCostPerCall)}</strong>
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