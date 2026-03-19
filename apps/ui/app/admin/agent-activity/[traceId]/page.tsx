'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { MainLayout } from '@/components/templates/MainLayout';
import { Card } from '@/components/molecules/Card';
import { Select } from '@/components/atoms/Select';
import { TraceTimeline } from '@/components/admin/TraceTimeline';
import { TraceWaterfall } from '@/components/admin/TraceWaterfall';
import {
  AGENT_MONITOR_RANGE_OPTIONS,
  DEFAULT_AGENT_MONITOR_RANGE,
  isTracingUnavailableError,
  useAgentTraceDetail,
} from '@/lib/hooks/useAgentMonitor';
import type { AgentMonitorTimeRange } from '@/lib/types/api';

export default function AgentActivityTraceDetailPage() {
  const params = useParams<{ traceId: string }>();
  const traceId = params?.traceId ?? '';
  const [timeRange, setTimeRange] = useState<AgentMonitorTimeRange>(DEFAULT_AGENT_MONITOR_RANGE);

  const { data, isLoading, isError, error, isFetching } = useAgentTraceDetail(traceId, timeRange);

  const isTracingUnavailable = Boolean(
    (data && !data.tracing_enabled) || (isError && isTracingUnavailableError(error))
  );

  return (
    <MainLayout>
      <div className="space-y-6">
        <nav aria-label="Breadcrumb" className="text-sm text-gray-600 dark:text-gray-400">
          <Link
            href="/admin/agent-activity"
            className="text-blue-600 hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:text-blue-400"
          >
            Agent Activity
          </Link>
          <span className="mx-2" aria-hidden="true">/</span>
          <span className="text-gray-900 dark:text-white">{traceId}</span>
        </nav>

        <header className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Trace Detail</h1>
            <p className="mt-1 text-gray-600 dark:text-gray-400">Span tree and timing waterfall for trace {traceId}.</p>
          </div>
          <div className="flex items-center gap-3">
            <label htmlFor="trace-detail-range" className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Time range
            </label>
            <div className="w-52">
              <Select
                name="trace-detail-range"
                ariaLabel="Trace detail time range"
                value={timeRange}
                options={AGENT_MONITOR_RANGE_OPTIONS}
                onChange={(event) => setTimeRange(event.target.value as AgentMonitorTimeRange)}
              />
            </div>
          </div>
        </header>

        {isFetching && !isLoading && (
          <p className="text-xs text-gray-500 dark:text-gray-400" aria-live="polite">
            Refreshing trace…
          </p>
        )}

        {isLoading && <Card className="p-6 text-gray-600 dark:text-gray-400">Loading trace details…</Card>}

        {isTracingUnavailable && (
          <Card className="p-6 border border-yellow-200 bg-yellow-50 text-yellow-800 dark:border-yellow-900 dark:bg-yellow-950 dark:text-yellow-300">
            Tracing is disabled or unavailable for this environment.
          </Card>
        )}

        {isError && !isTracingUnavailable && (
          <Card className="p-6 border border-red-200 dark:border-red-900 text-red-600 dark:text-red-400">
            Failed to load trace detail.
          </Card>
        )}

        {data && data.tracing_enabled && (
          <>
            <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <MetricCard label="Trace ID" value={data.trace_id} />
              <MetricCard label="Root agent" value={data.root_agent_name} />
              <MetricCard label="Status" value={data.status} />
              <MetricCard label="Duration" value={`${Math.round(data.duration_ms)} ms`} />
            </section>

            <Card className="p-4">
              <h2 className="mb-3 text-lg font-semibold text-gray-900 dark:text-white">Span timeline</h2>
              <TraceTimeline spans={data.spans} />
            </Card>

            <Card className="p-4">
              <h2 className="mb-3 text-lg font-semibold text-gray-900 dark:text-white">Timing waterfall</h2>
              <TraceWaterfall spans={data.spans} />
            </Card>
          </>
        )}
      </div>
    </MainLayout>
  );
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <Card className="p-4">
      <p className="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">{label}</p>
      <p className="mt-1 text-sm font-semibold text-gray-900 dark:text-white break-words">{value}</p>
    </Card>
  );
}
