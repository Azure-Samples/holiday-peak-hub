import { NextRequest, NextResponse } from 'next/server';

import { resolveAgentApiBaseUrl } from '../../api/_shared/base-url-resolver';

type TargetResolution = {
  targetUrl: string | null;
  baseUrl: string | null;
  sourceKey: string | null;
  upstreamPath: string;
};

function buildTargetUrl(request: NextRequest, pathSegments: string[]): TargetResolution {
  const { baseUrl, sourceKey } = resolveAgentApiBaseUrl();
  if (!baseUrl) {
    return {
      targetUrl: null,
      baseUrl: null,
      sourceKey,
      upstreamPath: '/agents',
    };
  }

  const joinedPath = pathSegments.filter(Boolean).join('/');
  const upstreamPath = joinedPath ? `/agents/${joinedPath}` : '/agents';
  const query = request.nextUrl.search;

  return {
    targetUrl: joinedPath ? `${baseUrl}/${joinedPath}${query}` : `${baseUrl}${query}`,
    baseUrl,
    sourceKey,
    upstreamPath,
  };
}

async function proxyRequest(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
): Promise<NextResponse> {
  const params = await context.params;
  const { targetUrl, baseUrl, sourceKey, upstreamPath } = buildTargetUrl(request, params.path);

  if (!targetUrl) {
    return NextResponse.json(
      {
        error:
          'Agent API proxy is not configured. Set NEXT_PUBLIC_AGENT_API_URL or AGENT_API_URL (fallbacks: NEXT_PUBLIC_CRUD_API_URL, NEXT_PUBLIC_API_URL, CRUD_API_URL).',
        proxy: {
          sourceKey,
          attemptedPath: upstreamPath,
        },
      },
      { status: 500 },
    );
  }

  const requestHeaders = new Headers(request.headers);
  requestHeaders.delete('host');
  requestHeaders.delete('content-length');

  const method = request.method.toUpperCase();
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
      {
        error: 'Agent API proxy could not reach upstream service.',
        proxy: {
          sourceKey,
          baseUrl,
          attemptedPath: upstreamPath,
        },
      },
      { status: 502 },
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
