'use client';

import { useCallback, useMemo, useRef, useState } from 'react';
import { MainLayout } from '@/components/templates/MainLayout';
import { Card } from '@/components/molecules/Card';
import { Badge } from '@/components/atoms/Badge';
import { Select } from '@/components/atoms/Select';
import { Button } from '@/components/atoms/Button';
import { ConfigPanel } from '@/components/admin/ConfigPanel';
import { EvaluationTrendChart } from '@/components/admin/EvaluationTrendChart';
import {
  useAdminServiceDashboard,
  DEFAULT_ADMIN_SERVICE_RANGE,
  ADMIN_SERVICE_RANGE_OPTIONS,
} from '@/lib/hooks/useAdminServiceDashboard';
import { useAgentEvaluations } from '@/lib/hooks/useAgentMonitor';
import { useTruthConfig, useUpdateTruthConfig } from '@/lib/hooks/useTruthAdmin';
import agentApiClient from '@/lib/api/agentClient';
import type {
  AdminServiceAppSurface,
  AdminServiceDashboard,
  AdminServiceDomain,
  AdminServiceFoundrySurface,
  AdminServicePromptDocument,
  AdminServiceResilienceStatus,
  AgentMonitorTimeRange,
  AdminServiceStatus,
  AdminServiceToolDescription,
  AgentTraceStatus,
  TenantConfig,
} from '@/lib/types/api';
import {
  FiClock, FiChevronDown, FiChevronRight,
  FiTool, FiCpu, FiMessageSquare, FiAlertCircle, FiCheckCircle, FiLoader,
  FiSend, FiZap, FiActivity, FiTerminal, FiCode,
  FiArrowRight, FiGrid, FiFileText, FiSettings, FiShield, FiUsers,
} from 'react-icons/fi';
import { AgentRobot } from '@/components/organisms/AgentRobot';
import { AGENT_PROFILES } from '@/lib/agents/profiles';
import type { AgentProfile } from '@/lib/agents/profiles';

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

type CockpitTabId = 'overview' | 'runs' | 'evaluations' | 'prompts' | 'tools' | 'resilience' | 'config';

interface CockpitTabDefinition {
  id: CockpitTabId;
  label: string;
  icon: typeof FiTool;
}

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
const ADMIN_AGENT_INVOKE_TIMEOUT_MS = 60_000;

const COCKPIT_TABS: CockpitTabDefinition[] = [
  { id: 'overview', label: 'Overview', icon: FiGrid },
  { id: 'runs', label: 'Runs & Traces', icon: FiActivity },
  { id: 'evaluations', label: 'Evaluations', icon: FiCpu },
  { id: 'prompts', label: 'Prompts', icon: FiFileText },
  { id: 'tools', label: 'Tools', icon: FiTool },
  { id: 'resilience', label: 'Resilience', icon: FiShield },
  { id: 'config', label: 'Config', icon: FiSettings },
];

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
  const mode = pickFirstString(context.overridePayload, ['mode']) ?? 'intelligent';

  return withPayloadMetadata(
    {
      ...(context.overridePayload ?? {}),
      query,
      prompt: context.promptText,
      mode,
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
  const [activeTab, setActiveTab] = useState<CockpitTabId>('overview');
  const tabRefs = useRef<Array<HTMLButtonElement | null>>([]);

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
  const agentProfile = useMemo(() => AGENT_PROFILES[agentSlug as keyof typeof AGENT_PROFILES], [agentSlug]);
  const promptCatalog = data?.prompt_catalog ?? [];
  const toolCatalog = data?.mcp_tools ?? [];
  const resilienceStatus = data?.self_healing ?? {
    service: agentSlug,
    enabled: false,
    detect_only: false,
    allowlisted_actions: [],
    incidents_total: 0,
    incidents_open: 0,
    incidents_closed: 0,
    manifest: null,
  } satisfies AdminServiceResilienceStatus;

  const handleStagePrompt = useCallback((prompt: AdminServicePromptDocument) => {
    const promptStem = prompt.name.replace(/\.[^.]+$/, '').replace(/[-_]+/g, ' ');
    setInvokeMessage(`Use ${promptStem} to summarize the live ${toTitleCase(service)} state and the next operator action.`);
    setActiveTab('prompts');
  }, [service]);

  const handleTabKeyDown = useCallback((event: React.KeyboardEvent<HTMLButtonElement>, index: number) => {
    let nextIndex = index;

    switch (event.key) {
      case 'ArrowRight':
        nextIndex = (index + 1) % COCKPIT_TABS.length;
        break;
      case 'ArrowLeft':
        nextIndex = (index - 1 + COCKPIT_TABS.length) % COCKPIT_TABS.length;
        break;
      case 'Home':
        nextIndex = 0;
        break;
      case 'End':
        nextIndex = COCKPIT_TABS.length - 1;
        break;
      default:
        return;
    }

    event.preventDefault();
    const nextTab = COCKPIT_TABS[nextIndex];
    setActiveTab(nextTab.id);
    tabRefs.current[nextIndex]?.focus();
  }, []);

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
      }, {
        timeout: ADMIN_AGENT_INVOKE_TIMEOUT_MS,
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

  const activeTabPanel = data ? (() => {
    switch (activeTab) {
      case 'overview':
        return (
          <CockpitOverviewPanel
            data={data}
            agentSlug={agentSlug}
            agentProfile={agentProfile}
            appSurface={appSurface}
            foundrySurface={foundrySurface}
            appLivenessBadge={appLivenessBadge}
            appReadinessBadge={appReadinessBadge}
            foundryReadinessBadge={foundryReadinessBadge}
            promptCatalog={promptCatalog}
            toolCatalog={toolCatalog}
            resilienceStatus={resilienceStatus}
          />
        );
      case 'runs':
        return (
          <CockpitRunsPanel
            activity={data.activity}
            runHistory={runHistory}
            expandedRunId={expandedRunId}
            onExpandedRunIdChange={setExpandedRunId}
            rawJsonRunId={showRawJson}
            onRawJsonRunIdChange={setShowRawJson}
          />
        );
      case 'evaluations':
        return (
          <CockpitEvaluationsPanel
            timeRange={timeRange}
            modelUsage={data.model_usage}
          />
        );
      case 'prompts':
        return (
          <CockpitPromptsPanel
            prompts={promptCatalog}
            onStagePrompt={handleStagePrompt}
          />
        );
      case 'tools':
        return (
          <CockpitToolsPanel
            tools={toolCatalog}
            agentSlug={agentSlug}
            collaborators={agentProfile?.collaborates ?? []}
          />
        );
      case 'resilience':
        return (
          <CockpitResiliencePanel
            resilienceStatus={resilienceStatus}
            appSurface={appSurface}
            foundrySurface={foundrySurface}
          />
        );
      case 'config':
        return <CockpitConfigPanel domain={domain} service={service} />;
      default:
        return null;
    }
  })() : null;

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

        {data && (
          <>
            <section aria-label="Cockpit tabs" className="space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h2 className="text-lg font-bold text-[var(--hp-text)] tracking-tight">Service cockpit</h2>
                  <p className="text-xs text-[var(--hp-text-muted)]">Runs, evaluations, prompt assets, tools, and resilience controls in one operator surface.</p>
                </div>
                <Badge variant="glass" size="sm">{COCKPIT_TABS.length} views</Badge>
              </div>

              <div role="tablist" aria-label={`${toTitleCase(service)} cockpit views`} className="flex flex-wrap gap-2 rounded-2xl border border-[var(--hp-border)] bg-[var(--hp-surface)] p-2">
                {COCKPIT_TABS.map((tab, index) => {
                  const selected = activeTab === tab.id;
                  const Icon = tab.icon;
                  return (
                    <button
                      key={tab.id}
                      id={`cockpit-tab-${tab.id}`}
                      ref={(element) => { tabRefs.current[index] = element; }}
                      type="button"
                      role="tab"
                      aria-selected={selected}
                      aria-controls={`cockpit-panel-${tab.id}`}
                      tabIndex={selected ? 0 : -1}
                      onClick={() => setActiveTab(tab.id)}
                      onKeyDown={(event) => handleTabKeyDown(event, index)}
                      className={`inline-flex items-center gap-2 rounded-xl px-3 py-2 text-sm font-semibold transition-colors ${selected ? 'bg-[var(--hp-text)] text-[var(--hp-bg)] shadow-[var(--hp-shadow-sm)]' : 'text-[var(--hp-text-muted)] hover:bg-[var(--hp-surface-strong)] hover:text-[var(--hp-text)]'}`}
                    >
                      <Icon className="h-4 w-4" />
                      <span>{tab.label}</span>
                    </button>
                  );
                })}
              </div>
            </section>

            <div
              id={`cockpit-panel-${activeTab}`}
              role="tabpanel"
              aria-labelledby={`cockpit-tab-${activeTab}`}
              tabIndex={0}
              className="space-y-6"
            >
              {activeTabPanel}
            </div>
          </>
        )}
      </div>
    </MainLayout>
  );
}

