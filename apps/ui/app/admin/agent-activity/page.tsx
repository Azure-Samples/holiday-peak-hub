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
import type { AgentMonitorTimeRange } from '@/lib/types/api';
import { useState } from 'react';

export default function AgentActivityPage() {
  const [timeRange, setTimeRange] = useState<AgentMonitorTimeRange>(DEFAULT_AGENT_MONITOR_RANGE);
  const { data, isLoading, isError, error, isFetching } = useAgentMonitorDashboard(timeRange);

  const isTracingUnavailable = Boolean(
    (data && !data.tracing_enabled) || (isError && isTracingUnavailableError(error))
  );

  const errorLog = (data?.trace_feed ?? [])
    .filter((trace) => trace.status === 'error' || trace.error_count > 0)
    .slice(0, 8);

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
                  <div className="overflow-x-auto">
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
                        {data.trace_feed.map((trace) => (
                          <tr key={trace.trace_id} className="border-t border-gray-200 dark:border-gray-700">
                            <td className="px-4 py-2">
                              <Link
                                href={`/admin/agent-activity/${trace.trace_id}`}
                                className="text-blue-600 hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:text-blue-400"
                              >
                                {trace.trace_id}
                              </Link>
                            </td>
                            <td className="px-4 py-2 text-gray-700 dark:text-gray-300">{trace.agent_name}</td>
                            <td className="px-4 py-2 text-gray-700 dark:text-gray-300">{trace.status}</td>
                            <td className="px-4 py-2 text-gray-700 dark:text-gray-300">{Math.round(trace.duration_ms)} ms</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
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
                <div className="overflow-x-auto">
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
              )}
            </Card>
          </>
        )}
      </div>
    </MainLayout>
  );
}
