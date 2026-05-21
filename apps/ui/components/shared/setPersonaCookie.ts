'use client';

import {
  PERSONA_COOKIE,
  PERSONA_COOKIE_MAX_AGE_SECONDS,
  type Persona,
} from '@/lib/persona/types';

/**
 * Set the persona cookie from the browser. Used by client-side handlers
 * (LaneSwitch click, audience-route CTA click).
 *
 * Per ADR-034: 90-day TTL, SameSite=Lax, Secure.
 */
export function setPersonaCookie(persona: Persona): void {
  if (typeof document === 'undefined') return;
  const secure = location.protocol === 'https:' ? '; Secure' : '';
  document.cookie =
    `${PERSONA_COOKIE}=${persona}; Max-Age=${PERSONA_COOKIE_MAX_AGE_SECONDS}; ` +
    `Path=/; SameSite=Lax${secure}`;
}
