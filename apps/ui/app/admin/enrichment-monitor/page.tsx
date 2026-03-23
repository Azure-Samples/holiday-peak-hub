'use client';

import Link from 'next/link';
import { MainLayout } from '@/components/templates/MainLayout';
import { Card } from '@/components/molecules/Card';
import { EnrichmentPipelineStatus } from '@/components/enrichment/EnrichmentPipelineStatus';
import { useEnrichmentMonitorDashboard } from '@/lib/hooks/useEnrichmentMonitor';

export default function EnrichmentMonitorPage() {
  const { data, isLoading, isError, refetch, isFetching } = useEnrichmentMonitorDashboard();

  const approvedCount = data?.status_cards.find((card) => card.label.toLowerCase().includes('approved'))?.value ?? 0;
  const reviewCount = data?.status_cards.find((card) => card.label.toLowerCase().includes('review'))?.value ?? 0;
  const rejectedCount = data?.status_cards.find((card) => card.label.toLowerCase().includes('rejected'))?.value ?? 0;
  const decisionTotal = approvedCount + reviewCount + rejectedCount;
  const approvalRate = decisionTotal > 0 ? Math.round((approvedCount / decisionTotal) * 100) : 0;
  const enrichmentsPerHour = data ? data.throughput.per_minute * 60 : 0;
  const enrichmentsPerHourBar = Math.min(100, Math.max(0, Math.round((enrichmentsPerHour / 500) * 100)));

  return (
    <MainLayout>
      <div className="space-y-6">
        <header>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Enrichment Monitor</h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">
            Real-time pipeline state, active jobs, and processing health.
          </p>
          <div className="mt-2 flex flex-wrap items-center gap-3">
            <Link
              href="/staff/review"
              className="inline-flex rounded-md border border-[var(--hp-border)] bg-[var(--hp-surface-strong)] px-3 py-1.5 text-sm font-semibold text-[var(--hp-text)] hover:bg-[var(--hp-surface)] focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
            >
              Open HITL review queue
            </Link>
            <Link
              href="/admin/agent-activity"
              className="inline-flex text-sm text-blue-600 dark:text-blue-400 hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 rounded"
            >
              Open Agent Activity dashboard
            </Link>
          </div>
        </header>

        {isLoading && <Card className="p-6 text-gray-600 dark:text-gray-400">Loading monitor data…</Card>}

        {isError && (
          <Card className="p-6 border border-red-200 dark:border-red-900 text-red-600 dark:text-red-400">
            <div className="flex items-center justify-between gap-3 flex-wrap">
              <span>Failed to load enrichment monitor data.</span>
              <button
                onClick={() => {
                  void refetch();
                }}
                className="px-3 py-1.5 rounded-md text-xs font-semibold border border-red-300 dark:border-red-700 hover:bg-red-50 dark:hover:bg-red-950/30 focus:outline-none focus-visible:ring-2 focus-visible:ring-red-500"
                disabled={isFetching}
              >
                Retry
              </button>
            </div>
          </Card>
        )}

        {data && (
          <>
            <section aria-label="Pipeline status cards" className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {data.status_cards.map((card) => (
                <Card key={card.label} className="p-4">
                  <p className="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">{card.label}</p>
                  <p className="mt-1 text-2xl font-bold text-gray-900 dark:text-white">{card.value.toLocaleString()}</p>
                </Card>
              ))}
            </section>

            <section className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <Card className="lg:col-span-2 p-0 overflow-hidden">
                <div className="p-4 border-b border-gray-200 dark:border-gray-700">
                  <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Active jobs</h2>
                </div>

                {data.active_jobs.length === 0 ? (
                  <p className="p-4 text-sm text-gray-500 dark:text-gray-400">No active jobs.</p>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="min-w-full text-sm">
                      <thead className="bg-gray-50 dark:bg-gray-900/40">
                        <tr>
                          <th className="text-left font-semibold text-gray-700 dark:text-gray-300 px-4 py-2">Entity</th>
                          <th className="text-left font-semibold text-gray-700 dark:text-gray-300 px-4 py-2">Status</th>
                          <th className="text-left font-semibold text-gray-700 dark:text-gray-300 px-4 py-2">Source</th>
                          <th className="text-left font-semibold text-gray-700 dark:text-gray-300 px-4 py-2">Confidence</th>
                          <th className="text-left font-semibold text-gray-700 dark:text-gray-300 px-4 py-2">Updated</th>
                          <th className="text-left font-semibold text-gray-700 dark:text-gray-300 px-4 py-2">HITL</th>
                        </tr>
                      </thead>
                      <tbody>
                        {data.active_jobs.map((job) => (
                          <tr key={job.id} className="border-t border-gray-200 dark:border-gray-700">
                            <td className="px-4 py-2">
                              <Link
                                href={`/admin/enrichment-monitor/${job.entity_id}`}
                                className="text-blue-600 dark:text-blue-400 hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 rounded"
                              >
                                {job.entity_id}
                              </Link>
                            </td>
                            <td className="px-4 py-2">
                              <EnrichmentPipelineStatus status={job.status} />
                            </td>
                            <td className="px-4 py-2 text-gray-700 dark:text-gray-300">{job.source_type}</td>
                            <td className="px-4 py-2 text-gray-700 dark:text-gray-300">{Math.round(job.confidence * 100)}%</td>
                            <td className="px-4 py-2 text-gray-500 dark:text-gray-400">
                              {new Date(job.updated_at).toLocaleString()}
                            </td>
                            <td className="px-4 py-2">
                              <Link
                                href={`/staff/review/${job.entity_id}`}
                                className="text-blue-600 dark:text-blue-400 hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 rounded"
                              >
                                Review item
                              </Link>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </Card>

              <Card className="p-4 space-y-3">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Throughput</h2>
                <div className="space-y-2" aria-label="Throughput chart">
                  <div>
                    <div className="mb-1 flex items-center justify-between text-xs text-gray-600 dark:text-gray-400">
                      <span>Enrichments/hour</span>
                      <span className="font-semibold text-gray-900 dark:text-white">{enrichmentsPerHour}</span>
                    </div>
                    <div className="h-2 rounded-full bg-gray-200 dark:bg-gray-700" role="progressbar" aria-valuemin={0} aria-valuemax={500} aria-valuenow={Math.min(enrichmentsPerHour, 500)} aria-label="Enrichments per hour">
                      <div className="h-full rounded-full bg-blue-500" style={{ width: `${enrichmentsPerHourBar}%` }} />
                    </div>
                  </div>
                  <div>
                    <div className="mb-1 flex items-center justify-between text-xs text-gray-600 dark:text-gray-400">
                      <span>Approval rate</span>
                      <span className="font-semibold text-gray-900 dark:text-white">{approvalRate}%</span>
                    </div>
                    <div className="h-2 rounded-full bg-gray-200 dark:bg-gray-700" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={approvalRate} aria-label="Approval rate">
                      <div className="h-full rounded-full bg-green-500" style={{ width: `${approvalRate}%` }} />
                    </div>
                  </div>
                </div>
                <div className="space-y-2 text-sm">
                  <div className="flex items-center justify-between">
                    <span className="text-gray-600 dark:text-gray-400">Per minute</span>
                    <span className="font-semibold text-gray-900 dark:text-white">{data.throughput.per_minute}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-gray-600 dark:text-gray-400">Last 10 min</span>
                    <span className="font-semibold text-gray-900 dark:text-white">{data.throughput.last_10m}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-gray-600 dark:text-gray-400">Failed (10 min)</span>
                    <span className="font-semibold text-red-600 dark:text-red-400">{data.throughput.failed_last_10m}</span>
                  </div>
                </div>
              </Card>
            </section>

            <section aria-label="Error log">
              <Card className="p-4">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">Error log</h2>
                {data.error_log.length === 0 ? (
                  <p className="text-sm text-gray-500 dark:text-gray-400">No recent errors.</p>
                ) : (
                  <ul className="space-y-2" role="list">
                    {data.error_log.map((entry) => (
                      <li key={entry.id} className="rounded-md border border-red-200 dark:border-red-900 p-3">
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <p className="text-sm text-red-700 dark:text-red-300">{entry.message}</p>
                            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                              {entry.entity_id ? `Entity ${entry.entity_id} · ` : ''}
                              {new Date(entry.timestamp).toLocaleString()}
                            </p>
                          </div>
                          <button
                            onClick={() => {
                              void refetch();
                            }}
                            className="px-2.5 py-1 rounded-md text-xs font-semibold border border-red-300 dark:border-red-700 hover:bg-red-50 dark:hover:bg-red-950/30 focus:outline-none focus-visible:ring-2 focus-visible:ring-red-500"
                            disabled={isFetching}
                          >
                            Retry
                          </button>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </Card>
            </section>
          </>
        )}
      </div>
    </MainLayout>
  );
}
