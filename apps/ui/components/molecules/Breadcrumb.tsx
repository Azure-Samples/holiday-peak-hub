/**
 * Breadcrumb Molecule Component
 * Breadcrumb navigation with separators
 * Migrated from components/breadcrumbs/index.tsx
 */

import React from 'react';
import Link from 'next/link';
import { FiChevronRight, FiHome } from 'react-icons/fi';
import { cn } from '../utils';
import type { BaseComponentProps } from '../types';

export interface BreadcrumbItem {
  /** Item label */
  label: string;
  /** Item href (if clickable) */
  href?: string;
  /** Whether item is current page */
  current?: boolean;
  /** Custom icon */
  icon?: React.ReactNode;
}

export interface BreadcrumbProps extends BaseComponentProps {
  /** Breadcrumb items */
  items: BreadcrumbItem[];
  /** Custom separator */
  separator?: React.ReactNode;
  /** Whether to show home icon for first item */
  showHomeIcon?: boolean;
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
}

export const Breadcrumb: React.FC<BreadcrumbProps> = ({
  items,
  separator,
  showHomeIcon = false,
  size = 'md',
  className,
  testId,
  ariaLabel,
}) => {
  const sizeClasses = {
    sm: 'text-xs',
    md: 'text-sm',
    lg: 'text-base',
  };

  const DefaultSeparator = () => (
    <FiChevronRight className="w-4 h-4 text-gray-400 dark:text-gray-500" />
  );

  return (
    <nav
      aria-label={ariaLabel || 'Breadcrumb'}
      data-testid={testId}
      className={cn('flex items-center space-x-2', sizeClasses[size], className)}
    >
      <ol className="flex items-center space-x-2">
        {items.map((item, index) => {
          const isLast = index === items.length - 1;
          const isFirst = index === 0;

          return (
            <li key={index} className="flex items-center space-x-2">
              {item.href && !item.current ? (
                <Link
                  href={item.href}
                  className={cn(
                    'flex items-center gap-1',
                    'text-gray-600 dark:text-gray-400',
                    'hover:text-gray-900 dark:hover:text-white',
                    'transition-colors duration-200'
                  )}
                >
                  {isFirst && showHomeIcon && !item.icon && (
                    <FiHome className="w-4 h-4" />
                  )}
                  {item.icon && <span>{item.icon}</span>}
                  <span>{item.label}</span>
                </Link>
              ) : (
                <span
                  className={cn(
                    'flex items-center gap-1',
                    item.current
                      ? 'text-gray-900 dark:text-white font-medium'
                      : 'text-gray-600 dark:text-gray-400'
                  )}
                  aria-current={item.current ? 'page' : undefined}
                >
                  {isFirst && showHomeIcon && !item.icon && (
                    <FiHome className="w-4 h-4" />
                  )}
                  {item.icon && <span>{item.icon}</span>}
                  <span>{item.label}</span>
                </span>
              )}

              {!isLast && (
                <span className="flex-shrink-0" aria-hidden="true">
                  {separator || <DefaultSeparator />}
                </span>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
};

Breadcrumb.displayName = 'Breadcrumb';
