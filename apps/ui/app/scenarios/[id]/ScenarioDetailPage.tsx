'use client';

import { useMemo, useState } from 'react';
import Link from 'next/link';
import { AgentProfileDrawer } from '@/components/demo/AgentProfileDrawer';
import { AgentRobot } from '@/components/organisms/AgentRobot';
import { AgentRobotOverlay } from '@/components/organisms/AgentRobotOverlay';
import { MainLayout } from '@/components/templates/MainLayout';
import { AGENT_PROFILES, type AgentProfileSlug } from '@/lib/agents/profiles';
import { SCENARIO_BY_ID, type ScenarioId } from '@/lib/demo/scenarios';
import { DEFAULT_AGENT_MONITOR_RANGE, useAgentMonitorDashboard } from '@/lib/hooks/useAgentMonitor';

function ScenarioAgentCard({
  slug,
  state,
  onOpen,
}: {
  slug: AgentProfileSlug;
  state: 'idle' | 'thinking' | 'using-tool' | 'talking';
  onOpen: (slug: AgentProfileSlug) => void;
}) {
  const profile = AGENT_PROFILES[slug];

  return (
    <button
      type="button"
      onClick={() => onOpen(slug)}
      className="rounded-[1.6rem] border border-white/10 bg-white/5 p-4 text-left transition hover:border-white/20 hover:bg-white/10"
      aria-label={`Open profile for ${profile.displayName}`}
    >
      <div className="flex items-start gap-4">
        <div className="rounded-[1.25rem] border border-white/10 bg-black/15 p-2">
          <AgentRobot
            agentSlug={slug}
            size={96}
            sticky={false}
            skipEntrance
            state={state}
          />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[var(--hp-text-faint)]">
            {profile.domainLabel}
          </p>
          <h2 className="mt-2 text-lg font-semibold text-white">{profile.displayName}</h2>
          <p className="mt-2 text-sm leading-7 text-[var(--hp-text-muted)]">{profile.oneLiner}</p>
        </div>
      </div>
    </button>
  );
}

