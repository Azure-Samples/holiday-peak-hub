import { useMemo } from 'react';
import { AGENT_PROFILE_LIST } from '@/lib/agents/profiles';
import type { AgentProfileDomain, AgentProfileSlug } from '@/lib/agents/profiles';
import { useAgentMonitorDashboard } from '@/lib/hooks/useAgentMonitor';
import type { AgentHealthCardMetric, AgentMonitorTimeRange } from '@/lib/types/api';

export interface FleetDomainSummary {
  domain: AgentProfileDomain;
  label: string;
  totalAgents: number;
  healthyAgents: number;
  incidentCount: number;
  avgLatencyMs: number;
  representativeSlug: AgentProfileSlug;
}

export interface FleetIncidentSummary {
  slug: AgentProfileSlug;
  label: string;
  status: AgentHealthCardMetric['status'];
  latencyMs: number;
  errorRate: number;
  updatedAt: string;
}

export interface FleetSummaryPayload {
  activeServices: number;
  availabilityPct: number;
  avgLatencyMs: number;
  totalThroughputRpm: number;
  openIncidents: number;
  traceCount: number;
  updatedAt: string | null;
  domains: FleetDomainSummary[];
  topIncident: FleetIncidentSummary | null;
  healthBySlug: Partial<Record<AgentProfileSlug, AgentHealthCardMetric>>;
}

function average(values: readonly number[]): number {
  if (values.length === 0) {
    return 0;
  }

  return values.reduce((total, value) => total + value, 0) / values.length;
}

function buildFleetSummary(
  cards: readonly AgentHealthCardMetric[],
  traceCount: number,
): FleetSummaryPayload {
  const knownSlugs = new Set(AGENT_PROFILE_LIST.map((profile) => profile.slug));
  const healthBySlug = Object.fromEntries(
    cards
      .filter((card) => knownSlugs.has(card.id as AgentProfileSlug))
      .map((card) => [card.id, card]),
  ) as Partial<Record<AgentProfileSlug, AgentHealthCardMetric>>;

  const activeServices = cards.length;
  const healthyCount = cards.filter((card) => card.status === 'healthy').length;
  const degradedCount = cards.filter((card) => card.status === 'degraded').length;
  const downCount = cards.filter((card) => card.status === 'down').length;
  const totalThroughputRpm = cards.reduce((total, card) => total + card.throughput_rpm, 0);
  const availabilityPct =
    activeServices === 0 ? 0 : ((healthyCount + degradedCount) / activeServices) * 100;

  const domains = AGENT_PROFILE_LIST.reduce<Map<AgentProfileDomain, FleetDomainSummary>>((accumulator, profile) => {
    const current = accumulator.get(profile.domain) ?? {
      domain: profile.domain,
      label: profile.domainLabel,
      totalAgents: 0,
      healthyAgents: 0,
      incidentCount: 0,
      avgLatencyMs: 0,
      representativeSlug: profile.slug,
    };

    const card = healthBySlug[profile.slug];
    current.totalAgents += 1;
    current.healthyAgents += card?.status === 'healthy' ? 1 : 0;
    current.incidentCount += card && (card.status === 'degraded' || card.status === 'down') ? 1 : 0;
    current.avgLatencyMs += card?.latency_ms ?? 0;

    accumulator.set(profile.domain, current);
    return accumulator;
  }, new Map());

  const normalizedDomains = Array.from(domains.values()).map((domain) => ({
    ...domain,
    avgLatencyMs: domain.totalAgents > 0 ? Math.round(domain.avgLatencyMs / domain.totalAgents) : 0,
  }));

  const topIncidentCard = cards
    .filter((card) => card.status === 'degraded' || card.status === 'down')
    .sort((left, right) => {
      const severityWeight = (status: AgentHealthCardMetric['status']) => (status === 'down' ? 2 : 1);
      return (
        severityWeight(right.status) - severityWeight(left.status)
        || right.error_rate - left.error_rate
        || right.latency_ms - left.latency_ms
      );
    })[0];

  const topIncidentProfile = AGENT_PROFILE_LIST.find((profile) => profile.slug === topIncidentCard?.id);
  const topIncident = topIncidentCard && topIncidentProfile
    ? {
        slug: topIncidentProfile.slug,
        label: topIncidentProfile.displayName,
        status: topIncidentCard.status,
        latencyMs: topIncidentCard.latency_ms,
        errorRate: topIncidentCard.error_rate,
        updatedAt: topIncidentCard.updated_at,
      }
    : null;

  const updatedAt = cards
    .map((card) => card.updated_at)
    .sort()
    .at(-1) ?? null;

  return {
    activeServices,
    availabilityPct,
    avgLatencyMs: Math.round(average(cards.map((card) => card.latency_ms))),
    totalThroughputRpm,
    openIncidents: degradedCount + downCount,
    traceCount,
    updatedAt,
    domains: normalizedDomains,
    topIncident,
    healthBySlug,
  };
}

export function useFleetSummary(timeRange: AgentMonitorTimeRange = '24h') {
  const query = useAgentMonitorDashboard(timeRange);

  const fleetSummary = useMemo(
    () => buildFleetSummary(query.data?.health_cards ?? [], query.data?.trace_feed.length ?? 0),
    [query.data],
  );

  return {
    ...query,
    fleetSummary,
  };
}