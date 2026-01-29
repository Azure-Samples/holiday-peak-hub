/**
 * Label Atom Component
 * Form label with support for required indicator and tooltips
 */

import React from 'react';
import { cn } from '../utils';
import type { BaseComponentProps } from '../types';

export interface LabelProps extends BaseComponentProps {
  /** Label text */
  children: React.ReactNode;
  /** Associated input name/id */
  htmlFor?: string;
  /** Whether field is required */
  required?: boolean;
  /** Whether to show required asterisk */
  showRequiredIndicator?: boolean;
  /** Optional tooltip */
  tooltip?: string;
}

export const Label: React.FC<LabelProps> = ({
  children,
  htmlFor,
  required = false,
  showRequiredIndicator = true,
  tooltip,
  className,
  testId,
}) => {
  return (
    <label
      htmlFor={htmlFor}
      data-testid={testId}
      className={cn(
        'block text-sm font-medium',
        'text-gray-700 dark:text-gray-200',
        'whitespace-nowrap',
        className
      )}
    >
      {children}
      {required && showRequiredIndicator && (
        <span className="ml-1 text-red-500" aria-label="required">
          *
        </span>
      )}
      {tooltip && (
        <span
          className="ml-1 text-gray-400 cursor-help"
          title={tooltip}
          aria-label={tooltip}
        >
          ?
        </span>
      )}
    </label>
  );
};

Label.displayName = 'Label';
