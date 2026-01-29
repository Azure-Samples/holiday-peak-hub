/**
 * ProgressBar Atom Component
 * Visual progress indicator
 */

import React from 'react';
import { cn } from '../utils';
import type { BaseComponentProps, Size, Variant } from '../types';

export interface ProgressBarProps extends BaseComponentProps {
  /** Current progress value (0-100) */
  value: number;
  /** Maximum value (default 100) */
  max?: number;
  /** Size variant */
  size?: Extract<Size, 'sm' | 'md' | 'lg'>;
  /** Color variant */
  variant?: Variant;
  /** Show percentage text */
  showValue?: boolean;
  /** Custom label */
  label?: string;
  /** Striped pattern */
  striped?: boolean;
  /** Animated stripes */
  animated?: boolean;
}

const sizeClasses = {
  sm: 'h-1',
  md: 'h-2',
  lg: 'h-3',
};

const variantClasses = {
  primary: 'bg-blue-600',
  secondary: 'bg-gray-600',
  success: 'bg-green-600',
  error: 'bg-red-600',
  warning: 'bg-yellow-600',
  info: 'bg-cyan-600',
  default: 'bg-blue-600',
};

export const ProgressBar: React.FC<ProgressBarProps> = ({
  value,
  max = 100,
  size = 'md',
  variant = 'primary',
  showValue = false,
  label,
  striped = false,
  animated = false,
  className,
  testId,
  ariaLabel,
}) => {
  const percentage = Math.min(Math.max((value / max) * 100, 0), 100);

  return (
    <div
      data-testid={testId}
      aria-label={ariaLabel}
      className={cn('w-full', className)}
    >
      {/* Label/Value */}
      {(label || showValue) && (
        <div className="flex justify-between items-center mb-1">
          {label && (
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
              {label}
            </span>
          )}
          {showValue && (
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
              {Math.round(percentage)}%
            </span>
          )}
        </div>
      )}

      {/* Progress Bar */}
      <div
        role="progressbar"
        aria-valuenow={value}
        aria-valuemin={0}
        aria-valuemax={max}
        className={cn(
          'w-full bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden',
          sizeClasses[size]
        )}
      >
        <div
          style={{ width: `${percentage}%` }}
          className={cn(
            'h-full rounded-full transition-all duration-300 ease-out',
            variantClasses[variant],
            striped && 'bg-gradient-to-r from-transparent via-white/20 to-transparent bg-[length:20px_100%]',
            animated && striped && 'animate-[shimmer_1s_ease-in-out_infinite]'
          )}
        />
      </div>
    </div>
  );
};

ProgressBar.displayName = 'ProgressBar';
