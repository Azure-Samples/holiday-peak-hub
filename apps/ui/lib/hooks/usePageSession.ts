'use client';

import { useEffect, useRef, useState } from 'react';
import { usePathname } from 'next/navigation';

/**
 * Generates a stable Foundry thread session ID scoped to the current
 * page route.  While the user stays on the same pathname (e.g.
 * `/admin/ecommerce/catalog`) the session ID remains constant, enabling
 * the backend to resume the same Foundry conversation thread.
 *
 * Navigating to a different route creates a new session ID automatically,
 * mirroring how M365 Copilot ties threads to the active surface.
 *
 * Session IDs are stored in `sessionStorage` keyed by pathname so that
 * a hard refresh on the same page reuses the thread.
 */

const SESSION_STORAGE_PREFIX = 'hp.foundry.page_session';

function buildStorageKey(pathname: string): string {
  return `${SESSION_STORAGE_PREFIX}:${pathname}`;
}

function generateSessionId(): string {
  return crypto.randomUUID();
}

function readOrCreatePageSessionId(pathname: string): string {
  if (typeof window === 'undefined') {
    return generateSessionId();
  }

  const key = buildStorageKey(pathname);
  try {
    const existing = window.sessionStorage.getItem(key);
    if (existing && existing.trim().length > 0) {
      return existing;
    }
  } catch {
    // sessionStorage may be unavailable in restricted environments.
  }

  const created = generateSessionId();
  try {
    window.sessionStorage.setItem(key, created);
  } catch {
    // Best-effort persist.
  }
  return created;
}

export interface PageSession {
  /** Stable session ID for the current page route. */
  sessionId: string;
  /** Current pathname used to scope the session. */
  pathname: string;
  /** Reset the session for the current route (starts a new thread). */
  reset: () => void;
}

export function usePageSession(): PageSession {
  const pathname = usePathname();
  const [sessionId, setSessionId] = useState(() => readOrCreatePageSessionId(pathname));
  const prevPathnameRef = useRef(pathname);

  useEffect(() => {
    if (pathname !== prevPathnameRef.current) {
      prevPathnameRef.current = pathname;
      setSessionId(readOrCreatePageSessionId(pathname));
    }
  }, [pathname]);

  const reset = () => {
    const key = buildStorageKey(pathname);
    try {
      window.sessionStorage.removeItem(key);
    } catch {
      // Best-effort.
    }
    const newId = generateSessionId();
    try {
      window.sessionStorage.setItem(key, newId);
    } catch {
      // Best-effort.
    }
    setSessionId(newId);
  };

  return { sessionId, pathname, reset };
}

/**
 * Global page-session holder for non-hook contexts (e.g. axios interceptors).
 *
 * The `PageSessionProvider` component (rendered at the layout level) keeps
 * this in sync.  Consumers that cannot use hooks read from here.
 */
let _currentPageSessionId: string | null = null;

export function setCurrentPageSessionId(id: string | null): void {
  _currentPageSessionId = id;
}

export function getCurrentPageSessionId(): string | null {
  return _currentPageSessionId;
}
