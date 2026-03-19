import React from 'react';
import { ConfidenceBadge } from '../truth/ConfidenceBadge';

export interface IntentClassificationDisplayProps {
  intent?: string;
  confidence?: number;
}

export const IntentClassificationDisplay: React.FC<IntentClassificationDisplayProps> = ({
  intent,
  confidence,
}) => {
  if (!intent) {
    return (
      <p className="text-xs text-gray-500 dark:text-gray-400">
        Intent classification unavailable
      </p>
    );
  }

  return (
    <div className="flex items-center gap-2" role="status" aria-live="polite" aria-atomic="true">
      <span className="text-xs font-medium uppercase tracking-wide text-gray-500 dark:text-gray-400">
        Intent
      </span>
      <span className="text-sm font-semibold text-gray-900 dark:text-white">{intent}</span>
      {typeof confidence === 'number' && <ConfidenceBadge value={confidence} />}
    </div>
  );
};

IntentClassificationDisplay.displayName = 'IntentClassificationDisplay';
