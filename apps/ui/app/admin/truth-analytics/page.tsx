'use client';

import React from 'react';
import { MainLayout } from '@/components/templates/MainLayout';
import { Card } from '@/components/molecules/Card';
import { Chart } from '@/components/atoms/Chart';
import { MetricsCard } from '@/components/admin/MetricsCard';
import { CompletenessChart } from '@/components/admin/CompletenessChart';
import { PipelineFlowDiagram } from '@/components/admin/PipelineFlowDiagram';
import {
  useTruthAnalyticsSummary,
  useTruthCompletenessBreakdown,
  useTruthPipelineThroughput,
} from '@/lib/hooks/useTruthAdmin';

export default function TruthAnalyticsPage() {
  const { data: summary, isLoading: summaryLoading, isError: summaryError } = useTruthAnalyticsSummary();
  const { data: completeness = [], isLoading: completenessLoading } = useTruthCompletenessBreakdown();
  const { data: throughput = [], isLoading: throughputLoading } = useTruthPipelineThroughput();

  const throughputChartData = throughput.map((pt) => ({
    time: new Date(pt.timestamp).toLocaleDateString(),
    ingested: pt.ingested,
    enriched: pt.enriched,
    approved: pt.approved,
  }));

  return (
    <MainLayout>
      <div className="max-w-7xl mx-auto py-8 space-y-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Truth Layer Analytics</h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">
            Monitor catalog completeness, enrichment pipeline health, and HITL review throughput.
          </p>
        </div>

        {summaryLoading && (
          <Card className="p-6 text-gray-600 dark:text-gray-400">Loading analytics...</Card>
        )}

        {summaryError && (
          <Card className="p-6 border border-red-200 dark:border-red-900 text-red-600 dark:text-red-400">
            Failed to load analytics data.
          </Card>
        )}

        {summary && (
          <>
            {/* KPI Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <MetricsCard
                label="Overall Completeness"
                value={`${Math.round(summary.overall_completeness * 100)}%`}
                description={`Across ${summary.total_products.toLocaleString()} products`}
              />
              <MetricsCard
                label="Enrichment Jobs"
                value={summary.enrichment_jobs_processed.toLocaleString()}
                description={`${summary.auto_approved.toLocaleString()} auto-approved`}
              />
              <MetricsCard
                label="HITL Queue Pending"
                value={summary.queue_pending.toLocaleString()}
                description={`Avg review time: ${summary.avg_review_time_minutes.toFixed(1)} min`}
                trend={summary.queue_pending > 50 ? 'up' : 'neutral'}
                trendValue={summary.queue_pending > 50 ? 'High' : 'Normal'}
              />
              <MetricsCard
                label="Exports"
                value={(summary.acp_exports + summary.ucp_exports).toLocaleString()}
                description={`ACP: ${summary.acp_exports.toLocaleString()} | UCP: ${summary.ucp_exports.toLocaleString()}`}
              />
            </div>

            {/* Review Queue Breakdown */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <MetricsCard
                label="Queue Approved"
                value={summary.queue_approved.toLocaleString()}
                trend="up"
                trendValue="Approved"
              />
              <MetricsCard
                label="Queue Rejected"
                value={summary.queue_rejected.toLocaleString()}
                trend="down"
                trendValue="Rejected"
              />
              <MetricsCard
                label="Sent to HITL"
                value={summary.sent_to_hitl.toLocaleString()}
                description="Requires human review"
              />
            </div>

            {/* Pipeline Flow */}
            <PipelineFlowDiagram
              ingested={summary.enrichment_jobs_processed}
              enriched={summary.enrichment_jobs_processed}
              autoApproved={summary.auto_approved}
              sentToHitl={summary.sent_to_hitl}
              exported={summary.acp_exports + summary.ucp_exports}
            />
          </>
        )}

        {/* Completeness by Category */}
        <CompletenessChart data={completeness} isLoading={completenessLoading} />

        {/* Pipeline Throughput Chart */}
        <Card className="p-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Pipeline Throughput (Time Series)
          </h3>
          {throughputLoading ? (
            <div className="h-64 flex items-center justify-center text-gray-500 dark:text-gray-400">
              Loading chart...
            </div>
          ) : throughputChartData.length === 0 ? (
            <div className="h-64 flex items-center justify-center text-gray-500 dark:text-gray-400">
              No throughput data available
            </div>
          ) : (
            <Chart
              type="area"
              data={throughputChartData}
              series={[
                { dataKey: 'ingested', name: 'Ingested', color: '#0ea5e9' },
                { dataKey: 'enriched', name: 'Enriched', color: '#84cc16' },
                { dataKey: 'approved', name: 'Approved', color: '#22c55e' },
              ]}
              xAxisKey="time"
              height={300}
              showGrid
              showTooltip
              showLegend
            />
          )}
        </Card>
      </div>
    </MainLayout>
  );
}
