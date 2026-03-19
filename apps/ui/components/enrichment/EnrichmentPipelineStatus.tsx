import React from 'react';
import { cn } from '../utils';

export interface EnrichmentPipelineStatusProps {
  status: string;
  className?: string;
}

function statusClasses(status: string): string {
  const normalized = status.toLowerCase();

  if (['approved', 'completed'].includes(normalized)) {
    return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200';
  }

  if (['running', 'queued', 'pending'].includes(normalized)) {
    return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200';
  }

  if (normalized === 'rejected') {
    return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200';
  }

  if (normalized === 'failed') {
    return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200';
  }

  return 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300';
}

export const EnrichmentPipelineStatus: React.FC<EnrichmentPipelineStatusProps> = ({
  status,
  className,
}) => {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold uppercase tracking-wide',
        statusClasses(status),
        className
      )}
      aria-label={`Pipeline status ${status}`}
    >
      {status}
    </span>
  );
};

EnrichmentPipelineStatus.displayName = 'EnrichmentPipelineStatus';
