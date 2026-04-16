'use client';

import Link from 'next/link';
import { MainLayout } from '@/components/templates/MainLayout';
import { Card } from '@/components/molecules/Card';
import { Select } from '@/components/atoms/Select';
import { AgentHealthCard } from '@/components/admin/AgentHealthCard';
import { ModelUsageTable } from '@/components/admin/ModelUsageTable';
import {
  AGENT_MONITOR_RANGE_OPTIONS,
  DEFAULT_AGENT_MONITOR_RANGE,
  isTracingUnavailableError,
  useAgentMonitorDashboard,
} from '@/lib/hooks/useAgentMonitor';
import type { AgentMonitorTimeRange, AgentTraceSummary } from '@/lib/types/api';
import { useState } from 'react';

const STATUS_STYLES: Record<AgentTraceSummary['status'], string> = {
  ok: 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300',
  warning: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300',
  error: 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300',
  unknown: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400',
};

function StatusBadge({ status }: { status: AgentTraceSummary['status'] }) {
  return (
    <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-semibold uppercase tracking-wide ${STATUS_STYLES[status]}`}>
      {status}
    </span>
  );
}

export default function AgentActivityPage() {
  const [timeRange, setTimeRange] = useState<AgentMonitorTimeRange>(DEFAULT_AGENT_MONITOR_RANGE);
  const { data, isLoading, isError, error, isFetching } = useAgentMonitorDashboard(timeRange);

  const isTracingUnavailable = Boolean(
    (data && !data.tracing_enabled) || (isError && isTracingUnavailableError(error))
  );

  const errorLog = (data?.trace_feed ?? [])
    .filter((trace) => trace.status === 'error' || trace.error_count > 0)
    .slice(0, 8);
  const traceCount = data?.trace_feed.length ?? 0;
  const retryNeededCount = errorLog.filter((trace) => trace.status === 'error').length;
  const recoveredCount = errorLog.filter((trace) => trace.status !== 'error').length;

  return (
    <MainLayout>
      <div className="space-y-6">
        <header className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Agent Activity</h1>
            <p className="mt-1 text-gray-600 dark:text-gray-400">
              Single-pane monitoring for agent health, trace activity, and model usage.
            </p>
          </div>
          <Link
            href="/admin/agent-activity/evaluations"
            className="rounded-md border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:border-gray-700 dark:text-gray-200 dark:hover:bg-gray-800"
          >
            View evaluations
          </Link>
        </header>

        <section className="flex items-center gap-3">
          <label htmlFor="agent-activity-range" className="text-sm font-medium text-gray-700 dark:text-gray-300">
            Time range
          </label>
          <div className="w-52">
            <Select
              name="agent-activity-range"
              ariaLabel="Agent activity time range"
              value={timeRange}
              options={AGENT_MONITOR_RANGE_OPTIONS}
              onChange={(event) => setTimeRange(event.target.value as AgentMonitorTimeRange)}
            />
          </div>
          {isFetching && !isLoading && (
            <span className="text-xs text-gray-500 dark:text-gray-400" aria-live="polite">
              Refreshing…
            </span>
          )}
        </section>

        {isLoading && <Card className="p-6 text-gray-600 dark:text-gray-400">Loading agent activity…</Card>}

        {isTracingUnavailable && (
          <Card className="p-6 border border-yellow-200 bg-yellow-50 text-yellow-800 dark:border-yellow-900 dark:bg-yellow-950 dark:text-yellow-300">
            Tracing is currently disabled or unavailable. Enable backend tracing APIs to populate this dashboard.
          </Card>
        )}

        {isError && !isTracingUnavailable && (
          <Card className="p-6 border border-red-200 dark:border-red-900 text-red-600 dark:text-red-400">
            Failed to load agent activity data.
          </Card>
        )}

        {data && data.tracing_enabled && (
          <>
            <section aria-label="Live monitor triage summary" className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
              <Card className="border border-[var(--hp-border)] bg-[var(--hp-surface)] p-4">
                <p className="text-xs font-semibold uppercase tracking-wide text-[var(--hp-text-muted)]">Tracing</p>
                <p className="mt-2 text-2xl font-black text-[var(--hp-text)]">Enabled</p>
                <p className="mt-1 text-xs text-[var(--hp-text-muted)]">Feed refreshes every 10 seconds.</p>
              </Card>
              <Card className="border border-[var(--hp-border)] bg-[var(--hp-surface)] p-4">
                <p className="text-xs font-semibold uppercase tracking-wide text-[var(--hp-text-muted)]">Active traces</p>
                <p className="mt-2 text-2xl font-black text-[var(--hp-text)]">{traceCount}</p>
                <p className="mt-1 text-xs text-[var(--hp-text-muted)]">Within selected time window.</p>
              </Card>
              <Card className="border border-[var(--hp-border)] bg-[var(--hp-surface)] p-4">
                <p className="text-xs font-semibold uppercase tracking-wide text-[var(--hp-text-muted)]">Needs retry</p>
                <p className="mt-2 text-2xl font-black text-red-600 dark:text-red-400">{retryNeededCount}</p>
                <p className="mt-1 text-xs text-[var(--hp-text-muted)]">Failed traces awaiting recovery.</p>
              </Card>
              <Card className="border border-[var(--hp-border)] bg-[var(--hp-surface)] p-4">
                <p className="text-xs font-semibold uppercase tracking-wide text-[var(--hp-text-muted)]">Recovered</p>
                <p className="mt-2 text-2xl font-black text-[var(--hp-accent)]">{recoveredCount}</p>
                <p className="mt-1 text-xs text-[var(--hp-text-muted)]">Retries completed in range.</p>
              </Card>
            </section>

            <section aria-label="Agent health cards" className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {data.health_cards.map((metric) => (
                <AgentHealthCard key={metric.id} metric={metric} />
              ))}
            </section>

            <section className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              <Card className="p-0 overflow-hidden">
                <div className="border-b border-gray-200 p-4 dark:border-gray-700">
                  <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Trace feed</h2>
                  <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">Auto-updates every 15 seconds.</p>
                </div>

                {data.trace_feed.length === 0 ? (
                  <p className="p-4 text-sm text-gray-500 dark:text-gray-400">No traces captured for this range.</p>
                ) : (
                  <div>
                    <div className="space-y-3 p-4 md:hidden">
                      {data.trace_feed.map((trace, index) => (
                        <article key={`${trace.trace_id}-${index}`} className="rounded-xl border border-[var(--hp-border)] bg-[var(--hp-surface)] p-3">
                          <div className="flex items-start justify-between gap-3">
                            <Link
                              href={`/admin/agent-activity/${trace.trace_id}`}
                              className="text-sm font-semibold text-[var(--hp-primary)] hover:underline"
                            >
                              {trace.trace_id}
                            </Link>
                            <StatusBadge status={trace.status} />
                          </div>
                          <p className="mt-2 text-xs text-[var(--hp-text-muted)]">{trace.agent_name}</p>
                          <p className="mt-1 text-xs text-[var(--hp-text-muted)]">{Math.round(trace.duration_ms)} ms</p>
                        </article>
                      ))}
                    </div>

                    <div className="hidden overflow-x-auto md:block">
                      <table className="min-w-full text-sm">
                        <thead className="bg-gray-50 dark:bg-gray-900/40">
                          <tr>
                            <th className="px-4 py-2 text-left font-semibold text-gray-700 dark:text-gray-300">Trace</th>
                            <th className="px-4 py-2 text-left font-semibold text-gray-700 dark:text-gray-300">Agent</th>
                            <th className="px-4 py-2 text-left font-semibold text-gray-700 dark:text-gray-300">Status</th>
                            <th className="px-4 py-2 text-left font-semibold text-gray-700 dark:text-gray-300">Duration</th>
                          </tr>
                        </thead>
                        <tbody>
                          {data.trace_feed.map((trace, index) => (
                            <tr key={`${trace.trace_id}-${index}`} className="border-t border-gray-200 dark:border-gray-700">
                              <td className="px-4 py-2">
                                <Link
                                  href={`/admin/agent-activity/${trace.trace_id}`}
                                  className="text-blue-600 hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:text-blue-400"
                                >
                                  {trace.trace_id}
                                </Link>
                              </td>
                              <td className="px-4 py-2 text-gray-700 dark:text-gray-300">{trace.agent_name}</td>
                              <td className="px-4 py-2"><StatusBadge status={trace.status} /></td>
                              <td className="px-4 py-2 text-gray-700 dark:text-gray-300">{Math.round(trace.duration_ms)} ms</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </Card>

              <Card className="p-0 overflow-hidden">
                <div className="border-b border-gray-200 p-4 dark:border-gray-700">
                  <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Model usage</h2>
                  <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">SLM vs LLM request and token split.</p>
                </div>
                <div className="p-4">
                  <ModelUsageTable rows={data.model_usage} />
                </div>
              </Card>
            </section>

            <Card className="p-0 overflow-hidden">
              <div className="border-b border-gray-200 p-4 dark:border-gray-700">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Error / retry log</h2>
                <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                  Recent failed or retried traces with current recovery status.
                </p>
              </div>

              {errorLog.length === 0 ? (
                <p className="p-4 text-sm text-gray-500 dark:text-gray-400">No failed traces for this range.</p>
              ) : (
                <div>
                  <div className="space-y-3 p-4 md:hidden">
                    {errorLog.map((trace) => (
                      <article key={`error-${trace.trace_id}`} className="rounded-xl border border-[var(--hp-border)] bg-[var(--hp-surface)] p-3">
                        <div className="flex items-start justify-between gap-2">
                          <Link
                            href={`/admin/agent-activity/${trace.trace_id}`}
                            className="text-sm font-semibold text-[var(--hp-primary)] hover:underline"
                          >
                            {trace.trace_id}
                          </Link>
                          <span className="rounded-full bg-[var(--hp-surface-strong)] px-2 py-1 text-xs font-semibold uppercase tracking-wide text-[var(--hp-text)]">
                            {trace.status === 'error' ? 'Needs retry' : 'Recovered'}
                          </span>
                        </div>
                        <p className="mt-2 text-xs text-[var(--hp-text-muted)]">{trace.agent_name}</p>
                        <p className="mt-1 text-xs text-[var(--hp-text-muted)]">Errors: {trace.error_count}</p>
                      </article>
                    ))}
                  </div>

                  <div className="hidden overflow-x-auto md:block">
                    <table className="min-w-full text-sm">
                      <thead className="bg-gray-50 dark:bg-gray-900/40">
                        <tr>
                          <th className="px-4 py-2 text-left font-semibold text-gray-700 dark:text-gray-300">Trace</th>
                          <th className="px-4 py-2 text-left font-semibold text-gray-700 dark:text-gray-300">Agent</th>
                          <th className="px-4 py-2 text-left font-semibold text-gray-700 dark:text-gray-300">Errors</th>
                          <th className="px-4 py-2 text-left font-semibold text-gray-700 dark:text-gray-300">Retry status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {errorLog.map((trace) => (
                          <tr key={`error-${trace.trace_id}`} className="border-t border-gray-200 dark:border-gray-700">
                            <td className="px-4 py-2">
                              <Link
                                href={`/admin/agent-activity/${trace.trace_id}`}
                                className="text-blue-600 hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:text-blue-400"
                              >
                                {trace.trace_id}
                              </Link>
                            </td>
                            <td className="px-4 py-2 text-gray-700 dark:text-gray-300">{trace.agent_name}</td>
                            <td className="px-4 py-2 text-gray-700 dark:text-gray-300">{trace.error_count}</td>
                            <td className="px-4 py-2 text-gray-700 dark:text-gray-300">
                              {trace.status === 'error' ? 'Needs retry' : 'Recovered'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </Card>
          </>
        )}
      </div>
    </MainLayout>
  );
}
