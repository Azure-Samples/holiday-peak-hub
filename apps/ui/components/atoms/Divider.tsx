/**
 * Divider Atom Component
 * Horizontal or vertical separator line
 */

import React from 'react';
import { cn } from '../utils';
import type { BaseComponentProps } from '../types';

export interface DividerProps extends BaseComponentProps {
  /** Orientation of divider */
  orientation?: 'horizontal' | 'vertical';
  /** Optional label to show in divider */
  label?: string;
  /** Label position */
  labelPosition?: 'left' | 'center' | 'right';
  /** Divider color */
  color?: string;
  /** Spacing around divider */
  spacing?: 'sm' | 'md' | 'lg';
}

export const Divider: React.FC<DividerProps> = ({
  orientation = 'horizontal',
  label,
  labelPosition = 'center',
  color = 'border-gray-200 dark:border-gray-700',
  spacing = 'md',
  className,
  testId,
  ariaLabel,
}) => {
  const spacingClasses = {
    sm: orientation === 'horizontal' ? 'my-2' : 'mx-2',
    md: orientation === 'horizontal' ? 'my-4' : 'mx-4',
    lg: orientation === 'horizontal' ? 'my-6' : 'mx-6',
  };

  if (orientation === 'vertical') {
    return (
      <div
        data-testid={testId}
        aria-label={ariaLabel || 'Vertical divider'}
        role="separator"
        aria-orientation="vertical"
        className={cn(
          'inline-block h-full w-px border-l',
          color,
          spacingClasses[spacing],
          className
        )}
      />
    );
  }

  // Horizontal divider without label
  if (!label) {
    return (
      <hr
        data-testid={testId}
        aria-label={ariaLabel || 'Horizontal divider'}
        className={cn(
          'border-t',
          color,
          spacingClasses[spacing],
          className
        )}
      />
    );
  }

  // Horizontal divider with label
  return (
    <div
      data-testid={testId}
      aria-label={ariaLabel || 'Horizontal divider'}
      role="separator"
      className={cn(
        'relative flex items-center',
        spacingClasses[spacing],
        className
      )}
    >
      {(labelPosition === 'center' || labelPosition === 'right') && (
        <div className={cn('flex-grow border-t', color)} />
      )}
      
      <span
        className={cn(
          'text-sm text-gray-500 dark:text-gray-400',
          labelPosition === 'center' && 'px-3',
          labelPosition === 'left' && 'pr-3',
          labelPosition === 'right' && 'pl-3'
        )}
      >
        {label}
      </span>
      
      {(labelPosition === 'center' || labelPosition === 'left') && (
        <div className={cn('flex-grow border-t', color)} />
      )}
    </div>
  );
};

Divider.displayName = 'Divider';
