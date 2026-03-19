import React from 'react';
import type { AgentModelUsageRow } from '@/lib/types/api';

export interface ModelUsageTableProps {
  rows: AgentModelUsageRow[];
}

function tierClass(tier: string): string {
  if (tier === 'slm') {
    return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200';
  }

  if (tier === 'llm') {
    return 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200';
  }

  return 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300';
}

export const ModelUsageTable: React.FC<ModelUsageTableProps> = ({ rows }) => {
  if (rows.length === 0) {
    return <p className="text-sm text-gray-500 dark:text-gray-400">No model usage available for this time range.</p>;
  }

  return (
    <div className="overflow-x-auto">
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
  );
};

ModelUsageTable.displayName = 'ModelUsageTable';
