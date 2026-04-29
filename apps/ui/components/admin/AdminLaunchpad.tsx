'use client';

import Link from 'next/link';
import { FiActivity, FiArrowRight, FiLayers, FiLifeBuoy, FiSettings, FiShield, FiTerminal } from 'react-icons/fi';
import { Badge } from '@/components/atoms/Badge';
import { Card } from '@/components/molecules/Card';
import { AgentFrieze } from '@/components/demo/AgentFrieze';
import { AgentRobot } from '@/components/organisms/AgentRobot';
import { MainLayout } from '@/components/templates/MainLayout';
import { AGENT_PROFILE_LIST } from '@/lib/agents/profiles';
import type { AgentProfileDomain, AgentProfileSlug } from '@/lib/agents/profiles';
import { useFleetSummary } from '@/lib/hooks/useFleetSummary';

const ADMIN_ROUTE_BY_AGENT: Record<AgentProfileSlug, string> = {
  'crm-campaign-intelligence': '/admin/crm/campaigns',
  'crm-profile-aggregation': '/admin/crm/profiles',
  'crm-segmentation-personalization': '/admin/crm/segmentation',
  'crm-support-assistance': '/admin/crm/support',
  'ecommerce-catalog-search': '/admin/ecommerce/catalog',
  'ecommerce-cart-intelligence': '/admin/ecommerce/cart',
  'ecommerce-checkout-support': '/admin/ecommerce/checkout',
  'ecommerce-order-status': '/admin/ecommerce/orders',
  'ecommerce-product-detail-enrichment': '/admin/ecommerce/products',
  'inventory-health-check': '/admin/inventory/health',
  'inventory-alerts-triggers': '/admin/inventory/alerts',
  'inventory-jit-replenishment': '/admin/inventory/replenishment',
  'inventory-reservation-validation': '/admin/inventory/reservation',
  'logistics-carrier-selection': '/admin/logistics/carriers',
  'logistics-eta-computation': '/admin/logistics/eta',
  'logistics-returns-support': '/admin/logistics/returns',
  'logistics-route-issue-detection': '/admin/logistics/routes',
  'product-management-acp-transformation': '/admin/products/acp',
  'product-management-assortment-optimization': '/admin/products/assortment',
  'product-management-consistency-validation': '/admin/products/validation',
  'product-management-normalization-classification': '/admin/products/normalization',
  'search-enrichment-agent': '/admin/ecommerce/catalog',
  'truth-ingestion': '/admin/enrichment-monitor',
  'truth-enrichment': '/admin/truth-analytics',
  'truth-hitl': '/staff/review',
  'truth-export': '/admin/workflows',
};

const DOMAIN_PRIMARY_ROUTE: Record<AgentProfileDomain, string> = {
  crm: '/admin/crm/campaigns',
  ecommerce: '/admin/ecommerce/catalog',
  inventory: '/admin/inventory/health',
  logistics: '/admin/logistics/eta',
  'product-management': '/admin/products/assortment',
  search: '/admin/ecommerce/catalog',
  'truth-layer': '/admin/truth-analytics',
};

const OPERATOR_LINKS = [
  { href: '/admin/agent-activity', label: 'Runs & traces', icon: FiActivity },
  { href: '/admin/truth-analytics', label: 'Truth analytics', icon: FiLayers },
  { href: '/admin/enrichment-monitor', label: 'Enrichment monitor', icon: FiShield },
  { href: '/admin/workflows', label: 'Workflow orchestration', icon: FiTerminal },
  { href: '/admin/config', label: 'Tenant config', icon: FiSettings },
  { href: '/staff/review', label: 'HITL review queue', icon: FiLifeBuoy },
];

function formatPercent(value: number): string {
  return `${value.toFixed(1)}%`;
}

function formatTimestamp(value: string | null): string {
  if (!value) {
    return 'Awaiting monitor data';
  }

  return new Date(value).toLocaleString();
}

