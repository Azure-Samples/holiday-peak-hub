import { NextRequest, NextResponse } from 'next/server';

const AGENT_API_BASE_URL = process.env.NEXT_PUBLIC_AGENT_API_URL;
const CRUD_API_BASE_URL = process.env.NEXT_PUBLIC_CRUD_API_URL;

function getAgentBaseUrl(): string | null {
  if (AGENT_API_BASE_URL) {
    return AGENT_API_BASE_URL.replace(/\/+$/, '');
  }

  if (CRUD_API_BASE_URL) {
    return `${CRUD_API_BASE_URL.replace(/\/+$/, '')}/agents`;
  }

  return null;
}

function buildTargetUrl(request: NextRequest, pathSegments: string[]): string | null {
  const baseUrl = getAgentBaseUrl();
  if (!baseUrl) {
    return null;
  }

  const joinedPath = pathSegments.filter(Boolean).join('/');
  const query = request.nextUrl.search;
  return `${baseUrl}/${joinedPath}${query}`;
}

async function proxyRequest(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
): Promise<NextResponse> {
  const params = await context.params;
  const targetUrl = buildTargetUrl(request, params.path);

  if (!targetUrl) {
    return NextResponse.json(
      { error: 'NEXT_PUBLIC_AGENT_API_URL or NEXT_PUBLIC_CRUD_API_URL is not configured.' },
      { status: 500 },
    );
  }

  const requestHeaders = new Headers(request.headers);
  requestHeaders.delete('host');
  requestHeaders.delete('content-length');

  const method = request.method.toUpperCase();
  const body = method === 'GET' || method === 'HEAD' ? undefined : await request.arrayBuffer();

  const upstream = await fetch(targetUrl, {
    method,
    headers: requestHeaders,
    body,
    redirect: 'manual',
    cache: 'no-store',
  });

  const responseHeaders = new Headers(upstream.headers);
  responseHeaders.delete('transfer-encoding');

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
