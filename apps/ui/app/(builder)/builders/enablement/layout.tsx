import { headers } from 'next/headers';
import { redirect } from 'next/navigation';
import type { ReactNode } from 'react';

import { decodeSwaPrincipal, evaluateGate, logAccess } from '@/lib/enablement/gate';

/**
 * `/builders/enablement/*` server-side gate (Issue #1051 / Epic #1053).
 *
 * The layout runs on the server; it reads the SWA `x-ms-client-principal`
 * header, evaluates the tenant + group gate, writes an audit log line, and
 * redirects to `/builders/architecture` when the gate denies.
 *
 * IMPORTANT: server-side enforcement only. There is NO client-side guard;
 * adding one would be cosmetic.
 *
 * Configuration: see `apps/ui/lib/enablement/gate.ts`.
 */
export default async function EnablementLayout({
  children,
}: {
  children: ReactNode;
}) {
  const requestHeaders = await headers();
  const principal = decodeSwaPrincipal(
    requestHeaders.get('x-ms-client-principal'),
  );
  const result = evaluateGate(principal);
  const pathname = requestHeaders.get('x-pathname') ?? '/builders/enablement';

  if (!result.allowed) {
    logAccess('deny', result.reason, principal, pathname);
    redirect('/builders/architecture');
  }

  logAccess('allow', 'ok', principal, pathname);
  return <>{children}</>;
}
