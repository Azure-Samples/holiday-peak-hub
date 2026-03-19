'use client';

import { useState } from 'react';
import Link from 'next/link';
import { MainLayout } from '@/components/templates/MainLayout';
import { Card } from '@/components/molecules/Card';
import { Select } from '@/components/atoms/Select';
import { EvaluationTrendChart } from '@/components/admin/EvaluationTrendChart';
import { EvaluationComparisonTable } from '@/components/admin/EvaluationComparisonTable';
import {
  AGENT_MONITOR_RANGE_OPTIONS,
  DEFAULT_AGENT_MONITOR_RANGE,
  isTracingUnavailableError,
  useAgentEvaluations,
} from '@/lib/hooks/useAgentMonitor';
import type { AgentMonitorTimeRange } from '@/lib/types/api';

export default function AgentActivityEvaluationsPage() {
  const [timeRange, setTimeRange] = useState<AgentMonitorTimeRange>(DEFAULT_AGENT_MONITOR_RANGE);
  const { data, isLoading, isError, error, isFetching } = useAgentEvaluations(timeRange);

  const isTracingUnavailable = Boolean(
    (data && !data.tracing_enabled) || (isError && isTracingUnavailableError(error))
  );

  return (
    <MainLayout>
      <div className="space-y-6">
        <header className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Agent Evaluations</h1>
            <p className="mt-1 text-gray-600 dark:text-gray-400">
              Latest model evaluation metrics, trend movement, and side-by-side comparisons.
            </p>
          </div>
          <Link
            href="/admin/agent-activity"
            className="rounded-md border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:border-gray-700 dark:text-gray-200 dark:hover:bg-gray-800"
          >
            Back to activity
          </Link>
        </header>

        <section className="flex items-center gap-3">
          <label htmlFor="agent-evaluations-range" className="text-sm font-medium text-gray-700 dark:text-gray-300">
            Time range
          </label>
          <div className="w-52">
            <Select
              name="agent-evaluations-range"
              ariaLabel="Agent evaluations time range"
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

        {isLoading && <Card className="p-6 text-gray-600 dark:text-gray-400">Loading evaluations…</Card>}

        {isTracingUnavailable && (
          <Card className="p-6 border border-yellow-200 bg-yellow-50 text-yellow-800 dark:border-yellow-900 dark:bg-yellow-950 dark:text-yellow-300">
            Evaluation data is unavailable because tracing is disabled or not configured.
          </Card>
        )}

        {isError && !isTracingUnavailable && (
          <Card className="p-6 border border-red-200 dark:border-red-900 text-red-600 dark:text-red-400">
            Failed to load evaluation metrics.
          </Card>
        )}

        {data && data.tracing_enabled && (
          <>
            <section className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <SummaryCard label="Overall score" value={data.summary.overall_score.toFixed(3)} />
              <SummaryCard label="Pass rate" value={`${(data.summary.pass_rate * 100).toFixed(1)}%`} />
              <SummaryCard label="Total runs" value={data.summary.total_runs.toLocaleString()} />
            </section>

            <Card className="p-4">
              <h2 className="mb-3 text-lg font-semibold text-gray-900 dark:text-white">Trend lines</h2>
              <EvaluationTrendChart trends={data.trends} />
            </Card>

            <Card className="p-4">
              <h2 className="mb-3 text-lg font-semibold text-gray-900 dark:text-white">Model comparison</h2>
              <EvaluationComparisonTable rows={data.comparison} />
            </Card>
          </>
        )}
      </div>
    </MainLayout>
  );
}

function SummaryCard({ label, value }: { label: string; value: string }) {
  return (
    <Card className="p-4">
      <p className="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">{label}</p>
      <p className="mt-1 text-2xl font-bold text-gray-900 dark:text-white">{value}</p>
    </Card>
  );
}
