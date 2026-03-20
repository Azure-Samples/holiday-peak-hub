import React from 'react';
import { Card } from '../molecules/Card';
import { ConfidenceBadge } from '../truth/ConfidenceBadge';
import type { SemanticSearchIntent } from '@/lib/services/semanticSearchService';

export interface IntentPanelProps {
  mode: 'keyword' | 'intelligent';
  intent?: SemanticSearchIntent | null;
  subqueries?: string[];
}

function formatEntityValue(value: unknown): string {
  if (Array.isArray(value)) {
    return value.map((entry) => String(entry)).join(', ');
  }
  if (value && typeof value === 'object') {
    return JSON.stringify(value);
  }
  return String(value);
}

export const IntentPanel: React.FC<IntentPanelProps> = ({ mode, intent, subqueries = [] }) => {
  if (mode !== 'intelligent') {
    return null;
  }

  const entities = intent?.entities && typeof intent.entities === 'object'
    ? Object.entries(intent.entities).filter(([, value]) => value !== null && value !== undefined && value !== '')
    : [];

  const hasData = Boolean(intent?.intent) || typeof intent?.confidence === 'number' || entities.length > 0 || subqueries.length > 0;

  if (!hasData) {
    return null;
  }

  return (
    <div role="region" aria-label="Search intent details">
      <Card className="border border-[var(--hp-border)] bg-[var(--hp-surface)] p-4">
        <details>
          <summary className="cursor-pointer list-none text-sm font-semibold uppercase tracking-wide text-[var(--hp-text-muted)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--hp-focus)]">
            Intent details
          </summary>

          <div className="mt-3 space-y-3 text-sm text-[var(--hp-text)]">
            {intent?.intent ? (
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-semibold">Intent:</span>
                <span>{intent.intent}</span>
                {typeof intent.confidence === 'number' ? <ConfidenceBadge value={intent.confidence} /> : null}
              </div>
            ) : null}

            {entities.length > 0 ? (
              <div>
                <p className="mb-1 font-semibold">Entities</p>
                <ul className="grid grid-cols-1 gap-1 sm:grid-cols-2" aria-label="Intent entities">
                  {entities.map(([key, value]) => (
                    <li key={key} className="rounded-lg border border-[var(--hp-border)] bg-[var(--hp-surface-strong)] px-2 py-1">
                      <span className="font-medium">{key}: </span>
                      <span>{formatEntityValue(value)}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}

            {subqueries.length > 0 ? (
              <div>
                <p className="mb-1 font-semibold">Subqueries</p>
                <ul className="list-disc space-y-1 pl-5" aria-label="Generated subqueries">
                  {subqueries.map((subquery) => (
                    <li key={subquery}>{subquery}</li>
                  ))}
                </ul>
              </div>
            ) : null}
          </div>
        </details>
      </Card>
    </div>
  );
};

IntentPanel.displayName = 'IntentPanel';
