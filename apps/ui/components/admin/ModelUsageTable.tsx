import React from 'react';
import type { AgentModelUsageRow } from '@/lib/types/api';

export interface ModelUsageTableProps {
  rows: AgentModelUsageRow[];
}

function tierClass(tier: string): string {
  if (tier === 'slm') {
    return 'bg-cyan-100 text-cyan-800 dark:bg-cyan-900 dark:text-cyan-100';
  }

  if (tier === 'llm') {
    return 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-100';
  }

  return 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300';
}

export const ModelUsageTable: React.FC<ModelUsageTableProps> = ({ rows }) => {
  if (rows.length === 0) {
    return <p className="text-sm text-gray-500 dark:text-gray-400">No model usage available for this time range.</p>;
  }

  return (
    <div>
      <div className="space-y-3 md:hidden" aria-label="Model usage cards">
        {rows.map((row) => (
          <article
            key={`${row.model_name}-${row.model_tier}`}
            className="rounded-xl border border-[var(--hp-border)] bg-[var(--hp-surface)] p-3"
          >
            <div className="flex items-start justify-between gap-3">
              <h3 className="font-semibold text-[var(--hp-text)]">{row.model_name}</h3>
              <span className={`inline-flex rounded-full px-2 py-1 text-xs font-semibold uppercase tracking-wide ${tierClass(row.model_tier)}`}>
                {row.model_tier}
              </span>
            </div>

            <dl className="mt-3 grid grid-cols-2 gap-2 text-xs">
              <div className="rounded-lg bg-[var(--hp-surface-strong)] p-2">
                <dt className="text-[var(--hp-text-muted)]">Requests</dt>
                <dd className="font-semibold text-[var(--hp-text)]">{row.requests.toLocaleString()}</dd>
              </div>
              <div className="rounded-lg bg-[var(--hp-surface-strong)] p-2">
                <dt className="text-[var(--hp-text-muted)]">Total tokens</dt>
                <dd className="font-semibold text-[var(--hp-text)]">{row.total_tokens.toLocaleString()}</dd>
              </div>
              <div className="rounded-lg bg-[var(--hp-surface-strong)] p-2">
                <dt className="text-[var(--hp-text-muted)]">Avg latency</dt>
                <dd className="font-semibold text-[var(--hp-text)]">{Math.round(row.avg_latency_ms)} ms</dd>
              </div>
              <div className="rounded-lg bg-[var(--hp-surface-strong)] p-2">
                <dt className="text-[var(--hp-text-muted)]">Cost</dt>
                <dd className="font-semibold text-[var(--hp-text)]">${row.cost_usd.toFixed(2)}</dd>
              </div>
            </dl>
          </article>
        ))}
      </div>

      <div className="hidden overflow-x-auto md:block">
        <table className="min-w-full text-sm">
          <thead className="bg-gray-50 dark:bg-gray-900/40">
            <tr>
              <th className="px-4 py-2 text-left font-semibold text-gray-700 dark:text-gray-300">Model</th>
              <th className="px-4 py-2 text-left font-semibold text-gray-700 dark:text-gray-300">Tier</th>
              <th className="px-4 py-2 text-left font-semibold text-gray-700 dark:text-gray-300">Requests</th>
              <th className="px-4 py-2 text-left font-semibold text-gray-700 dark:text-gray-300">Tokens</th>
              <th className="px-4 py-2 text-left font-semibold text-gray-700 dark:text-gray-300">Avg latency</th>
              <th className="px-4 py-2 text-left font-semibold text-gray-700 dark:text-gray-300">Cost</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={`${row.model_name}-${row.model_tier}`} className="border-t border-gray-200 dark:border-gray-700">
                <td className="px-4 py-2 text-gray-900 dark:text-white">{row.model_name}</td>
                <td className="px-4 py-2">
                  <span className={`inline-flex rounded-full px-2 py-1 text-xs font-semibold uppercase tracking-wide ${tierClass(row.model_tier)}`}>
                    {row.model_tier}
                  </span>
                </td>
                <td className="px-4 py-2 text-gray-700 dark:text-gray-300">{row.requests.toLocaleString()}</td>
                <td className="px-4 py-2 text-gray-700 dark:text-gray-300">{row.total_tokens.toLocaleString()}</td>
                <td className="px-4 py-2 text-gray-700 dark:text-gray-300">{Math.round(row.avg_latency_ms)} ms</td>
                <td className="px-4 py-2 text-gray-700 dark:text-gray-300">${row.cost_usd.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

ModelUsageTable.displayName = 'ModelUsageTable';
