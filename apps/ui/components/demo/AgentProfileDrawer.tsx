'use client';

import React, { useEffect, useRef, useState } from 'react';
import { TraceWaterfall } from '@/components/admin/TraceWaterfall';
import { AgentRobot } from '@/components/organisms/AgentRobot';
import {
  DEFAULT_AGENT_MONITOR_RANGE,
  useAgentTraceDetail,
  useRecentTraces,
} from '@/lib/hooks/useAgentMonitor';
import type { AgentHealthStatus } from '@/lib/types/api';
import type { AgentProfile } from '@/lib/agents/profiles';
import { streamAgentInvocation } from '@/lib/services/agentStreamingService';

export interface AgentProfileLiveMetrics {
  status: AgentHealthStatus;
  latencyLabel: string;
  errorRateLabel: string;
  throughputLabel: string;
  costLabel: string;
  tierMixLabel: string;
  evaluationLabel: string;
  lastUpdatedLabel?: string;
  kpiValues: Record<string, string>;
}

export interface AgentProfileDrawerProps {
  open: boolean;
  profile: AgentProfile | null;
  liveMetrics: AgentProfileLiveMetrics | null;
  onClose: () => void;
}

type SampleRunStatus = 'idle' | 'running' | 'success' | 'error';

function statusTone(status: AgentHealthStatus): string {
  if (status === 'healthy') return 'bg-emerald-500';
  if (status === 'degraded') return 'bg-amber-400';
  if (status === 'down') return 'bg-rose-500';
  return 'bg-[var(--hp-text-faint)]';
}

