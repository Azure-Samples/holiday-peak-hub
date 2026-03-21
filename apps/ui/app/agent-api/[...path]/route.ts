import { NextRequest, NextResponse } from 'next/server';

import { resolveAgentApiBaseUrl, validateProxyBaseUrlPolicy } from '../../api/_shared/base-url-resolver';

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

function buildTargetUrl(request: NextRequest, pathSegments: string[]): TargetResolution {
  const joinedPath = pathSegments.filter(Boolean).join('/');
  const upstreamPath = joinedPath ? `/agents/${joinedPath}` : '/agents';
  const { baseUrl, sourceKey } = resolveAgentApiBaseUrl();
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
    targetUrl: joinedPath ? `${baseUrl}/${joinedPath}${query}` : `${baseUrl}${query}`,
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
      'Set NEXT_PUBLIC_AGENT_API_URL or AGENT_API_URL to the APIM gateway URL with /agents suffix.',
      'Redeploy or restart the UI host after updating environment variables.',
    ],
    policy: [
      'Use an APIM gateway URL (*.azure-api.net) for NEXT_PUBLIC_AGENT_API_URL or AGENT_API_URL.',
      'For local development only, use a loopback URL (http://localhost:*/agents) or set UI_ALLOW_NON_APIM_PROXY_URL=true.',
    ],
    network: [
      'Verify DNS, firewall rules, and outbound network access from the UI host to the agent backend URL.',
      'Check agent backend availability and retry the request.',
    ],
    upstream: [
      'Inspect upstream agent service logs for request failures and dependency outages.',
      'Retry after backend recovery or fail over to a healthy upstream instance.',
    ],
  };

  const errorByKind: Record<ProxyFailureKind, string> = {
    config: 'Agent API proxy is not configured for backend routing.',
    policy: 'Agent API proxy rejected a non-APIM upstream target URL.',
    network: 'Agent API proxy could not reach upstream service.',
    upstream: 'Agent API proxy received a bad gateway response from upstream.',
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
          'x-holiday-peak-proxy': 'next-app-agent-api',
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
      console.error('Agent API proxy upstream fetch failed', {
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
          'x-holiday-peak-proxy': 'next-app-agent-api',
          'x-holiday-peak-proxy-source': sourceKey ?? '',
          'x-holiday-peak-proxy-failure-kind': 'network',
        },
      },
    );
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
          'x-holiday-peak-proxy': 'next-app-agent-api',
          'x-holiday-peak-proxy-source': sourceKey ?? '',
          'x-holiday-peak-proxy-failure-kind': 'upstream',
        },
      },
    );
  }

  const responseHeaders = new Headers(upstream.headers);
  responseHeaders.delete('transfer-encoding');
  responseHeaders.set('x-holiday-peak-proxy', 'next-app-agent-api');
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
