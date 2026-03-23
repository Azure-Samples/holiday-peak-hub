'use client';

import Link from 'next/link';
import { useParams } from 'next/navigation';
import { MainLayout } from '@/components/templates/MainLayout';
import { Card } from '@/components/molecules/Card';
import { AttributeDiffView } from '@/components/enrichment/AttributeDiffView';
import { ImageEvidenceGallery } from '@/components/enrichment/ImageEvidenceGallery';
import { AgentReasoningPanel } from '@/components/enrichment/AgentReasoningPanel';
import { EnrichmentPipelineStatus } from '@/components/enrichment/EnrichmentPipelineStatus';
import {
  useEnrichmentDecision,
  useEnrichmentMonitorDetail,
} from '@/lib/hooks/useEnrichmentMonitor';

export default function EnrichmentMonitorDetailPage() {
  const params = useParams<{ entityId: string }>();
  const entityId = params?.entityId ?? '';

  const { data, isLoading, isError } = useEnrichmentMonitorDetail(entityId);
  const decisionMutation = useEnrichmentDecision();

  return (
    <MainLayout>
      <div className="space-y-6">
        <nav aria-label="Breadcrumb" className="text-sm text-gray-600 dark:text-gray-400">
          <Link
            href="/admin/enrichment-monitor"
            className="text-blue-600 dark:text-blue-400 hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 rounded"
          >
            Enrichment Monitor
          </Link>
          <span className="mx-2" aria-hidden="true">/</span>
          <span className="text-gray-900 dark:text-white">{entityId}</span>
          <span className="mx-2" aria-hidden="true">·</span>
          <Link
            href={data?.trace_id ? `/admin/agent-activity/${data.trace_id}` : '/admin/agent-activity'}
            className="text-blue-600 dark:text-blue-400 hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 rounded"
          >
            {data?.trace_id ? 'Related Trace' : 'Agent Activity'}
          </Link>
        </nav>

        {isLoading && <Card className="p-6 text-gray-600 dark:text-gray-400">Loading enrichment detail…</Card>}

        {isError && (
          <Card className="p-6 border border-red-200 dark:border-red-900 text-red-600 dark:text-red-400">
            Failed to load enrichment detail.
          </Card>
        )}

        {data && (
          <>
            <header className="flex items-start justify-between gap-4 flex-wrap">
              <div>
                <h1 className="text-3xl font-bold text-gray-900 dark:text-white">{data.title}</h1>
                <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">{data.entity_id}</p>
              </div>

              <div className="flex items-center gap-2">
                <EnrichmentPipelineStatus status={data.status} />
                <span className="text-sm font-semibold text-gray-700 dark:text-gray-300">
                  Confidence {Math.round(data.confidence * 100)}%
                </span>
              </div>
            </header>

            <section className="flex flex-wrap gap-2" aria-label="Quick actions">
              <Link
                href="/staff/review"
                className="px-4 py-2 rounded-md text-sm font-medium border border-[var(--hp-border)] bg-[var(--hp-surface-strong)] text-[var(--hp-text)] hover:bg-[var(--hp-surface)] focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
              >
                Open HITL queue
              </Link>
              <Link
                href={`/staff/review/${entityId}`}
                className="px-4 py-2 rounded-md text-sm font-medium border border-[var(--hp-border)] bg-[var(--hp-surface-strong)] text-[var(--hp-text)] hover:bg-[var(--hp-surface)] focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
              >
                Review this entity
              </Link>
              <button
                onClick={() => decisionMutation.mutate({ entityId, action: 'approve' })}
                disabled={decisionMutation.isPending}
                className="px-4 py-2 rounded-md text-sm font-medium bg-green-600 text-white hover:bg-green-700 disabled:opacity-40 focus:outline-none focus-visible:ring-2 focus-visible:ring-green-500"
              >
                Quick approve
              </button>
              <button
                onClick={() => decisionMutation.mutate({ entityId, action: 'reject' })}
                disabled={decisionMutation.isPending}
                className="px-4 py-2 rounded-md text-sm font-medium bg-red-600 text-white hover:bg-red-700 disabled:opacity-40 focus:outline-none focus-visible:ring-2 focus-visible:ring-red-500"
              >
                Quick reject
              </button>
            </section>

            <section aria-label="Original vs enriched attributes">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">Attribute differences</h2>
              <AttributeDiffView diffs={data.diffs} />
            </section>

            <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <ImageEvidenceGallery images={data.image_evidence} />
              <AgentReasoningPanel reasoning={data.reasoning} sourceAssets={data.source_assets} />
            </section>
          </>
        )}
      </div>
    </MainLayout>
  );
}
