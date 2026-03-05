import React from 'react';
import { cn } from '../utils';

export interface ConfidenceBadgeProps {
  value: number;
  className?: string;
}

function getConfidenceLabel(value: number): string {
  if (value >= 0.85) return 'High';
  if (value >= 0.5) return 'Medium';
  return 'Low';
}

function getConfidenceClasses(value: number): string {
  if (value >= 0.85) return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200';
  if (value >= 0.5) return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200';
  return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200';
}

export const ConfidenceBadge: React.FC<ConfidenceBadgeProps> = ({ value, className }) => {
  const pct = Math.round(value * 100);
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold',
        getConfidenceClasses(value),
        className
      )}
      aria-label={`Confidence: ${pct}% (${getConfidenceLabel(value)})`}
    >
      <span className="tabular-nums">{pct}%</span>
      <span>{getConfidenceLabel(value)}</span>
    </span>
  );
};

ConfidenceBadge.displayName = 'ConfidenceBadge';
