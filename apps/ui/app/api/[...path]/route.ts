import { NextRequest, NextResponse } from 'next/server';

import { resolveCrudApiBaseUrl, validateProxyBaseUrlPolicy } from '../_shared/base-url-resolver';

type TargetResolution = {
  targetUrl: string | null;
  baseUrl: string | null;
  sourceKey: string | null;
  upstreamPath: string;
  policyViolation: 'missing' | 'non-apim' | null;
};

type ProxyFailureKind = 'config' | 'policy' | 'network' | 'upstream';

type ProxyErrorPayload = {
  error: string;
  proxy: {
    failureKind: ProxyFailureKind;
    sourceKey: string | null;
    baseUrl: string | null;
    attemptedPath: string;
    method: string;
    upstreamStatus?: number;
    upstreamStatusText?: string;
    upstreamError?: string | null;
    upstreamRequestId?: string | null;
    remediation: string[];
  };
};

type AgentMonitorDashboardFallback = {
  tracing_enabled: false;
  generated_at: string;
  health_cards: [];
  trace_feed: [];
  model_usage: [];
};

type AgentTraceDetailFallback = {
  tracing_enabled: false;
  trace_id: string;
  root_agent_name: 'unavailable';
  status: 'unknown';
  started_at: string;
  duration_ms: 0;
  spans: [];
};

type AgentEvaluationsFallback = {
  tracing_enabled: false;
  generated_at: string;
  summary: {
    overall_score: 0;
    pass_rate: 0;
    total_runs: 0;
  };
  trends: [];
  comparison: [];
};

type AgentActivityFallbackPayload =
  | AgentMonitorDashboardFallback
  | AgentTraceDetailFallback
  | AgentEvaluationsFallback;

type StaffReviewFallbackPayload =
  | {
      items: unknown[];
      total: number;
      page: number;
      page_size: number;
    }
  | {
      pending: number;
      approved_today: number;
      rejected_today: number;
      avg_confidence: number;
    }
  | {
      entity_id: string;
      product_title: string;
      category: string;
      completeness_score: number;
      proposed_attributes: unknown[];
    }
  | unknown[];

type EnrichmentMonitorFallbackPayload =
  | {
      status_cards: Array<{
        label: string;
        value: number;
      }>;
      active_jobs: Array<{
        id: string;
        entity_id: string;
        status: 'pending' | 'approved' | 'rejected' | 'queued' | 'running' | 'completed' | 'failed';
        source_type: string;
        confidence: number;
        updated_at: string;
      }>;
      error_log: unknown[];
      throughput: {
        per_minute: number;
        last_10m: number;
        failed_last_10m: number;
      };
    }
  | {
      entity_id: string;
      title: string;
      status: 'unknown' | 'pending';
      confidence: number;
      source_assets: unknown[];
      image_evidence: unknown[];
      attribute_diffs: Array<Record<string, unknown>>;
      diffs: Array<Record<string, unknown>>;
      reasoning: string;
      trace_id: null;
    };

type AgentActivityRouteKind = 'dashboard' | 'health' | 'evaluations' | 'trace-detail';

type AgentTraceSummaryShape = {
  trace_id: string;
  agent_name: string;
  operation: string;
  status: 'ok' | 'warning' | 'error' | 'unknown';
  started_at: string;
  duration_ms: number;
  model_tier: 'slm' | 'llm' | 'unknown';
  error_count: number;
};

type AgentSourceData = {
  service: string;
  traces: Array<Record<string, unknown>>;
  metrics: Record<string, unknown> | null;
  latestEvaluation: Record<string, unknown> | null;
};

type AdminServiceDomain = 'crm' | 'ecommerce' | 'inventory' | 'logistics' | 'products';

type AdminServiceRouteMatch = {
  domain: AdminServiceDomain;
  service: string;
  agentService: string;
};

type AdminServiceActivityRow = {
  id: string;
  timestamp: string;
  event: string;
  entity: string;
  status: 'ok' | 'warning' | 'error' | 'unknown';
  latency_ms: number;
};

type AdminServiceModelUsageRow = {
  model_name: string;
  model_tier: 'slm' | 'llm' | 'unknown';
  requests: number;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  avg_latency_ms: number;
  cost_usd: number;
};

type AdminServiceFallbackPayload = {
  domain: AdminServiceDomain;
  service: string;
  agent_service: string;
  generated_at: string;
  tracing_enabled: boolean;
  status_cards: Array<{
    label: string;
    value: string | number;
    status: 'healthy' | 'warning' | 'error' | 'unknown';
  }>;
  activity: AdminServiceActivityRow[];
  model_usage: AdminServiceModelUsageRow[];
};

const DEFAULT_AGENT_ACTIVITY_SERVICES = [
  'ecommerce-catalog-search',
  'search-enrichment-agent',
  'truth-enrichment',
  'ecommerce-product-detail-enrichment',
  'ecommerce-cart-intelligence',
  'ecommerce-checkout-support',
  'ecommerce-order-status',
  'inventory-health-check',
  'inventory-jit-replenishment',
  'inventory-reservation-validation',
  'logistics-eta-computation',
  'logistics-route-issue-detection',
  'logistics-returns-support',
] as const;

const ADMIN_SERVICE_AGENT_MAP: Record<string, string> = {
  'crm/campaigns': 'crm-campaign-intelligence',
  'crm/profiles': 'crm-profile-aggregation',
  'crm/segmentation': 'crm-segmentation-personalization',
  'crm/support': 'crm-support-assistance',
  'ecommerce/catalog': 'ecommerce-catalog-search',
  'ecommerce/cart': 'ecommerce-cart-intelligence',
  'ecommerce/checkout': 'ecommerce-checkout-support',
  'ecommerce/orders': 'ecommerce-order-status',
  'ecommerce/products': 'ecommerce-product-detail-enrichment',
  'inventory/health': 'inventory-health-check',
  'inventory/alerts': 'inventory-alerts-triggers',
  'inventory/replenishment': 'inventory-jit-replenishment',
  'inventory/reservation': 'inventory-reservation-validation',
  'logistics/carriers': 'logistics-carrier-selection',
  'logistics/eta': 'logistics-eta-computation',
  'logistics/returns': 'logistics-returns-support',
  'logistics/routes': 'logistics-route-issue-detection',
  'products/acp': 'product-management-acp-transformation',
  'products/assortment': 'product-management-assortment-optimization',
  'products/validation': 'product-management-consistency-validation',
  'products/normalization': 'product-management-normalization-classification',
};

const ADMIN_SERVICE_DOMAINS = new Set<AdminServiceDomain>([
  'crm',
  'ecommerce',
  'inventory',
  'logistics',
  'products',
]);

