import React from 'react';
import { Card } from '../molecules/Card';
import type { AgentHealthCardMetric } from '@/lib/types/api';

export interface AgentHealthCardProps {
  metric: AgentHealthCardMetric;
}

const STATUS_CLASS_MAP: Record<AgentHealthCardMetric['status'], string> = {
  healthy: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  degraded: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
  down: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
  unknown: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
};

function formatErrorRate(errorRate: number): string {
  if (errorRate <= 1) {
    return `${(errorRate * 100).toFixed(2)}%`;
  }

  return `${errorRate.toFixed(2)}%`;
}

export const AgentHealthCard: React.FC<AgentHealthCardProps> = ({ metric }) => {
  return (
    <Card className="p-4 space-y-3">
      <div className="flex items-start justify-between gap-3">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-white">{metric.label}</h3>
        <span
          className={`inline-flex items-center rounded-full px-2 py-1 text-xs font-semibold uppercase tracking-wide ${STATUS_CLASS_MAP[metric.status]}`}
          aria-label={`${metric.label} status ${metric.status}`}
        >
          {metric.status}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-2 text-sm">
        <MetricItem label="Latency" value={`${Math.round(metric.latency_ms)} ms`} />
        <MetricItem label="Error rate" value={formatErrorRate(metric.error_rate)} />
        <MetricItem label="Throughput" value={`${Math.round(metric.throughput_rpm)} rpm`} />
        <MetricItem label="Updated" value={new Date(metric.updated_at).toLocaleTimeString()} />
      </div>
    </Card>
  );
};

function MetricItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md bg-gray-50 p-2 dark:bg-gray-900/50">
      <p className="text-xs text-gray-500 dark:text-gray-400">{label}</p>
      <p className="font-semibold text-gray-900 dark:text-white">{value}</p>
    </div>
  );
}

AgentHealthCard.displayName = 'AgentHealthCard';
