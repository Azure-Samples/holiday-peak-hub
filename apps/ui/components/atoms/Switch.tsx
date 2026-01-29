/**
 * Switch Atom Component
 * Toggle switch for binary options
 */

import React from 'react';
import { cn } from '../utils';
import type { BaseComponentProps, Size } from '../types';

export interface SwitchProps extends BaseComponentProps {
  /** Whether the switch is checked */
  checked: boolean;
  /** Change handler */
  onChange: (checked: boolean) => void;
  /** Label text */
  label?: string;
  /** Description text */
  description?: string;
  /** Size variant */
  size?: Extract<Size, 'sm' | 'md' | 'lg'>;
  /** Whether switch is disabled */
  disabled?: boolean;
  /** Label position */
  labelPosition?: 'left' | 'right';
}

const sizeConfig = {
  sm: {
    track: 'h-5 w-9',
    thumb: 'h-4 w-4',
    translate: 'translate-x-4',
  },
  md: {
    track: 'h-6 w-11',
    thumb: 'h-5 w-5',
    translate: 'translate-x-5',
  },
  lg: {
    track: 'h-7 w-14',
    thumb: 'h-6 w-6',
    translate: 'translate-x-7',
  },
};

export const Switch: React.FC<SwitchProps> = ({
  checked,
  onChange,
  label,
  description,
  size = 'md',
  disabled = false,
  labelPosition = 'left',
  className,
  testId,
  ariaLabel,
}) => {
  const config = sizeConfig[size];

  const switchElement = (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={ariaLabel || label}
      data-testid={testId}
      onClick={() => !disabled && onChange(!checked)}
      disabled={disabled}
      className={cn(
        'relative inline-flex items-center rounded-full transition-colors',
        'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2',
        'dark:focus:ring-offset-gray-900',
        config.track,
        checked
          ? 'bg-blue-600 dark:bg-blue-500'
          : 'bg-gray-200 dark:bg-gray-700',
        disabled && 'opacity-50 cursor-not-allowed',
        !disabled && 'cursor-pointer'
      )}
    >
      <span
        className={cn(
          'inline-block bg-white dark:bg-gray-900 rounded-full shadow-lg transform transition-transform',
          config.thumb,
          checked ? config.translate : 'translate-x-0.5'
        )}
      />
    </button>
  );

  if (!label && !description) {
    return switchElement;
  }

  const labelElement = (
    <div className="flex flex-col">
      {label && (
        <span className="text-sm font-medium text-gray-900 dark:text-white">
          {label}
        </span>
      )}
      {description && (
        <span className="text-xs text-gray-500 dark:text-gray-400">
          {description}
        </span>
      )}
    </div>
  );

  return (
    <div className={cn('flex items-center gap-3', className)}>
      {labelPosition === 'left' && labelElement}
      {switchElement}
      {labelPosition === 'right' && labelElement}
    </div>
  );
};

Switch.displayName = 'Switch';
