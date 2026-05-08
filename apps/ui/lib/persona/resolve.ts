import { cookies } from 'next/headers';

import {
  PERSONA_COOKIE,
  PERSONA_QUERY_PARAM,
  type Persona,
  resolvePersona,
} from './types';

/**
 * Resolve the effective persona from the current request, server-side.
 *
 * Reads the `persona` cookie via `next/headers` and respects the
 * `?as=retailer|builder` query-param override per ADR-034.
 *
 * Returns `null` when no persona is known. Callers MUST treat `null` as the
 * neutral default (e.g. retailer CTA renders first on `/`) — they MUST NOT
 * show "you are a retailer" copy when persona is `null` and they MUST NOT
 * gate content based on persona.
 */
export async function resolvePersonaFromRequest(
  searchParams: Record<string, string | string[] | undefined> | undefined,
): Promise<Persona | null> {
  const cookieStore = await cookies();
  const cookieValue = cookieStore.get(PERSONA_COOKIE)?.value;
  const queryRaw = searchParams?.[PERSONA_QUERY_PARAM];
  const queryValue = Array.isArray(queryRaw) ? queryRaw[0] : queryRaw;
  return resolvePersona(cookieValue, queryValue);
}
