'use client';

import { ReactNode, useEffect } from 'react';
import { usePageSession, setCurrentPageSessionId } from '@/lib/hooks/usePageSession';

/**
 * Syncs the page-scoped Foundry session ID with the global holder
 * consumed by the axios interceptor on `agentClient`.
 *
 * Must be rendered inside the client-side providers tree.
 */
export function PageSessionProvider({ children }: { children: ReactNode }) {
  const { sessionId } = usePageSession();

  useEffect(() => {
    setCurrentPageSessionId(sessionId);
    return () => {
      setCurrentPageSessionId(null);
    };
  }, [sessionId]);

  return <>{children}</>;
}
