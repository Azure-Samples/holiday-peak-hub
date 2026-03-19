import React from 'react';
import type { AgentEvaluationComparisonRow } from '@/lib/types/api';

export interface EvaluationComparisonTableProps {
  rows: AgentEvaluationComparisonRow[];
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

export const EvaluationComparisonTable: React.FC<EvaluationComparisonTableProps> = ({ rows }) => {
  if (rows.length === 0) {
    return <p className="text-sm text-gray-500 dark:text-gray-400">No evaluation comparison data available.</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead className="bg-gray-50 dark:bg-gray-900/40">
          <tr>
            <th className="px-4 py-2 text-left font-semibold text-gray-700 dark:text-gray-300">Model</th>
            <th className="px-4 py-2 text-left font-semibold text-gray-700 dark:text-gray-300">Tier</th>
            <th className="px-4 py-2 text-left font-semibold text-gray-700 dark:text-gray-300">Dataset</th>
            <th className="px-4 py-2 text-left font-semibold text-gray-700 dark:text-gray-300">Score</th>
            <th className="px-4 py-2 text-left font-semibold text-gray-700 dark:text-gray-300">Pass rate</th>
            <th className="px-4 py-2 text-left font-semibold text-gray-700 dark:text-gray-300">Latency</th>
            <th className="px-4 py-2 text-left font-semibold text-gray-700 dark:text-gray-300">Cost / 1K</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={`${row.model_name}-${row.dataset}-${row.model_tier}`} className="border-t border-gray-200 dark:border-gray-700">
              <td className="px-4 py-2 text-gray-900 dark:text-white">{row.model_name}</td>
              <td className="px-4 py-2">
                <span className={`inline-flex rounded-full px-2 py-1 text-xs font-semibold uppercase tracking-wide ${tierClass(row.model_tier)}`}>
                  {row.model_tier}
                </span>
              </td>
              <td className="px-4 py-2 text-gray-700 dark:text-gray-300">{row.dataset}</td>
              <td className="px-4 py-2 text-gray-700 dark:text-gray-300">{row.score.toFixed(3)}</td>
              <td className="px-4 py-2 text-gray-700 dark:text-gray-300">{(row.pass_rate * 100).toFixed(1)}%</td>
              <td className="px-4 py-2 text-gray-700 dark:text-gray-300">{Math.round(row.avg_latency_ms)} ms</td>
              <td className="px-4 py-2 text-gray-700 dark:text-gray-300">${row.cost_per_1k_tokens.toFixed(4)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

EvaluationComparisonTable.displayName = 'EvaluationComparisonTable';