function buildTargetUrl(request: NextRequest, pathSegments: string[]): TargetResolution {
  const { baseUrl, sourceKey } = resolveCrudApiBaseUrl();
  const joinedPath = pathSegments.filter(Boolean).join('/');
  const upstreamPath = `/api/${joinedPath}`;
  const policyResult = validateProxyBaseUrlPolicy(baseUrl);

  if (!baseUrl || !policyResult.allowed) {
    return {
      targetUrl: null,
      baseUrl,
      sourceKey,
      upstreamPath,
      policyViolation: policyResult.violation,
    };
  }

  const query = request.nextUrl.search;

  return {
    targetUrl: `${baseUrl}${upstreamPath}${query}`,
    baseUrl,
    sourceKey,
    upstreamPath,
    policyViolation: null,
  };
}

function extractFirstMessage(payload: unknown): string | null {
  const extract = (value: unknown, depth = 0): string | null => {
    if (depth > 4 || value === null || value === undefined) {
      return null;
    }

    if (typeof value === 'string') {
      const trimmed = value.trim();
      return trimmed.length > 0 ? trimmed : null;
    }

    if (Array.isArray(value)) {
      for (const item of value) {
        const message = extract(item, depth + 1);
        if (message) {
          return message;
        }
      }
      return null;
    }

    if (typeof value === 'object') {
      const record = value as Record<string, unknown>;
      for (const key of ['error', 'message', 'detail', 'title', 'msg']) {
        const message = extract(record[key], depth + 1);
        if (message) {
          return message;
        }
      }
    }

    return null;
  };

  return extract(payload);
}

async function readUpstreamErrorPayload(response: Response): Promise<string | null> {
  const contentType = response.headers.get('content-type') || '';

  if (contentType.includes('application/json')) {
    try {
      const jsonPayload = await response.json();
      return extractFirstMessage(jsonPayload);
    } catch {
      return null;
    }
  }

  try {
    const text = (await response.text()).trim();
    if (!text) {
      return null;
    }

    return text.slice(0, 240);
  } catch {
    return null;
  }
}

function buildProxyErrorPayload(params: {
  failureKind: ProxyFailureKind;
  sourceKey: string | null;
  baseUrl: string | null;
  attemptedPath: string;
  method: string;
  upstreamStatus?: number;
  upstreamStatusText?: string;
  upstreamError?: string | null;
  upstreamRequestId?: string | null;
}): ProxyErrorPayload {
  const remediationByKind: Record<ProxyFailureKind, string[]> = {
    config: [
      'Set NEXT_PUBLIC_CRUD_API_URL (or NEXT_PUBLIC_API_URL / CRUD_API_URL) to the APIM gateway URL.',
      'Redeploy or restart the UI host after updating environment variables.',
    ],
    policy: [
      'Use an APIM gateway URL (*.azure-api.net) for NEXT_PUBLIC_CRUD_API_URL / NEXT_PUBLIC_API_URL / CRUD_API_URL.',
      'For local development only, use a loopback URL (http://localhost:*) or set UI_ALLOW_NON_APIM_PROXY_URL=true.',
    ],
    network: [
      'Verify DNS, firewall rules, and outbound network access from the UI host to the backend URL.',
      'Check backend availability and retry the request.',
    ],
    upstream: [
      'Inspect upstream service logs for request failures and dependency outages.',
      'Retry after backend recovery or fail over to a healthy upstream instance.',
    ],
  };

  const errorByKind: Record<ProxyFailureKind, string> = {
    config: 'API proxy is not configured for backend routing.',
    policy: 'API proxy rejected a non-APIM upstream target URL.',
    network: 'API proxy could not reach upstream service.',
    upstream: 'API proxy received a bad gateway response from upstream.',
  };

  return {
    error: errorByKind[params.failureKind],
    proxy: {
      failureKind: params.failureKind,
      sourceKey: params.sourceKey,
      baseUrl: params.baseUrl,
      attemptedPath: params.attemptedPath,
      method: params.method,
      upstreamStatus: params.upstreamStatus,
      upstreamStatusText: params.upstreamStatusText,
      upstreamError: params.upstreamError ?? null,
      upstreamRequestId: params.upstreamRequestId ?? null,
      remediation: remediationByKind[params.failureKind],
    },
  };
}

function isAgentActivityRoute(path: string): boolean {
  return (
    path === '/api/admin/agent-activity'
    || path === '/api/admin/agent-activity/health'
    || path === '/api/admin/agent-activity/evaluations'
    || path.startsWith('/api/admin/agent-activity/traces/')
  );
}

function resolveAdminServiceRoute(path: string): AdminServiceRouteMatch | null {
  const match = path.match(/^\/api\/admin\/([^/]+)\/([^/]+)$/);
  if (!match) {
    return null;
  }

  const domainCandidate = decodeURIComponent(match[1]) as AdminServiceDomain;
  const service = decodeURIComponent(match[2]);

  if (!ADMIN_SERVICE_DOMAINS.has(domainCandidate)) {
    return null;
  }

  const mappingKey = `${domainCandidate}/${service}`;
  const agentService = ADMIN_SERVICE_AGENT_MAP[mappingKey];
  if (!agentService) {
    return null;
  }

  return {
    domain: domainCandidate,
    service,
    agentService,
  };
}

function resolveAgentActivityRoute(upstreamPath: string): { kind: AgentActivityRouteKind; traceId?: string } | null {
  if (upstreamPath === '/api/admin/agent-activity') {
    return { kind: 'dashboard' };
  }

  if (upstreamPath === '/api/admin/agent-activity/health') {
    return { kind: 'health' };
  }

  if (upstreamPath === '/api/admin/agent-activity/evaluations') {
    return { kind: 'evaluations' };
  }

  if (upstreamPath.startsWith('/api/admin/agent-activity/traces/')) {
    return {
      kind: 'trace-detail',
      traceId: decodeURIComponent(upstreamPath.split('/').pop() || 'unknown-trace'),
    };
  }

  return null;
}

function toRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return null;
  }
  return value as Record<string, unknown>;
}

function toArray(value: unknown): unknown[] {
  if (Array.isArray(value)) {
    return value;
  }
  return [];
}

function readString(record: Record<string, unknown> | null, keys: string[]): string | null {
  if (!record) {
    return null;
  }

  for (const key of keys) {
    const value = record[key];
    if (typeof value === 'string' && value.trim().length > 0) {
      return value;
    }
  }

  return null;
}

function readNumber(record: Record<string, unknown> | null, keys: string[]): number | null {
  if (!record) {
    return null;
  }

  for (const key of keys) {
    const value = record[key];
    if (typeof value === 'number' && Number.isFinite(value)) {
      return value;
    }
    if (typeof value === 'string') {
      const parsed = Number(value);
      if (Number.isFinite(parsed)) {
        return parsed;
      }
    }
  }

  return null;
}

function normalizeModelTier(value: string | null): 'slm' | 'llm' | 'unknown' {
  if (!value) {
    return 'unknown';
  }

  const normalized = value.toLowerCase();
  if (normalized.includes('slm') || normalized.includes('small') || normalized.includes('fast')) {
    return 'slm';
  }
  if (normalized.includes('llm') || normalized.includes('gpt') || normalized.includes('rich') || normalized.includes('large')) {
    return 'llm';
  }

  return 'unknown';
}

