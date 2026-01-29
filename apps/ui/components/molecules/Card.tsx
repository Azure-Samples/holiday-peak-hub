/**
 * Card Molecule Component
 * Container component with header, body, and footer sections
 * Enhanced from components/Card.tsx
 */

import React from 'react';
import { cn } from '../utils';
import type { BaseComponentProps } from '../types';

export interface CardProps extends BaseComponentProps {
  /** Card content */
  children: React.ReactNode;
  /** Card title (renders in header) */
  title?: string;
  /** Card subtitle */
  subtitle?: string;
  /** Header content (overrides title/subtitle) */
  header?: React.ReactNode;
  /** Footer content */
  footer?: React.ReactNode;
  /** Card variant */
  variant?: 'default' | 'outlined' | 'elevated' | 'flat';
  /** Whether card has hover effect */
  hoverable?: boolean;
  /** Whether card is clickable */
  clickable?: boolean;
  /** Click handler for entire card */
  onClick?: () => void;
  /** Custom padding */
  padding?: 'none' | 'sm' | 'md' | 'lg';
  /** Whether to remove border radius */
  square?: boolean;
}

export const Card: React.FC<CardProps> = ({
  children,
  title,
  subtitle,
  header,
  footer,
  variant = 'default',
  hoverable = false,
  clickable = false,
  onClick,
  padding = 'md',
  square = false,
  className,
  testId,
  ariaLabel,
}) => {
  const paddingClasses = {
    none: '',
    sm: 'p-3',
    md: 'p-4',
    lg: 'p-6',
  };

  const variantClasses = {
    default: 'bg-white dark:bg-gray-800 shadow-sm',
    outlined: 'bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700',
    elevated: 'bg-white dark:bg-gray-800 shadow-lg',
    flat: 'bg-gray-50 dark:bg-gray-900',
  };

  const hasHeader = title || subtitle || header;

  return (
    <div
      data-testid={testId}
      aria-label={ariaLabel}
      onClick={clickable ? onClick : undefined}
      className={cn(
        'w-full',
        variantClasses[variant],
        !square && 'rounded-lg',
        hoverable && 'transition-shadow duration-200 hover:shadow-md',
        clickable && 'cursor-pointer',
        className
      )}
    >
      {hasHeader && (
        <div
          className={cn(
            'border-b border-gray-200 dark:border-gray-700',
            paddingClasses[padding]
          )}
        >
          {header || (
            <div>
              {title && (
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                  {title}
                </h3>
              )}
              {subtitle && (
                <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                  {subtitle}
                </p>
              )}
            </div>
          )}
        </div>
      )}

      <div className={cn(paddingClasses[padding])}>
        {children}
      </div>

      {footer && (
        <div
          className={cn(
            'border-t border-gray-200 dark:border-gray-700',
            paddingClasses[padding]
          )}
        >
          {footer}
        </div>
      )}
    </div>
  );
};

Card.displayName = 'Card';
