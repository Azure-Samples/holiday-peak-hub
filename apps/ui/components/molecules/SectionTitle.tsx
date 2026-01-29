/**
 * SectionTitle Molecule Component
 * Page/section header with title and optional actions
 */

import React from 'react';
import { cn } from '../utils';
import type { BaseComponentProps } from '../types';

export interface SectionTitleProps extends BaseComponentProps {
  /** Main title */
  title: React.ReactNode;
  /** Subtitle or description */
  subtitle?: React.ReactNode;
  /** Right-side actions or content */
  actions?: React.ReactNode;
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Show bottom border */
  bordered?: boolean;
}

const sizeConfig = {
  sm: {
    title: 'text-lg font-semibold',
    subtitle: 'text-sm',
  },
  md: {
    title: 'text-xl font-bold',
    subtitle: 'text-base',
  },
  lg: {
    title: 'text-2xl font-bold',
    subtitle: 'text-lg',
  },
};

export const SectionTitle: React.FC<SectionTitleProps> = ({
  title,
  subtitle,
  actions,
  size = 'md',
  bordered = false,
  className,
  testId,
  ariaLabel,
}) => {
  const config = sizeConfig[size];

  return (
    <div
      data-testid={testId}
      aria-label={ariaLabel}
      className={cn(
        'w-full mb-6',
        bordered && 'pb-4 border-b border-gray-200 dark:border-gray-700',
        className
      )}
    >
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        {/* Title Section */}
        <div className="flex flex-col gap-1">
          {typeof title === 'string' ? (
            <h2
              className={cn(
                'text-gray-900 dark:text-white',
                config.title
              )}
            >
              {title}
            </h2>
          ) : (
            <div className={cn('text-gray-900 dark:text-white', config.title)}>
              {title}
            </div>
          )}

          {subtitle && (
            <div
              className={cn(
                'text-gray-600 dark:text-gray-400',
                config.subtitle
              )}
            >
              {subtitle}
            </div>
          )}
        </div>

        {/* Actions Section */}
        {actions && (
          <div className="flex items-center gap-2">
            {actions}
          </div>
        )}
      </div>
    </div>
  );
};

SectionTitle.displayName = 'SectionTitle';