function normalizeTraceStatus(value: string | null): 'ok' | 'warning' | 'error' | 'unknown' {
  if (!value) {
    return 'unknown';
  }

  const normalized = value.toLowerCase();
  if (normalized.includes('error') || normalized.includes('fail')) {
    return 'error';
  }
  if (normalized.includes('warn') || normalized.includes('retry')) {
    return 'warning';
  }
  if (normalized.includes('ok') || normalized.includes('success') || normalized.includes('completed')) {
    return 'ok';
  }

  return 'unknown';
}

function getAgentActivityServices(): string[] {
  const configured = process.env.ADMIN_AGENT_ACTIVITY_SERVICES;
  if (!configured) {
    return [...DEFAULT_AGENT_ACTIVITY_SERVICES];
  }

  const parsed = configured
    .split(',')
    .map((service) => service.trim())
    .filter((service) => service.length > 0);

  return parsed.length > 0 ? parsed : [...DEFAULT_AGENT_ACTIVITY_SERVICES];
}

function mapTraceEntryToSummary(entry: Record<string, unknown>, fallbackService: string, index: number): AgentTraceSummaryShape {
  const metadata = toRecord(entry.metadata);
  const startedAt =
    readString(entry, ['timestamp', 'started_at', 'time'])
    || readString(metadata, ['timestamp', 'started_at'])
    || new Date().toISOString();
  const durationMs =
    readNumber(metadata, ['duration_ms', 'latency_ms', 'duration'])
    || readNumber(entry, ['duration_ms', 'latency_ms'])
    || 0;
  const outcome = readString(entry, ['outcome', 'status']) || readString(metadata, ['outcome', 'status']);
  const status = normalizeTraceStatus(outcome);
  const errorCount =
    readNumber(metadata, ['error_count', 'errors'])
    || readNumber(entry, ['error_count'])
    || (status === 'error' ? 1 : 0);
  const serviceName =
    readString(entry, ['service', 'service_name', 'agent_name'])
    || readString(metadata, ['service', 'service_name', 'agent_name'])
    || fallbackService;
  const operation =
    readString(entry, ['name', 'operation', 'type'])
    || readString(metadata, ['operation'])
    || 'agent.activity';
  const modelName = readString(metadata, ['model_name', 'model', 'deployment', 'model_deployment']);
  const modelTier =
    normalizeModelTier(readString(metadata, ['model_tier']) || readString(entry, ['model_tier']) || modelName);
  const traceId =
    readString(metadata, ['trace_id', 'id'])
    || readString(entry, ['trace_id', 'id'])
    || `${serviceName}-${Date.parse(startedAt) || Date.now()}-${index}`;

  return {
    trace_id: traceId,
    agent_name: serviceName,
    operation,
    status,
    started_at: startedAt,
    duration_ms: durationMs,
    model_tier: modelTier,
    error_count: errorCount,
  };
}

async function fetchJsonIfOk(url: string, headers: Headers): Promise<unknown | null> {
  try {
    const response = await fetch(url, {
      method: 'GET',
      headers,
      redirect: 'manual',
      cache: 'no-store',
    });

    if (!response.ok) {
      return null;
    }

    const contentType = response.headers.get('content-type') || '';
    if (!contentType.includes('application/json')) {
      return null;
    }

    return await response.json();
  } catch {
    return null;
  }
}

async function collectAgentSourceData(baseUrl: string, requestHeaders: Headers): Promise<AgentSourceData[]> {
  const services = getAgentActivityServices();
  const sources: AgentSourceData[] = [];

  await Promise.all(
    services.map(async (service) => {
      const [tracesPayload, metricsPayload, evaluationPayload] = await Promise.all([
        fetchJsonIfOk(`${baseUrl}/agents/${service}/agent/traces?limit=25`, requestHeaders),
        fetchJsonIfOk(`${baseUrl}/agents/${service}/agent/metrics`, requestHeaders),
        fetchJsonIfOk(`${baseUrl}/agents/${service}/agent/evaluation/latest`, requestHeaders),
      ]);

      const tracesRecord = toRecord(tracesPayload);
      const traceEntries = toArray(tracesRecord?.traces)
        .map((item) => toRecord(item))
        .filter((item): item is Record<string, unknown> => item !== null);

      const evaluationRecord = toRecord(evaluationPayload);
      const latestEvaluation = toRecord(evaluationRecord?.latest) || toRecord(evaluationPayload);

      if (traceEntries.length > 0 || toRecord(metricsPayload) || latestEvaluation) {
        sources.push({
          service,
          traces: traceEntries,
          metrics: toRecord(metricsPayload),
          latestEvaluation,
        });
      }
    }),
  );

  return sources;
}

function buildAgentActivityDashboardFromSources(sources: AgentSourceData[]): AgentMonitorDashboardFallback | Record<string, unknown> | null {
  if (sources.length === 0) {
    return null;
  }

  const generatedAt = new Date().toISOString();
  const allSummaries = sources
    .flatMap((source) => source.traces.map((entry, index) => mapTraceEntryToSummary(entry, source.service, index)))
    .sort((left, right) => Date.parse(right.started_at) - Date.parse(left.started_at));

  const healthCards = sources.map((source) => {
    const metrics = source.metrics;
    const enabled = typeof metrics?.enabled === 'boolean' ? metrics.enabled : true;
    const counts = toRecord(metrics?.counts);
    const errors = readNumber(counts, ['error', 'errors', 'tool_call:error', 'decision:error']) || 0;
    const total =
      readNumber(counts, ['model_invocation', 'tool_call', 'decision'])
      || Math.max(source.traces.length, 1);
    const errorRate = total > 0 ? errors / total : 0;

    return {
      id: source.service,
      label: source.service,
      status: enabled ? (errorRate > 0.35 ? 'degraded' : 'healthy') : 'unknown',
      latency_ms: 0,
      error_rate: Number(errorRate.toFixed(4)),
      throughput_rpm: source.traces.length,
      updated_at: generatedAt,
    };
  });

  const modelUsageMap = new Map<string, {
    model_name: string;
    model_tier: 'slm' | 'llm' | 'unknown';
    requests: number;
    input_tokens: number;
    output_tokens: number;
    total_tokens: number;
    latencySum: number;
    cost_usd: number;
  }>();

  for (const source of sources) {
    for (const traceEntry of source.traces) {
      const metadata = toRecord(traceEntry.metadata);
      const modelName = readString(metadata, ['model_name', 'model', 'deployment']) || 'unknown-model';
      const modelTier = normalizeModelTier(readString(metadata, ['model_tier']) || modelName);
      const mapKey = `${modelTier}:${modelName}`;
      const inputTokens = readNumber(metadata, ['input_tokens', 'prompt_tokens']) || 0;
      const outputTokens = readNumber(metadata, ['output_tokens', 'completion_tokens']) || 0;
      const totalTokens = readNumber(metadata, ['total_tokens']) || inputTokens + outputTokens;
      const latencyMs = readNumber(metadata, ['latency_ms', 'duration_ms']) || 0;
      const costUsd = readNumber(metadata, ['cost_usd']) || 0;

      const current = modelUsageMap.get(mapKey) || {
        model_name: modelName,
        model_tier: modelTier,
        requests: 0,
        input_tokens: 0,
        output_tokens: 0,
        total_tokens: 0,
        latencySum: 0,
        cost_usd: 0,
      };

      current.requests += 1;
      current.input_tokens += inputTokens;
      current.output_tokens += outputTokens;
      current.total_tokens += totalTokens;
      current.latencySum += latencyMs;
      current.cost_usd += costUsd;
      modelUsageMap.set(mapKey, current);
    }
  }

  const modelUsage = Array.from(modelUsageMap.values()).map((item) => ({
    model_name: item.model_name,
    model_tier: item.model_tier,
    requests: item.requests,
    input_tokens: item.input_tokens,
    output_tokens: item.output_tokens,
    total_tokens: item.total_tokens,
    avg_latency_ms: item.requests > 0 ? item.latencySum / item.requests : 0,
    cost_usd: Number(item.cost_usd.toFixed(6)),
  }));

  return {
    tracing_enabled: true,
    generated_at: generatedAt,
    health_cards: healthCards,
    trace_feed: allSummaries.slice(0, 100),
    model_usage: modelUsage,
  };
}