export function AgentProfileDrawer({
  open,
  profile,
  liveMetrics,
  onClose,
}: AgentProfileDrawerProps) {
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const sampleAbortRef = useRef<AbortController | null>(null);
  const [sampleRunStatus, setSampleRunStatus] = useState<SampleRunStatus>('idle');
  const [sampleResponsePreview, setSampleResponsePreview] = useState<string[]>([]);
  const [sampleError, setSampleError] = useState<string | null>(null);
  const [traceExplorerOpen, setTraceExplorerOpen] = useState(false);
  const [selectedTraceId, setSelectedTraceId] = useState<string>('');
  const recentTracesQuery = useRecentTraces(profile?.slug, DEFAULT_AGENT_MONITOR_RANGE, 5, {
    enabled: open && Boolean(profile?.slug),
  });
  const { data: traceDetail, isLoading: isTraceDetailLoading } = useAgentTraceDetail(
    traceExplorerOpen ? selectedTraceId : '',
    DEFAULT_AGENT_MONITOR_RANGE,
  );
  const recentTraces = recentTracesQuery.data ?? [];

  useEffect(() => {
    if (!open || !profile) {
      return undefined;
    }

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    closeButtonRef.current?.focus();

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [open, profile, onClose]);

  useEffect(() => {
    if (!open || !profile) {
      sampleAbortRef.current?.abort();
      sampleAbortRef.current = null;
      setSampleRunStatus('idle');
      setSampleResponsePreview([]);
      setSampleError(null);
      setTraceExplorerOpen(false);
      setSelectedTraceId('');
    }
  }, [open, profile]);

  useEffect(() => {
    return () => {
      sampleAbortRef.current?.abort();
      sampleAbortRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (!selectedTraceId && recentTraces.length > 0) {
      setSelectedTraceId(recentTraces[0].trace_id);
    }
  }, [recentTraces, selectedTraceId]);

  if (!open || !profile) {
    return null;
  }

  const hasSamplePreview = sampleResponsePreview.some((line) => line.trim().length > 0);
  const robotState = sampleRunStatus === 'running'
    ? hasSamplePreview ? 'talking' : 'thinking'
    : sampleRunStatus === 'success'
      ? 'talking'
      : 'idle';
  const robotBubble = sampleRunStatus === 'running'
    ? sampleResponsePreview[0] ?? 'Running sample…'
    : sampleRunStatus === 'success'
      ? sampleResponsePreview[0] ?? 'Sample completed.'
      : sampleRunStatus === 'error'
        ? sampleError ?? 'Sample failed.'
        : undefined;

  const handleRunSample = async () => {
    sampleAbortRef.current?.abort();
    setSampleRunStatus('running');
    setSampleError(null);
    setSampleResponsePreview([]);

    let streamedText = '';
    let latestPreview: string[] = [];

    sampleAbortRef.current = streamAgentInvocation(profile.slug, profile.sampleInput, {
      onToken: (text) => {
        streamedText += text;
        const nextPreview = [streamedText.trim() || text.trim()].filter(Boolean);
        latestPreview = nextPreview;
        setSampleResponsePreview(nextPreview);
      },
      onResults: (payload) => {
        if (streamedText.trim().length > 0) {
          return;
        }

        const preview = buildSampleResponsePreview(payload);
        latestPreview = preview;
        setSampleResponsePreview(preview);
      },
      onDone: () => {
        if (latestPreview.length === 0 && streamedText.trim().length === 0) {
          latestPreview = ['Sample completed.'];
          setSampleResponsePreview(latestPreview);
        }

        setSampleRunStatus('success');
        sampleAbortRef.current = null;
      },
      onError: (error) => {
        setSampleError(error.message || 'Sample run failed.');
        setSampleRunStatus('error');
        sampleAbortRef.current = null;
      },
    });
  };

  return (
    <div className="fixed inset-0 z-[110]">
      <button
        type="button"
        aria-label="Close agent profile drawer"
        onClick={onClose}
        className="absolute inset-0 bg-black/55 backdrop-blur-sm"
      />
      <aside
        role="dialog"
        aria-modal="true"
        aria-labelledby="agent-profile-title"
        className="demo-panel absolute inset-y-0 right-0 flex h-full w-full max-w-[34rem] flex-col overflow-y-auto border-l border-white/10 px-5 py-5 text-left text-[var(--hp-text)] sm:px-6"
      >
        <div className="@container/profile flex flex-col gap-5">
          <header className="flex items-start justify-between gap-4 border-b border-white/10 pb-5">
            <div className="flex items-start gap-4">
              <div className="rounded-[1.75rem] border border-white/10 bg-black/15 p-3">
                <AgentRobot
                  agentSlug={profile.slug}
                  size={88}
                  sticky={false}
                  skipEntrance
                  state={robotState}
                  thinkingMessage={robotBubble}
                />
              </div>
              <div className="space-y-2">
                <span className="inline-flex rounded-full border border-white/10 bg-white/5 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.24em] text-[var(--hp-text-muted)]">
                  {profile.domainLabel}
                </span>
                <div>
                  <h2 id="agent-profile-title" className="text-2xl font-semibold leading-tight text-white">
                    {profile.displayName}
                  </h2>
                  <p className="mt-1 text-sm leading-6 text-[var(--hp-text-muted)]">
                    {profile.oneLiner}
                  </p>
                </div>
              </div>
            </div>
            <button
              ref={closeButtonRef}
              type="button"
              onClick={onClose}
              className="rounded-full border border-white/10 bg-white/5 px-3 py-2 text-sm font-medium text-white transition hover:border-white/20 hover:bg-white/10"
            >
              Close
            </button>
          </header>

          <section className="space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-[0.28em] text-[var(--hp-text-faint)]">
              Where To Use
            </h3>
            <ul className="grid gap-2 text-sm text-[var(--hp-text-muted)] @lg/profile:grid-cols-2">
              {profile.fitFor.map((scenario) => (
                <li key={scenario} className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
                  {scenario}
                </li>
              ))}
            </ul>
          </section>

          <section className="space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-[0.28em] text-[var(--hp-text-faint)]">
              Retail Problem
            </h3>
            <p className="rounded-3xl border border-white/10 bg-white/5 px-4 py-4 text-sm leading-7 text-[var(--hp-text-muted)]">
              {profile.retailProblem}
            </p>
          </section>

          <section className="space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-[0.28em] text-[var(--hp-text-faint)]">
              Productivity Gain
            </h3>
            <div className="grid gap-3 @lg/profile:grid-cols-2">
              <article className="rounded-3xl border border-white/10 bg-white/5 px-4 py-4">
                <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[var(--hp-text-faint)]">
                  Latency
                </p>
                <p className="mt-2 text-lg font-semibold text-white">{profile.productivityGain.latency}</p>
              </article>
              <article className="rounded-3xl border border-white/10 bg-white/5 px-4 py-4">
                <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[var(--hp-text-faint)]">
                  Quality
                </p>
                <p className="mt-2 text-lg font-semibold text-white">{profile.productivityGain.quality}</p>
              </article>
              <article className="rounded-3xl border border-white/10 bg-white/5 px-4 py-4">
                <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[var(--hp-text-faint)]">
                  Cost
                </p>
                <p className="mt-2 text-lg font-semibold text-white">{profile.productivityGain.cost}</p>
              </article>
              <article className="rounded-3xl border border-white/10 bg-white/5 px-4 py-4">
                <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[var(--hp-text-faint)]">
                  Revenue Impact
                </p>
                <p className="mt-2 text-lg font-semibold text-white">
                  {profile.productivityGain.revenueImpact ?? 'Operational trust and faster decisions'}
                </p>
              </article>
            </div>
          </section>

          <section className="space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-[0.28em] text-[var(--hp-text-faint)]">
              Current State
            </h3>
            <div className="rounded-[1.75rem] border border-white/10 bg-white/5 px-4 py-4">
              <div className="flex items-center gap-3 text-sm text-white">
                <span className={`h-2.5 w-2.5 rounded-full ${statusTone(liveMetrics?.status ?? 'unknown')}`} />
                <span className="font-medium capitalize">{liveMetrics?.status ?? 'unknown'}</span>
                {liveMetrics?.lastUpdatedLabel ? (
                  <span className="text-[var(--hp-text-faint)]">Updated {liveMetrics.lastUpdatedLabel}</span>
                ) : null}
              </div>
              <dl className="demo-telemetry mt-4 grid gap-3 text-sm text-[var(--hp-text-muted)] @lg/profile:grid-cols-2">
                <div className="rounded-2xl border border-white/10 bg-black/15 px-3 py-3">
                  <dt className="text-[11px] uppercase tracking-[0.24em] text-[var(--hp-text-faint)]">Latency</dt>
                  <dd className="mt-1 text-white">{liveMetrics?.latencyLabel ?? 'Awaiting live traces'}</dd>
                </div>
                <div className="rounded-2xl border border-white/10 bg-black/15 px-3 py-3">
                  <dt className="text-[11px] uppercase tracking-[0.24em] text-[var(--hp-text-faint)]">Error rate</dt>
                  <dd className="mt-1 text-white">{liveMetrics?.errorRateLabel ?? 'Awaiting live traces'}</dd>
                </div>
                <div className="rounded-2xl border border-white/10 bg-black/15 px-3 py-3">
                  <dt className="text-[11px] uppercase tracking-[0.24em] text-[var(--hp-text-faint)]">Throughput</dt>
                  <dd className="mt-1 text-white">{liveMetrics?.throughputLabel ?? 'Awaiting live traces'}</dd>
                </div>
                <div className="rounded-2xl border border-white/10 bg-black/15 px-3 py-3">
                  <dt className="text-[11px] uppercase tracking-[0.24em] text-[var(--hp-text-faint)]">Cost</dt>
                  <dd className="mt-1 text-white">{liveMetrics?.costLabel ?? 'Awaiting usage data'}</dd>
                </div>
                <div className="rounded-2xl border border-white/10 bg-black/15 px-3 py-3">
                  <dt className="text-[11px] uppercase tracking-[0.24em] text-[var(--hp-text-faint)]">Tier mix</dt>
                  <dd className="mt-1 text-white">{liveMetrics?.tierMixLabel ?? 'Awaiting model mix'}</dd>
                </div>
                <div className="rounded-2xl border border-white/10 bg-black/15 px-3 py-3">
                  <dt className="text-[11px] uppercase tracking-[0.24em] text-[var(--hp-text-faint)]">Eval score</dt>
                  <dd className="mt-1 text-white">{liveMetrics?.evaluationLabel ?? 'Awaiting evaluation data'}</dd>
                </div>
              </dl>
            </div>
          </section>

          <section className="space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-[0.28em] text-[var(--hp-text-faint)]">
              KPIs To Track
            </h3>
            <div className="space-y-3">
              {profile.kpisToTrack.map((kpi) => (
                <article
                  key={kpi.id}
                  className="rounded-[1.5rem] border border-white/10 bg-white/5 px-4 py-4"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <h4 className="text-sm font-semibold text-white">{kpi.label}</h4>
                      <p className="mt-2 text-sm leading-6 text-[var(--hp-text-muted)]">{kpi.why}</p>
                    </div>
                    <div className="demo-telemetry text-right">
                      <p className="text-[11px] uppercase tracking-[0.24em] text-[var(--hp-text-faint)]">Target</p>
                      <p className="mt-1 text-sm font-semibold text-white">{kpi.target}</p>
                      <p className="mt-3 text-[11px] uppercase tracking-[0.24em] text-[var(--hp-text-faint)]">Current</p>
                      <p className="mt-1 text-sm font-semibold text-white">
                        {liveMetrics?.kpiValues[kpi.id] ?? 'Live value pending'}
                      </p>
                    </div>
                  </div>
                </article>
              ))}
            </div>
          </section>

          <section className="space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-[0.28em] text-[var(--hp-text-faint)]">
              Interface Contract
            </h3>
            <div className="grid gap-3">
              <details className="rounded-[1.5rem] border border-white/10 bg-white/5 px-4 py-4" open>
                <summary className="cursor-pointer text-sm font-semibold text-white">Input schema</summary>
                <p className="mt-3 text-xs text-[var(--hp-text-faint)]">{profile.inputSchema.description}</p>
                <pre className="mt-3 overflow-x-auto rounded-2xl border border-white/10 bg-black/15 px-4 py-4 text-[11px] leading-relaxed text-[var(--hp-text-muted)]">{JSON.stringify(profile.inputSchema, null, 2)}</pre>
              </details>
              <details className="rounded-[1.5rem] border border-white/10 bg-white/5 px-4 py-4">
                <summary className="cursor-pointer text-sm font-semibold text-white">Output schema</summary>
                <p className="mt-3 text-xs text-[var(--hp-text-faint)]">{profile.outputSchema.description}</p>
                <pre className="mt-3 overflow-x-auto rounded-2xl border border-white/10 bg-black/15 px-4 py-4 text-[11px] leading-relaxed text-[var(--hp-text-muted)]">{JSON.stringify(profile.outputSchema, null, 2)}</pre>
              </details>
            </div>
          </section>

          <section className="space-y-3 pb-4">
            <h3 className="text-xs font-semibold uppercase tracking-[0.28em] text-[var(--hp-text-faint)]">
              Collaborates With
            </h3>
            <div className="flex flex-wrap gap-2">
              {profile.collaborates.map((slug) => (
                <span
                  key={slug}
                  className="rounded-full border border-white/10 bg-black/15 px-3 py-2 text-xs font-medium uppercase tracking-[0.18em] text-[var(--hp-text-muted)]"
                >
                  {slug}
                </span>
              ))}
            </div>
          </section>

          <section className="space-y-3 pb-4">
            <h3 className="text-xs font-semibold uppercase tracking-[0.28em] text-[var(--hp-text-faint)]">
              Mini Playground
            </h3>
            <div className="rounded-[1.5rem] border border-white/10 bg-white/5 px-4 py-4">
              <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[var(--hp-text-faint)]">Sample input</p>
              <pre className="mt-3 overflow-x-auto rounded-2xl border border-white/10 bg-black/15 px-4 py-4 text-[11px] leading-relaxed text-[var(--hp-text-muted)]">{JSON.stringify(profile.sampleInput, null, 2)}</pre>
              <div className="mt-4 flex flex-wrap gap-3">
                <button
                  type="button"
                  onClick={() => setTraceExplorerOpen(true)}
                  className="inline-flex items-center rounded-full border border-white/10 bg-black/15 px-4 py-2 text-sm font-semibold text-white transition hover:border-white/20 hover:bg-black/20"
                >
                  Open trace explorer
                </button>
                <a
                  href={profile.traceExplorerHref}
                  className="inline-flex items-center rounded-full border border-white/10 bg-black/5 px-4 py-2 text-sm font-semibold text-[var(--hp-text-muted)] transition hover:border-white/20 hover:bg-black/10 hover:text-white"
                >
                  Open operator cockpit
                </a>
                <button
                  type="button"
                  onClick={() => { void handleRunSample(); }}
                  disabled={sampleRunStatus === 'running'}
                  className="inline-flex items-center rounded-full border border-white/10 bg-white/10 px-4 py-2 text-sm font-semibold text-white transition hover:border-white/20 hover:bg-white/15 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {sampleRunStatus === 'running' ? 'Streaming sample…' : 'Run a sample'}
                </button>
              </div>
              {(sampleRunStatus === 'running' || sampleRunStatus === 'success') && sampleResponsePreview.length > 0 && (
                <div className="mt-4 rounded-2xl border border-emerald-400/20 bg-emerald-400/10 px-4 py-4">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-emerald-200">Sample response</p>
                  <div className="mt-3 space-y-2 text-sm leading-6 text-white">
                    {sampleResponsePreview.map((line) => (
                      <p key={line}>{line}</p>
                    ))}
                  </div>
                </div>
              )}
              {sampleRunStatus === 'error' && sampleError && (
                <div className="mt-4 rounded-2xl border border-rose-400/20 bg-rose-400/10 px-4 py-4 text-sm text-white">
                  {sampleError}
                </div>
              )}
            </div>
          </section>
        </div>
      </aside>

      {traceExplorerOpen && (
        <div className="fixed inset-0 z-[90] flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
          <div className="max-h-[90vh] w-full max-w-6xl overflow-hidden rounded-[2rem] border border-white/10 bg-[radial-gradient(circle_at_top,rgba(56,189,248,0.12),transparent_35%),rgba(5,8,16,0.96)] shadow-[0_40px_140px_rgba(15,23,42,0.45)]">
            <div className="flex items-center justify-between gap-4 border-b border-white/10 px-6 py-5">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[var(--hp-text-faint)]">Trace explorer</p>
                <h3 className="mt-2 text-2xl font-semibold text-white">{profile.displayName} runtime evidence</h3>
                <p className="mt-1 text-sm text-[var(--hp-text-muted)]">Latest traces and the full waterfall remain visible without leaving the scene.</p>
              </div>
              <button
                type="button"
                onClick={() => setTraceExplorerOpen(false)}
                className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-white/10 bg-white/5 text-lg text-white transition hover:bg-white/10"
                aria-label="Close trace explorer"
              >
                ×
              </button>
            </div>

            <div className="grid gap-0 lg:grid-cols-[320px_minmax(0,1fr)]">
              <aside className="border-r border-white/10 bg-black/20 p-5">
                <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[var(--hp-text-faint)]">Recent traces</p>
                <div className="mt-4 space-y-3">
                  {recentTraces.length === 0 && (
                    <div className="rounded-[1.5rem] border border-white/10 bg-white/5 px-4 py-4 text-sm text-[var(--hp-text-muted)]">
                      No recent traces are available for this agent yet.
                    </div>
                  )}
                  {recentTraces.map((trace) => {
                    const active = trace.trace_id === selectedTraceId;

                    return (
                      <button
                        key={trace.trace_id}
                        type="button"
                        onClick={() => setSelectedTraceId(trace.trace_id)}
                        className={`w-full rounded-[1.5rem] border px-4 py-4 text-left transition ${active ? 'border-cyan-400/30 bg-cyan-400/10' : 'border-white/10 bg-white/5 hover:border-white/20 hover:bg-white/10'}`}
                      >
                        <p className="text-sm font-semibold text-white">{trace.operation}</p>
                        <p className="mt-2 text-xs uppercase tracking-[0.18em] text-[var(--hp-text-faint)]">{trace.status} · {trace.model_tier}</p>
                        <p className="mt-2 text-xs text-[var(--hp-text-muted)]">{Math.round(trace.duration_ms)} ms · {new Date(trace.started_at).toLocaleString()}</p>
                      </button>
                    );
                  })}
                </div>
              </aside>

              <div className="p-6">
                <div className="grid gap-4 md:grid-cols-3">
                  <article className="rounded-[1.5rem] border border-white/10 bg-white/5 p-4">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[var(--hp-text-faint)]">Trace ID</p>
                    <p className="mt-2 text-sm text-white">{traceDetail?.trace_id ?? 'Awaiting selection'}</p>
                  </article>
                  <article className="rounded-[1.5rem] border border-white/10 bg-white/5 p-4">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[var(--hp-text-faint)]">Status</p>
                    <p className="mt-2 text-sm text-white">{traceDetail?.status ?? 'Unknown'}</p>
                  </article>
                  <article className="rounded-[1.5rem] border border-white/10 bg-white/5 p-4">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[var(--hp-text-faint)]">Duration</p>
                    <p className="mt-2 text-sm text-white">{traceDetail ? `${Math.round(traceDetail.duration_ms)} ms` : 'Awaiting selection'}</p>
                  </article>
                </div>

                <div className="mt-5 rounded-[2rem] border border-white/10 bg-black/20 p-5">
                  <div className="flex items-center justify-between gap-4">
                    <div>
                      <h4 className="text-lg font-semibold text-white">Trace waterfall</h4>
                      <p className="mt-1 text-sm text-[var(--hp-text-muted)]">Span timing, tool hops, and model work for the selected run.</p>
                    </div>
                    {isTraceDetailLoading && (
                      <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-[var(--hp-text-muted)]">Loading trace…</span>
                    )}
                  </div>
                  <div className="mt-5">
                    <TraceWaterfall spans={traceDetail?.spans ?? []} />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function buildSampleResponsePreview(payload: unknown): string[] {
  if (typeof payload === 'string') {
    return [payload];
  }

  if (!payload || typeof payload !== 'object') {
    return ['Sample completed.'];
  }

  const record = payload as Record<string, unknown>;
  const lines: string[] = [];

  for (const key of ['summary', 'message', 'result', 'status']) {
    const value = record[key];
    if (typeof value === 'string' && value.trim()) {
      lines.push(value.trim());
    }
  }

  if (lines.length === 0) {
    lines.push(JSON.stringify(payload).slice(0, 240));
  }

  return lines.slice(0, 4);
}

export default AgentProfileDrawer;