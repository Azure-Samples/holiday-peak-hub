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

  const toolCalls = data?.tool_calls ?? [];
  const modelInvocations = data?.model_invocations ?? [];

  const fallbackToolCalls =
    toolCalls.length > 0
      ? toolCalls
      : (data?.spans ?? [])
          .filter((span) => span.tool_name)
          .map((span) => ({
            span_id: span.span_id,
            tool_name: span.tool_name ?? 'unknown-tool',
            input: span.tool_input,
            output: span.tool_output,
            status: span.status,
          }));

  const fallbackModelInvocations =
    modelInvocations.length > 0
      ? modelInvocations
      : (data?.spans ?? [])
          .filter((span) => Boolean(span.model_name) || Boolean(span.prompt_excerpt) || Boolean(span.completion_excerpt))
          .map((span) => ({
            span_id: span.span_id,
            model_name: span.model_name ?? span.service,
            model_tier: span.model_tier ?? 'unknown',
            prompt_excerpt: span.prompt_excerpt,
            completion_excerpt: span.completion_excerpt,
            latency_ms: span.duration_ms,
          }));

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

            <section className="grid grid-cols-1 gap-6 xl:grid-cols-2">
              <Card className="p-4">
                <h2 className="mb-3 text-lg font-semibold text-gray-900 dark:text-white">Tool calls</h2>
                {fallbackToolCalls.length === 0 ? (
                  <p className="text-sm text-gray-500 dark:text-gray-400">No tool call details available.</p>
                ) : (
                  <ul className="space-y-3" aria-label="Tool call list">
                    {fallbackToolCalls.map((toolCall) => (
                      <li key={`${toolCall.span_id}-${toolCall.tool_name}`} className="rounded-md border border-gray-200 p-3 dark:border-gray-700">
                        <p className="text-sm font-semibold text-gray-900 dark:text-white">{toolCall.tool_name}</p>
                        {toolCall.input && (
                          <p className="mt-1 text-xs text-gray-600 dark:text-gray-300">
                            Input: {toolCall.input.slice(0, 180)}
                            {toolCall.input.length > 180 ? '…' : ''}
                          </p>
                        )}
                        {toolCall.output && (
                          <p className="mt-1 text-xs text-gray-600 dark:text-gray-300">
                            Output: {toolCall.output.slice(0, 180)}
                            {toolCall.output.length > 180 ? '…' : ''}
                          </p>
                        )}
                      </li>
                    ))}
                  </ul>
                )}
              </Card>

              <Card className="p-4">
                <h2 className="mb-3 text-lg font-semibold text-gray-900 dark:text-white">Model invocations</h2>
                {fallbackModelInvocations.length === 0 ? (
                  <p className="text-sm text-gray-500 dark:text-gray-400">No model invocation details available.</p>
                ) : (
                  <ul className="space-y-3" aria-label="Model invocation list">
                    {fallbackModelInvocations.map((invocation) => (
                      <li key={`${invocation.span_id}-${invocation.model_name}`} className="rounded-md border border-gray-200 p-3 dark:border-gray-700">
                        <p className="text-sm font-semibold text-gray-900 dark:text-white">
                          {invocation.model_name} ({invocation.model_tier})
                        </p>
                        {invocation.prompt_excerpt && (
                          <p className="mt-1 text-xs text-gray-600 dark:text-gray-300">
                            Prompt: {invocation.prompt_excerpt.slice(0, 220)}
                            {invocation.prompt_excerpt.length > 220 ? '…' : ''}
                          </p>
                        )}
                        {invocation.completion_excerpt && (
                          <p className="mt-1 text-xs text-gray-600 dark:text-gray-300">
                            Completion: {invocation.completion_excerpt.slice(0, 220)}
                            {invocation.completion_excerpt.length > 220 ? '…' : ''}
                          </p>
                        )}
                      </li>
                    ))}
                  </ul>
                )}
              </Card>
            </section>

            <Card className="p-4">
              <h2 className="mb-3 text-lg font-semibold text-gray-900 dark:text-white">Decision outcome</h2>
              <p className="text-sm text-gray-700 dark:text-gray-300">
                {data.decision_outcome ?? data.spans.find((span) => span.decision_outcome)?.decision_outcome ?? 'Not captured'}
              </p>
              <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
                Confidence:{' '}
                {typeof data.decision_confidence === 'number'
                  ? `${Math.round(data.decision_confidence * 100)}%`
                  : typeof data.spans.find((span) => typeof span.confidence_score === 'number')?.confidence_score === 'number'
                    ? `${Math.round((data.spans.find((span) => typeof span.confidence_score === 'number')?.confidence_score ?? 0) * 100)}%`
                    : 'N/A'}
              </p>
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