function buildAgentTraceDetailFromSources(traceId: string, sources: AgentSourceData[]): Record<string, unknown> | null {
  if (sources.length === 0) {
    return null;
  }

  const summaries = sources.flatMap((source) =>
    source.traces.map((entry, index) => ({ summary: mapTraceEntryToSummary(entry, source.service, index), entry })),
  );

  const selected = summaries.find((candidate) => candidate.summary.trace_id === traceId);
  if (!selected) {
    return null;
  }

  const metadata = toRecord(selected.entry.metadata);
  const endedAt = new Date(Date.parse(selected.summary.started_at) + selected.summary.duration_ms).toISOString();
  const toolName = readString(selected.entry, ['name']) || readString(metadata, ['tool_name']);
  const modelName = readString(metadata, ['model_name', 'model']);

  const span = {
    span_id: `${selected.summary.trace_id}-span-1`,
    parent_span_id: null,
    name: selected.summary.operation,
    service: selected.summary.agent_name,
    status: selected.summary.status,
    started_at: selected.summary.started_at,
    ended_at: endedAt,
    duration_ms: selected.summary.duration_ms,
    model_tier: selected.summary.model_tier,
    tool_name: toolName,
    model_name: modelName,
  };

  return {
    tracing_enabled: true,
    trace_id: selected.summary.trace_id,
    root_agent_name: selected.summary.agent_name,
    status: selected.summary.status,
    started_at: selected.summary.started_at,
    duration_ms: selected.summary.duration_ms,
    spans: [span],
    tool_calls: toolName
      ? [
          {
            span_id: span.span_id,
            tool_name: toolName,
            status: selected.summary.status,
          },
        ]
      : [],
    model_invocations: modelName
      ? [
          {
            span_id: span.span_id,
            model_name: modelName,
            model_tier: selected.summary.model_tier,
            latency_ms: selected.summary.duration_ms,
          },
        ]
      : [],
  };
}

function buildAgentEvaluationsFromSources(sources: AgentSourceData[]): Record<string, unknown> | null {
  const evaluations = sources
    .map((source) => ({
      service: source.service,
      latest: source.latestEvaluation,
    }))
    .filter((entry) => entry.latest !== null);

  if (evaluations.length === 0) {
    return null;
  }

  const generatedAt = new Date().toISOString();
  const overallScores = evaluations
    .map((entry) =>
      readNumber(entry.latest, ['overall_score', 'score', 'quality_score', 'accuracy'])
      || 0,
    );
  const passRates = evaluations
    .map((entry) =>
      readNumber(entry.latest, ['pass_rate', 'pass', 'success_rate'])
      || 0,
    );

  const comparison = evaluations.map((entry) => ({
    model_name: readString(entry.latest, ['model_name', 'model', 'deployment']) || entry.service,
    model_tier: normalizeModelTier(readString(entry.latest, ['model_tier', 'tier']) || null),
    dataset: readString(entry.latest, ['dataset', 'dataset_name']) || 'latest',
    score: readNumber(entry.latest, ['overall_score', 'score', 'quality_score', 'accuracy']) || 0,
    pass_rate: readNumber(entry.latest, ['pass_rate', 'pass', 'success_rate']) || 0,
    avg_latency_ms: readNumber(entry.latest, ['avg_latency_ms', 'latency_ms']) || 0,
    cost_per_1k_tokens: readNumber(entry.latest, ['cost_per_1k_tokens', 'cost']) || 0,
  }));

  return {
    tracing_enabled: true,
    generated_at: generatedAt,
    summary: {
      overall_score: overallScores.reduce((sum, value) => sum + value, 0) / Math.max(overallScores.length, 1),
      pass_rate: passRates.reduce((sum, value) => sum + value, 0) / Math.max(passRates.length, 1),
      total_runs: evaluations.length,
    },
    trends: comparison.map((row) => ({
      metric: `${row.model_name} score`,
      latest: row.score,
      change_pct: 0,
      points: [{ timestamp: generatedAt, value: row.score }],
    })),
    comparison,
  };
}

async function buildAgentActivitySecondaryPayload(params: {
  upstreamPath: string;
  baseUrl: string | null;
  requestHeaders: Headers;
}): Promise<Record<string, unknown> | null> {
  if (!params.baseUrl) {
    return null;
  }

  const route = resolveAgentActivityRoute(params.upstreamPath);
  if (!route) {
    return null;
  }

  const sources = await collectAgentSourceData(params.baseUrl, params.requestHeaders);
  if (sources.length === 0) {
    return null;
  }

  if (route.kind === 'dashboard' || route.kind === 'health') {
    return buildAgentActivityDashboardFromSources(sources) as Record<string, unknown>;
  }

  if (route.kind === 'evaluations') {
    return buildAgentEvaluationsFromSources(sources);
  }

  if (route.kind === 'trace-detail') {
    return buildAgentTraceDetailFromSources(route.traceId || 'unknown-trace', sources);
  }

  return null;
}

function buildEmptyAdminServicePayload(route: AdminServiceRouteMatch): AdminServiceFallbackPayload {
  return {
    domain: route.domain,
    service: route.service,
    agent_service: route.agentService,
    generated_at: new Date().toISOString(),
    tracing_enabled: false,
    status_cards: [],
    activity: [],
    model_usage: [],
  };
}

