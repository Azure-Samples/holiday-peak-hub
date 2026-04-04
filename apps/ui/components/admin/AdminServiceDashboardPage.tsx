'use client';

import { useCallback, useMemo, useState } from 'react';
import { MainLayout } from '@/components/templates/MainLayout';
import { Card } from '@/components/molecules/Card';
import { Badge } from '@/components/atoms/Badge';
import { Select } from '@/components/atoms/Select';
import { Button } from '@/components/atoms/Button';
import {
  useAdminServiceDashboard,
  DEFAULT_ADMIN_SERVICE_RANGE,
  ADMIN_SERVICE_RANGE_OPTIONS,
} from '@/lib/hooks/useAdminServiceDashboard';
import agentApiClient from '@/lib/api/agentClient';
import type {
  AdminServiceAppSurface,
  AdminServiceDomain,
  AdminServiceFoundrySurface,
  AgentMonitorTimeRange,
  AdminServiceStatus,
  AgentTraceStatus,
} from '@/lib/types/api';
import {
  FiClock, FiChevronDown, FiChevronRight,
  FiTool, FiCpu, FiMessageSquare, FiAlertCircle, FiCheckCircle, FiLoader,
  FiSend, FiZap, FiActivity, FiTerminal, FiCode,
  FiArrowRight,
} from 'react-icons/fi';

// ── Types ──

type InvokeRunStatus = 'idle' | 'running' | 'success' | 'error';

interface AgentRunRecord {
  id: string;
  message: string;
  status: InvokeRunStatus;
  startedAt: string;
  durationMs?: number;
  response?: Record<string, unknown>;
  responsePreview?: string[];
  error?: string;
  steps?: AgentRunStep[];
  tripleEvaluation?: TripleEvaluation;
}

interface AgentRunStep {
  type: 'tool_call' | 'model_invocation' | 'decision' | 'error';
  name: string;
  detail?: string;
  durationMs?: number;
  input?: string;
  output?: string;
}

interface TripleEvaluation {
  process: number;
  output: number;
  intent: number;
  legitimacy: 'high' | 'medium' | 'low';
  rationale: string[];
}

type PayloadOverride = Record<string, unknown>;

interface ParsedInvokeInput {
  promptText: string;
  overridePayload?: PayloadOverride;
}

interface PayloadBuildContext {
  domain: AdminServiceDomain;
  service: string;
  promptText: string;
  overridePayload?: PayloadOverride;
}

type PayloadStrategy = (context: PayloadBuildContext) => Record<string, unknown>;

// ── Constants ──

const STATUS_BADGE_VARIANT: Record<AdminServiceStatus, 'success' | 'warning' | 'danger' | 'secondary'> = {
  healthy: 'success',
  warning: 'warning',
  error: 'danger',
  unknown: 'secondary',
};

const ACTIVITY_STATUS_BADGE_VARIANT: Record<AgentTraceStatus, 'success' | 'warning' | 'danger' | 'secondary'> = {
  ok: 'success',
  warning: 'warning',
  error: 'danger',
  unknown: 'secondary',
};

const AGENT_SLUG_MAP: Record<string, Record<string, string>> = {
  crm: {
    campaigns: 'crm-campaign-intelligence',
    profiles: 'crm-profile-aggregation',
    segmentation: 'crm-segmentation-personalization',
    support: 'crm-support-assistance',
  },
  ecommerce: {
    catalog: 'ecommerce-catalog-search',
    cart: 'ecommerce-cart-intelligence',
    checkout: 'ecommerce-checkout-support',
    orders: 'ecommerce-order-status',
    products: 'ecommerce-product-detail-enrichment',
  },
  inventory: {
    health: 'inventory-health-check',
    alerts: 'inventory-alerts-triggers',
    replenishment: 'inventory-jit-replenishment',
    reservation: 'inventory-reservation-validation',
  },
  logistics: {
    carriers: 'logistics-carrier-selection',
    eta: 'logistics-eta-computation',
    returns: 'logistics-returns-support',
    routes: 'logistics-route-issue-detection',
  },
  products: {
    acp: 'product-management-acp-transformation',
    assortment: 'product-management-assortment-optimization',
    validation: 'product-management-consistency-validation',
    normalization: 'product-management-normalization-classification',
  },
};

const STEP_CONFIG: Record<AgentRunStep['type'], { color: string; bgLight: string; bgDark: string; icon: typeof FiTool }> = {
  tool_call: { color: '#3b82f6', bgLight: 'bg-blue-50', bgDark: 'dark:bg-blue-950/30', icon: FiTool },
  model_invocation: { color: '#8b5cf6', bgLight: 'bg-violet-50', bgDark: 'dark:bg-violet-950/30', icon: FiCpu },
  decision: { color: '#10b981', bgLight: 'bg-emerald-50', bgDark: 'dark:bg-emerald-950/30', icon: FiCheckCircle },
  error: { color: '#ef4444', bgLight: 'bg-red-50', bgDark: 'dark:bg-red-950/30', icon: FiAlertCircle },
};

const DOMAIN_GRADIENT: Record<string, string> = {
  crm: 'from-violet-500/10 via-fuchsia-500/5 to-transparent',
  ecommerce: 'from-blue-500/10 via-cyan-500/5 to-transparent',
  inventory: 'from-amber-500/10 via-orange-500/5 to-transparent',
  logistics: 'from-emerald-500/10 via-teal-500/5 to-transparent',
  products: 'from-rose-500/10 via-pink-500/5 to-transparent',
};

const DOMAIN_ACCENT: Record<string, string> = {
  crm: 'text-violet-600 dark:text-violet-400',
  ecommerce: 'text-blue-600 dark:text-blue-400',
  inventory: 'text-amber-600 dark:text-amber-400',
  logistics: 'text-emerald-600 dark:text-emerald-400',
  products: 'text-rose-600 dark:text-rose-400',
};

const PREVIEW_SENSITIVE_KEY_PATTERN = /(password|passphrase|secret|token|api[_-]?key|access[_-]?key|authorization|cookie|set-cookie|connection[_-]?string|credential|jwt|signature|private[_-]?key)/i;
const PREVIEW_MAX_LINES = 8;
const PREVIEW_MAX_STRING_LENGTH = 240;
const PREVIEW_MAX_JSON_LENGTH = 360;
const PREVIEW_MAX_DEPTH = 3;
const PREVIEW_MAX_ENTRIES_PER_LEVEL = 6;

const PREVIEW_PRIORITY_KEYS = [
  'summary', 'message', 'insight', 'recommendation', 'recommendations',
  'analysis', 'result', 'results', 'status', 'validation', 'error',
];

const TRACKING_ID_AGENT_SLUGS = new Set<string>([
  'logistics-eta-computation',
  'logistics-carrier-selection',
  'logistics-returns-support',
  'logistics-route-issue-detection',
]);

const CONTACT_ID_AGENT_SLUGS = new Set<string>([
  'crm-profile-aggregation',
  'crm-segmentation-personalization',
]);

const GENERIC_IDENTIFIER_TOKENS = new Set<string>([
  'check',
  'contact',
  'customer',
  'find',
  'for',
  'lookup',
  'my',
  'order',
  'please',
  'show',
  'status',
  'the',
  'tracking',
  'update',
  'with',
]);

const SAFE_FOUNDRY_FALLBACK_URL = 'https://ai.azure.com';

