import React from 'react';
import type { EnrichmentAttributeDiff } from '@/lib/types/api';
import { Card } from '../molecules/Card';
import { ConfidenceBadge } from '../truth/ConfidenceBadge';
import { IntentClassificationDisplay } from './IntentClassificationDisplay';

export interface AttributeDiffViewProps {
  diffs: EnrichmentAttributeDiff[];
}

export const AttributeDiffView: React.FC<AttributeDiffViewProps> = ({ diffs }) => {
  if (diffs.length === 0) {
    return (
      <Card className="p-4 text-sm text-gray-500 dark:text-gray-400">
        No attribute differences available.
      </Card>
    );
  }

  return (
    <div className="space-y-3" role="list" aria-label="Attribute differences">
      {diffs.map((diff, index) => (
        <div key={`${diff.field_name}-${index}`} role="listitem">
          <Card className="p-4">
            <div className="flex items-start justify-between gap-3 flex-wrap">
              <h3 className="text-sm font-semibold capitalize text-gray-900 dark:text-white">
                {diff.field_name.replace(/_/g, ' ')}
              </h3>
              <div className="flex items-center gap-2">
                <span className="text-xs font-medium text-gray-500 dark:text-gray-400">
                  {diff.source_type}
                </span>
                <ConfidenceBadge value={diff.confidence} />
              </div>
            </div>

            <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
              <div className="rounded-md border border-gray-200 dark:border-gray-700 p-3">
                <p className="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">Original</p>
                <p className="mt-1 text-gray-700 dark:text-gray-300">
                  {diff.original_value || '—'}
                </p>
              </div>
              <div className="rounded-md border border-blue-200 dark:border-blue-900 p-3 bg-blue-50/40 dark:bg-blue-950/20">
                <p className="text-xs uppercase tracking-wide text-blue-700 dark:text-blue-300">Enriched</p>
                <p className="mt-1 font-medium text-gray-900 dark:text-white">{diff.enriched_value}</p>
              </div>
            </div>

            <div className="mt-3 space-y-2">
              <IntentClassificationDisplay intent={diff.intent} confidence={diff.intent_confidence} />
              {diff.reasoning && (
                <p className="text-sm text-gray-700 dark:text-gray-300">{diff.reasoning}</p>
              )}
            </div>
          </Card>
        </div>
      ))}
    </div>
  );
};

AttributeDiffView.displayName = 'AttributeDiffView';