function buildAdminServiceModelUsageRows(
  traces: Array<Record<string, unknown>>,
  metrics: Record<string, unknown> | null,
  latestEvaluation: Record<string, unknown> | null,
): AdminServiceModelUsageRow[] {
  const usageMap = new Map<string, {
    model_name: string;
    model_tier: 'slm' | 'llm' | 'unknown';
    requests: number;
    input_tokens: number;
    output_tokens: number;
    total_tokens: number;
    latency_sum: number;
    cost_usd: number;
  }>();

  for (const trace of traces) {
    const metadata = toRecord(trace.metadata);
    const modelName = readString(metadata, ['model_name', 'model', 'deployment', 'model_deployment']) || 'unknown-model';
    const modelTier = normalizeModelTier(readString(metadata, ['model_tier']) || modelName);
    const key = `${modelTier}:${modelName}`;
    const inputTokens = readNumber(metadata, ['input_tokens', 'prompt_tokens']) || 0;
    const outputTokens = readNumber(metadata, ['output_tokens', 'completion_tokens']) || 0;
    const totalTokens = readNumber(metadata, ['total_tokens']) || inputTokens + outputTokens;
    const latency = readNumber(metadata, ['latency_ms', 'duration_ms']) || 0;
    const cost = readNumber(metadata, ['cost_usd']) || 0;

    const current = usageMap.get(key) || {
      model_name: modelName,
      model_tier: modelTier,
      requests: 0,
      input_tokens: 0,
      output_tokens: 0,
      total_tokens: 0,
      latency_sum: 0,
      cost_usd: 0,
    };

    current.requests += 1;
    current.input_tokens += inputTokens;
    current.output_tokens += outputTokens;
    current.total_tokens += totalTokens;
    current.latency_sum += latency;
    current.cost_usd += cost;
    usageMap.set(key, current);
  }

  if (usageMap.size === 0) {
    const metricsModelUsage = toArray(toRecord(metrics?.model_usage)?.rows ?? metrics?.model_usage)
      .map((row) => toRecord(row))
      .filter((row): row is Record<string, unknown> => row !== null)
      .map((row) => {
        const modelName = readString(row, ['model_name', 'model', 'deployment']) || 'unknown-model';
        const requests = readNumber(row, ['requests', 'count']) || 0;
        const inputTokens = readNumber(row, ['input_tokens', 'prompt_tokens']) || 0;
        const outputTokens = readNumber(row, ['output_tokens', 'completion_tokens']) || 0;
        const totalTokens = readNumber(row, ['total_tokens']) || inputTokens + outputTokens;
        const avgLatency = readNumber(row, ['avg_latency_ms', 'latency_ms']) || 0;
        return {
          model_name: modelName,
          model_tier: normalizeModelTier(readString(row, ['model_tier', 'tier']) || modelName),
          requests,
          input_tokens: inputTokens,
          output_tokens: outputTokens,
          total_tokens: totalTokens,
          avg_latency_ms: avgLatency,
          cost_usd: readNumber(row, ['cost_usd']) || 0,
        };
      });

    if (metricsModelUsage.length > 0) {
      return metricsModelUsage;
    }

    if (latestEvaluation) {
      const modelName = readString(latestEvaluation, ['model_name', 'model', 'deployment']) || 'unknown-model';
      const avgLatency = readNumber(latestEvaluation, ['avg_latency_ms', 'latency_ms']) || 0;
      return [
        {
          model_name: modelName,
          model_tier: normalizeModelTier(readString(latestEvaluation, ['model_tier', 'tier']) || modelName),
          requests: 0,
          input_tokens: 0,
          output_tokens: 0,
          total_tokens: 0,
          avg_latency_ms: avgLatency,
          cost_usd: readNumber(latestEvaluation, ['cost_per_1k_tokens', 'cost']) || 0,
        },
      ];
    }

    return [];
  }

  return Array.from(usageMap.values()).map((row) => ({
    model_name: row.model_name,
    model_tier: row.model_tier,
    requests: row.requests,
    input_tokens: row.input_tokens,
    output_tokens: row.output_tokens,
    total_tokens: row.total_tokens,
    avg_latency_ms: row.requests > 0 ? row.latency_sum / row.requests : 0,
    cost_usd: Number(row.cost_usd.toFixed(6)),
  }));
}

async function buildAdminServiceSecondaryPayload(params: {
  route: AdminServiceRouteMatch;
  baseUrl: string | null;
  requestHeaders: Headers;
}): Promise<AdminServiceFallbackPayload> {
  const { route, baseUrl, requestHeaders } = params;

  if (!baseUrl) {
    return buildEmptyAdminServicePayload(route);
  }

  const [tracesPayload, metricsPayload, evaluationPayload] = await Promise.all([
    fetchJsonIfOk(`${baseUrl}/agents/${route.agentService}/agent/traces?limit=40`, requestHeaders),
    fetchJsonIfOk(`${baseUrl}/agents/${route.agentService}/agent/metrics`, requestHeaders),
    fetchJsonIfOk(`${baseUrl}/agents/${route.agentService}/agent/evaluation/latest`, requestHeaders),
  ]);

  const tracesRecord = toRecord(tracesPayload);
  const traces = toArray(tracesRecord?.traces)
    .map((entry) => toRecord(entry))
    .filter((entry): entry is Record<string, unknown> => entry !== null);
  const metrics = toRecord(metricsPayload);
  const evaluationRecord = toRecord(evaluationPayload);
  const latestEvaluation = toRecord(evaluationRecord?.latest) || evaluationRecord;

  const generatedAt = new Date().toISOString();
  const activity = traces.map((entry, index) => {
    const metadata = toRecord(entry.metadata);
    const timestamp =
      readString(entry, ['timestamp', 'started_at', 'time'])
      || readString(metadata, ['timestamp', 'started_at'])
      || generatedAt;
    const status = normalizeTraceStatus(
      readString(entry, ['status', 'outcome']) || readString(metadata, ['status', 'outcome']),
    );
    const eventName =
      readString(entry, ['name', 'operation', 'type'])
      || readString(metadata, ['operation', 'tool_name'])
      || 'agent.activity';
    const entity =
      readString(metadata, ['entity_id', 'resource_id'])
      || readString(entry, ['entity_id', 'id'])
      || route.agentService;
    const latency =
      readNumber(metadata, ['latency_ms', 'duration_ms'])
      || readNumber(entry, ['latency_ms', 'duration_ms'])
      || 0;
    const id =
      readString(metadata, ['trace_id', 'id'])
      || readString(entry, ['trace_id', 'id'])
      || `${route.agentService}-${index + 1}`;

    return {
      id,
      timestamp,
      event: eventName,
      entity,
      status,
      latency_ms: latency,
    };
  });

  const errorCount = activity.filter((row) => row.status === 'error').length;
  const totalCount = activity.length;
  const averageLatency =
    totalCount > 0 ? Math.round(activity.reduce((sum, row) => sum + row.latency_ms, 0) / totalCount) : 0;
  const errorRate = totalCount > 0 ? errorCount / totalCount : 0;
  const evaluationScore = readNumber(latestEvaluation, ['overall_score', 'score', 'quality_score', 'accuracy']) || 0;
  const metricsEnabled = typeof metrics?.enabled === 'boolean' ? metrics.enabled : totalCount > 0;

  const statusCards: AdminServiceFallbackPayload['status_cards'] = [
    {
      label: 'Trace events',
      value: totalCount,
      status: totalCount > 0 ? 'healthy' : 'unknown',
    },
    {
      label: 'Avg latency (ms)',
      value: averageLatency,
      status: averageLatency > 0 && averageLatency > 1200 ? 'warning' : averageLatency > 0 ? 'healthy' : 'unknown',
    },
    {
      label: 'Error rate',
      value: `${Math.round(errorRate * 100)}%`,
      status: errorRate >= 0.25 ? 'error' : errorRate > 0 ? 'warning' : totalCount > 0 ? 'healthy' : 'unknown',
    },
    {
      label: 'Latest evaluation',
      value: Number(evaluationScore.toFixed(3)),
      status: evaluationScore >= 0.75 ? 'healthy' : evaluationScore > 0 ? 'warning' : 'unknown',
    },
  ];

  return {
    domain: route.domain,
    service: route.service,
    agent_service: route.agentService,
    generated_at: generatedAt,
    tracing_enabled: metricsEnabled,
    status_cards: statusCards,
    activity: activity.slice(0, 40),
    model_usage: buildAdminServiceModelUsageRows(traces, metrics, latestEvaluation),
  };
}