// ── Sub-components ──

function countSchemaProperties(schema: Record<string, unknown> | null | undefined): number | null {
  if (!schema) {
    return null;
  }

  const properties = schema.properties;
  if (!isRecord(properties)) {
    return null;
  }

  return Object.keys(properties).length;
}

function renderJsonSnippet(value: unknown, maxLength = 1200): string {
  try {
    return truncateText(JSON.stringify(value, null, 2), maxLength);
  } catch {
    return '[Unserializable value]';
  }
}

interface CockpitOverviewPanelProps {
  data: AdminServiceDashboard;
  agentSlug: string;
  agentProfile?: AgentProfile;
  appSurface: AdminServiceAppSurface;
  foundrySurface: AdminServiceFoundrySurface;
  appLivenessBadge: {
    label: string;
    variant: 'success' | 'danger' | 'secondary';
  };
  appReadinessBadge: {
    label: string;
    variant: 'success' | 'danger' | 'secondary';
  };
  foundryReadinessBadge: {
    label: string;
    variant: 'success' | 'danger' | 'secondary';
  };
  promptCatalog: AdminServicePromptDocument[];
  toolCatalog: AdminServiceToolDescription[];
  resilienceStatus: AdminServiceResilienceStatus;
}

function CockpitOverviewPanel({
  data,
  agentSlug,
  agentProfile,
  appSurface,
  foundrySurface,
  appLivenessBadge,
  appReadinessBadge,
  foundryReadinessBadge,
  promptCatalog,
  toolCatalog,
  resilienceStatus,
}: CockpitOverviewPanelProps) {
  return (
    <>
      <section aria-label="Ownership surfaces">
        <div className="flex flex-wrap items-center gap-3 mb-4">
          <h2 className="text-lg font-bold text-[var(--hp-text)] tracking-tight">Ownership surfaces</h2>
          <p className="text-xs text-[var(--hp-text-muted)]">App probes, Foundry visibility, and introspection inventory for this service.</p>
        </div>

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-[1.1fr_1.1fr_0.8fr]">
          <Card variant="outlined" className="p-5 space-y-4">
            <div className="flex items-center justify-between gap-2">
              <div>
                <h3 className="text-sm font-bold text-[var(--hp-text)]">App surface</h3>
                <p className="text-xs text-[var(--hp-text-muted)]">AKS and service probes</p>
              </div>
              <Badge variant={STATUS_BADGE_VARIANT[appSurface.status]} size="xs">{appSurface.status}</Badge>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <Badge variant={appLivenessBadge.variant} size="xs">Liveness: {appLivenessBadge.label}</Badge>
              <Badge variant={appReadinessBadge.variant} size="xs">Readiness: {appReadinessBadge.label}</Badge>
              <Badge variant="secondary" size="xs">Source: {formatReadinessSource(appSurface.source)}</Badge>
            </div>

            <p className="text-[11px] text-[var(--hp-text-muted)]">
              Last probe: {appSurface.checked_at ? new Date(appSurface.checked_at).toLocaleString() : 'Unavailable'}
            </p>

            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              <a
                href={appSurface.links.health}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center justify-between rounded-xl border border-[var(--hp-border)] bg-[var(--hp-surface)] px-3 py-2 text-xs font-medium text-[var(--hp-text)] hover:bg-[var(--hp-surface-strong)] transition-colors"
              >
                <span>Health endpoint</span>
                <FiArrowRight className="w-3.5 h-3.5" />
              </a>
              <a
                href={appSurface.links.ready}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center justify-between rounded-xl border border-[var(--hp-border)] bg-[var(--hp-surface)] px-3 py-2 text-xs font-medium text-[var(--hp-text)] hover:bg-[var(--hp-surface-strong)] transition-colors"
              >
                <span>Ready endpoint</span>
                <FiArrowRight className="w-3.5 h-3.5" />
              </a>
            </div>
          </Card>

          <Card variant="outlined" className="p-5 space-y-4">
            <div className="flex items-center justify-between gap-2">
              <div>
                <h3 className="text-sm font-bold text-[var(--hp-text)]">Foundry surface</h3>
                <p className="text-xs text-[var(--hp-text-muted)]">Agent execution visibility</p>
              </div>
              <Badge variant={STATUS_BADGE_VARIANT[foundrySurface.status]} size="xs">{foundrySurface.status}</Badge>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <Badge variant={foundryReadinessBadge.variant} size="xs">Foundry: {foundryReadinessBadge.label}</Badge>
              <Badge variant={resilienceStatus.enabled ? 'success' : 'secondary'} size="xs">
                Self-healing: {resilienceStatus.enabled ? 'Enabled' : 'Off'}
              </Badge>
            </div>

            <p className="text-[11px] text-[var(--hp-text-muted)]">
              Last check: {foundrySurface.checked_at ? new Date(foundrySurface.checked_at).toLocaleString() : 'Unavailable'}
            </p>

            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              <a href={foundrySurface.links.studio} target="_blank" rel="noopener noreferrer" className="inline-flex items-center justify-between rounded-xl border border-[var(--hp-border)] bg-[var(--hp-surface)] px-3 py-2 text-xs font-medium text-[var(--hp-text)] hover:bg-[var(--hp-surface-strong)] transition-colors">
                <span>Foundry Studio</span>
                <FiArrowRight className="w-3.5 h-3.5" />
              </a>
              <a href={foundrySurface.links.project} target="_blank" rel="noopener noreferrer" className="inline-flex items-center justify-between rounded-xl border border-[var(--hp-border)] bg-[var(--hp-surface)] px-3 py-2 text-xs font-medium text-[var(--hp-text)] hover:bg-[var(--hp-surface-strong)] transition-colors">
                <span>Project link</span>
                <FiArrowRight className="w-3.5 h-3.5" />
              </a>
              <a href={foundrySurface.links.traces} target="_blank" rel="noopener noreferrer" className="inline-flex items-center justify-between rounded-xl border border-[var(--hp-border)] bg-[var(--hp-surface)] px-3 py-2 text-xs font-medium text-[var(--hp-text)] hover:bg-[var(--hp-surface-strong)] transition-colors">
                <span>Traces</span>
                <FiArrowRight className="w-3.5 h-3.5" />
              </a>
              <a href={foundrySurface.links.evaluations} target="_blank" rel="noopener noreferrer" className="inline-flex items-center justify-between rounded-xl border border-[var(--hp-border)] bg-[var(--hp-surface)] px-3 py-2 text-xs font-medium text-[var(--hp-text)] hover:bg-[var(--hp-surface-strong)] transition-colors">
                <span>Evaluations</span>
                <FiArrowRight className="w-3.5 h-3.5" />
              </a>
            </div>
          </Card>

          <Card variant="glass" className="p-5 space-y-4">
            <div className="flex items-center gap-3">
              <AgentRobot agentSlug={agentSlug} size={88} sticky={false} skipEntrance />
              <div>
                <h3 className="text-sm font-bold text-[var(--hp-text)]">Agent brief</h3>
                <p className="text-xs text-[var(--hp-text-muted)]">{agentProfile?.oneLiner ?? 'Operational summary unavailable.'}</p>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-3 text-center text-sm">
              <div className="rounded-2xl bg-[var(--hp-surface)] px-3 py-3">
                <p className="text-[10px] uppercase tracking-[0.2em] text-[var(--hp-text-muted)]">Prompts</p>
                <p className="mt-1 text-2xl font-bold text-[var(--hp-text)]">{promptCatalog.length}</p>
              </div>
              <div className="rounded-2xl bg-[var(--hp-surface)] px-3 py-3">
                <p className="text-[10px] uppercase tracking-[0.2em] text-[var(--hp-text-muted)]">Tools</p>
                <p className="mt-1 text-2xl font-bold text-[var(--hp-text)]">{toolCatalog.length}</p>
              </div>
              <div className="rounded-2xl bg-[var(--hp-surface)] px-3 py-3">
                <p className="text-[10px] uppercase tracking-[0.2em] text-[var(--hp-text-muted)]">Open incidents</p>
                <p className="mt-1 text-2xl font-bold text-[var(--hp-text)]">{resilienceStatus.incidents_open}</p>
              </div>
            </div>

            {agentProfile?.fitFor && (
              <div className="space-y-2">
                <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[var(--hp-text-muted)]">Best fit</p>
                <div className="flex flex-wrap gap-2">
                  {agentProfile.fitFor.slice(0, 3).map((item) => (
                    <Badge key={item} size="xs" variant="glass">{item}</Badge>
                  ))}
                </div>
              </div>
            )}
          </Card>
        </div>
      </section>

      <section aria-label="Status metrics">
        <div className="flex items-center gap-3 mb-4">
          <h2 className="text-lg font-bold text-[var(--hp-text)] tracking-tight">Metrics</h2>
          <p className="text-xs text-[var(--hp-text-muted)]">Current service-specific counters synthesized from traces, readiness, and evaluations.</p>
        </div>

        {data.status_cards.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-[var(--hp-border)] bg-[var(--hp-surface-strong)]/50 p-8 text-center">
            <FiActivity className="w-6 h-6 text-[var(--hp-text-faint)] mx-auto mb-2" />
            <p className="text-sm text-[var(--hp-text-muted)]">No status metrics available yet</p>
            <p className="text-xs text-gray-400 mt-1">Run the agent to start collecting data</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {data.status_cards.map((card) => (
              <div key={card.label} className="group relative rounded-2xl border border-[var(--hp-border-subtle)] bg-[var(--hp-surface)] p-5 hover:shadow-lg hover:border-[var(--hp-border)] transition-all duration-300">
                <div className="flex items-center justify-between mb-3">
                  <p className="text-[10px] uppercase tracking-widest font-semibold text-gray-400">{card.label}</p>
                  <Badge variant={STATUS_BADGE_VARIANT[card.status]} size="xs">{card.status}</Badge>
                </div>
                <p className="text-3xl font-bold text-[var(--hp-text)] tabular-nums tracking-tight">{card.value}</p>
              </div>
            ))}
          </div>
        )}
      </section>
    </>
  );
}