export function AdminLaunchpad() {
  const { fleetSummary, isLoading, isFetching, isError } = useFleetSummary('24h');

  const representativeRoutes = Object.fromEntries(
    AGENT_PROFILE_LIST.map((profile) => [profile.slug, ADMIN_ROUTE_BY_AGENT[profile.slug]]),
  ) as Record<AgentProfileSlug, string>;

  return (
    <MainLayout>
      <div className="mx-auto max-w-7xl space-y-8 px-4 md:px-8">
        <section className="overflow-hidden rounded-[2rem] border border-[var(--hp-border)] bg-[radial-gradient(circle_at_top_left,rgba(240,120,88,0.18),transparent_36%),radial-gradient(circle_at_88%_18%,rgba(76,201,187,0.22),transparent_26%),var(--hp-surface)] shadow-[var(--hp-shadow-lg)]">
          <div className="grid gap-6 px-6 py-8 lg:grid-cols-[1.35fr_0.95fr] lg:px-8 lg:py-10">
            <div className="space-y-6">
              <div className="space-y-3">
                <Badge size="sm" variant="glass">Fleet panorama</Badge>
                <div className="space-y-2">
                  <h1 className="max-w-3xl text-4xl font-black tracking-tight text-[var(--hp-text)] md:text-5xl">
                    One cockpit for the full retail agent fleet.
                  </h1>
                  <p className="max-w-2xl text-sm leading-6 text-[var(--hp-text-muted)] md:text-base">
                    The launchpad tracks live service health, directs operators to the right surface, and keeps the active incident in view before the board asks for it.
                  </p>
                </div>
              </div>

              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                <MetricTile label="Active services" value={String(fleetSummary.activeServices)} />
                <MetricTile label="Availability" value={formatPercent(fleetSummary.availabilityPct)} />
                <MetricTile label="Avg latency" value={`${fleetSummary.avgLatencyMs} ms`} />
                <MetricTile label="Open incidents" value={String(fleetSummary.openIncidents)} />
              </div>

              <div className="flex flex-wrap items-center gap-3">
                <Link href="/admin/agent-activity" className="inline-flex items-center justify-center gap-2 rounded-xl bg-[var(--hp-primary)] px-4 py-2.5 text-sm font-semibold text-white shadow-[var(--hp-shadow-sm)] transition-all hover:-translate-y-px hover:shadow-[var(--hp-shadow-md)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--hp-primary)] focus-visible:ring-offset-2">
                  <span>Open runs & traces</span>
                  <FiArrowRight className="h-4 w-4" />
                </Link>
                <Link href="/admin/truth-analytics" className="inline-flex items-center justify-center rounded-xl border border-[var(--hp-border)] bg-[var(--hp-surface)] px-4 py-2.5 text-sm font-semibold text-[var(--hp-text)] shadow-[var(--hp-shadow-sm)] transition-colors hover:bg-[var(--hp-surface-strong)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--hp-focus)] focus-visible:ring-offset-2">
                  Open truth analytics
                </Link>
                <p className="text-xs text-[var(--hp-text-muted)]" aria-live="polite">
                  Updated {formatTimestamp(fleetSummary.updatedAt)}{isFetching && !isLoading ? ' · refreshing' : ''}
                </p>
              </div>
            </div>

            <div className="grid gap-4 lg:grid-rows-[auto_1fr]">
              <Card variant="glass" className="overflow-hidden border-[var(--hp-glass-border)]/70" padding="md">
                <div className="flex items-start justify-between gap-4">
                  <div className="space-y-2">
                    <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[var(--hp-text-muted)]">
                      Broadcast incident
                    </p>
                    {fleetSummary.topIncident ? (
                      <>
                        <h2 className="text-lg font-bold text-[var(--hp-text)]">{fleetSummary.topIncident.label}</h2>
                        <p className="text-sm text-[var(--hp-text-muted)]">
                          {fleetSummary.topIncident.status} · {Math.round(fleetSummary.topIncident.errorRate * 100)}% error rate · {fleetSummary.topIncident.latencyMs} ms latency
                        </p>
                        <Link href={ADMIN_ROUTE_BY_AGENT[fleetSummary.topIncident.slug]} className="inline-flex items-center gap-2 text-sm font-semibold text-[var(--hp-primary)]">
                          Open affected cockpit <FiArrowRight className="h-4 w-4" />
                        </Link>
                      </>
                    ) : (
                      <p className="text-sm text-[var(--hp-text-muted)]">
                        No degraded or down services in the current window.
                      </p>
                    )}
                  </div>
                  <Badge variant={fleetSummary.topIncident ? 'warning' : 'success'} size="sm">
                    {fleetSummary.topIncident ? 'Watchlist' : 'Stable'}
                  </Badge>
                </div>
              </Card>

              <Card variant="glass" className="border-[var(--hp-glass-border)]/70" padding="md">
                <div className="flex h-full flex-col justify-between gap-4 lg:flex-row lg:items-end">
                  <div className="max-w-sm space-y-2">
                    <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[var(--hp-text-muted)]">
                      Operator presenter
                    </p>
                    <p className="text-sm leading-6 text-[var(--hp-text-muted)]">
                      Keep the active narrative in one place: {fleetSummary.traceCount} traces collected, {fleetSummary.totalThroughputRpm} rpm flowing across the fleet, and every service already linked to its cockpit.
                    </p>
                    {isError && (
                      <p className="text-sm text-[var(--hp-error)]">
                        The fleet monitor is currently unavailable. Core admin routes remain accessible from the operator lanes.
                      </p>
                    )}
                  </div>
                  <div className="self-center lg:self-end">
                    <AgentRobot agentSlug="truth-enrichment" size={168} state={fleetSummary.openIncidents > 0 ? 'using-tool' : 'talking'} sticky={false} skipEntrance toolOverride={fleetSummary.openIncidents > 0 ? '🛠️' : '📡'} />
                  </div>
                </div>
              </Card>
            </div>
          </div>
        </section>

        <section className="space-y-4" aria-labelledby="fleet-frieze-heading">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h2 id="fleet-frieze-heading" className="text-xl font-bold text-[var(--hp-text)]">All 26 agents</h2>
              <p className="text-sm text-[var(--hp-text-muted)]">A single horizontal panorama so operators can scan the entire cast before drilling into a domain.</p>
            </div>
            <Badge variant={isError ? 'danger' : 'glass'} size="sm">
              {isError ? 'Tracing unavailable' : 'Live fleet status'}
            </Badge>
          </div>
          <AgentFrieze healthBySlug={fleetSummary.healthBySlug} hrefBySlug={representativeRoutes} />
        </section>

        <section className="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]" aria-labelledby="fleet-domains-heading">
          <div className="space-y-4">
            <div>
              <h2 id="fleet-domains-heading" className="text-xl font-bold text-[var(--hp-text)]">Domain lanes</h2>
              <p className="text-sm text-[var(--hp-text-muted)]">Each lane groups the agents that collaborate in production and links to the primary cockpit for that motion.</p>
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              {fleetSummary.domains.map((domain) => (
                <Link key={domain.domain} href={DOMAIN_PRIMARY_ROUTE[domain.domain]}>
                  <Card variant="elevated" hoverable className="h-full">
                    <div className="space-y-3">
                      <div className="flex items-center justify-between gap-3">
                        <div>
                          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[var(--hp-text-muted)]">{domain.domain}</p>
                          <h3 className="text-lg font-bold text-[var(--hp-text)]">{domain.label}</h3>
                        </div>
                        <Badge variant={domain.incidentCount > 0 ? 'warning' : 'success'} size="xs">
                          {domain.incidentCount > 0 ? `${domain.incidentCount} incident${domain.incidentCount === 1 ? '' : 's'}` : 'Clear'}
                        </Badge>
                      </div>
                      <div className="grid grid-cols-3 gap-3 text-sm">
                        <div>
                          <p className="text-[11px] uppercase tracking-[0.2em] text-[var(--hp-text-muted)]">Agents</p>
                          <p className="mt-1 text-xl font-bold text-[var(--hp-text)]">{domain.totalAgents}</p>
                        </div>
                        <div>
                          <p className="text-[11px] uppercase tracking-[0.2em] text-[var(--hp-text-muted)]">Healthy</p>
                          <p className="mt-1 text-xl font-bold text-[var(--hp-text)]">{domain.healthyAgents}</p>
                        </div>
                        <div>
                          <p className="text-[11px] uppercase tracking-[0.2em] text-[var(--hp-text-muted)]">Latency</p>
                          <p className="mt-1 text-xl font-bold text-[var(--hp-text)]">{domain.avgLatencyMs} ms</p>
                        </div>
                      </div>
                    </div>
                  </Card>
                </Link>
              ))}
            </div>
          </div>

          <Card variant="outlined" title="Operator lanes" subtitle="Cross-cutting control surfaces that stay outside any single service cockpit.">
            <div className="grid gap-3">
              {OPERATOR_LINKS.map((link) => {
                const Icon = link.icon;
                return (
                  <Link key={link.href} href={link.href} className="flex items-center justify-between rounded-2xl border border-[var(--hp-border)] bg-[var(--hp-surface-strong)] px-4 py-3 transition-colors hover:bg-[var(--hp-surface)]">
                    <span className="flex items-center gap-3 text-sm font-semibold text-[var(--hp-text)]">
                      <span className="rounded-xl bg-[var(--hp-surface)] p-2 text-[var(--hp-primary)]"><Icon className="h-4 w-4" /></span>
                      {link.label}
                    </span>
                    <FiArrowRight className="h-4 w-4 text-[var(--hp-text-muted)]" />
                  </Link>
                );
              })}
            </div>
          </Card>
        </section>
      </div>
    </MainLayout>
  );
}

function MetricTile({ label, value }: { label: string; value: string }) {
  return (
    <Card variant="glass" padding="sm" className="border-[var(--hp-glass-border)]/70">
      <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[var(--hp-text-muted)]">{label}</p>
      <p className="mt-2 text-3xl font-black tracking-tight text-[var(--hp-text)]">{value}</p>
    </Card>
  );
}