function isStaffReviewRoute(path: string): boolean {
  return path === '/api/staff/review' || path.startsWith('/api/staff/review/');
}

function isEnrichmentMonitorRoute(path: string): boolean {
  return path === '/api/admin/enrichment-monitor' || path.startsWith('/api/admin/enrichment-monitor/');
}

function parsePositiveInt(value: string | null, fallback: number): number {
  if (!value) {
    return fallback;
  }

  const parsed = Number.parseInt(value, 10);
  if (!Number.isFinite(parsed) || parsed <= 0) {
    return fallback;
  }

  return parsed;
}

async function postJsonIfOk(url: string, headers: Headers, payload: unknown): Promise<unknown | null> {
  try {
    const requestHeaders = new Headers(headers);
    requestHeaders.set('content-type', 'application/json');

    const response = await fetch(url, {
      method: 'POST',
      headers: requestHeaders,
      body: JSON.stringify(payload),
      redirect: 'manual',
      cache: 'no-store',
    });

    if (!response.ok) {
      return null;
    }

    const contentType = response.headers.get('content-type') || '';
    if (!contentType.includes('application/json')) {
      return null;
    }

    return await response.json();
  } catch {
    return null;
  }
}

async function getJsonIfOk(url: string, headers: Headers): Promise<unknown | null> {
  try {
    const requestHeaders = new Headers(headers);

    const response = await fetch(url, {
      method: 'GET',
      headers: requestHeaders,
      redirect: 'manual',
      cache: 'no-store',
    });

    if (!response.ok) {
      return null;
    }

    const contentType = response.headers.get('content-type') || '';
    if (!contentType.includes('application/json')) {
      return null;
    }

    return await response.json();
  } catch {
    return null;
  }
}

async function buildStaffReviewSecondaryPayload(
  upstreamPath: string,
  query: URLSearchParams,
  {
    baseUrl,
    requestHeaders,
  }: {
    baseUrl: string | null;
    requestHeaders: Headers;
  },
): Promise<StaffReviewFallbackPayload | null> {
  if (!baseUrl) {
    return null;
  }

  const invokeUrl = `${baseUrl}/agents/truth-hitl/invoke`;

  if (upstreamPath === '/api/staff/review') {
    const page = parsePositiveInt(query.get('page'), 1);
    const pageSize = parsePositiveInt(query.get('page_size'), 20);
    const skip = (page - 1) * pageSize;

    const payload = await postJsonIfOk(invokeUrl, requestHeaders, {
      action: 'queue',
      skip,
      limit: pageSize,
      field_name: query.get('field_name') || undefined,
      entity_id: query.get('entity_id') || undefined,
    });
    const record = toRecord(payload);
    const items = toArray(record?.items);
    if (items.length === 0) {
      return null;
    }

    return {
      items,
      total: readNumber(record, ['total', 'count']) || items.length,
      page,
      page_size: pageSize,
    } as StaffReviewFallbackPayload;
  }

  if (upstreamPath === '/api/staff/review/stats') {
    const payload = await postJsonIfOk(invokeUrl, requestHeaders, { action: 'stats' });
    const record = toRecord(payload);
    const stats = toRecord(record?.stats);
    if (!stats) {
      return null;
    }

    return {
      pending: readNumber(stats, ['pending', 'pending_review']) || 0,
      approved_today: readNumber(stats, ['approved_today', 'approved']) || 0,
      rejected_today: readNumber(stats, ['rejected_today', 'rejected']) || 0,
      avg_confidence: readNumber(stats, ['avg_confidence']) || 0,
    };
  }

  const auditMatch = upstreamPath.match(/^\/api\/staff\/review\/([^/]+)\/audit$/);
  if (auditMatch) {
    const entityId = decodeURIComponent(auditMatch[1]);
    const payload = await postJsonIfOk(invokeUrl, requestHeaders, {
      action: 'audit',
      entity_id: entityId,
    });
    const record = toRecord(payload);
    const events = toArray(record?.events);
    if (events.length === 0) {
      return null;
    }
    return events as StaffReviewFallbackPayload;
  }

  const detailMatch = upstreamPath.match(/^\/api\/staff\/review\/([^/]+)$/);
  if (detailMatch && detailMatch[1] !== 'stats' && detailMatch[1] !== 'proposals') {
    const entityId = decodeURIComponent(detailMatch[1]);
    const payload = await postJsonIfOk(invokeUrl, requestHeaders, {
      action: 'detail',
      entity_id: entityId,
    });
    const record = toRecord(payload);
    if (!record) {
      return null;
    }

    return {
      entity_id: readString(record, ['entity_id']) || entityId,
      product_title: readString(record, ['product_title']) || entityId,
      category: readString(record, ['category']) || 'Unknown',
      completeness_score: readNumber(record, ['completeness_score']) || 0,
      proposed_attributes: toArray(record.proposed_attributes),
    };
  }

  return null;
}

function mapReviewStatusToEnrichmentStatus(status: string | null): 'pending' | 'approved' | 'rejected' | 'queued' | 'running' | 'completed' | 'failed' {
  if (!status) {
    return 'pending';
  }

  const normalized = status.toLowerCase();
  if (normalized.includes('approved')) {
    return 'approved';
  }
  if (normalized.includes('reject')) {
    return 'rejected';
  }
  if (normalized.includes('running')) {
    return 'running';
  }
  if (normalized.includes('complete')) {
    return 'completed';
  }
  if (normalized.includes('fail')) {
    return 'failed';
  }
  if (normalized.includes('queue')) {
    return 'queued';
  }

  return 'pending';
}

