/**
 * Spinner Atom Component
 * Loading spinner indicator
 */

import React from 'react';
import { cn } from '../utils';
import type { Size, BaseComponentProps } from '../types';

export interface SpinnerProps extends BaseComponentProps {
  /** Spinner size */
  size?: Size;
  /** Spinner color */
  color?: string;
  /** Optional label */
  label?: string;
}

const sizeMap: Record<Size, string> = {
  xs: 'h-3 w-3',
  sm: 'h-4 w-4',
  md: 'h-5 w-5',
  lg: 'h-8 w-8',
  xl: 'h-12 w-12',
};

export const Spinner: React.FC<SpinnerProps> = ({
  size = 'md',
  color = 'text-blue-600',
  label,
  className,
  testId,
  ariaLabel,
}) => {
  return (
    <div
      data-testid={testId}
      role="status"
      aria-label={ariaLabel || label || 'Loading'}
      className={cn('inline-flex items-center gap-2', className)}
    >
      <svg
        className={cn('animate-spin', color, sizeMap[size])}
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
      >
        <circle
          className="opacity-25"
          cx="12"
          cy="12"
          r="10"
          stroke="currentColor"
          strokeWidth="4"
        />
        <path
          className="opacity-75"
          fill="currentColor"
          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
        />
      </svg>
      
      {label && (
        <span className="text-sm text-gray-600 dark:text-gray-400">
          {label}
        </span>
      )}
    </div>
  );
};

Spinner.displayName = 'Spinner';