function toTitleCase(value: string): string {
  return value
    .split(/[-_\s]+/)
    .filter((part) => part.length > 0)
    .map((part) => `${part.slice(0, 1).toUpperCase()}${part.slice(1)}`)
    .join(' ');
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function truncateText(value: string, maxLength: number): string {
  if (value.length <= maxLength) return value;
  return `${value.slice(0, Math.max(0, maxLength - 1))}…`;
}

function pickFirstString(source: PayloadOverride | undefined, keys: string[]): string | undefined {
  if (!source) return undefined;
  for (const key of keys) {
    const candidate = source[key];
    if (typeof candidate === 'string' && candidate.trim().length > 0) {
      return candidate.trim();
    }
  }
  return undefined;
}

function pickFirstNumber(source: PayloadOverride | undefined, keys: string[]): number | undefined {
  if (!source) return undefined;
  for (const key of keys) {
    const candidate = source[key];
    if (typeof candidate === 'number' && Number.isFinite(candidate)) {
      return candidate;
    }
    if (typeof candidate === 'string') {
      const parsed = Number(candidate.trim());
      if (Number.isFinite(parsed)) {
        return parsed;
      }
    }
  }
  return undefined;
}

function isLikelyIdentifierToken(candidate: string): boolean {
  const normalized = candidate.trim();
  if (!normalized) return false;
  if (GENERIC_IDENTIFIER_TOKENS.has(normalized.toLowerCase())) return false;

  const hasDigit = /\d/.test(normalized);
  const hasAlphaNumericMix = /[A-Za-z]/.test(normalized) && hasDigit;
  const hasSeparatorWithDigit = /[-_]/.test(normalized) && hasDigit;
  const isLongNumeric = /^\d{5,}$/.test(normalized);

  return hasAlphaNumericMix || hasSeparatorWithDigit || isLongNumeric;
}

function inferIdentifierFromPrompt(promptText: string): string | undefined {
  const keywordMatch = promptText.match(
    /\b(?:order|tracking|track|contact|customer|shipment|return|id)\b[\s:#-]*([A-Za-z0-9][A-Za-z0-9_-]{2,})/i,
  );
  if (keywordMatch?.[1] && isLikelyIdentifierToken(keywordMatch[1])) {
    return keywordMatch[1];
  }

  const candidates = promptText.match(/[A-Za-z0-9][A-Za-z0-9_-]{2,}/g) ?? [];
  return candidates.find((candidate) => isLikelyIdentifierToken(candidate));
}

function inferQuantityFromPrompt(promptText: string): number | undefined {
  const match = promptText.match(/\b\d+(?:\.\d+)?\b/);
  if (!match) return undefined;
  const parsed = Number(match[0]);
  return Number.isFinite(parsed) ? parsed : undefined;
}

function parseInvokeInput(input: string): ParsedInvokeInput {
  let overridePayload: PayloadOverride | undefined;

  try {
    const parsed = JSON.parse(input) as unknown;
    if (isRecord(parsed)) {
      overridePayload = parsed;
    }
  } catch {
    // Free-text input should continue without JSON parsing errors.
  }

  const promptFromOverride = pickFirstString(overridePayload, ['prompt', 'message', 'query', 'text', 'input']);

  return {
    promptText: promptFromOverride ?? input,
    overridePayload,
  };
}

function withPayloadMetadata(payload: Record<string, unknown>, context: PayloadBuildContext): Record<string, unknown> {
  return {
    ...payload,
    source: 'admin_dashboard',
    domain: context.domain,
    service: context.service,
  };
}

function buildDefaultPayload(context: PayloadBuildContext): Record<string, unknown> {
  const query = pickFirstString(context.overridePayload, ['query', 'prompt', 'message', 'text', 'input']) ?? context.promptText;

  return withPayloadMetadata(
    {
      ...(context.overridePayload ?? {}),
      query,
      prompt: context.promptText,
      message: context.promptText,
    },
    context,
  );
}

function buildCatalogSearchPayload(context: PayloadBuildContext): Record<string, unknown> {
  const query = pickFirstString(context.overridePayload, ['query', 'prompt', 'message', 'text']) ?? context.promptText;
  return withPayloadMetadata(
    {
      ...(context.overridePayload ?? {}),
      query,
      prompt: context.promptText,
    },
    context,
  );
}

function buildInventoryReservationPayload(context: PayloadBuildContext): Record<string, unknown> {
  const sku =
    pickFirstString(context.overridePayload, ['sku', 'item_sku', 'product_id'])
    ?? inferIdentifierFromPrompt(context.promptText)
    ?? context.promptText;
  const requestQty =
    pickFirstNumber(context.overridePayload, ['request_qty', 'quantity', 'qty'])
    ?? inferQuantityFromPrompt(context.promptText)
    ?? 1;

  return withPayloadMetadata(
    {
      ...(context.overridePayload ?? {}),
      sku,
      request_qty: requestQty,
      prompt: context.promptText,
    },
    context,
  );
}

function buildOrderStatusPayload(context: PayloadBuildContext): Record<string, unknown> {
  const inferredIdentifier = inferIdentifierFromPrompt(context.promptText);
  const orderId = pickFirstString(context.overridePayload, ['order_id', 'orderId']);
  const trackingId = pickFirstString(context.overridePayload, ['tracking_id', 'trackingId']);
  const resolvedOrderId = orderId ?? (!trackingId ? inferredIdentifier : undefined);
  const resolvedTrackingId = trackingId ?? (!orderId ? inferredIdentifier : undefined);

  return withPayloadMetadata(
    {
      ...(context.overridePayload ?? {}),
      ...(resolvedOrderId ? { order_id: resolvedOrderId } : {}),
      ...(resolvedTrackingId ? { tracking_id: resolvedTrackingId } : {}),
      prompt: context.promptText,
    },
    context,
  );
}

function buildTrackingPayload(context: PayloadBuildContext): Record<string, unknown> {
  const trackingId =
    pickFirstString(context.overridePayload, ['tracking_id', 'trackingId'])
    ?? inferIdentifierFromPrompt(context.promptText);

  return withPayloadMetadata(
    {
      ...(context.overridePayload ?? {}),
      ...(trackingId ? { tracking_id: trackingId } : {}),
      prompt: context.promptText,
    },
    context,
  );
}

function buildContactPayload(context: PayloadBuildContext): Record<string, unknown> {
  const contactId =
    pickFirstString(context.overridePayload, ['contact_id', 'contactId', 'customer_id'])
    ?? inferIdentifierFromPrompt(context.promptText);

  return withPayloadMetadata(
    {
      ...(context.overridePayload ?? {}),
      ...(contactId ? { contact_id: contactId } : {}),
      prompt: context.promptText,
    },
    context,
  );
}

// Strategy pattern: each slug resolves to a payload shaping strategy.
const PAYLOAD_STRATEGIES: Record<string, PayloadStrategy> = {
  'crm-campaign-intelligence': buildCatalogSearchPayload,
  'ecommerce-catalog-search': buildCatalogSearchPayload,
  'inventory-reservation-validation': buildInventoryReservationPayload,
  'ecommerce-order-status': buildOrderStatusPayload,
};

function buildInvokePayload(agentSlug: string, context: PayloadBuildContext): Record<string, unknown> {
  const strategy =
    PAYLOAD_STRATEGIES[agentSlug]
    ?? (TRACKING_ID_AGENT_SLUGS.has(agentSlug) ? buildTrackingPayload : undefined)
    ?? (CONTACT_ID_AGENT_SLUGS.has(agentSlug) ? buildContactPayload : undefined)
    ?? buildDefaultPayload;

  return strategy(context);
}

function sanitizePreviewValue(value: unknown, keyPath: string[] = [], depth = 0): unknown {
  const currentKey = keyPath[keyPath.length - 1] ?? '';
  if (PREVIEW_SENSITIVE_KEY_PATTERN.test(currentKey)) {
    return '[REDACTED]';
  }

  if (typeof value === 'string') {
    return truncateText(value, PREVIEW_MAX_STRING_LENGTH);
  }

  if (typeof value === 'number' || typeof value === 'boolean' || value == null) {
    return value;
  }

  if (Array.isArray(value)) {
    if (depth >= PREVIEW_MAX_DEPTH) {
      return `[Array(${value.length})]`;
    }
    const sliced = value.slice(0, PREVIEW_MAX_ENTRIES_PER_LEVEL).map((item) => sanitizePreviewValue(item, keyPath, depth + 1));
    if (value.length > PREVIEW_MAX_ENTRIES_PER_LEVEL) {
      sliced.push(`... (${value.length - PREVIEW_MAX_ENTRIES_PER_LEVEL} more item${value.length - PREVIEW_MAX_ENTRIES_PER_LEVEL === 1 ? '' : 's'})`);
    }
    return sliced;
  }

  if (isRecord(value)) {
    if (depth >= PREVIEW_MAX_DEPTH) {
      return '[Object]';
    }

    const entries = Object.entries(value);
    const visibleEntries = entries.slice(0, PREVIEW_MAX_ENTRIES_PER_LEVEL).map(([key, nested]) => [
      key,
      sanitizePreviewValue(nested, [...keyPath, key], depth + 1),
    ] as const);

    if (entries.length > PREVIEW_MAX_ENTRIES_PER_LEVEL) {
      visibleEntries.push([
        '_truncated',
        `... (${entries.length - PREVIEW_MAX_ENTRIES_PER_LEVEL} more key${entries.length - PREVIEW_MAX_ENTRIES_PER_LEVEL === 1 ? '' : 's'})`,
      ]);
    }

    return Object.fromEntries(visibleEntries);
  }

  return String(value);
}

function formatPreviewValue(value: unknown): string {
  if (typeof value === 'string') {
    return value;
  }
  if (value == null) {
    return String(value);
  }
  if (typeof value === 'number' || typeof value === 'boolean') {
    return String(value);
  }

  try {
    return truncateText(JSON.stringify(value), PREVIEW_MAX_JSON_LENGTH);
  } catch {
    return '[Unserializable value]';
  }
}

function addPreviewLine(lines: string[], label: string, value: unknown): void {
  if (lines.length >= PREVIEW_MAX_LINES) return;
  const rendered = formatPreviewValue(value).trim();
  if (!rendered || rendered === '{}' || rendered === '[]') return;
  const normalizedLabel = toTitleCase(label.replace(/[.]+/g, ' '));
  lines.push(`${normalizedLabel}: ${rendered}`);
}

function buildResponsePreview(responseData: Record<string, unknown>): string[] {
  const sanitized = sanitizePreviewValue(responseData);
  const lines: string[] = [];

  if (!isRecord(sanitized)) {
    return [formatPreviewValue(sanitized)];
  }

  const usedKeys = new Set<string>();

  for (const key of PREVIEW_PRIORITY_KEYS) {
    if (Object.prototype.hasOwnProperty.call(sanitized, key)) {
      addPreviewLine(lines, key, sanitized[key]);
      usedKeys.add(key);
    }
  }

  for (const [key, value] of Object.entries(sanitized)) {
    if (lines.length >= PREVIEW_MAX_LINES) break;
    if (usedKeys.has(key)) continue;
    if (key === 'tool_calls' || key === 'model_invocations' || key === 'spans') continue;
    addPreviewLine(lines, key, value);
  }

  if (lines.length < PREVIEW_MAX_LINES) {
    const nestedContainerKeys = ['result', 'results', 'payload', 'data', 'output'];
    for (const key of nestedContainerKeys) {
      if (lines.length >= PREVIEW_MAX_LINES) break;
      const nested = sanitized[key];
      if (!isRecord(nested)) continue;
      for (const [nestedKey, nestedValue] of Object.entries(nested)) {
        if (lines.length >= PREVIEW_MAX_LINES) break;
        addPreviewLine(lines, `${key}.${nestedKey}`, nestedValue);
      }
    }
  }

  return lines.length > 0 ? lines : ['Response available. Open raw JSON for full details.'];
}

function toSurfaceSignalBadge(
  value: boolean | null,
  labels: {
    positive: string;
    negative: string;
  },
): {
  label: string;
  variant: 'success' | 'danger' | 'secondary';
} {
  if (value === true) {
    return {
      label: labels.positive,
      variant: 'success',
    };
  }

  if (value === false) {
    return {
      label: labels.negative,
      variant: 'danger',
    };
  }

  return {
    label: 'Unknown',
    variant: 'secondary',
  };
}

function formatReadinessSource(source: AdminServiceAppSurface['source']): string {
  if (source === 'apim-readiness') {
    return 'APIM';
  }

  if (source === 'agc-direct-readiness') {
    return 'AGC direct';
  }

  return 'Unavailable';
}

function extractSteps(responseData: Record<string, unknown>): AgentRunStep[] {
  const steps: AgentRunStep[] = [];

  const toolCalls = responseData.tool_calls as Array<Record<string, unknown>> | undefined;
  if (Array.isArray(toolCalls)) {
    for (const tc of toolCalls) {
      steps.push({
        type: 'tool_call',
        name: String(tc.tool_name || tc.name || 'tool'),
        input: tc.input ? String(tc.input).slice(0, 500) : undefined,
        output: tc.output ? String(tc.output).slice(0, 500) : undefined,
        durationMs: typeof tc.latency_ms === 'number' ? tc.latency_ms : undefined,
      });
    }
  }

  const modelInvocations = responseData.model_invocations as Array<Record<string, unknown>> | undefined;
  if (Array.isArray(modelInvocations)) {
    for (const mi of modelInvocations) {
      steps.push({
        type: 'model_invocation',
        name: String(mi.model_name || mi.model || 'model'),
        detail: mi.completion_excerpt ? String(mi.completion_excerpt).slice(0, 300) : undefined,
        input: mi.prompt_excerpt ? String(mi.prompt_excerpt).slice(0, 300) : undefined,
        durationMs: typeof mi.latency_ms === 'number' ? mi.latency_ms : undefined,
      });
    }
  }

  const spans = responseData.spans as Array<Record<string, unknown>> | undefined;
  if (Array.isArray(spans)) {
    for (const span of spans) {
      if (span.tool_name) {
        steps.push({
          type: 'tool_call',
          name: String(span.tool_name),
          input: span.tool_input ? String(span.tool_input).slice(0, 500) : undefined,
          output: span.tool_output ? String(span.tool_output).slice(0, 500) : undefined,
          durationMs: typeof span.duration_ms === 'number' ? span.duration_ms : undefined,
        });
      } else if (span.model_name) {
        steps.push({
          type: 'model_invocation',
          name: String(span.model_name),
          detail: span.completion_excerpt ? String(span.completion_excerpt).slice(0, 300) : undefined,
          durationMs: typeof span.duration_ms === 'number' ? span.duration_ms : undefined,
        });
      } else if (span.decision_outcome) {
        steps.push({
          type: 'decision',
          name: 'Decision',
          detail: String(span.decision_outcome),
        });
      }
    }
  }

  if (responseData.decision_outcome) {
    steps.push({
      type: 'decision',
      name: 'Final decision',
      detail: String(responseData.decision_outcome),
    });
  }

  return steps;
}

function scoreToLegitimacy(score: number): 'high' | 'medium' | 'low' {
  if (score >= 80) return 'high';
  if (score >= 55) return 'medium';
  return 'low';
}

function extractResponseText(responseData: Record<string, unknown> | undefined): string {
  if (!responseData) return '';

  const candidateKeys = [
    'insight', 'summary', 'recommendation', 'recommendations', 'analysis',
    'result', 'results', 'message', 'status', 'validation', 'assortment',
  ];

  const chunks: string[] = [];
  for (const key of candidateKeys) {
    const value = responseData[key as keyof typeof responseData];
    if (typeof value === 'string') {
      chunks.push(value);
    } else if (value && typeof value === 'object') {
      chunks.push(JSON.stringify(value));
    }
  }

  if (chunks.length > 0) {
    return chunks.join(' ').toLowerCase();
  }

  return JSON.stringify(responseData).toLowerCase();
}

function evaluateRun(params: {
  message: string;
  status: InvokeRunStatus;
  response?: Record<string, unknown>;
  error?: string;
  steps?: AgentRunStep[];
}): TripleEvaluation {
  const { message, status, response, error, steps } = params;
  const rationale: string[] = [];

  // Process score: was execution stable and observable?
  let process = status === 'success' ? 70 : status === 'running' ? 40 : 20;
  const stepCount = steps?.length ?? 0;
  if (stepCount > 0) {
    process = Math.min(100, process + Math.min(20, stepCount * 3));
    rationale.push(`Captured ${stepCount} execution steps.`);
  } else {
    rationale.push('No structured execution steps were captured.');
  }
  if (error) {
    process = Math.max(5, process - 35);
    rationale.push('Execution reported an error state.');
  }

  // Output score: does response look actionable instead of validation noise?
  let output = 15;
  const hasResponse = Boolean(response && Object.keys(response).length > 0);
  const responseError = response?.error;
  if (hasResponse) {
    output = 60;
    if (typeof responseError === 'string' && responseError.trim().length > 0) {
      output = 25;
      rationale.push(`Response returned validation/business error: "${responseError}".`);
    } else {
      const responseKeys = Object.keys(response ?? {});
      output = Math.min(95, output + Math.min(30, responseKeys.length * 4));
      rationale.push(`Response contains ${responseKeys.length} structured fields.`);
    }
  } else {
    rationale.push('No response payload was returned.');
  }

  // Intent score: lexical alignment between prompt and output.
  const tokens = message
    .toLowerCase()
    .split(/[^a-z0-9]+/)
    .filter((token) => token.length >= 4);
  const uniqueTokens = Array.from(new Set(tokens));
  const responseText = extractResponseText(response);
  const overlapCount = uniqueTokens.filter((token) => responseText.includes(token)).length;
  const overlapRatio = uniqueTokens.length > 0 ? overlapCount / uniqueTokens.length : 0;
  const intent = Math.max(15, Math.min(95, Math.round(20 + overlapRatio * 75)));
  rationale.push(
    uniqueTokens.length > 0
      ? `Intent match ${Math.round(overlapRatio * 100)}% (${overlapCount}/${uniqueTokens.length} key terms).`
      : 'Intent match not computed (prompt too short for lexical scoring).',
  );

  const aggregate = Math.round((process + output + intent) / 3);

  return {
    process,
    output,
    intent,
    legitimacy: scoreToLegitimacy(aggregate),
    rationale,
  };
}

// ── Props ──

export interface AdminServiceDashboardPageProps {
  domain: AdminServiceDomain;
  service: string;
}

// ── Component ──

export function AdminServiceDashboardPage({ domain, service }: AdminServiceDashboardPageProps) {
  const [timeRange, setTimeRange] = useState<AgentMonitorTimeRange>(DEFAULT_ADMIN_SERVICE_RANGE);
  const { data, isLoading, isError, isFetching, error, refetch } = useAdminServiceDashboard(domain, service, timeRange);

  // Agent invoke state
  const [invokeMessage, setInvokeMessage] = useState('');
  const [invokeStatus, setInvokeStatus] = useState<InvokeRunStatus>('idle');
  const [runHistory, setRunHistory] = useState<AgentRunRecord[]>([]);
  const [expandedRunId, setExpandedRunId] = useState<string | null>(null);
  const [showRawJson, setShowRawJson] = useState<string | null>(null);

  const agentSlug = useMemo(() => {
    if (data?.agent_service) return data.agent_service;
    return AGENT_SLUG_MAP[domain]?.[service] ?? `${domain}-${service}`;
  }, [data?.agent_service, domain, service]);

  const appSurface = useMemo<AdminServiceAppSurface>(() => {
    if (data?.app_surface) {
      return data.app_surface;
    }

    return {
      status: 'unknown',
      source: 'unavailable',
      checked_at: data?.generated_at ?? null,
      liveness_ok: null,
      readiness_ok: null,
      links: {
        health: `/agents/${agentSlug}/health`,
        ready: `/agents/${agentSlug}/ready`,
      },
    };
  }, [agentSlug, data?.app_surface, data?.generated_at]);

  const foundrySurface = useMemo<AdminServiceFoundrySurface>(() => {
    if (data?.foundry_surface) {
      return data.foundry_surface;
    }

    return {
      status: 'unknown',
      checked_at: data?.generated_at ?? null,
      foundry_ready: null,
      links: {
        studio: SAFE_FOUNDRY_FALLBACK_URL,
        project: SAFE_FOUNDRY_FALLBACK_URL,
        traces: SAFE_FOUNDRY_FALLBACK_URL,
        evaluations: SAFE_FOUNDRY_FALLBACK_URL,
      },
    };
  }, [data?.foundry_surface, data?.generated_at]);

  const gradient = DOMAIN_GRADIENT[domain] ?? DOMAIN_GRADIENT.ecommerce;
  const accent = DOMAIN_ACCENT[domain] ?? DOMAIN_ACCENT.ecommerce;

  const appLivenessBadge = toSurfaceSignalBadge(appSurface.liveness_ok, {
    positive: 'Healthy',
    negative: 'Down',
  });
  const appReadinessBadge = toSurfaceSignalBadge(appSurface.readiness_ok, {
    positive: 'Ready',
    negative: 'Not ready',
  });
  const foundryReadinessBadge = toSurfaceSignalBadge(foundrySurface.foundry_ready, {
    positive: 'Ready',
    negative: 'Not ready',
  });

  const handleInvokeAgent = useCallback(async () => {
    const inputText = invokeMessage.trim();
    if (!inputText) return;

    const parsedInput = parseInvokeInput(inputText);
    const runMessage = parsedInput.overridePayload
      ? parsedInput.promptText !== inputText
        ? parsedInput.promptText
        : 'JSON override payload'
      : parsedInput.promptText;

    const shapedPayload = buildInvokePayload(agentSlug, {
      domain,
      service,
      promptText: parsedInput.promptText,
      overridePayload: parsedInput.overridePayload,
    });

    const runId = `run-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
    const startedAt = new Date().toISOString();

    const newRun: AgentRunRecord = {
      id: runId,
      message: runMessage,
      status: 'running',
      startedAt,
    };

    setRunHistory((prev) => [newRun, ...prev]);
    setInvokeStatus('running');
    setExpandedRunId(runId);
    setInvokeMessage('');

    const startMs = performance.now();

    try {
      const response = await agentApiClient.post(`/${agentSlug}/invoke`, {
        intent: 'default',
        payload: shapedPayload,
      });

      const durationMs = Math.round(performance.now() - startMs);
      const responseData = response.data as Record<string, unknown>;
      const steps = extractSteps(responseData);
      const tripleEvaluation = evaluateRun({
        message: parsedInput.promptText,
        status: 'success',
        response: responseData,
        steps,
      });
      const responsePreview = buildResponsePreview(responseData);

      setRunHistory((prev) =>
        prev.map((r) =>
          r.id === runId
            ? {
                ...r,
                status: 'success' as const,
                durationMs,
                response: responseData,
                responsePreview,
                steps,
                tripleEvaluation,
              }
            : r,
        ),
      );
      setInvokeStatus('success');
    } catch (invokeError: unknown) {
      const durationMs = Math.round(performance.now() - startMs);
      const errMsg =
        invokeError instanceof Error ? invokeError.message : 'Agent invocation failed';
      const tripleEvaluation = evaluateRun({
        message: parsedInput.promptText,
        status: 'error',
        error: errMsg,
      });

      setRunHistory((prev) =>
        prev.map((r) =>
          r.id === runId
            ? {
                ...r,
                status: 'error' as const,
                durationMs,
                error: errMsg,
                tripleEvaluation,
              }
            : r,
        ),
      );
      setInvokeStatus('error');
    }
  }, [invokeMessage, agentSlug, domain, service]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        void handleInvokeAgent();
      }
    },
    [handleInvokeAgent],
  );

  return (
    <MainLayout>
      <div className="max-w-7xl mx-auto space-y-8">
        {/* ── Hero Header with gradient ── */}
        <header className={`relative -mx-4 md:-mx-0 rounded-none md:rounded-3xl bg-gradient-to-br ${gradient} border border-gray-100 dark:border-gray-800/50 overflow-hidden`}>
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(255,255,255,0.8),transparent_70%)] dark:bg-[radial-gradient(circle_at_top_right,rgba(255,255,255,0.03),transparent_70%)]" />
          <div className="relative px-6 md:px-8 py-6 md:py-8">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div className="space-y-2">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-2xl bg-white/80 dark:bg-gray-800/80 backdrop-blur-sm shadow-sm border border-gray-200/50 dark:border-gray-700/50 flex items-center justify-center">
                    <FiZap className={`w-5 h-5 ${accent}`} />
                  </div>
                  <div>
                    <h1 className="text-2xl font-bold text-gray-900 dark:text-white tracking-tight">
                      {toTitleCase(service)} Service
                    </h1>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      <span className={`font-semibold ${accent}`}>{domain}</span>
                      <span className="mx-1.5 text-gray-300 dark:text-gray-600">/</span>
                      <span className="font-medium text-gray-700 dark:text-gray-300">{service}</span>
                    </p>
                  </div>
                </div>
                {data && (
                  <p className="text-xs text-gray-400 pl-[52px]">
                    <span className="inline-flex items-center gap-1.5 bg-white/60 dark:bg-gray-800/60 backdrop-blur-sm rounded-full px-2.5 py-0.5 border border-gray-200/50 dark:border-gray-700/50">
                      <FiTerminal className="w-3 h-3" />
                      {data.agent_service}
                    </span>
                    <span className="ml-2 text-gray-400">
                      Updated {new Date(data.generated_at).toLocaleString()}
                    </span>
                  </p>
                )}
              </div>
              <div className="flex items-center gap-2">
                <Badge variant={data?.tracing_enabled ? 'success' : 'warning'} size="sm">
                  {data?.tracing_enabled ? 'Tracing enabled' : 'Tracing unavailable'}
                </Badge>
              </div>
            </div>
          </div>
        </header>

        {/* ── Controls Row ── */}
        <section className="flex flex-wrap items-center gap-3">
          <label htmlFor="admin-service-range" className="text-sm font-medium text-gray-700 dark:text-gray-300">
            Time range
          </label>
          <div className="w-52">
            <Select
              name="admin-service-range"
              ariaLabel="Admin service time range"
              value={timeRange}
              options={ADMIN_SERVICE_RANGE_OPTIONS}
              onChange={(event) => setTimeRange(event.target.value as AgentMonitorTimeRange)}
            />
          </div>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => { void refetch(); }}
            loading={isFetching}
            ariaLabel="Refresh service dashboard"
          >
            Refresh
          </Button>
        </section>

        {/* ── Invoke Agent — Hero Card ── */}
        <section aria-label="Invoke agent">
          <Card variant="glass" className="p-0 overflow-hidden">
            <div className="px-6 pt-6 pb-4">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-8 h-8 rounded-xl bg-gray-900 dark:bg-white flex items-center justify-center">
                  <FiSend className="w-4 h-4 text-white dark:text-gray-900" />
                </div>
                <div className="flex-1">
                  <h2 className="text-sm font-bold text-gray-900 dark:text-white">Invoke Agent</h2>
                  <p className="text-[11px] text-gray-400">Send free text or a JSON object override to the {toTitleCase(service)} agent</p>
                </div>
                <span className="text-[10px] font-mono text-gray-400 bg-gray-100 dark:bg-gray-800 rounded-lg px-2.5 py-1">
                  {agentSlug}
                </span>
              </div>

              <div className="relative">
                <textarea
                  value={invokeMessage}
                  onChange={(e) => setInvokeMessage(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder={`Describe what you want the ${toTitleCase(service)} agent to do…`}
                  rows={4}
                  disabled={invokeStatus === 'running'}
                  className="w-full rounded-2xl border-0 bg-white dark:bg-gray-900/80 ring-1 ring-gray-200 dark:ring-gray-700 px-5 py-4 text-sm text-gray-900 dark:text-white placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-gray-900 dark:focus:ring-white resize-none transition-all duration-200 shadow-sm disabled:opacity-50"
                />
                <div className="absolute bottom-3 right-3">
                  <span className="text-[10px] text-gray-400">
                    {navigator.platform.includes('Mac') ? '⌘' : 'Ctrl'} + Enter to send
                  </span>
                </div>
              </div>
            </div>

            <div className="px-6 pb-6 flex items-center gap-3">
              <Button
                size="sm"
                onClick={() => { void handleInvokeAgent(); }}
                disabled={invokeStatus === 'running' || invokeMessage.trim().length === 0}
                iconLeft={invokeStatus === 'running' ? <FiLoader className="w-3.5 h-3.5 animate-spin" /> : <FiArrowRight className="w-3.5 h-3.5" />}
              >
                {invokeStatus === 'running' ? 'Running…' : 'Run agent'}
              </Button>
              {invokeStatus === 'success' && (
                <span className="flex items-center gap-1.5 text-xs font-medium text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-900/20 rounded-full px-3 py-1">
                  <FiCheckCircle className="w-3.5 h-3.5" /> Completed
                </span>
              )}
              {invokeStatus === 'error' && (
                <span className="flex items-center gap-1.5 text-xs font-medium text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 rounded-full px-3 py-1">
                  <FiAlertCircle className="w-3.5 h-3.5" /> Failed
                </span>
              )}
            </div>
          </Card>
        </section>

        {/* ── Run History ── */}
        {runHistory.length > 0 && (
          <section aria-label="Run history" className="space-y-4">
            <div className="flex items-center gap-3">
              <h2 className="text-lg font-bold text-gray-900 dark:text-white tracking-tight">Run History</h2>
              <span className="text-xs text-gray-400 bg-gray-100 dark:bg-gray-800 rounded-full px-2.5 py-0.5 tabular-nums">
                {runHistory.length}
              </span>
            </div>

            <div className="space-y-3">
              {runHistory.map((run) => {
                const isExpanded = expandedRunId === run.id;
                const isJsonExpanded = showRawJson === run.id;
                return (
                  <Card
                    key={run.id}
                    variant={run.status === 'running' ? 'outlined' : 'default'}
                    className={`p-0 overflow-hidden transition-all duration-300 ${run.status === 'running' ? 'ring-2 ring-blue-200 dark:ring-blue-800' : ''}`}
                  >
                    {/* Run header row */}
                    <button
                      type="button"
                      onClick={() => setExpandedRunId(isExpanded ? null : run.id)}
                      className="w-full px-5 py-4 flex items-center gap-3 text-left hover:bg-gray-50/50 dark:hover:bg-gray-800/30 transition-colors"
                    >
                      <RunStatusIcon status={run.status} />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 dark:text-white truncate">{run.message}</p>
                        <div className="flex items-center gap-2 mt-0.5">
                          <span className="text-[10px] text-gray-400 tabular-nums">
                            {new Date(run.startedAt).toLocaleTimeString()}
                          </span>
                          {run.durationMs != null && (
                            <>
                              <span className="text-gray-300 dark:text-gray-600">·</span>
                              <span className="text-[10px] font-medium text-gray-500 tabular-nums">
                                {run.durationMs < 1000 ? `${run.durationMs}ms` : `${(run.durationMs / 1000).toFixed(1)}s`}
                              </span>
                            </>
                          )}
                          {run.steps && run.steps.length > 0 && (
                            <>
                              <span className="text-gray-300 dark:text-gray-600">·</span>
                              <span className="text-[10px] text-gray-400">
                                {run.steps.length} step{run.steps.length !== 1 ? 's' : ''}
                              </span>
                            </>
                          )}
                        </div>
                      </div>
                      <div className="shrink-0 w-6 h-6 rounded-lg bg-gray-100 dark:bg-gray-800 flex items-center justify-center">
                        {isExpanded
                          ? <FiChevronDown className="w-3.5 h-3.5 text-gray-500" />
                          : <FiChevronRight className="w-3.5 h-3.5 text-gray-500" />}
                      </div>
                    </button>

                    {/* Expanded trace detail */}
                    {isExpanded && (
                      <div className="border-t border-gray-100 dark:border-gray-800">
                        {/* Steps timeline */}
                        {run.steps && run.steps.length > 0 && (
                          <div className="px-5 pt-5 pb-3">
                            <div className="flex items-center gap-2 mb-4">
                              <FiActivity className="w-3.5 h-3.5 text-gray-400" />
                              <p className="text-[11px] font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Execution trace</p>
                            </div>
                            <div className="relative ml-3">
                              {/* Vertical connector line */}
                              <div className="absolute left-[11px] top-2 bottom-2 w-px bg-gradient-to-b from-gray-200 via-gray-200 to-transparent dark:from-gray-700 dark:via-gray-700" />

                              {run.steps.map((step, idx) => {
                                const cfg = STEP_CONFIG[step.type];
                                const StepIcon = cfg.icon;
                                return (
                                  <div key={idx} className="relative pl-10 pb-5 last:pb-0">
                                    {/* Node dot */}
                                    <div
                                      className="absolute left-0 top-0.5 w-[22px] h-[22px] rounded-lg flex items-center justify-center shadow-sm"
                                      style={{ background: cfg.color }}
                                    >
                                      <StepIcon className="w-3 h-3 text-white" />
                                    </div>

                                    {/* Step content card */}
                                    <div className={`rounded-xl border border-gray-100 dark:border-gray-800 ${cfg.bgLight} ${cfg.bgDark} p-3.5`}>
                                      <div className="flex items-center gap-2 mb-1">
                                        <span className="text-xs font-bold text-gray-900 dark:text-white">{step.name}</span>
                                        <span className="text-[10px] text-gray-400 bg-white/60 dark:bg-gray-800/60 rounded-md px-1.5 py-0.5">
                                          {step.type.replace('_', ' ')}
                                        </span>
                                        {step.durationMs != null && (
                                          <span className="ml-auto text-[10px] font-medium text-gray-400 tabular-nums">
                                            {step.durationMs < 1000 ? `${step.durationMs}ms` : `${(step.durationMs / 1000).toFixed(1)}s`}
                                          </span>
                                        )}
                                      </div>
                                      {step.input && (
                                        <details className="mt-2 group/input">
                                          <summary className="text-[10px] font-semibold text-gray-400 cursor-pointer select-none hover:text-gray-600 dark:hover:text-gray-300 transition-colors">
                                            Input
                                          </summary>
                                          <pre className="mt-1.5 text-[11px] text-gray-600 dark:text-gray-300 bg-white/70 dark:bg-gray-900/50 rounded-lg p-2.5 overflow-x-auto max-h-32 font-mono leading-relaxed">{step.input}</pre>
                                        </details>
                                      )}
                                      {step.output && (
                                        <details className="mt-2 group/output" open>
                                          <summary className="text-[10px] font-semibold text-emerald-600 dark:text-emerald-400 cursor-pointer select-none hover:text-emerald-700 dark:hover:text-emerald-300 transition-colors">
                                            Output
                                          </summary>
                                          <pre className="mt-1.5 text-[11px] text-emerald-700 dark:text-emerald-300 bg-white/70 dark:bg-gray-900/50 rounded-lg p-2.5 overflow-x-auto max-h-32 font-mono leading-relaxed">{step.output}</pre>
                                        </details>
                                      )}
                                      {step.detail && (
                                        <p className="mt-2 text-xs text-gray-600 dark:text-gray-300 leading-relaxed">{step.detail}</p>
                                      )}
                                    </div>
                                  </div>
                                );
                              })}
                            </div>
                          </div>
                        )}

                        {/* Triple evaluation */}
                        {run.tripleEvaluation && (
                          <div className="px-5 pb-4">
                            <div className="rounded-2xl border border-gray-100 dark:border-gray-800 bg-gray-50/70 dark:bg-gray-900/50 p-4">
                              <div className="flex items-center gap-2 mb-3">
                                <FiCheckCircle className="w-4 h-4 text-gray-500" />
                                <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Triple Evaluation</h3>
                                <Badge
                                  size="xs"
                                  variant={
                                    run.tripleEvaluation.legitimacy === 'high'
                                      ? 'success'
                                      : run.tripleEvaluation.legitimacy === 'medium'
                                      ? 'warning'
                                      : 'danger'
                                  }
                                  className="ml-auto"
                                >
                                  {run.tripleEvaluation.legitimacy} legitimacy
                                </Badge>
                              </div>

                              <div className="space-y-3">
                                <EvaluationBar label="Process" value={run.tripleEvaluation.process} />
                                <EvaluationBar label="Output" value={run.tripleEvaluation.output} />
                                <EvaluationBar label="Intent" value={run.tripleEvaluation.intent} />
                              </div>

                              <div className="mt-3 space-y-1">
                                {run.tripleEvaluation.rationale.map((line, idx) => (
                                  <p key={idx} className="text-[11px] text-gray-500 dark:text-gray-400 leading-relaxed">
                                    • {line}
                                  </p>
                                ))}
                              </div>
                            </div>
                          </div>
                        )}

                        {/* Response preview (sanitized) */}
                        {run.response && (
                          <div className="px-5 pb-4">
                            <div className="rounded-2xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900/40 p-4">
                              <div className="flex items-center gap-2 mb-3">
                                <FiMessageSquare className="w-3.5 h-3.5 text-gray-400" />
                                <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Response Preview</h3>
                              </div>
                              <div className="space-y-1.5">
                                {(run.responsePreview ?? []).map((line, idx) => (
                                  <p key={idx} className="text-xs text-gray-600 dark:text-gray-300 leading-relaxed break-words">
                                    {line}
                                  </p>
                                ))}
                              </div>
                              <p className="mt-3 text-[10px] text-gray-400">Sensitive fields are redacted and long values are truncated for readability.</p>
                            </div>
                          </div>
                        )}

                        {/* Raw response toggle */}
                        {run.response && (
                          <div className="px-5 pb-4">
                            <button
                              type="button"
                              onClick={() => setShowRawJson(isJsonExpanded ? null : run.id)}
                              className="flex items-center gap-1.5 text-[11px] font-medium text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
                            >
                              <FiCode className="w-3 h-3" />
                              {isJsonExpanded ? 'Hide raw response' : 'View raw response'}
                            </button>
                            {isJsonExpanded && (
                              <pre className="mt-2 text-[11px] text-gray-600 dark:text-gray-300 bg-gray-50 dark:bg-gray-800/80 rounded-xl p-4 overflow-x-auto max-h-64 font-mono leading-relaxed border border-gray-100 dark:border-gray-700">
                                {JSON.stringify(run.response, null, 2)}
                              </pre>
                            )}
                          </div>
                        )}

                        {/* Error banner */}
                        {run.error && (
                          <div className="mx-5 mb-4 rounded-xl border border-red-200 dark:border-red-900/50 bg-red-50 dark:bg-red-950/20 px-4 py-3 flex items-start gap-2.5">
                            <FiAlertCircle className="w-4 h-4 text-red-500 shrink-0 mt-0.5" />
                            <p className="text-xs font-medium text-red-700 dark:text-red-400 leading-relaxed">{run.error}</p>
                          </div>
                        )}

                        {/* Processing indicator */}
                        {!run.steps?.length && !run.response && !run.error && run.status === 'running' && (
                          <div className="px-5 pb-5 flex items-center gap-3">
                            <div className="flex gap-1">
                              <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-bounce [animation-delay:0ms]" />
                              <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-bounce [animation-delay:150ms]" />
                              <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-bounce [animation-delay:300ms]" />
                            </div>
                            <span className="text-xs text-gray-400">Agent is thinking…</span>
                          </div>
                        )}
                      </div>
                    )}
                  </Card>
                );
              })}
            </div>
          </section>
        )}

        {/* ── Loading / Error ── */}
        {isLoading && (
          <div className="flex items-center justify-center py-12 gap-3">
            <FiLoader className="w-5 h-5 text-gray-400 animate-spin" />
            <span className="text-sm text-gray-500 dark:text-gray-400">Loading service dashboard…</span>
          </div>
        )}

        {isError && (
          <Card className="p-5 border border-red-200 dark:border-red-900/50">
            <div className="flex items-start gap-3">
              <FiAlertCircle className="w-5 h-5 text-red-500 shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-red-700 dark:text-red-400">Failed to load service dashboard</p>
                <p className="text-xs text-red-600/70 dark:text-red-400/70 mt-0.5">{error instanceof Error ? error.message : 'Unknown error'}</p>
              </div>
            </div>
          </Card>
        )}

        {/* ── Status Metrics ── */}
        {data && (
          <>
            <section aria-label="Ownership surfaces">
              <div className="flex flex-wrap items-center gap-3 mb-4">
                <h2 className="text-lg font-bold text-gray-900 dark:text-white tracking-tight">Ownership Surfaces</h2>
                <p className="text-xs text-gray-500 dark:text-gray-400">App liveness/readiness and Foundry execution navigation</p>
              </div>

              <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                <Card variant="outlined" className="p-5 space-y-4">
                  <div className="flex items-center justify-between gap-2">
                    <div>
                      <h3 className="text-sm font-bold text-gray-900 dark:text-white">App Surface</h3>
                      <p className="text-xs text-gray-500 dark:text-gray-400">AKS and service probes</p>
                    </div>
                    <Badge variant={STATUS_BADGE_VARIANT[appSurface.status]} size="xs">{appSurface.status}</Badge>
                  </div>

                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant={appLivenessBadge.variant} size="xs">Liveness: {appLivenessBadge.label}</Badge>
                    <Badge variant={appReadinessBadge.variant} size="xs">Readiness: {appReadinessBadge.label}</Badge>
                    <Badge variant="secondary" size="xs">Source: {formatReadinessSource(appSurface.source)}</Badge>
                  </div>

                  <p className="text-[11px] text-gray-500 dark:text-gray-400">
                    Last probe: {appSurface.checked_at ? new Date(appSurface.checked_at).toLocaleString() : 'Unavailable'}
                  </p>

                  <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                    <a
                      href={appSurface.links.health}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center justify-between rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-2 text-xs font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                    >
                      <span>Health endpoint</span>
                      <FiArrowRight className="w-3.5 h-3.5" />
                    </a>
                    <a
                      href={appSurface.links.ready}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center justify-between rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-2 text-xs font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                    >
                      <span>Ready endpoint</span>
                      <FiArrowRight className="w-3.5 h-3.5" />
                    </a>
                  </div>
                </Card>

                <Card variant="outlined" className="p-5 space-y-4">
                  <div className="flex items-center justify-between gap-2">
                    <div>
                      <h3 className="text-sm font-bold text-gray-900 dark:text-white">Foundry Surface</h3>
                      <p className="text-xs text-gray-500 dark:text-gray-400">Agent execution visibility</p>
                    </div>
                    <Badge variant={STATUS_BADGE_VARIANT[foundrySurface.status]} size="xs">{foundrySurface.status}</Badge>
                  </div>

                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant={foundryReadinessBadge.variant} size="xs">Foundry: {foundryReadinessBadge.label}</Badge>
                  </div>

                  <p className="text-[11px] text-gray-500 dark:text-gray-400">
                    Last check: {foundrySurface.checked_at ? new Date(foundrySurface.checked_at).toLocaleString() : 'Unavailable'}
                  </p>

                  <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                    <a
                      href={foundrySurface.links.studio}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center justify-between rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-2 text-xs font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                    >
                      <span>Foundry Studio</span>
                      <FiArrowRight className="w-3.5 h-3.5" />
                    </a>
                    <a
                      href={foundrySurface.links.project}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center justify-between rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-2 text-xs font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                    >
                      <span>Project link</span>
                      <FiArrowRight className="w-3.5 h-3.5" />
                    </a>
                    <a
                      href={foundrySurface.links.traces}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center justify-between rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-2 text-xs font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                    >
                      <span>Traces</span>
                      <FiArrowRight className="w-3.5 h-3.5" />
                    </a>
                    <a
                      href={foundrySurface.links.evaluations}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center justify-between rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-2 text-xs font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                    >
                      <span>Evaluations</span>
                      <FiArrowRight className="w-3.5 h-3.5" />
                    </a>
                  </div>
                </Card>
              </div>
            </section>

            <section aria-label="Status metrics">
              <div className="flex items-center gap-3 mb-4">
                <h2 className="text-lg font-bold text-gray-900 dark:text-white tracking-tight">Metrics</h2>
              </div>

              {data.status_cards.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-gray-200 dark:border-gray-700 bg-gray-50/50 dark:bg-gray-800/20 p-8 text-center">
                  <FiActivity className="w-6 h-6 text-gray-300 dark:text-gray-600 mx-auto mb-2" />
                  <p className="text-sm text-gray-500 dark:text-gray-400">No status metrics available yet</p>
                  <p className="text-xs text-gray-400 mt-1">Run the agent to start collecting data</p>
                </div>
              ) : (
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                  {data.status_cards.map((card) => (
                    <div
                      key={card.label}
                      className="group relative rounded-2xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900 p-5 hover:shadow-lg hover:border-gray-200 dark:hover:border-gray-700 transition-all duration-300"
                    >
                      <div className="flex items-center justify-between mb-3">
                        <p className="text-[10px] uppercase tracking-widest font-semibold text-gray-400">{card.label}</p>
                        <Badge variant={STATUS_BADGE_VARIANT[card.status]} size="xs">{card.status}</Badge>
                      </div>
                      <p className="text-3xl font-bold text-gray-900 dark:text-white tabular-nums tracking-tight">{card.value}</p>
                    </div>
                  ))}
                </div>
              )}
            </section>

            {/* ── Activity & Model Usage ── */}
            <section className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              {/* Activity Table */}
              <div className="space-y-4">
                <div className="flex items-center gap-2">
                  <FiMessageSquare className="w-4 h-4 text-gray-400" />
                  <h2 className="text-lg font-bold text-gray-900 dark:text-white tracking-tight">Activity</h2>
                </div>

                <Card variant="outlined" className="p-0 overflow-hidden">
                  {data.activity.length === 0 ? (
                    <div className="p-8 text-center">
                      <FiClock className="w-6 h-6 text-gray-300 dark:text-gray-600 mx-auto mb-2" />
                      <p className="text-sm text-gray-500 dark:text-gray-400">No activity for this time range</p>
                    </div>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="min-w-full text-sm">
                        <thead>
                          <tr className="border-b border-gray-100 dark:border-gray-800">
                            <th className="px-4 py-3 text-left text-[10px] uppercase tracking-widest font-semibold text-gray-400">Timestamp</th>
                            <th className="px-4 py-3 text-left text-[10px] uppercase tracking-widest font-semibold text-gray-400">Event</th>
                            <th className="px-4 py-3 text-left text-[10px] uppercase tracking-widest font-semibold text-gray-400">Entity</th>
                            <th className="px-4 py-3 text-left text-[10px] uppercase tracking-widest font-semibold text-gray-400">Status</th>
                            <th className="px-4 py-3 text-left text-[10px] uppercase tracking-widest font-semibold text-gray-400">Latency</th>
                          </tr>
                        </thead>
                        <tbody>
                          {data.activity.map((row) => (
                            <tr key={row.id} className="border-t border-gray-50 dark:border-gray-800/50 hover:bg-gray-50/50 dark:hover:bg-gray-800/20 transition-colors">
                              <td className="px-4 py-2.5 text-xs text-gray-500 tabular-nums">{new Date(row.timestamp).toLocaleString()}</td>
                              <td className="px-4 py-2.5 text-xs font-medium text-gray-700 dark:text-gray-300">{row.event}</td>
                              <td className="px-4 py-2.5 text-xs text-gray-500 font-mono">{row.entity}</td>
                              <td className="px-4 py-2.5">
                                <Badge variant={ACTIVITY_STATUS_BADGE_VARIANT[row.status]} size="xs">{row.status}</Badge>
                              </td>
                              <td className="px-4 py-2.5 text-xs text-gray-500 tabular-nums">{Math.round(row.latency_ms)} ms</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </Card>
              </div>

              {/* Model Usage Table */}
              <div className="space-y-4">
                <div className="flex items-center gap-2">
                  <FiCpu className="w-4 h-4 text-gray-400" />
                  <h2 className="text-lg font-bold text-gray-900 dark:text-white tracking-tight">Model Usage</h2>
                </div>

                <Card variant="outlined" className="p-0 overflow-hidden">
                  {data.model_usage.length === 0 ? (
                    <div className="p-8 text-center">
                      <FiCpu className="w-6 h-6 text-gray-300 dark:text-gray-600 mx-auto mb-2" />
                      <p className="text-sm text-gray-500 dark:text-gray-400">No model usage data available</p>
                    </div>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="min-w-full text-sm">
                        <thead>
                          <tr className="border-b border-gray-100 dark:border-gray-800">
                            <th className="px-4 py-3 text-left text-[10px] uppercase tracking-widest font-semibold text-gray-400">Model</th>
                            <th className="px-4 py-3 text-left text-[10px] uppercase tracking-widest font-semibold text-gray-400">Tier</th>
                            <th className="px-4 py-3 text-left text-[10px] uppercase tracking-widest font-semibold text-gray-400">Requests</th>
                            <th className="px-4 py-3 text-left text-[10px] uppercase tracking-widest font-semibold text-gray-400">Tokens</th>
                            <th className="px-4 py-3 text-left text-[10px] uppercase tracking-widest font-semibold text-gray-400">Avg latency</th>
                          </tr>
                        </thead>
                        <tbody>
                          {data.model_usage.map((row) => (
                            <tr key={`${row.model_tier}-${row.model_name}`} className="border-t border-gray-50 dark:border-gray-800/50 hover:bg-gray-50/50 dark:hover:bg-gray-800/20 transition-colors">
                              <td className="px-4 py-2.5 text-xs font-medium text-gray-700 dark:text-gray-300 font-mono">{row.model_name}</td>
                              <td className="px-4 py-2.5 text-xs text-gray-500">{row.model_tier}</td>
                              <td className="px-4 py-2.5 text-xs text-gray-500 tabular-nums">{row.requests.toLocaleString()}</td>
                              <td className="px-4 py-2.5 text-xs text-gray-500 tabular-nums">{row.total_tokens.toLocaleString()}</td>
                              <td className="px-4 py-2.5 text-xs text-gray-500 tabular-nums">{Math.round(row.avg_latency_ms)} ms</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </Card>
              </div>
            </section>
          </>
        )}
      </div>
    </MainLayout>
  );
}

// ── Sub-components ──

function RunStatusIcon({ status }: { status: InvokeRunStatus }) {
  const base = 'w-8 h-8 rounded-xl flex items-center justify-center shrink-0';
  switch (status) {
    case 'running':
      return (
        <div className={`${base} bg-blue-50 dark:bg-blue-950/30`}>
          <FiLoader className="w-4 h-4 text-blue-500 animate-spin" />
        </div>
      );
    case 'success':
      return (
        <div className={`${base} bg-emerald-50 dark:bg-emerald-950/30`}>
          <FiCheckCircle className="w-4 h-4 text-emerald-500" />
        </div>
      );
    case 'error':
      return (
        <div className={`${base} bg-red-50 dark:bg-red-950/30`}>
          <FiAlertCircle className="w-4 h-4 text-red-500" />
        </div>
      );
    default:
      return (
        <div className={`${base} bg-gray-50 dark:bg-gray-800`}>
          <FiClock className="w-4 h-4 text-gray-400" />
        </div>
      );
  }
}

function EvaluationBar({ label, value }: { label: string; value: number }) {
  const colorClass = value >= 80
    ? 'bg-emerald-500'
    : value >= 55
    ? 'bg-amber-500'
    : 'bg-red-500';

  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs font-medium text-gray-700 dark:text-gray-300">{label}</span>
        <span className="text-[11px] text-gray-500 dark:text-gray-400 tabular-nums">{value}/100</span>
      </div>
      <div className="h-2 w-full rounded-full bg-gray-200 dark:bg-gray-700 overflow-hidden">
        <div
          className={`h-full ${colorClass} transition-all duration-500`}
          style={{ width: `${Math.max(0, Math.min(100, value))}%` }}
        />
      </div>
    </div>
  );
}

export default AdminServiceDashboardPage;