async function buildEnrichmentMonitorSecondaryPayload(
  upstreamPath: string,
  {
    baseUrl,
    requestHeaders,
  }: {
    baseUrl: string | null;
    requestHeaders: Headers;
  },
): Promise<EnrichmentMonitorFallbackPayload | null> {
  if (!baseUrl) {
    return null;
  }

  const reviewBaseUrl = `${baseUrl}/agents/truth-hitl/review`;

  if (upstreamPath === '/api/admin/enrichment-monitor') {
    const [queuePayload, statsPayload] = await Promise.all([
      getJsonIfOk(`${reviewBaseUrl}/queue?skip=0&limit=50`, requestHeaders),
      getJsonIfOk(`${reviewBaseUrl}/stats`, requestHeaders),
    ]);

    const queueRecord = toRecord(queuePayload);
    const statsRecord = toRecord(statsPayload);
    const stats = toRecord(statsRecord?.stats) ?? statsRecord;
    const queueItems = toArray(queueRecord?.items)
      .map((item) => toRecord(item))
      .filter((item): item is Record<string, unknown> => item !== null);

    const pendingReview = readNumber(stats, ['pending_review', 'pending']) || 0;
    const approved = readNumber(stats, ['approved']) || 0;
    const rejected = readNumber(stats, ['rejected']) || 0;

    if (queueItems.length === 0 && pendingReview === 0 && approved === 0 && rejected === 0) {
      return null;
    }

    const generatedAt = new Date().toISOString();
    const activeJobs = queueItems.map((item, index) => {
      const status = mapReviewStatusToEnrichmentStatus(readString(item, ['status']));
      return {
        id: readString(item, ['id', 'attr_id']) || `job-${index + 1}`,
        entity_id: readString(item, ['entity_id']) || 'unknown-entity',
        status,
        source_type: readString(item, ['source_type', 'source']) || 'ai',
        confidence: readNumber(item, ['confidence']) || 0,
        updated_at: readString(item, ['proposed_at', 'updated_at']) || generatedAt,
      };
    });

    return {
      status_cards: [
        { label: 'Pending review', value: pendingReview || activeJobs.length },
        { label: 'Approved', value: approved },
        { label: 'Rejected', value: rejected },
        { label: 'Active jobs', value: activeJobs.length },
      ],
      active_jobs: activeJobs,
      error_log: [],
      throughput: {
        per_minute: activeJobs.length,
        last_10m: activeJobs.length,
        failed_last_10m: 0,
      },
    };
  }

  const detailMatch = upstreamPath.match(/^\/api\/admin\/enrichment-monitor\/([^/]+)$/);
  if (detailMatch && detailMatch[1]) {
    const entityId = decodeURIComponent(detailMatch[1]);
    const detailPayload = await getJsonIfOk(`${reviewBaseUrl}/${encodeURIComponent(entityId)}`, requestHeaders);
    const detail = toRecord(detailPayload);
    if (!detail) {
      return null;
    }

    const proposals = toArray(detail.proposed_attributes ?? detail.items)
      .map((item) => toRecord(item))
      .filter((item): item is Record<string, unknown> => item !== null);

    const averageConfidence = proposals.length > 0
      ? proposals.reduce((sum, item) => sum + (readNumber(item, ['confidence']) || 0), 0) / proposals.length
      : 0;

    const diffs = proposals.map((item) => ({
      field_name: readString(item, ['field_name']) || 'unknown_field',
      original_value: readString(item, ['current_value']),
      enriched_value: readString(item, ['proposed_value']) || '',
      confidence: readNumber(item, ['confidence']) || 0,
      source_type: readString(item, ['source_type', 'source']) || 'ai',
      reasoning: readString(item, ['reasoning']) || undefined,
    }));

    return {
      entity_id: readString(detail, ['entity_id']) || entityId,
      title: readString(detail, ['product_title']) || entityId,
      status: diffs.length > 0 ? 'pending' : 'unknown',
      confidence: Number(averageConfidence.toFixed(3)),
      source_assets: [],
      image_evidence: [],
      attribute_diffs: diffs,
      diffs,
      reasoning: '',
      trace_id: null,
    };
  }

  return null;
}

function buildStaffReviewFallbackPayload(
  upstreamPath: string,
  query: URLSearchParams,
): StaffReviewFallbackPayload | null {
  if (upstreamPath === '/api/staff/review') {
    return {
      items: [],
      total: 0,
      page: parsePositiveInt(query.get('page'), 1),
      page_size: parsePositiveInt(query.get('page_size'), 20),
    };
  }

  if (upstreamPath === '/api/staff/review/stats') {
    return {
      pending: 0,
      approved_today: 0,
      rejected_today: 0,
      avg_confidence: 0,
    };
  }

  const auditMatch = upstreamPath.match(/^\/api\/staff\/review\/([^/]+)\/audit$/);
  if (auditMatch) {
    return [];
  }

  const detailMatch = upstreamPath.match(/^\/api\/staff\/review\/([^/]+)$/);
  if (detailMatch && detailMatch[1] !== 'stats') {
    const entityId = decodeURIComponent(detailMatch[1]);
    return {
      entity_id: entityId,
      product_title: entityId,
      category: 'Unknown',
      completeness_score: 0,
      proposed_attributes: [],
    };
  }

  return null;
}

function buildAgentActivityFallbackPayload(upstreamPath: string): AgentActivityFallbackPayload | null {
  if (!isAgentActivityRoute(upstreamPath)) {
    return null;
  }

  const timestamp = new Date().toISOString();

  if (upstreamPath === '/api/admin/agent-activity' || upstreamPath === '/api/admin/agent-activity/health') {
    return {
      tracing_enabled: false,
      generated_at: timestamp,
      health_cards: [],
      trace_feed: [],
      model_usage: [],
    };
  }

  if (upstreamPath === '/api/admin/agent-activity/evaluations') {
    return {
      tracing_enabled: false,
      generated_at: timestamp,
      summary: {
        overall_score: 0,
        pass_rate: 0,
        total_runs: 0,
      },
      trends: [],
      comparison: [],
    };
  }

  if (upstreamPath.startsWith('/api/admin/agent-activity/traces/')) {
    const traceId = decodeURIComponent(upstreamPath.split('/').pop() || 'unknown-trace');
    return {
      tracing_enabled: false,
      trace_id: traceId,
      root_agent_name: 'unavailable',
      status: 'unknown',
      started_at: timestamp,
      duration_ms: 0,
      spans: [],
    };
  }

  return null;
}