export function ScenarioDetailPage({ scenarioId }: { scenarioId: ScenarioId }) {
  const scenario = SCENARIO_BY_ID[scenarioId];
  const leadProfile = AGENT_PROFILES[scenario.leadAgent];
  const [selectedAgentSlug, setSelectedAgentSlug] = useState<AgentProfileSlug | null>(null);
  const { data: monitorDashboard } = useAgentMonitorDashboard(DEFAULT_AGENT_MONITOR_RANGE);
  const selectedLiveMetrics = useMemo(() => {
    if (!selectedAgentSlug) {
      return null;
    }

    const healthCard = monitorDashboard?.health_cards.find((card) => card.id === selectedAgentSlug);
    if (!healthCard) {
      return null;
    }

    return {
      status: healthCard.status,
      latencyLabel: `${Math.round(healthCard.latency_ms)} ms`,
      throughputLabel: `${Math.round(healthCard.throughput_rpm)} rpm`,
      errorRateLabel: `${Math.round(healthCard.error_rate * 100)}% error rate`,
      costLabel: 'Awaiting model usage',
      tierMixLabel: 'Awaiting model mix',
      evaluationLabel: 'Awaiting evaluation data',
      kpiValues: {},
    };
  }, [monitorDashboard, selectedAgentSlug]);

  return (
    <MainLayout fullWidth>
      <div className="demo-stage min-h-[calc(100dvh-4.25rem)] px-6 py-10 md:px-10 lg:px-14">
        <div className="mx-auto max-w-6xl space-y-8">
          <nav className="flex flex-wrap items-center gap-2 text-sm text-[var(--hp-text-muted)]">
            <Link href="/" className="transition hover:text-white">
              Executive demo
            </Link>
            <span>/</span>
            <span className="text-white">{scenario.title}</span>
          </nav>

          <section className="grid gap-6 lg:grid-cols-[minmax(0,1.05fr)_minmax(19rem,0.95fr)] lg:items-center">
            <div className="space-y-6">
              <span className="inline-flex rounded-full border border-white/10 bg-white/5 px-4 py-1.5 text-[11px] font-semibold uppercase tracking-[0.28em] text-[var(--hp-text-faint)]">
                {scenario.eyebrow}
              </span>
              <h1 className="text-balance text-4xl font-semibold tracking-tight text-white md:text-5xl lg:text-6xl">
                {scenario.title}
              </h1>
              <p className="max-w-3xl text-base leading-8 text-[var(--hp-text-muted)] md:text-lg">
                {scenario.summary}
              </p>

              <div className="grid gap-3 sm:grid-cols-3">
                <article className="rounded-[1.4rem] border border-white/10 bg-white/5 p-4">
                  <p className="text-[11px] uppercase tracking-[0.24em] text-[var(--hp-text-faint)]">Hero metric</p>
                  <p className="mt-2 text-2xl font-semibold text-white">{scenario.metric}</p>
                </article>
                <article className="rounded-[1.4rem] border border-white/10 bg-white/5 p-4 sm:col-span-2">
                  <p className="text-[11px] uppercase tracking-[0.24em] text-[var(--hp-text-faint)]">Business outcome</p>
                  <p className="mt-2 text-sm leading-7 text-[var(--hp-text-muted)]">{scenario.outcome}</p>
                </article>
              </div>

              <div className="flex flex-wrap gap-3">
                <Link
                  href={scenario.liveSurfaceHref}
                  className="btn-primary inline-flex items-center rounded-full px-5 py-3 text-sm font-semibold"
                >
                  Open live surface
                </Link>
                <Link
                  href={scenario.operatorHref}
                  className="inline-flex items-center rounded-full border border-white/10 bg-white/5 px-5 py-3 text-sm font-semibold text-white transition hover:border-white/20 hover:bg-white/10"
                >
                  Open operator view
                </Link>
                <Link
                  href="/"
                  className="inline-flex items-center rounded-full border border-white/10 bg-black/15 px-5 py-3 text-sm font-semibold text-white transition hover:border-white/20 hover:bg-white/10"
                >
                  Back to demo
                </Link>
              </div>
            </div>

            <div className="demo-panel rounded-[2rem] border border-white/10 p-6">
              <div className="flex justify-center">
                <button
                  type="button"
                  onClick={() => setSelectedAgentSlug(scenario.leadAgent)}
                  className="rounded-[2rem] border border-white/10 bg-black/15 p-4 transition hover:border-white/20 hover:bg-black/20"
                  aria-label={`Open profile for ${leadProfile.displayName}`}
                >
                  <AgentRobot
                    agentSlug={scenario.leadAgent}
                    size={176}
                    sticky={false}
                    skipEntrance
                    state="talking"
                    thinkingMessage={leadProfile.oneLiner}
                  />
                </button>
              </div>

              <div className="mt-6 grid gap-3 sm:grid-cols-2">
                {scenario.supportingAgents.map((slug, index) => (
                  <ScenarioAgentCard
                    key={slug}
                    slug={slug}
                    state={index === 0 ? 'using-tool' : 'idle'}
                    onOpen={setSelectedAgentSlug}
                  />
                ))}
              </div>
            </div>
          </section>

          <section className="grid gap-6 lg:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)]">
            <article className="demo-panel rounded-[2rem] border border-white/10 p-6">
              <h2 className="text-2xl font-semibold text-white">What happens in this flow</h2>
              <ol className="mt-5 space-y-3">
                {scenario.storyBeats.map((beat, index) => (
                  <li
                    key={beat}
                    className="flex items-start gap-3 rounded-[1.3rem] border border-white/10 bg-black/15 px-4 py-4"
                  >
                    <span className="demo-telemetry mt-0.5 inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-white/10 bg-white/5 text-xs text-white">
                      {index + 1}
                    </span>
                    <p className="text-sm leading-7 text-[var(--hp-text-muted)]">{beat}</p>
                  </li>
                ))}
              </ol>
            </article>

            <article className="demo-panel rounded-[2rem] border border-white/10 p-6">
              <h2 className="text-2xl font-semibold text-white">Agent roster for this scenario</h2>
              <div className="mt-5 grid gap-3">
                {[scenario.leadAgent, ...scenario.supportingAgents].map((slug) => {
                  const profile = AGENT_PROFILES[slug];
                  return (
                    <button
                      key={slug}
                      type="button"
                      onClick={() => setSelectedAgentSlug(slug)}
                      className="rounded-[1.3rem] border border-white/10 bg-white/5 px-4 py-4 text-left transition hover:border-white/20 hover:bg-white/10"
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div>
                          <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[var(--hp-text-faint)]">
                            {profile.domainLabel}
                          </p>
                          <h3 className="mt-2 text-base font-semibold text-white">{profile.displayName}</h3>
                          <p className="mt-2 text-sm leading-7 text-[var(--hp-text-muted)]">{profile.fitFor[0]}</p>
                        </div>
                        <span className="demo-telemetry rounded-full border border-white/10 bg-black/15 px-3 py-1 text-xs text-white">
                          {profile.productivityGain.latency}
                        </span>
                      </div>
                    </button>
                  );
                })}
              </div>
            </article>
          </section>
        </div>
      </div>

      <AgentRobotOverlay
        agentSlug={scenario.leadAgent}
        state="idle"
        position="bottom-right"
        size="sm"
        visible
      />

      <AgentRobotOverlay
        agentSlug={scenario.supportingAgents[0]}
        state="using-tool"
        position="bottom-left"
        size="sm"
        visible={scenario.supportingAgents.length > 0}
        facing="right"
        scenePeer="left"
        className="hidden xl:block"
      />

      <AgentProfileDrawer
        open={Boolean(selectedAgentSlug)}
        profile={selectedAgentSlug ? AGENT_PROFILES[selectedAgentSlug] : null}
        liveMetrics={selectedLiveMetrics}
        onClose={() => setSelectedAgentSlug(null)}
      />
    </MainLayout>
  );
}

export default ScenarioDetailPage;