interface CockpitRunsPanelProps {
  activity: AdminServiceDashboard['activity'];
  runHistory: AgentRunRecord[];
  expandedRunId: string | null;
  onExpandedRunIdChange: (runId: string | null) => void;
  rawJsonRunId: string | null;
  onRawJsonRunIdChange: (runId: string | null) => void;
}

function CockpitRunsPanel({
  activity,
  runHistory,
  expandedRunId,
  onExpandedRunIdChange,
  rawJsonRunId,
  onRawJsonRunIdChange,
}: CockpitRunsPanelProps) {
  return (
    <section className="space-y-6" aria-label="Runs and traces">
      <div className="space-y-4">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-bold text-[var(--hp-text)] tracking-tight">Run history</h2>
          <span className="text-xs text-gray-400 bg-[var(--hp-surface-strong)] rounded-full px-2.5 py-0.5 tabular-nums">
            {runHistory.length}
          </span>
        </div>

        {runHistory.length === 0 ? (
          <Card variant="outlined" className="p-8 text-center">
            <FiSend className="w-6 h-6 text-[var(--hp-text-faint)] mx-auto mb-2" />
            <p className="text-sm text-[var(--hp-text-muted)]">No manual runs yet.</p>
            <p className="text-xs text-gray-400 mt-1">Use the invoke composer above to record a local operator run.</p>
          </Card>
        ) : (
          <div className="space-y-3">
            {runHistory.map((run) => {
              const isExpanded = expandedRunId === run.id;
              const isJsonExpanded = rawJsonRunId === run.id;
              return (
                <Card
                  key={run.id}
                  variant={run.status === 'running' ? 'outlined' : 'default'}
                  className={`p-0 overflow-hidden transition-all duration-300 ${run.status === 'running' ? 'ring-2 ring-blue-300/40' : ''}`}
                >
                  <button
                    type="button"
                    onClick={() => onExpandedRunIdChange(isExpanded ? null : run.id)}
                    className="w-full px-5 py-4 flex items-center gap-3 text-left hover:bg-[var(--hp-surface-strong)]/50 transition-colors"
                  >
                    <RunStatusIcon status={run.status} />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-[var(--hp-text)] truncate">{run.message}</p>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className="text-[10px] text-gray-400 tabular-nums">{new Date(run.startedAt).toLocaleTimeString()}</span>
                        {run.durationMs != null && (
                          <>
                            <span className="text-[var(--hp-text-faint)]">·</span>
                            <span className="text-[10px] font-medium text-gray-500 tabular-nums">
                              {run.durationMs < 1000 ? `${run.durationMs}ms` : `${(run.durationMs / 1000).toFixed(1)}s`}
                            </span>
                          </>
                        )}
                        {run.steps && run.steps.length > 0 && (
                          <>
                            <span className="text-[var(--hp-text-faint)]">·</span>
                            <span className="text-[10px] text-gray-400">{run.steps.length} step{run.steps.length !== 1 ? 's' : ''}</span>
                          </>
                        )}
                      </div>
                    </div>
                    <div className="shrink-0 w-6 h-6 rounded-lg bg-[var(--hp-surface-strong)] flex items-center justify-center">
                      {isExpanded ? <FiChevronDown className="w-3.5 h-3.5 text-gray-500" /> : <FiChevronRight className="w-3.5 h-3.5 text-gray-500" />}
                    </div>
                  </button>

                  {isExpanded && (
                    <div className="border-t border-[var(--hp-border-subtle)]">
                      {run.steps && run.steps.length > 0 && (
                        <div className="px-5 pt-5 pb-3">
                          <div className="flex items-center gap-2 mb-4">
                            <FiActivity className="w-3.5 h-3.5 text-gray-400" />
                            <p className="text-[11px] font-semibold text-[var(--hp-text-muted)] uppercase tracking-wider">Execution trace</p>
                          </div>
                          <div className="relative ml-3">
                            <div className="absolute left-[11px] top-2 bottom-2 w-px bg-gradient-to-b from-[var(--hp-border)] via-[var(--hp-border)] to-transparent" />

                            {run.steps.map((step, idx) => {
                              const cfg = STEP_CONFIG[step.type];
                              const StepIcon = cfg.icon;
                              return (
                                <div key={idx} className="relative pl-10 pb-5 last:pb-0">
                                  <div className="absolute left-0 top-0.5 w-[22px] h-[22px] rounded-lg flex items-center justify-center shadow-sm" style={{ background: cfg.color }}>
                                    <StepIcon className="w-3 h-3 text-white" />
                                  </div>

                                  <div className={`rounded-xl border border-[var(--hp-border-subtle)] ${cfg.bgLight} ${cfg.bgDark} p-3.5`}>
                                    <div className="flex items-center gap-2 mb-1">
                                      <span className="text-xs font-bold text-[var(--hp-text)]">{step.name}</span>
                                      <span className="text-[10px] text-gray-400 bg-[var(--hp-glass-bg)] rounded-md px-1.5 py-0.5">{step.type.replace('_', ' ')}</span>
                                      {step.durationMs != null && (
                                        <span className="ml-auto text-[10px] font-medium text-gray-400 tabular-nums">
                                          {step.durationMs < 1000 ? `${step.durationMs}ms` : `${(step.durationMs / 1000).toFixed(1)}s`}
                                        </span>
                                      )}
                                    </div>
                                    {step.input && (
                                      <details className="mt-2 group/input">
                                        <summary className="text-[10px] font-semibold text-gray-400 cursor-pointer select-none hover:text-[var(--hp-text-muted)] transition-colors">Input</summary>
                                        <pre className="mt-1.5 text-[11px] text-[var(--hp-text-muted)] bg-[var(--hp-surface)] rounded-lg p-2.5 overflow-x-auto max-h-32 font-mono leading-relaxed">{step.input}</pre>
                                      </details>
                                    )}
                                    {step.output && (
                                      <details className="mt-2 group/output" open>
                                        <summary className="text-[10px] font-semibold text-[var(--hp-success)] cursor-pointer select-none hover:text-[var(--hp-success)] transition-colors">Output</summary>
                                        <pre className="mt-1.5 text-[11px] text-[var(--hp-success)] bg-[var(--hp-surface)] rounded-lg p-2.5 overflow-x-auto max-h-32 font-mono leading-relaxed">{step.output}</pre>
                                      </details>
                                    )}
                                    {step.detail && <p className="mt-2 text-xs text-[var(--hp-text-muted)] leading-relaxed">{step.detail}</p>}
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      )}

                      {run.tripleEvaluation && (
                        <div className="px-5 pb-4">
                          <div className="rounded-2xl border border-[var(--hp-border-subtle)] bg-[var(--hp-surface-strong)] p-4">
                            <div className="flex items-center gap-2 mb-3">
                              <FiCheckCircle className="w-4 h-4 text-gray-500" />
                              <h3 className="text-sm font-semibold text-[var(--hp-text)]">Triple evaluation</h3>
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
                                <p key={idx} className="text-[11px] text-[var(--hp-text-muted)] leading-relaxed">• {line}</p>
                              ))}
                            </div>
                          </div>
                        </div>
                      )}

                      {run.response && (
                        <div className="px-5 pb-4">
                          <div className="rounded-2xl border border-[var(--hp-border-subtle)] bg-[var(--hp-surface)]/40 p-4">
                            <div className="flex items-center gap-2 mb-3">
                              <FiMessageSquare className="w-3.5 h-3.5 text-gray-400" />
                              <h3 className="text-sm font-semibold text-[var(--hp-text)]">Response preview</h3>
                            </div>
                            <div className="space-y-1.5">
                              {(run.responsePreview ?? []).map((line, idx) => (
                                <p key={idx} className="text-xs text-[var(--hp-text-muted)] leading-relaxed break-words">{line}</p>
                              ))}
                            </div>
                            <p className="mt-3 text-[10px] text-gray-400">Sensitive fields are redacted and long values are truncated for readability.</p>
                          </div>
                        </div>
                      )}

                      {run.response && (
                        <div className="px-5 pb-4">
                          <button
                            type="button"
                            onClick={() => onRawJsonRunIdChange(isJsonExpanded ? null : run.id)}
                            className="flex items-center gap-1.5 text-[11px] font-medium text-gray-400 hover:text-[var(--hp-text-muted)] transition-colors"
                          >
                            <FiCode className="w-3 h-3" />
                            {isJsonExpanded ? 'Hide raw response' : 'View raw response'}
                          </button>
                          {isJsonExpanded && (
                            <pre className="mt-2 text-[11px] text-[var(--hp-text-muted)] bg-[var(--hp-surface-strong)] rounded-xl p-4 overflow-x-auto max-h-64 font-mono leading-relaxed border border-[var(--hp-border-subtle)]">
                              {JSON.stringify(run.response, null, 2)}
                            </pre>
                          )}
                        </div>
                      )}

                      {run.error && (
                        <div className="mx-5 mb-4 rounded-xl border border-[var(--hp-error)]/20 bg-[var(--hp-error)]/10 px-4 py-3 flex items-start gap-2.5">
                          <FiAlertCircle className="w-4 h-4 text-red-500 shrink-0 mt-0.5" />
                          <p className="text-xs font-medium text-[var(--hp-error)] leading-relaxed">{run.error}</p>
                        </div>
                      )}

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
        )}
      </div>

      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <FiMessageSquare className="w-4 h-4 text-gray-400" />
          <h2 className="text-lg font-bold text-[var(--hp-text)] tracking-tight">Activity feed</h2>
        </div>

        <Card variant="outlined" className="p-0 overflow-hidden">
          {activity.length === 0 ? (
            <div className="p-8 text-center">
              <FiClock className="w-6 h-6 text-[var(--hp-text-faint)] mx-auto mb-2" />
              <p className="text-sm text-[var(--hp-text-muted)]">No activity for this time range</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="border-b border-[var(--hp-border-subtle)]">
                    <th className="px-4 py-3 text-left text-[10px] uppercase tracking-widest font-semibold text-gray-400">Timestamp</th>
                    <th className="px-4 py-3 text-left text-[10px] uppercase tracking-widest font-semibold text-gray-400">Event</th>
                    <th className="px-4 py-3 text-left text-[10px] uppercase tracking-widest font-semibold text-gray-400">Entity</th>
                    <th className="px-4 py-3 text-left text-[10px] uppercase tracking-widest font-semibold text-gray-400">Status</th>
                    <th className="px-4 py-3 text-left text-[10px] uppercase tracking-widest font-semibold text-gray-400">Latency</th>
                  </tr>
                </thead>
                <tbody>
                  {activity.map((row, index) => (
                    <tr key={`${row.id}-${row.timestamp}-${index}`} className="border-t border-[var(--hp-border-subtle)] hover:bg-[var(--hp-surface-strong)]/50 transition-colors">
                      <td className="px-4 py-2.5 text-xs text-gray-500 tabular-nums">{new Date(row.timestamp).toLocaleString()}</td>
                      <td className="px-4 py-2.5 text-xs font-medium text-[var(--hp-text)]">{row.event}</td>
                      <td className="px-4 py-2.5 text-xs text-gray-500 font-mono">{row.entity}</td>
                      <td className="px-4 py-2.5"><Badge variant={ACTIVITY_STATUS_BADGE_VARIANT[row.status]} size="xs">{row.status}</Badge></td>
                      <td className="px-4 py-2.5 text-xs text-gray-500 tabular-nums">{row.latency_ms != null ? (row.latency_ms < 1 ? '< 1 ms' : `${Math.round(row.latency_ms)} ms`) : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>
    </section>
  );
}

function CockpitEvaluationsPanel({
  timeRange,
  modelUsage,
}: {
  timeRange: AgentMonitorTimeRange;
  modelUsage: AdminServiceDashboard['model_usage'];
}) {
  const { data, isLoading, isError } = useAgentEvaluations(timeRange);

  return (
    <section className="grid gap-6 lg:grid-cols-[1.05fr_0.95fr]" aria-label="Evaluations">
      <Card variant="outlined" className="p-5 space-y-4">
        <div className="flex items-center gap-2">
          <FiCpu className="w-4 h-4 text-gray-400" />
          <h2 className="text-lg font-bold text-[var(--hp-text)] tracking-tight">Evaluation trend</h2>
        </div>

        {isLoading && <p className="text-sm text-[var(--hp-text-muted)]">Loading evaluation trend…</p>}
        {isError && <p className="text-sm text-[var(--hp-error)]">Unable to load evaluation trend data.</p>}

        {data && (
          <>
            <div className="grid grid-cols-3 gap-3">
              <div className="rounded-2xl bg-[var(--hp-surface-strong)] px-3 py-3">
                <p className="text-[10px] uppercase tracking-[0.2em] text-[var(--hp-text-muted)]">Overall score</p>
                <p className="mt-1 text-2xl font-bold text-[var(--hp-text)]">{data.summary.overall_score.toFixed(2)}</p>
              </div>
              <div className="rounded-2xl bg-[var(--hp-surface-strong)] px-3 py-3">
                <p className="text-[10px] uppercase tracking-[0.2em] text-[var(--hp-text-muted)]">Pass rate</p>
                <p className="mt-1 text-2xl font-bold text-[var(--hp-text)]">{Math.round(data.summary.pass_rate * 100)}%</p>
              </div>
              <div className="rounded-2xl bg-[var(--hp-surface-strong)] px-3 py-3">
                <p className="text-[10px] uppercase tracking-[0.2em] text-[var(--hp-text-muted)]">Runs</p>
                <p className="mt-1 text-2xl font-bold text-[var(--hp-text)]">{data.summary.total_runs}</p>
              </div>
            </div>
            <EvaluationTrendChart trends={data.trends} />
          </>
        )}
      </Card>

      <Card variant="outlined" className="p-0 overflow-hidden">
        <div className="px-5 py-4 border-b border-[var(--hp-border-subtle)] flex items-center gap-2">
          <FiCpu className="w-4 h-4 text-gray-400" />
          <h2 className="text-lg font-bold text-[var(--hp-text)] tracking-tight">Model usage</h2>
        </div>

        {modelUsage.length === 0 ? (
          <div className="p-8 text-center">
            <FiCpu className="w-6 h-6 text-[var(--hp-text-faint)] mx-auto mb-2" />
            <p className="text-sm text-[var(--hp-text-muted)]">No model usage data available</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--hp-border-subtle)]">
                  <th className="px-4 py-3 text-left text-[10px] uppercase tracking-widest font-semibold text-gray-400">Model</th>
                  <th className="px-4 py-3 text-left text-[10px] uppercase tracking-widest font-semibold text-gray-400">Tier</th>
                  <th className="px-4 py-3 text-left text-[10px] uppercase tracking-widest font-semibold text-gray-400">Requests</th>
                  <th className="px-4 py-3 text-left text-[10px] uppercase tracking-widest font-semibold text-gray-400">Tokens</th>
                  <th className="px-4 py-3 text-left text-[10px] uppercase tracking-widest font-semibold text-gray-400">Avg latency</th>
                </tr>
              </thead>
              <tbody>
                {modelUsage.map((row) => (
                  <tr key={`${row.model_tier}-${row.model_name}`} className="border-t border-[var(--hp-border-subtle)] hover:bg-[var(--hp-surface-strong)]/50 transition-colors">
                    <td className="px-4 py-2.5 text-xs font-medium text-[var(--hp-text)] font-mono">{row.model_name}</td>
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
    </section>
  );
}

function CockpitPromptsPanel({
  prompts,
  onStagePrompt,
}: {
  prompts: AdminServicePromptDocument[];
  onStagePrompt: (prompt: AdminServicePromptDocument) => void;
}) {
  return (
    <section className="space-y-4" aria-label="Prompt catalog">
      <div className="flex items-center gap-3">
        <h2 className="text-lg font-bold text-[var(--hp-text)] tracking-tight">Prompt catalog</h2>
        <Badge variant="glass" size="sm">{prompts.length} document{prompts.length === 1 ? '' : 's'}</Badge>
      </div>

      {prompts.length === 0 ? (
        <Card variant="outlined" className="p-8 text-center">
          <FiFileText className="w-6 h-6 text-[var(--hp-text-faint)] mx-auto mb-2" />
          <p className="text-sm text-[var(--hp-text-muted)]">No prompt files were exposed by this service.</p>
        </Card>
      ) : (
        <div className="space-y-4">
          {prompts.map((prompt, index) => (
            <Card key={`${prompt.name}-${prompt.sha}`} variant={index === 0 ? 'glass' : 'outlined'} className="p-5 space-y-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h3 className="text-sm font-bold text-[var(--hp-text)]">{prompt.name}</h3>
                  <p className="text-xs text-[var(--hp-text-muted)]">
                    SHA {prompt.sha.slice(0, 12)} · {prompt.last_modified ? new Date(prompt.last_modified).toLocaleString() : 'timestamp unavailable'}
                  </p>
                </div>
                <Button size="sm" variant="secondary" onClick={() => onStagePrompt(prompt)}>
                  Stage sample run
                </Button>
              </div>
              <pre className="max-h-80 overflow-auto rounded-2xl border border-[var(--hp-border-subtle)] bg-[var(--hp-surface)] p-4 text-[11px] leading-relaxed text-[var(--hp-text-muted)]">{truncateText(prompt.content, 2400)}</pre>
            </Card>
          ))}
        </div>
      )}
    </section>
  );
}

function CockpitToolsPanel({
  tools,
  agentSlug,
  collaborators,
}: {
  tools: AdminServiceToolDescription[];
  agentSlug: string;
  collaborators: string[];
}) {
  return (
    <section className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]" aria-label="Tools and integrations">
      <div className="space-y-4">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-bold text-[var(--hp-text)] tracking-tight">MCP tools</h2>
          <Badge variant="glass" size="sm">{tools.length} registered</Badge>
        </div>

        {tools.length === 0 ? (
          <Card variant="outlined" className="p-8 text-center">
            <FiTool className="w-6 h-6 text-[var(--hp-text-faint)] mx-auto mb-2" />
            <p className="text-sm text-[var(--hp-text-muted)]">No MCP tools registered for this service.</p>
          </Card>
        ) : (
          <div className="space-y-4">
            {tools.map((tool) => {
              const inputCount = countSchemaProperties(tool.input_schema ?? null);
              const outputCount = countSchemaProperties(tool.output_schema ?? null);
              return (
                <Card key={`${tool.path}-${tool.name}`} variant="outlined" className="p-5 space-y-3">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <h3 className="text-sm font-bold text-[var(--hp-text)]">{tool.name}</h3>
                      <p className="text-xs font-mono text-[var(--hp-text-muted)]">{tool.path}</p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <Badge size="xs" variant="secondary">Input {inputCount ?? 'n/a'}</Badge>
                      <Badge size="xs" variant="secondary">Output {outputCount ?? 'n/a'}</Badge>
                    </div>
                  </div>
                  <p className="text-sm text-[var(--hp-text-muted)]">{tool.description}</p>
                  <div className="grid gap-3 md:grid-cols-2">
                    <details className="rounded-2xl border border-[var(--hp-border-subtle)] bg-[var(--hp-surface)] p-3">
                      <summary className="cursor-pointer text-xs font-semibold uppercase tracking-[0.2em] text-[var(--hp-text-muted)]">Input schema</summary>
                      <pre className="mt-3 overflow-auto text-[11px] leading-relaxed text-[var(--hp-text-muted)]">{renderJsonSnippet(tool.input_schema ?? tool.input_schema_ref ?? { message: 'Unavailable' })}</pre>
                    </details>
                    <details className="rounded-2xl border border-[var(--hp-border-subtle)] bg-[var(--hp-surface)] p-3">
                      <summary className="cursor-pointer text-xs font-semibold uppercase tracking-[0.2em] text-[var(--hp-text-muted)]">Output schema</summary>
                      <pre className="mt-3 overflow-auto text-[11px] leading-relaxed text-[var(--hp-text-muted)]">{renderJsonSnippet(tool.output_schema ?? tool.output_schema_ref ?? { message: 'Unavailable' })}</pre>
                    </details>
                  </div>
                </Card>
              );
            })}
          </div>
        )}
      </div>

      <Card variant="glass" className="p-5 space-y-4">
        <div className="flex items-center gap-2">
          <FiUsers className="w-4 h-4 text-gray-400" />
          <h2 className="text-lg font-bold text-[var(--hp-text)] tracking-tight">Integration notes</h2>
        </div>
        <p className="text-sm text-[var(--hp-text-muted)]">
          {agentSlug} exchanges context through registered MCP tools and collaborates with adjacent agents in the retail workflow.
        </p>
        <div className="space-y-2">
          <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[var(--hp-text-muted)]">Collaborators</p>
          <div className="flex flex-wrap gap-2">
            {collaborators.length > 0 ? collaborators.map((name) => (
              <Badge key={name} variant="glass" size="xs">{name}</Badge>
            )) : <Badge variant="secondary" size="xs">No collaborators declared</Badge>}
          </div>
        </div>
      </Card>
    </section>
  );
}

function CockpitResiliencePanel({
  resilienceStatus,
  appSurface,
  foundrySurface,
}: {
  resilienceStatus: AdminServiceResilienceStatus;
  appSurface: AdminServiceAppSurface;
  foundrySurface: AdminServiceFoundrySurface;
}) {
  return (
    <section className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]" aria-label="Resilience and self-healing">
      <Card variant="glass" className="p-5 space-y-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-bold text-[var(--hp-text)] tracking-tight">Self-healing status</h2>
            <p className="text-sm text-[var(--hp-text-muted)]">Incident posture and repair policy for this service.</p>
          </div>
          <Badge variant={resilienceStatus.enabled ? 'success' : 'secondary'} size="sm">
            {resilienceStatus.enabled ? 'Enabled' : 'Disabled'}
          </Badge>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-2xl bg-[var(--hp-surface)] px-4 py-3">
            <p className="text-[10px] uppercase tracking-[0.2em] text-[var(--hp-text-muted)]">Mode</p>
            <p className="mt-1 text-lg font-bold text-[var(--hp-text)]">{resilienceStatus.detect_only ? 'Detect only' : 'Repair'}</p>
          </div>
          <div className="rounded-2xl bg-[var(--hp-surface)] px-4 py-3">
            <p className="text-[10px] uppercase tracking-[0.2em] text-[var(--hp-text-muted)]">Open incidents</p>
            <p className="mt-1 text-lg font-bold text-[var(--hp-text)]">{resilienceStatus.incidents_open}</p>
          </div>
          <div className="rounded-2xl bg-[var(--hp-surface)] px-4 py-3">
            <p className="text-[10px] uppercase tracking-[0.2em] text-[var(--hp-text-muted)]">Total incidents</p>
            <p className="mt-1 text-lg font-bold text-[var(--hp-text)]">{resilienceStatus.incidents_total}</p>
          </div>
          <div className="rounded-2xl bg-[var(--hp-surface)] px-4 py-3">
            <p className="text-[10px] uppercase tracking-[0.2em] text-[var(--hp-text-muted)]">Closed incidents</p>
            <p className="mt-1 text-lg font-bold text-[var(--hp-text)]">{resilienceStatus.incidents_closed}</p>
          </div>
        </div>

        <div className="space-y-2">
          <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[var(--hp-text-muted)]">Allowlisted actions</p>
          <div className="flex flex-wrap gap-2">
            {resilienceStatus.allowlisted_actions.length > 0 ? resilienceStatus.allowlisted_actions.map((action) => (
              <Badge key={action} size="xs" variant="glass">{action}</Badge>
            )) : <Badge size="xs" variant="secondary">No actions exposed</Badge>}
          </div>
        </div>
      </Card>

      <div className="space-y-4">
        <Card variant="outlined" className="p-5 space-y-3">
          <div className="flex items-center gap-2">
            <FiShield className="w-4 h-4 text-gray-400" />
            <h2 className="text-lg font-bold text-[var(--hp-text)] tracking-tight">Manifest snapshot</h2>
          </div>
          <pre className="max-h-80 overflow-auto rounded-2xl border border-[var(--hp-border-subtle)] bg-[var(--hp-surface)] p-4 text-[11px] leading-relaxed text-[var(--hp-text-muted)]">{renderJsonSnippet(resilienceStatus.manifest ?? { message: 'Manifest unavailable' })}</pre>
        </Card>

        <Card variant="outlined" className="p-5 space-y-3">
          <div className="flex items-center gap-2">
            <FiActivity className="w-4 h-4 text-gray-400" />
            <h2 className="text-lg font-bold text-[var(--hp-text)] tracking-tight">Recovery surfaces</h2>
          </div>
          <div className="grid gap-2 sm:grid-cols-2">
            <a href={appSurface.links.ready} target="_blank" rel="noopener noreferrer" className="inline-flex items-center justify-between rounded-xl border border-[var(--hp-border)] bg-[var(--hp-surface)] px-3 py-2 text-xs font-medium text-[var(--hp-text)] hover:bg-[var(--hp-surface-strong)] transition-colors">
              <span>Ready probe</span>
              <FiArrowRight className="w-3.5 h-3.5" />
            </a>
            <a href={appSurface.links.health} target="_blank" rel="noopener noreferrer" className="inline-flex items-center justify-between rounded-xl border border-[var(--hp-border)] bg-[var(--hp-surface)] px-3 py-2 text-xs font-medium text-[var(--hp-text)] hover:bg-[var(--hp-surface-strong)] transition-colors">
              <span>Health probe</span>
              <FiArrowRight className="w-3.5 h-3.5" />
            </a>
            <a href={foundrySurface.links.traces} target="_blank" rel="noopener noreferrer" className="inline-flex items-center justify-between rounded-xl border border-[var(--hp-border)] bg-[var(--hp-surface)] px-3 py-2 text-xs font-medium text-[var(--hp-text)] hover:bg-[var(--hp-surface-strong)] transition-colors">
              <span>Trace explorer</span>
              <FiArrowRight className="w-3.5 h-3.5" />
            </a>
            <a href={foundrySurface.links.evaluations} target="_blank" rel="noopener noreferrer" className="inline-flex items-center justify-between rounded-xl border border-[var(--hp-border)] bg-[var(--hp-surface)] px-3 py-2 text-xs font-medium text-[var(--hp-text)] hover:bg-[var(--hp-surface-strong)] transition-colors">
              <span>Evaluation center</span>
              <FiArrowRight className="w-3.5 h-3.5" />
            </a>
          </div>
        </Card>
      </div>
    </section>
  );
}

function CockpitConfigPanel({ domain, service }: { domain: AdminServiceDomain; service: string }) {
  const { data: config, isLoading, isError } = useTruthConfig();
  const updateMutation = useUpdateTruthConfig();

  const handleSave = useCallback((partial: Partial<TenantConfig>) => {
    updateMutation.mutate(partial);
  }, [updateMutation]);

  return (
    <section className="space-y-4" aria-label="Shared configuration">
      <Card variant="glass" className="p-5">
        <h2 className="text-lg font-bold text-[var(--hp-text)] tracking-tight">Shared tenant configuration</h2>
        <p className="mt-2 text-sm text-[var(--hp-text-muted)]">
          The {toTitleCase(service)} cockpit can stage and observe runs locally, but threshold and pipeline toggles remain shared across the truth layer for {domain} operators.
        </p>
      </Card>

      {updateMutation.isSuccess && (
        <Card className="p-4 border border-lime-500/30 bg-lime-500/10 text-lime-600">Configuration saved successfully.</Card>
      )}

      {updateMutation.isError && (
        <Card className="p-4 border border-[var(--hp-error)]/20 bg-[var(--hp-error)]/10 text-[var(--hp-error)]">Failed to save configuration. Please try again.</Card>
      )}

      {isLoading && <Card className="p-6 text-[var(--hp-text-muted)]">Loading configuration…</Card>}
      {isError && <Card className="p-6 border border-[var(--hp-error)]/20 text-[var(--hp-error)]">Failed to load configuration.</Card>}

      {config && (
        <ConfigPanel config={config} onSave={handleSave} isSaving={updateMutation.isPending} />
      )}
    </section>
  );
}

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