async function proxyRequest(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
): Promise<NextResponse> {
  const params = await context.params;
  const { targetUrl, baseUrl, sourceKey, upstreamPath, policyViolation } = buildTargetUrl(request, params.path);
  const method = request.method.toUpperCase();

  if (!targetUrl) {
    const failureKind: ProxyFailureKind = policyViolation === 'non-apim' ? 'policy' : 'config';

    return NextResponse.json(
      buildProxyErrorPayload({
        failureKind,
        sourceKey,
        baseUrl,
        attemptedPath: upstreamPath,
        method,
      }),
      {
        status: 502,
        headers: {
          'x-holiday-peak-proxy': 'next-app-api',
          'x-holiday-peak-proxy-failure-kind': failureKind,
        },
      },
    );
  }

  const requestHeaders = new Headers(request.headers);
  requestHeaders.delete('host');
  requestHeaders.delete('content-length');

  const body = method === 'GET' || method === 'HEAD' ? undefined : await request.arrayBuffer();

  let upstream: Response;

  try {
    upstream = await fetch(targetUrl, {
      method,
      headers: requestHeaders,
      body,
      redirect: 'manual',
      cache: 'no-store',
    });
  } catch (error) {
    if (error instanceof Error) {
      console.error('API proxy upstream fetch failed', {
        attemptedPath: upstreamPath,
        sourceKey,
        message: error.message,
      });
    }
    return NextResponse.json(
      buildProxyErrorPayload({
        failureKind: 'network',
        sourceKey,
        baseUrl,
        attemptedPath: upstreamPath,
        method,
        upstreamError: error instanceof Error ? error.message : null,
      }),
      {
        status: 502,
        headers: {
          'x-holiday-peak-proxy': 'next-app-api',
          'x-holiday-peak-proxy-source': sourceKey ?? '',
          'x-holiday-peak-proxy-failure-kind': 'network',
        },
      },
    );
  }

  const shouldFallbackAgentActivity =
    method === 'GET'
    && isAgentActivityRoute(upstreamPath)
    && (upstream.status === 404 || upstream.status >= 500);

  const adminServiceRoute = resolveAdminServiceRoute(upstreamPath);
  const shouldFallbackAdminService =
    method === 'GET'
    && adminServiceRoute !== null
    && (upstream.status === 404 || upstream.status >= 500);

  const shouldFallbackStaffReview =
    method === 'GET'
    && isStaffReviewRoute(upstreamPath)
    && (upstream.status === 404 || upstream.status >= 500);

  const shouldFallbackEnrichmentMonitor =
    method === 'GET'
    && isEnrichmentMonitorRoute(upstreamPath)
    && (upstream.status === 404 || upstream.status >= 500);

  if (shouldFallbackAdminService && adminServiceRoute) {
    const payload = await buildAdminServiceSecondaryPayload({
      route: adminServiceRoute,
      baseUrl,
      requestHeaders,
    });

    return NextResponse.json(payload, {
      status: 200,
      headers: {
        'x-holiday-peak-proxy': 'next-app-api',
        'x-holiday-peak-proxy-source': sourceKey ?? '',
        'x-holiday-peak-proxy-fallback': payload.activity.length > 0 ? 'admin-service-live-aggregate' : 'admin-service-empty',
        'x-holiday-peak-proxy-fallback-upstream-status': String(upstream.status),
      },
    });
  }

  if (shouldFallbackAgentActivity) {
    const secondaryPayload = await buildAgentActivitySecondaryPayload({
      upstreamPath,
      baseUrl,
      requestHeaders,
    });

    if (secondaryPayload) {
      return NextResponse.json(secondaryPayload, {
        status: 200,
        headers: {
          'x-holiday-peak-proxy': 'next-app-api',
          'x-holiday-peak-proxy-source': sourceKey ?? '',
          'x-holiday-peak-proxy-fallback': 'agent-activity-live-aggregate',
          'x-holiday-peak-proxy-fallback-upstream-status': String(upstream.status),
        },
      });
    }

    const staticFallbackPayload = buildAgentActivityFallbackPayload(upstreamPath);
    if (staticFallbackPayload) {
      return NextResponse.json(staticFallbackPayload, {
        status: 200,
        headers: {
          'x-holiday-peak-proxy': 'next-app-api',
          'x-holiday-peak-proxy-source': sourceKey ?? '',
          'x-holiday-peak-proxy-fallback': 'agent-activity-unavailable',
          'x-holiday-peak-proxy-fallback-upstream-status': String(upstream.status),
        },
      });
    }
  }

  if (shouldFallbackStaffReview) {
    const secondaryPayload = await buildStaffReviewSecondaryPayload(
      upstreamPath,
      request.nextUrl.searchParams,
      {
        baseUrl,
        requestHeaders,
      },
    );
    if (secondaryPayload !== null) {
      return NextResponse.json(secondaryPayload, {
        status: 200,
        headers: {
          'x-holiday-peak-proxy': 'next-app-api',
          'x-holiday-peak-proxy-source': sourceKey ?? '',
          'x-holiday-peak-proxy-fallback': 'staff-review-live-aggregate',
          'x-holiday-peak-proxy-fallback-upstream-status': String(upstream.status),
        },
      });
    }

    const staticFallbackPayload = buildStaffReviewFallbackPayload(upstreamPath, request.nextUrl.searchParams);
    if (staticFallbackPayload !== null) {
      return NextResponse.json(staticFallbackPayload, {
        status: 200,
        headers: {
          'x-holiday-peak-proxy': 'next-app-api',
          'x-holiday-peak-proxy-source': sourceKey ?? '',
          'x-holiday-peak-proxy-fallback': 'staff-review-unavailable',
          'x-holiday-peak-proxy-fallback-upstream-status': String(upstream.status),
        },
      });
    }
  }

  if (shouldFallbackEnrichmentMonitor) {
    const secondaryPayload = await buildEnrichmentMonitorSecondaryPayload(upstreamPath, {
      baseUrl,
      requestHeaders,
    });

    if (secondaryPayload !== null) {
      return NextResponse.json(secondaryPayload, {
        status: 200,
        headers: {
          'x-holiday-peak-proxy': 'next-app-api',
          'x-holiday-peak-proxy-source': sourceKey ?? '',
          'x-holiday-peak-proxy-fallback': 'enrichment-monitor-live-aggregate',
          'x-holiday-peak-proxy-fallback-upstream-status': String(upstream.status),
        },
      });
    }
  }

  if (
    method === 'POST'
    && upstream.status === 404
    && upstreamPath.startsWith('/api/staff/review/proposals/')
  ) {
    return new NextResponse(null, {
      status: 202,
      headers: {
        'x-holiday-peak-proxy': 'next-app-api',
        'x-holiday-peak-proxy-source': sourceKey ?? '',
        'x-holiday-peak-proxy-fallback': 'staff-review-action-noop',
      },
    });
  }

  if (upstream.status === 502) {
    const upstreamError = await readUpstreamErrorPayload(upstream);
    const upstreamRequestId =
      upstream.headers.get('x-request-id') || upstream.headers.get('x-ms-request-id');

    return NextResponse.json(
      buildProxyErrorPayload({
        failureKind: 'upstream',
        sourceKey,
        baseUrl,
        attemptedPath: upstreamPath,
        method,
        upstreamStatus: upstream.status,
        upstreamStatusText: upstream.statusText,
        upstreamError,
        upstreamRequestId,
      }),
      {
        status: 502,
        headers: {
          'x-holiday-peak-proxy': 'next-app-api',
          'x-holiday-peak-proxy-source': sourceKey ?? '',
          'x-holiday-peak-proxy-failure-kind': 'upstream',
        },
      },
    );
  }

  const responseHeaders = new Headers(upstream.headers);
  responseHeaders.delete('transfer-encoding');
  responseHeaders.set('x-holiday-peak-proxy', 'next-app-api');
  if (sourceKey) {
    responseHeaders.set('x-holiday-peak-proxy-source', sourceKey);
  }

  return new NextResponse(upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: responseHeaders,
  });
}

export async function GET(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return proxyRequest(request, context);
}

export async function POST(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return proxyRequest(request, context);
}

export async function PUT(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return proxyRequest(request, context);
}

export async function PATCH(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return proxyRequest(request, context);
}

export async function DELETE(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return proxyRequest(request, context);
}
