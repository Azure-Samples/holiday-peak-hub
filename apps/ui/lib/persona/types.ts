/**
 * Persona type — used by LaneSwitch for soft persona
 * detection per ADR-034. Persona is a HINT, not a GATE.
 *
 * Only retailer / builder are personas. The deploy lane is procedural and
 * does not represent a long-lived audience identity.
 */
export type Persona = 'retailer' | 'builder';

/** Cookie name used by the soft persona detection per ADR-034. */
export const PERSONA_COOKIE = 'persona';

/** Cookie TTL: 90 days, per ADR-034. */
export const PERSONA_COOKIE_MAX_AGE_SECONDS = 60 * 60 * 24 * 90;

/** Query parameter override per ADR-034 ("?as=retailer|builder"). */
export const PERSONA_QUERY_PARAM = 'as';

export function isPersona(value: unknown): value is Persona {
  return value === 'retailer' || value === 'builder';
}

/**
 * Resolve the effective persona from a (possibly undefined) cookie value and
 * an optional query-param override. The query param wins for sharable links.
 */
export function resolvePersona(
  cookieValue: string | undefined,
  queryValue: string | undefined,
): Persona | null {
  if (isPersona(queryValue)) return queryValue;
  if (isPersona(cookieValue)) return cookieValue;
  return null;
}
