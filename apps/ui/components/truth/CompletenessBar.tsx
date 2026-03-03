import React from 'react';
import { cn } from '../utils';

export interface CompletenessBarProps {
  value: number;
  className?: string;
  showLabel?: boolean;
}

function getVariantClasses(value: number): string {
  if (value >= 0.8) return 'bg-green-500';
  if (value >= 0.5) return 'bg-yellow-500';
  return 'bg-red-500';
}

export const CompletenessBar: React.FC<CompletenessBarProps> = ({
  value,
  className,
  showLabel = true,
}) => {
  const pct = Math.min(Math.max(Math.round(value * 100), 0), 100);

  return (
    <div className={cn('w-full', className)}>
      {showLabel && (
        <div className="flex justify-between items-center mb-1">
          <span className="text-xs font-medium text-gray-600 dark:text-gray-400">
            Completeness
          </span>
          <span className="text-xs font-semibold text-gray-800 dark:text-gray-200">
            {pct}%
          </span>
        </div>
      )}
      <div
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`Product completeness: ${pct}%`}
        className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden"
      >
        <div
          style={{ width: `${pct}%` }}
          className={cn(
            'h-full rounded-full transition-all duration-300',
            getVariantClasses(value)
          )}
        />
      </div>
    </div>
  );
};

CompletenessBar.displayName = 'CompletenessBar';
